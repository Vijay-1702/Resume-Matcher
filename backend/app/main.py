from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

try:
    from .database import engine
    from . import models
    from .routers import router
except ImportError:  # pragma: no cover
    from app.database import engine
    from app import models
    from app.routers import router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Resume Matcher API")

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Resume Matcher API is running",
    }