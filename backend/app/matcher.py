from sentence_transformers import SentenceTransformer, util
from app.skill_extractor import analyze_skills

model = SentenceTransformer("all-MiniLM-L6-v2")


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    embedding1 = model.encode(text1, convert_to_tensor=True)
    embedding2 = model.encode(text2, convert_to_tensor=True)
    similarity = util.cos_sim(embedding1, embedding2)
    return round(float(similarity[0][0]) * 100, 2)


def calculate_match_score(resume_text: str, jd_text: str) -> dict:
    semantic_score = calculate_semantic_similarity(resume_text, jd_text)

    skill_result = analyze_skills(resume_text, jd_text)
    jd_skills = skill_result["jd_skills"]
    matched_skills = skill_result["matched_skills"]

    skill_score = round(
        len(matched_skills) / len(jd_skills) * 100
        if jd_skills else 0, 2
    )

    experience_keywords = [
        "experience", "worked", "developed", "built", "implemented",
        "designed", "led", "managed", "created", "deployed"
    ]
    resume_lower = resume_text.lower()
    exp_count = sum(1 for k in experience_keywords if k in resume_lower)
    experience_score = min(round(exp_count * 10, 2), 100)

    education_keywords = [
        "b.tech", "bachelor", "master", "phd", "degree", "university", "college"
    ]
    edu_count = sum(1 for k in education_keywords if k in resume_lower)
    education_score = min(round(edu_count * 25, 2), 100)

    final_score = round(
        (semantic_score * 0.50) +
        (skill_score * 0.30) +
        (experience_score * 0.10) +
        (education_score * 0.10), 2
    )

    return {
        "final_score": final_score,
        "semantic_score": semantic_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "matched_skills": matched_skills,
        "missing_skills": skill_result["missing_skills"],
        "resume_skills": skill_result["resume_skills"],
        "jd_skills": jd_skills
    }