from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.parser import extract_text
from app.skill_extractor import analyze_skills
from app.matcher import calculate_match_score
from app.ai_suggestions import generate_suggestions
import os
import shutil
from uuid import uuid4

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

workflow_sessions = {}


def _ensure_session(session_id: str | None = None) -> str:
    if session_id and session_id in workflow_sessions:
        return session_id

    new_session_id = session_id or str(uuid4())
    workflow_sessions[new_session_id] = {
        "user_id": 1,
        "jd_id": 1,
        "resume_version_id": None,
        "resume_text": None,
        "resume_file_path": None,
        "resume_file_name": None,
        "jd_text": None,
        "results": None,
    }
    return new_session_id


def _get_previous_jd_id(db: Session, user_id: int, current_jd_id: int) -> int:
    previous_version = (
        db.query(models.ResumeVersion)
        .filter(
            models.ResumeVersion.user_id == user_id,
            models.ResumeVersion.jd_id != current_jd_id,
        )
        .order_by(models.ResumeVersion.id.desc())
        .first()
    )
    return previous_version.jd_id if previous_version else current_jd_id


def _ensure_user_and_job_description(db: Session, user_id: int, jd_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        user = models.User(
            id=user_id,
            name="Default User",
            email=f"user{user_id}@example.com",
            password="password",
        )
        db.add(user)

    jd = db.query(models.JobDescription).filter(models.JobDescription.id == jd_id).first()
    if not jd:
        jd = models.JobDescription(
            id=jd_id,
            user_id=user.id,
            title="Default Job Description",
            description="Software engineering role",
        )
        db.add(jd)

    db.commit()
    return user, jd


def _extract_text_from_upload(file_path: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    return extract_text(file_path)


def _build_results_payload(resume_text: str, jd_text: str) -> dict:
    result = calculate_match_score(resume_text, jd_text)
    return {
        "score": result["final_score"],
        "matchedSkills": result["matched_skills"],
        "missingSkills": result["missing_skills"],
        "semanticScore": result["semantic_score"],
        "skillScore": result["skill_score"],
        "resumeSkills": result["resume_skills"],
        "jdSkills": result["jd_skills"],
        "recommendations": [],
        "ai_suggestions": [],
        "aiSuggestions": [],
    }


@router.post("/workflow/upload/resume")
async def workflow_upload_resume(
    file: UploadFile = File(...),
    session_id: str | None = None,
    db: Session = Depends(get_db),
):
    filename = file.filename or "resume.pdf"
    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(400, "Only PDF and DOCX files are allowed")

    session_key = _ensure_session(session_id)
    session_data = workflow_sessions[session_key]
    user_id = session_data["user_id"]
    jd_id = session_data["jd_id"]
    _ensure_user_and_job_description(db, user_id, jd_id)

    version_no = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id,
        models.ResumeVersion.jd_id == jd_id,
    ).count() + 1

    ext = os.path.splitext(filename)[1]
    saved_filename = f"resume_v{version_no}{ext}"
    user_folder = os.path.join(UPLOAD_DIR, f"user_{user_id}")
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        extracted_text = extract_text(file_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    resume_version = models.ResumeVersion(
        user_id=user_id,
        jd_id=jd_id,
        version_no=version_no,
        file_name=saved_filename,
        file_path=file_path,
        extracted_text=extracted_text,
    )
    db.add(resume_version)
    db.commit()
    db.refresh(resume_version)

    session_data["resume_version_id"] = resume_version.id
    session_data["resume_text"] = extracted_text
    session_data["resume_file_path"] = file_path
    session_data["resume_file_name"] = saved_filename

    return {
        "success": True,
        "session_id": session_key,
        "message": "Resume uploaded successfully",
        "resume_version_id": resume_version.id,
    }


@router.post("/workflow/upload/job-description/text")
def workflow_upload_job_description_text(
    text: str = Body(..., embed=True),
    session_id: str | None = None,
    db: Session = Depends(get_db),
):
    session_key = _ensure_session(session_id)
    session_data = workflow_sessions[session_key]
    user_id = session_data["user_id"]
    jd_id = session_data["jd_id"]
    _ensure_user_and_job_description(db, user_id, jd_id)

    jd = db.query(models.JobDescription).filter(models.JobDescription.id == jd_id).first()
    if not jd:
        jd = models.JobDescription(
            id=jd_id,
            user_id=user_id,
            title="Imported Job Description",
            description=text,
        )
        db.add(jd)
    else:
        jd.description = text
    db.commit()

    session_data["jd_text"] = text
    if session_data.get("resume_text"):
        session_data["results"] = _build_results_payload(session_data["resume_text"], text)

    return {
        "success": True,
        "session_id": session_key,
        "message": "Job description processed",
    }


@router.post("/workflow/upload/job-description")
async def workflow_upload_job_description(
    file: UploadFile = File(...),
    session_id: str | None = None,
    db: Session = Depends(get_db),
):
    filename = file.filename or "job-description.txt"
    if not filename.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(400, "Only PDF, DOCX, and TXT files are allowed")

    session_key = _ensure_session(session_id)
    session_data = workflow_sessions[session_key]
    user_id = session_data["user_id"]
    jd_id = session_data["jd_id"]
    _ensure_user_and_job_description(db, user_id, jd_id)

    user_folder = os.path.join(UPLOAD_DIR, f"user_{user_id}")
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, f"job_description{os.path.splitext(filename)[1]}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = _extract_text_from_upload(file_path, filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    jd = db.query(models.JobDescription).filter(models.JobDescription.id == jd_id).first()
    if not jd:
        jd = models.JobDescription(
            id=jd_id,
            user_id=user_id,
            title="Imported Job Description",
            description=text,
        )
        db.add(jd)
    else:
        jd.description = text
    db.commit()

    session_data["jd_text"] = text
    if session_data.get("resume_text"):
        session_data["results"] = _build_results_payload(session_data["resume_text"], text)

    return {
        "success": True,
        "session_id": session_key,
        "message": "Job description processed",
    }


@router.post("/workflow/save-resume")
def workflow_save_resume(payload: dict = Body(...), db: Session = Depends(get_db)):
    session_id = payload.get("session_id")
    target_jd = str(payload.get("target_jd", "current")).lower()

    if not session_id or session_id not in workflow_sessions:
        raise HTTPException(404, "No active session")

    session_data = workflow_sessions[session_id]
    user_id = session_data.get("user_id", 1)
    current_jd_id = session_data.get("jd_id", 1)

    target_jd_id = current_jd_id
    if target_jd == "previous":
        target_jd_id = _get_previous_jd_id(db, user_id, current_jd_id)

    _ensure_user_and_job_description(db, user_id, target_jd_id)

    resume_text = session_data.get("resume_text")
    file_path = session_data.get("resume_file_path")
    file_name = session_data.get("resume_file_name") or "resume.pdf"

    if not resume_text or not file_path or not os.path.exists(file_path):
        raise HTTPException(400, "No resume available to save yet")

    version_no = (
        db.query(models.ResumeVersion)
        .filter(
            models.ResumeVersion.user_id == user_id,
            models.ResumeVersion.jd_id == target_jd_id,
        )
        .count() + 1
    )

    saved_filename = os.path.basename(file_path)
    resume_version = models.ResumeVersion(
        user_id=user_id,
        jd_id=target_jd_id,
        version_no=version_no,
        file_name=saved_filename,
        file_path=file_path,
        extracted_text=resume_text,
    )
    db.add(resume_version)
    db.commit()
    db.refresh(resume_version)

    results = session_data.get("results")
    if results:
        match_result = models.MatchResult(
            resume_version_id=resume_version.id,
            score=results.get("score"),
            matched_skills=results.get("matchedSkills", []),
            missing_skills=results.get("missingSkills", []),
            ai_suggestions=[],
        )
        db.add(match_result)
        db.commit()

    return {
        "success": True,
        "message": f"Resume saved for {'previous' if target_jd == 'previous' else 'current'} job description",
        "resume_version_id": resume_version.id,
        "jd_id": target_jd_id,
    }


@router.get("/workflow/results")
def workflow_get_results(session_id: str | None = None, db: Session = Depends(get_db)):
    if not session_id or session_id not in workflow_sessions:
        return {"success": False, "message": "No active session"}

    session_data = workflow_sessions[session_id]
    if not session_data.get("results") and session_data.get("resume_text") and session_data.get("jd_text"):
        session_data["results"] = _build_results_payload(session_data["resume_text"], session_data["jd_text"])

    if not session_data.get("results"):
        return {"success": False, "message": "No analysis results available yet"}

    return {"success": True, **session_data["results"]}


@router.post("/upload/resume")
async def upload_resume(
    user_id: int,
    jd_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    filename = file.filename
    if not filename.endswith((".pdf", ".docx")):
        raise HTTPException(400, "Only PDF and DOCX files are allowed")

    user_folder = os.path.join(UPLOAD_DIR, f"user_{user_id}")
    os.makedirs(user_folder, exist_ok=True)

    version_no = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id,
        models.ResumeVersion.jd_id == jd_id
    ).count() + 1

    ext = os.path.splitext(filename)[1]
    saved_filename = f"resume_v{version_no}{ext}"
    file_path = os.path.join(user_folder, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        extracted_text = extract_text(file_path)
    except ValueError as e:
        raise HTTPException(400, str(e))

    resume_version = models.ResumeVersion(
        user_id=user_id,
        jd_id=jd_id,
        version_no=version_no,
        file_name=saved_filename,
        file_path=file_path,
        extracted_text=extracted_text
    )
    db.add(resume_version)
    db.commit()
    db.refresh(resume_version)

    return {
        "message": "Resume uploaded successfully",
        "resume_version_id": resume_version.id,
        "version_no": version_no,
        "file_name": saved_filename,
        "extracted_text_preview": extracted_text[:300] + "..."
    }


@router.get("/resume/history/{user_id}")
def get_resume_history(user_id: int, db: Session = Depends(get_db)):
    versions = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id
    ).order_by(models.ResumeVersion.version_no).all()

    if not versions:
        raise HTTPException(404, "No resumes found for this user")

    return [
        {
            "resume_version_id": v.id,
            "version_no": v.version_no,
            "file_name": v.file_name,
            "uploaded_at": v.uploaded_at
        }
        for v in versions
    ]


@router.post("/extract-skills")
def extract_skills_endpoint(
    resume_version_id: int,
    jd_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.id == resume_version_id
    ).first()
    if not resume:
        raise HTTPException(404, "Resume not found")

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == jd_id
    ).first()
    if not jd:
        raise HTTPException(404, "Job description not found")

    result = analyze_skills(resume.extracted_text, jd.description)

    return {
        "resume_version_id": resume_version_id,
        "jd_id": jd_id,
        "resume_skills": result["resume_skills"],
        "jd_skills": result["jd_skills"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "match_percentage": round(
            len(result["matched_skills"]) / len(result["jd_skills"]) * 100
            if result["jd_skills"] else 0, 2
        )
    }


@router.post("/match")
def match_resume(
    resume_version_id: int,
    jd_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.id == resume_version_id
    ).first()
    if not resume:
        raise HTTPException(404, "Resume not found")

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == jd_id
    ).first()
    if not jd:
        raise HTTPException(404, "Job description not found")

    result = calculate_match_score(resume.extracted_text, jd.description)

    existing = db.query(models.MatchResult).filter(
        models.MatchResult.resume_version_id == resume_version_id
    ).first()

    if existing:
        existing.score = result["final_score"]
        existing.matched_skills = result["matched_skills"]
        existing.missing_skills = result["missing_skills"]
        existing.ai_suggestions = []
        db.commit()
    else:
        match_result = models.MatchResult(
            resume_version_id=resume_version_id,
            score=result["final_score"],
            matched_skills=result["matched_skills"],
            missing_skills=result["missing_skills"],
            ai_suggestions=[]
        )
        db.add(match_result)
        db.commit()

    return {
        "resume_version_id": resume_version_id,
        "jd_id": jd_id,
        "final_score": result["final_score"],
        "semantic_score": result["semantic_score"],
        "skill_score": result["skill_score"],
        "experience_score": result["experience_score"],
        "education_score": result["education_score"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "resume_skills": result["resume_skills"],
        "jd_skills": result["jd_skills"]
    }


@router.get("/results/{resume_version_id}")
def get_match_results(resume_version_id: int, db: Session = Depends(get_db)):
    result = db.query(models.MatchResult).filter(
        models.MatchResult.resume_version_id == resume_version_id
    ).first()
    if not result:
        raise HTTPException(404, "No match results found")

    return {
        "resume_version_id": resume_version_id,
        "score": result.score,
        "matched_skills": result.matched_skills,
        "missing_skills": result.missing_skills,
        "ai_suggestions": result.ai_suggestions,
        "created_at": result.created_at
    }


@router.post("/analyze")
async def analyze_resume(
    user_id: int,
    jd_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith((".pdf", ".docx")):
        raise HTTPException(400, "Only PDF and DOCX allowed")

    user_folder = os.path.join(UPLOAD_DIR, f"user_{user_id}")
    os.makedirs(user_folder, exist_ok=True)

    version_no = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id,
        models.ResumeVersion.jd_id == jd_id
    ).count() + 1

    ext = os.path.splitext(file.filename)[1]
    saved_filename = f"resume_v{version_no}{ext}"
    file_path = os.path.join(user_folder, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        extracted_text = extract_text(file_path)
    except ValueError as e:
        raise HTTPException(400, str(e))

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == jd_id
    ).first()
    if not jd:
        raise HTTPException(404, "Job description not found")

    resume_version = models.ResumeVersion(
        user_id=user_id,
        jd_id=jd_id,
        version_no=version_no,
        file_name=saved_filename,
        file_path=file_path,
        extracted_text=extracted_text
    )
    db.add(resume_version)
    db.commit()
    db.refresh(resume_version)

    result = calculate_match_score(extracted_text, jd.description)

    match_result = models.MatchResult(
        resume_version_id=resume_version.id,
        score=result["final_score"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        ai_suggestions=[]
    )
    db.add(match_result)
    db.commit()

    return {
        "message": "Analysis complete",
        "resume_version_id": resume_version.id,
        "version_no": version_no,
        "final_score": result["final_score"],
        "semantic_score": result["semantic_score"],
        "skill_score": result["skill_score"],
        "experience_score": result["experience_score"],
        "education_score": result["education_score"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "resume_skills": result["resume_skills"],
        "jd_skills": result["jd_skills"],
        "extracted_text_preview": extracted_text[:300] + "..."
    }


@router.get("/version-history/{user_id}/{jd_id}")
def get_version_history(
    user_id: int,
    jd_id: int,
    db: Session = Depends(get_db)
):
    versions = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id,
        models.ResumeVersion.jd_id == jd_id
    ).order_by(models.ResumeVersion.version_no).all()

    if not versions:
        raise HTTPException(404, "No versions found")

    result = []
    for v in versions:
        match = db.query(models.MatchResult).filter(
            models.MatchResult.resume_version_id == v.id
        ).first()

        result.append({
            "version_no": v.version_no,
            "file_name": v.file_name,
            "uploaded_at": v.uploaded_at,
            "score": match.score if match else None,
            "matched_skills": match.matched_skills if match else [],
            "missing_skills": match.missing_skills if match else []
        })

    return {
        "user_id": user_id,
        "jd_id": jd_id,
        "total_versions": len(result),
        "versions": result
    }


@router.get("/version-compare/{user_id}/{jd_id}")
def compare_versions(
    user_id: int,
    jd_id: int,
    db: Session = Depends(get_db)
):
    versions = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id,
        models.ResumeVersion.jd_id == jd_id
    ).order_by(models.ResumeVersion.version_no).all()

    if len(versions) < 2:
        raise HTTPException(400, "Need at least 2 versions to compare")

    scores = []
    for v in versions:
        match = db.query(models.MatchResult).filter(
            models.MatchResult.resume_version_id == v.id
        ).first()
        if match:
            scores.append({
                "version_no": v.version_no,
                "score": match.score,
                "matched_skills": match.matched_skills,
                "missing_skills": match.missing_skills,
                "uploaded_at": v.uploaded_at
            })

    if len(scores) < 2:
        raise HTTPException(400, "Need at least 2 scored versions to compare")

    latest = scores[-1]
    previous = scores[-2]
    improvement = round(latest["score"] - previous["score"], 2)

    new_skills = [
        s for s in previous["missing_skills"]
        if s not in latest["missing_skills"]
    ]

    return {
        "previous_version": previous["version_no"],
        "previous_score": previous["score"],
        "latest_version": latest["version_no"],
        "latest_score": latest["score"],
        "improvement": improvement,
        "improved": improvement > 0,
        "newly_added_skills": new_skills,
        "still_missing_skills": latest["missing_skills"],
        "all_versions": scores
    }


@router.post("/suggestions/{resume_version_id}")
def get_ai_suggestions(
    resume_version_id: int,
    db: Session = Depends(get_db)
):
    match_result = db.query(models.MatchResult).filter(
        models.MatchResult.resume_version_id == resume_version_id
    ).first()

    if not match_result:
        raise HTTPException(404, "No match result found. Run /analyze first.")

    resume = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.id == resume_version_id
    ).first()

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == resume.jd_id
    ).first()

    suggestions = generate_suggestions(
        matched_skills=match_result.matched_skills or [],
        missing_skills=match_result.missing_skills or [],
        score=match_result.score,
        jd_title=jd.title if jd else "the target role"
    )

    match_result.ai_suggestions = suggestions
    db.commit()

    return {
        "resume_version_id": resume_version_id,
        "score": match_result.score,
        "matched_skills": match_result.matched_skills,
        "missing_skills": match_result.missing_skills,
        "ai_suggestions": suggestions
    }


