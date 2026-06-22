from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.parser import extract_text
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
    # 1. Validate file type
    filename = file.filename
    if not filename.endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are allowed"
        )

    # 2. Create user folder
    user_folder = os.path.join(UPLOAD_DIR, f"user_{user_id}")
    os.makedirs(user_folder, exist_ok=True)

    # 3. Get version number
    existing_versions = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.user_id == user_id,
        models.ResumeVersion.jd_id == jd_id
    ).count()
    version_no = existing_versions + 1

    # 4. Save file to disk
    file_extension = os.path.splitext(filename)[1]
    saved_filename = f"resume_v{version_no}{file_extension}"
    file_path = os.path.join(user_folder, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 5. Extract text
    try:
        extracted_text = extract_text(file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 6. Save to database
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