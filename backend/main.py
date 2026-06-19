from fastapi import FastAPI
from fastapi import UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os

app = FastAPI()

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


class JDTextInput(BaseModel):
    text: str


@app.get("/")
def home():
    return {"message": "Resume Matcher API"}


@app.post("/upload/resume")
async def upload_resume(
    file: UploadFile = File(...)
):
    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "message": "Resume uploaded",
        "filename": file.filename
    }


@app.post("/upload/job-description")
async def upload_jd(
    file: UploadFile = File(...)
):
    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "message": "JD uploaded",
        "filename": file.filename
    }


@app.post("/upload/job-description/text")
async def upload_jd_text(
    jd_input: JDTextInput
):
    # Save text JD to a file for consistency
    filename = "job_description.txt"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(jd_input.text)
    
    return {
        "message": "JD text uploaded",
        "filename": filename,
        "character_count": len(jd_input.text)
    }