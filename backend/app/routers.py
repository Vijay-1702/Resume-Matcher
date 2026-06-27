from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.parser import extract_text
from app.skill_extractor import analyze_skills
from app.matcher import calculate_match_score
import os
import shutil
from app.ai_suggestions import generate_suggestions

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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

    still_missing = latest["missing_skills"]

    return {
        "previous_version": previous["version_no"],
        "previous_score": previous["score"],
        "latest_version": latest["version_no"],
        "latest_score": latest["score"],
        "improvement": improvement,
        "improved": improvement > 0,
        "newly_added_skills": new_skills,
        "still_missing_skills": still_missing,
        "all_versions": scores
    }

@router.post("/suggestions/{resume_version_id}")
def get_ai_suggestions(
    resume_version_id: int,
    db: Session = Depends(get_db)
):
    # 1. Get match result
    match_result = db.query(models.MatchResult).filter(
        models.MatchResult.resume_version_id == resume_version_id
    ).first()

    if not match_result:
        raise HTTPException(404, "No match result found. Run /analyze first.")

    # 2. Get JD title
    resume = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.id == resume_version_id
    ).first()

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == resume.jd_id
    ).first()

    # 3. Generate suggestions
    suggestions = generate_suggestions(
        matched_skills=match_result.matched_skills or [],
        missing_skills=match_result.missing_skills or [],
        score=match_result.score,
        jd_title=jd.title if jd else "the target role"
    )

    # 4. Save suggestions to DB
    match_result.ai_suggestions = suggestions
    db.commit()

    return {
        "resume_version_id": resume_version_id,
        "score": match_result.score,
        "matched_skills": match_result.matched_skills,
        "missing_skills": match_result.missing_skills,
        "ai_suggestions": suggestions
    }