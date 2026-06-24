from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine
from backend import models
from backend.routers import router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Resume Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Resume Matcher API is running"}

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