@router.get("/versions-scored/{user_id}/{jd_id}")
def get_all_versions_scored(
    user_id: int,
    jd_id: int,
    db: Session = Depends(get_db)
):
    versions = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id,
        models.ResumeVersion.jd_id == jd_id
    ).order_by(models.ResumeVersion.version_no).all()

    if not versions:
        raise HTTPException(404, "No versions found")

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == jd_id
    ).first()

    scored_versions = []
    for v in versions:
        match = db.query(models.MatchResult).filter(
            models.MatchResult.resume_version_id == v.id
        ).first()

        scored_versions.append({
            "version_no": v.version_no,
            "file_name": v.file_name,
            "uploaded_at": v.uploaded_at,
            "score": match.score if match else None,
            "matched_skills": match.matched_skills if match else [],
            "missing_skills": match.missing_skills if match else [],
            "ai_suggestions": match.ai_suggestions if match else []
        })

    improvements = []
    for i in range(1, len(scored_versions)):
        current = scored_versions[i]
        previous = scored_versions[i - 1]

        if current["score"] and previous["score"]:
            diff = round(current["score"] - previous["score"], 2)
            newly_added = [
                s for s in previous["missing_skills"]
                if s not in current["missing_skills"]
            ]
            improvements.append({
                "from_version": previous["version_no"],
                "to_version": current["version_no"],
                "score_change": diff,
                "improved": diff > 0,
                "newly_added_skills": newly_added,
                "still_missing": current["missing_skills"]
            })

    return {
        "user_id": user_id,
        "jd_id": jd_id,
        "jd_title": jd.title if jd else "Unknown",
        "total_versions": len(scored_versions),
        "versions": scored_versions,
        "improvements": improvements,
        "best_version": max(
            scored_versions,
            key=lambda x: x["score"] or 0
        )
    }