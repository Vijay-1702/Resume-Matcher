from fastapi import FastAPI
from fastapi import UploadFile, File
import os

app = FastAPI()

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


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