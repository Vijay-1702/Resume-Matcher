from datetime import datetime
<<<<<<< HEAD
import hashlib
import hmac
import os
import re
import secrets
import shutil
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app import models
from backend.app.parser import extract_text
from backend.app.matcher import analyze_skills, calculate_match_score
from backend.app.ai_suggestions import generate_suggestions
=======
import os
import shutil
from app.ai_suggestions import generate_suggestions

>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

workflow_sessions = {}


class JDTextInput(BaseModel):
    text: str


<<<<<<< HEAD
class SaveResumeInput(BaseModel):
    session_id: str
    user_id: int | None = None
    # 'existing' or 'new'
    target_type: str = "existing"
    jd_id: int | None = None
    new_jd_title: str | None = None
    # if provided, will use session jd_text unless overridden
    new_jd_description: str | None = None


class AuthInput(BaseModel):
    username: str
    password: str


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,}$")


def _normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not normalized:
        raise HTTPException(400, "Username is required")
    return normalized


def _validate_password(password: str) -> None:
    if not PASSWORD_PATTERN.match(password):
        raise HTTPException(
            400,
            "Password must be at least 8 characters and include one uppercase letter, one lowercase letter, and one special character.",
        )


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def _verify_password(password: str, stored_password: str) -> bool:
    try:
        algorithm, salt, expected_digest = stored_password.split("$", 2)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hmac.compare_digest(digest.hex(), expected_digest)


def _auth_response(user: models.User, message: str) -> dict:
    return {
        "success": True,
        "message": message,
        "user": {
            "id": user.id,
            "username": user.name,
        },
    }


def _validate_extension(filename: str, allowed_extensions: tuple[str, ...], label: str) -> None:
    if not filename.lower().endswith(allowed_extensions):
        allowed = ", ".join(ext.upper().replace(".", "") for ext in allowed_extensions)
        raise HTTPException(400, f"Only {allowed} files are allowed for {label}")


