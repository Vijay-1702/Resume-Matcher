from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(255), nullable=False)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resume_versions  = relationship("ResumeVersion", back_populates="user")
    job_descriptions = relationship("JobDescription", back_populates="user")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    title       = Column(String(255))
    description = Column(Text, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    user            = relationship("User", back_populates="job_descriptions")
    resume_versions = relationship("ResumeVersion", back_populates="job_description")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    jd_id          = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    version_no     = Column(Integer, nullable=False, default=1)
    file_name      = Column(String(255), nullable=False)
    file_path      = Column(String(500), nullable=False)
    extracted_text = Column(Text)
    uploaded_at    = Column(DateTime(timezone=True), server_default=func.now())

    user            = relationship("User", back_populates="resume_versions")
    job_description = relationship("JobDescription", back_populates="resume_versions")
    match_result    = relationship("MatchResult", back_populates="resume_version", uselist=False)


class MatchResult(Base):
    __tablename__ = "match_results"

    id                = Column(Integer, primary_key=True, index=True)
    resume_version_id = Column(Integer, ForeignKey("resume_versions.id"), nullable=False)
    score             = Column(Float)
    matched_skills    = Column(JSON)
    missing_skills    = Column(JSON)
    ai_suggestions    = Column(JSON)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    resume_version = relationship("ResumeVersion", back_populates="match_result")