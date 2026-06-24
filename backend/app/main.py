from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import engine
from backend.app import models
from backend.app.routers import router

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