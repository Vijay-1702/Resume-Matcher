from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app import models
from backend.app.parser import extract_text
from backend.app.skill_extractor import analyze_skills
from backend.app.matcher import calculate_match_score
import os
import shutil

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
