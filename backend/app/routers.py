from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app import models
from backend.app.parser import extract_text
from backend.app.skill_extractor import analyze_skills
from backend.app.matcher import calculate_match_score
import os
import shutil
from pydantic import BaseModel
import uuid
from datetime import datetime

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

workflow_sessions = {}


class JDTextInput(BaseModel):
    text: str


@router.post("/upload/resume")
async def upload_resume(
    user_id: int,
    jd_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    filename = file.filename
    if not filename.endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are allowed"
        )

    user_folder = os.path.join(UPLOAD_DIR, f"user_{user_id}")
    os.makedirs(user_folder, exist_ok=True)

    existing_versions = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id,
        models.ResumeVersion.jd_id == jd_id
    ).count()
    version_no = existing_versions + 1

    file_extension = os.path.splitext(filename)[1]
    saved_filename = f"resume_v{version_no}{file_extension}"
    file_path = os.path.join(user_folder, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        extracted_text = extract_text(file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
        raise HTTPException(status_code=404, detail="No resumes found for this user")

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
        raise HTTPException(status_code=404, detail="Resume not found")

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == jd_id
    ).first()

    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    result = analyze_skills(resume.extracted_text, jd.description)

    match_percentage = round(
        len(result["matched_skills"]) / len(result["jd_skills"]) * 100
        if result["jd_skills"] else 0, 2
    )

    return {
        "resume_version_id": resume_version_id,
        "jd_id": jd_id,
        "resume_skills": result["resume_skills"],
        "jd_skills": result["jd_skills"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "match_percentage": match_percentage
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
        raise HTTPException(status_code=404, detail="Resume not found")

    jd = db.query(models.JobDescription).filter(
        models.JobDescription.id == jd_id
    ).first()

    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

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
        db.refresh(existing)
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
        raise HTTPException(status_code=404, detail="No match results found")

    return {
        "resume_version_id": resume_version_id,
        "score": result.score,
        "matched_skills": result.matched_skills,
        "missing_skills": result.missing_skills,
        "ai_suggestions": result.ai_suggestions,
        "created_at": result.created_at
    }


@router.post("/workflow/upload/resume")
async def workflow_upload_resume(file: UploadFile = File(...)):
    filename = file.filename
    if not filename.endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are allowed"
        )

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_DIR, f"session_{session_id}")
    os.makedirs(session_folder, exist_ok=True)

    file_path = os.path.join(session_folder, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        resume_text = extract_text(file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    workflow_sessions[session_id] = {
        "resume_text": resume_text,
        "resume_file": filename,
        "created_at": datetime.now()
    }

    return {
        "success": True,
        "message": "Resume uploaded successfully",
        "session_id": session_id,
        "resume_preview": resume_text[:200] + "..."
    }


@router.post("/workflow/upload/job-description/text")
async def workflow_upload_jd_text(session_id: str, jd_input: JDTextInput):
    if session_id not in workflow_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not jd_input.text or not jd_input.text.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty")

    session = workflow_sessions[session_id]
    resume_text = session.get("resume_text")

    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume not found in session")

    jd_text = jd_input.text
    skill_result = analyze_skills(resume_text, jd_text)
    match_result = calculate_match_score(resume_text, jd_text)

    session.update({
        "jd_text": jd_text,
        "skill_result": skill_result,
        "match_result": match_result
    })

    return {
        "success": True,
        "message": "Job description processed",
        "session_id": session_id
    }


@router.post("/workflow/upload/job-description")
async def workflow_upload_jd_file(session_id: str, file: UploadFile = File(...)):
    if session_id not in workflow_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    filename = file.filename
    if not filename.endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, and TXT files are allowed"
        )

    session = workflow_sessions[session_id]
    session_folder = os.path.join(UPLOAD_DIR, f"session_{session_id}")
    os.makedirs(session_folder, exist_ok=True)

    file_path = os.path.join(session_folder, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        jd_text = extract_text(file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    resume_text = session.get("resume_text")

    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume not found in session")

    skill_result = analyze_skills(resume_text, jd_text)
    match_result = calculate_match_score(resume_text, jd_text)

    session.update({
        "jd_text": jd_text,
        "jd_file": filename,
        "skill_result": skill_result,
        "match_result": match_result
    })

    return {
        "success": True,
        "message": "Job description processed",
        "session_id": session_id
    }


@router.get("/workflow/results")
async def workflow_get_results(session_id: str):
    if session_id not in workflow_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = workflow_sessions[session_id]
    match_result = session.get("match_result")
    skill_result = session.get("skill_result")

    if not match_result or not skill_result:
        raise HTTPException(status_code=400, detail="Results not ready. Please upload job description first.")

    return {
        "success": True,
        "session_id": session_id,
        "score": round(match_result.get("final_score", 0), 2),
        "matchedSkills": match_result.get("matched_skills", []),
        "missingSkills": match_result.get("missing_skills", []),
        "semanticScore": round(match_result.get("semantic_score", 0), 2),
        "skillScore": round(match_result.get("skill_score", 0), 2),
        "resumeSkills": skill_result.get("resume_skills", []),
        "jdSkills": skill_result.get("jd_skills", [])
    }
