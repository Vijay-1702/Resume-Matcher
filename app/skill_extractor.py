import spacy

nlp = spacy.load("en_core_web_sm")

SKILL_LIST = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "r", "matlab", "scala", "php", "ruby",
    "fastapi", "flask", "django", "react", "angular", "vue", "node.js",
    "express", "spring boot", "next.js",
    "postgresql", "mysql", "mongodb", "redis", "sqlite", "cassandra",
    "elasticsearch", "firebase",
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "huggingface",
    "transformers", "bert", "gpt", "llm", "rag", "fine-tuning",
    "xgboost", "lightgbm", "pandas", "numpy", "matplotlib", "seaborn",
    "docker", "kubernetes", "aws", "azure", "gcp", "mlflow", "airflow",
    "ci/cd", "jenkins", "terraform", "git", "github", "linux",
    "spark", "hadoop", "kafka", "dbt", "etl", "sql",
    "data pipeline", "feature engineering",
    "rest api", "graphql", "microservices", "agile", "scrum",
    "langchain", "openai", "gemini", "prompt engineering",
    "shap", "qlora", "smote", "vector embeddings", "spacy"
]


def extract_skills(text: str) -> list:
    text_lower = text.lower()
    found_skills = []
    for skill in SKILL_LIST:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    return list(set(found_skills))


def get_missing_skills(resume_skills: list, jd_skills: list) -> list:
    resume_lower = [s.lower() for s in resume_skills]
    missing = [s for s in jd_skills if s.lower() not in resume_lower]
    return missing


def analyze_skills(resume_text: str, jd_text: str) -> dict:
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