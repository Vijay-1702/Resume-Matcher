from fastapi import FastAPI
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from services.pdf_reader import extract_pdf_text
from services.docx_reader import extract_docx_text
import os

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    try:
        file_path = os.path.join(
            UPLOAD_DIR,
            file.filename
        )

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        extracted_text = ""

        if file.filename.endswith(".pdf"):
            extracted_text = extract_pdf_text(
                file_path
            )

        elif file.filename.endswith(".docx"):
            extracted_text = extract_docx_text(
                file_path
            )

        return {
            "success": True,
            "message": "Resume uploaded successfully",
            "filename": file.filename,
            "text": extracted_text[:1000]
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error uploading resume: {str(e)}"
        }


@app.post("/upload/job-description")
async def upload_jd(
    file: UploadFile = File(...)
):
    try:
        file_path = os.path.join(
            UPLOAD_DIR,
            file.filename
        )

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        extracted_text = ""

        if file.filename.endswith(".pdf"):
            extracted_text = extract_pdf_text(
                file_path
            )

        elif file.filename.endswith(".docx"):
            extracted_text = extract_docx_text(
                file_path
            )

        return {
            "success": True,
            "message": "Job description uploaded successfully",
            "filename": file.filename,
            "text": extracted_text[:1000]
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error uploading job description: {str(e)}"
        }


@app.post("/upload/job-description/text")
async def upload_jd_text(
    jd_input: JDTextInput
):
    try:
        if not jd_input.text or not jd_input.text.strip():
            return {
                "success": False,
                "message": "Job description text cannot be empty"
            }

        # Save text JD to a file for consistency
        filename = "job_description.txt"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(jd_input.text)
        
        return {
            "success": True,
            "message": "Job description uploaded successfully",
            "filename": filename,
            "character_count": len(jd_input.text)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error uploading job description: {str(e)}"
        }