def _save_upload(file: UploadFile, session_id: str, prefix: str) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    session_folder = os.path.join(UPLOAD_DIR, "workflow", session_id)
    os.makedirs(session_folder, exist_ok=True)
    file_path = os.path.join(session_folder, f"{prefix}{ext}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path


def _build_workflow_results(session: dict) -> dict:
    if not session.get("resume_text"):
        raise HTTPException(400, "Resume has not been uploaded for this session")

    if not session.get("jd_text"):
        raise HTTPException(400, "Job description has not been uploaded for this session")

    result = calculate_match_score(session["resume_text"], session["jd_text"])
    suggestions = generate_suggestions(
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        score=result["final_score"],
    )

    return {
        "success": True,
        "session_id": session["session_id"],
        "score": result["final_score"],
        "semanticScore": result["semantic_score"],
        "skillScore": result["skill_score"],
        "experienceScore": result["experience_score"],
        "educationScore": result["education_score"],
        "matchedSkills": result["matched_skills"],
        "missingSkills": result["missing_skills"],
        "resumeSkills": result["resume_skills"],
        "jdSkills": result["jd_skills"],
        "recommendations": suggestions,
        "ai_suggestions": suggestions,
        "aiSuggestions": suggestions,
    }


@router.post("/auth/signup")
def signup(payload: AuthInput, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    _validate_password(payload.password)

    existing_user = db.query(models.User).filter(models.User.name == username).first()
    if existing_user:
        raise HTTPException(409, "Username is already taken")

    user = models.User(
        name=username,
        email=f"{username}@local.resume-matcher",
        password=_hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username is already taken")
    db.refresh(user)

    return _auth_response(user, "Sign up successful")


@router.post("/auth/signin")
def signin(payload: AuthInput, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    user = db.query(models.User).filter(models.User.name == username).first()

    if not user or not _verify_password(payload.password, user.password):
        raise HTTPException(401, "Invalid username or password")

    return _auth_response(user, "Sign in successful")


@router.post("/workflow/upload/resume")
async def workflow_upload_resume(file: UploadFile = File(...)):
    _validate_extension(file.filename or "", (".pdf", ".docx"), "resumes")

    session_id = str(uuid4())
    file_path = _save_upload(file, session_id, "resume")

    try:
        extracted_text = extract_text(file_path)
    except ValueError as e:
        raise HTTPException(400, str(e))

    workflow_sessions[session_id] = {
        "session_id": session_id,
        "resume_filename": file.filename,
        "resume_path": file_path,
        "resume_text": extracted_text,
        "created_at": datetime.utcnow().isoformat(),
    }

    return {
        "success": True,
        "message": "Resume uploaded successfully",
        "session_id": session_id,
        "extracted_text_preview": extracted_text[:300],
    }


@router.post("/workflow/upload/job-description/text")
async def workflow_upload_jd_text(session_id: str, payload: JDTextInput):
    session = workflow_sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Workflow session not found")

    jd_text = payload.text.strip()
    if not jd_text:
        raise HTTPException(400, "Job description text is required")

    session["jd_text"] = jd_text
    session["jd_filename"] = "pasted-job-description.txt"
    session["results"] = _build_workflow_results(session)

    return {
        "success": True,
        "message": "Job description processed successfully",
        "session_id": session_id,
    }


@router.post("/workflow/upload/job-description")
async def workflow_upload_jd_file(session_id: str, file: UploadFile = File(...)):
    session = workflow_sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Workflow session not found")

    _validate_extension(file.filename or "", (".pdf", ".docx", ".txt"), "job descriptions")
    file_path = _save_upload(file, session_id, "job_description")

    try:
        extracted_text = extract_text(file_path)
    except ValueError as e:
        raise HTTPException(400, str(e))

    session["jd_filename"] = file.filename
    session["jd_path"] = file_path
    session["jd_text"] = extracted_text
    session["results"] = _build_workflow_results(session)

    return {
        "success": True,
        "message": "Job description processed successfully",
        "session_id": session_id,
    }


@router.get("/workflow/results")
def workflow_results(session_id: str):
    session = workflow_sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Workflow session not found")

    if "results" not in session:
        session["results"] = _build_workflow_results(session)

    return session["results"]


@router.post("/workflow/save-resume")
def workflow_save_resume(payload: SaveResumeInput, db: Session = Depends(get_db)):
    session = workflow_sessions.get(payload.session_id)
    if not session:
        raise HTTPException(404, "Workflow session not found")

    # Require user_id to associate saved resume
    if not payload.user_id:
        raise HTTPException(400, "user_id is required to save resume")

    # Determine JD to save under
    if payload.target_type == "existing":
        if not payload.jd_id:
            raise HTTPException(400, "jd_id is required for existing target")
        jd = db.query(models.JobDescription).filter(
            models.JobDescription.id == payload.jd_id,
            models.JobDescription.user_id == payload.user_id
        ).first()
        if not jd:
            raise HTTPException(404, "Job description not found")
    else:
        # create new JD using provided description or session jd_text
        jd_text = payload.new_jd_description or session.get("jd_text")
        if not jd_text:
            raise HTTPException(400, "No job description available to create new JD")
        jd = models.JobDescription(
            user_id=payload.user_id,
            title=payload.new_jd_title or "Untitled JD",
            description=jd_text
        )
        db.add(jd)
        db.commit()
        db.refresh(jd)

    # Save resume file from session into user folder and create ResumeVersion
    # session contains resume_path saved under uploads/workflow/<session>
    src_path = session.get("resume_path")
    if not src_path or not os.path.exists(src_path):
        raise HTTPException(400, "Resume file not available to save")

    user_folder = os.path.join(UPLOAD_DIR, f"user_{payload.user_id}")
    os.makedirs(user_folder, exist_ok=True)

    version_no = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == payload.user_id,
        models.ResumeVersion.jd_id == jd.id
    ).count() + 1

    ext = os.path.splitext(session.get("resume_filename", "resume"))[1] or ".pdf"
    saved_filename = f"resume_v{version_no}{ext}"
    dest_path = os.path.join(user_folder, saved_filename)
    shutil.copyfile(src_path, dest_path)

    extracted_text = session.get("resume_text")

    resume_version = models.ResumeVersion(
        user_id=payload.user_id,
        jd_id=jd.id,
        version_no=version_no,
        file_name=saved_filename,
        file_path=dest_path,
        extracted_text=extracted_text
    )
    db.add(resume_version)
    db.commit()
    db.refresh(resume_version)

    # run matching immediately and store result
    result = calculate_match_score(extracted_text or "", jd.description)
    match_result = models.MatchResult(
        resume_version_id=resume_version.id,
        score=result.get("final_score"),
        matched_skills=result.get("matched_skills"),
        missing_skills=result.get("missing_skills"),
        ai_suggestions=[]
    )
    db.add(match_result)
    db.commit()

    session["saved"] = True
    session["save_target"] = jd.id
    session["saved_at"] = datetime.utcnow().isoformat()

    return {
        "success": True,
        "message": "Resume saved to job description",
        "session_id": payload.session_id,
        "jd_id": jd.id,
        "resume_version_id": resume_version.id,
        "version_no": version_no,
        "score": result.get("final_score")
    }


=======
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
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
<<<<<<< HEAD
        "experience_score": result["experience_score"],
        "education_score": result["education_score"],
=======
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
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
<<<<<<< HEAD
        "experience_score": result["experience_score"],
        "education_score": result["education_score"],
=======
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
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
<<<<<<< HEAD
            "resume_version_id": v.id,
=======
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
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

<<<<<<< HEAD
=======
    still_missing = latest["missing_skills"]

>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
    return {
        "previous_version": previous["version_no"],
        "previous_score": previous["score"],
        "latest_version": latest["version_no"],
        "latest_score": latest["score"],
        "improvement": improvement,
        "improved": improvement > 0,
        "newly_added_skills": new_skills,
<<<<<<< HEAD
        "still_missing_skills": latest["missing_skills"],
        "all_versions": scores
    }


=======
        "still_missing_skills": still_missing,
        "all_versions": scores
    }

>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
@router.post("/suggestions/{resume_version_id}")
def get_ai_suggestions(
    resume_version_id: int,
    db: Session = Depends(get_db)
):
<<<<<<< HEAD
=======
    # 1. Get match result
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
    match_result = db.query(models.MatchResult).filter(
        models.MatchResult.resume_version_id == resume_version_id
    ).first()

    if not match_result:
        raise HTTPException(404, "No match result found. Run /analyze first.")

<<<<<<< HEAD
=======
    # 2. Get JD title
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
    resume = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.id == resume_version_id
    ).first()

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == resume.jd_id
    ).first()

