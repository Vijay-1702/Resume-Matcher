import spacy

nlp = spacy.load("en_core_web_sm")

SKILL_LIST = [
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "r", "matlab", "scala", "php", "ruby",

    # Web Frameworks
    "fastapi", "flask", "django", "react", "angular", "vue", "node.js",
    "express", "spring boot", "next.js",

    # Databases
    "postgresql", "mysql", "mongodb", "redis", "sqlite", "cassandra",
    "elasticsearch", "firebase",

    # ML / AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "huggingface",
    "transformers", "bert", "gpt", "llm", "rag", "fine-tuning",
    "xgboost", "lightgbm", "pandas", "numpy", "matplotlib", "seaborn",

    # MLOps / Cloud
    "docker", "kubernetes", "aws", "azure", "gcp", "mlflow", "airflow",
    "ci/cd", "jenkins", "terraform", "git", "github", "linux",

    # Data Engineering
    "spark", "hadoop", "kafka", "dbt", "etl", "sql",
    "data pipeline", "feature engineering",

    # Other
    "rest api", "graphql", "microservices", "agile", "scrum",
    "object detection", "faiss", "langchain", "openai", "gemini",
    "prompt engineering", "shap", "qlora", "smote", "mlflow",
    "vector embeddings", "sentence transformers", "spacy"
]


def extract_skills(text: str) -> list:
    """Extract skills from text by matching against skill list"""
    text_lower = text.lower()
    found_skills = []

    for skill in SKILL_LIST:
        if skill.lower() in text_lower:
            found_skills.append(skill)

    return list(set(found_skills))


def get_missing_skills(resume_skills: list, jd_skills: list) -> list:
    """Find skills required in JD but missing from resume"""
    resume_lower = [s.lower() for s in resume_skills]
    missing = [s for s in jd_skills if s.lower() not in resume_lower]
    return missing


def analyze_skills(resume_text: str, jd_text: str) -> dict:
    """Compare resume skills vs JD skills"""
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)
    matched_skills = [s for s in resume_skills if s in jd_skills]
    missing_skills = get_missing_skills(resume_skills, jd_skills)

    return {
        "resume_skills": resume_skills,
        "jd_skills": jd_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills
    }