<<<<<<< HEAD
=======
    # 3. Generate suggestions
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
    suggestions = generate_suggestions(
        matched_skills=match_result.matched_skills or [],
        missing_skills=match_result.missing_skills or [],
        score=match_result.score,
        jd_title=jd.title if jd else "the target role"
    )

<<<<<<< HEAD
=======
    # 4. Save suggestions to DB
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
    match_result.ai_suggestions = suggestions
    db.commit()

    return {
        "resume_version_id": resume_version_id,
        "score": match_result.score,
        "matched_skills": match_result.matched_skills,
        "missing_skills": match_result.missing_skills,
        "ai_suggestions": suggestions
    }
<<<<<<< HEAD


@router.get("/job-descriptions/{user_id}")
def list_job_descriptions(user_id: int, db: Session = Depends(get_db)):
    jds = db.query(models.JobDescription).filter(models.JobDescription.user_id == user_id).order_by(models.JobDescription.created_at.desc()).all()
    return [
        {
            "id": jd.id,
            "title": jd.title,
            "description_preview": (jd.description or "")[:300],
            "created_at": jd.created_at
        }
        for jd in jds
    ]


@router.post("/job-descriptions")
def create_job_description(payload: JDTextInput, user_id: int, title: str | None = None, db: Session = Depends(get_db)):
    jd = models.JobDescription(
        user_id=user_id,
        title=title or "Untitled JD",
        description=payload.text
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return {"id": jd.id, "title": jd.title}


@router.post("/compare-resumes")
class CompareInput(BaseModel):
    resume_a_id: int
    resume_b_id: int


@router.post("/compare-resumes")
def compare_two_resumes(payload: CompareInput, db: Session = Depends(get_db)):
    resume_a_id = payload.resume_a_id
    resume_b_id = payload.resume_b_id
    a = db.query(models.ResumeVersion).filter(models.ResumeVersion.id == resume_a_id).first()
    b = db.query(models.ResumeVersion).filter(models.ResumeVersion.id == resume_b_id).first()
    if not a or not b:
        raise HTTPException(404, "One or both resume versions not found")

    a_text = a.extracted_text or ""
    b_text = b.extracted_text or ""

    # attempt to use google generative ai for a richer comparison if available
    summary = None
    try:
        import google.generativeai as genai
        # Expect the API key to be set in env GOOGLE_API_KEY
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        prompt = (
            "Compare the two resume texts. List what improved in the second resume compared to the first, "
            "and list what is still lacking. Provide a short bullet summary.\n\nFirst Resume:\n" + a_text[:4000] + "\n\nSecond Resume:\n" + b_text[:4000]
        )
        resp = genai.text.generate(model="gemini-pro", prompt=prompt, max_output_tokens=512)
        summary = resp.text
    except Exception:
        # fallback: simple diff using skills from match results
        match_a = db.query(models.MatchResult).filter(models.MatchResult.resume_version_id == a.id).first()
        match_b = db.query(models.MatchResult).filter(models.MatchResult.resume_version_id == b.id).first()
        a_missing = set(match_a.missing_skills or []) if match_a else set()
        b_missing = set(match_b.missing_skills or []) if match_b else set()
        newly_added = sorted(list(a_missing - b_missing))
        still_missing = sorted(list(b_missing))
        summary = {
            "previous_score": match_a.score if match_a else None,
            "latest_score": match_b.score if match_b else None,
            "newly_added_skills": newly_added,
            "still_missing_skills": still_missing,
        }

    return {"comparison": summary}
=======
>>>>>>> eaa6d34 ( UI changes and Folder correction and Routing correction (#14))
