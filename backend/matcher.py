from sentence_transformers import SentenceTransformer, util
from backend.skill_extractor import analyze_skills

# Load SBERT model once when app starts
model = SentenceTransformer("all-MiniLM-L6-v2")


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts using SBERT"""
    embedding1 = model.encode(text1, convert_to_tensor=True)
    embedding2 = model.encode(text2, convert_to_tensor=True)
    similarity = util.cos_sim(embedding1, embedding2)
    return round(float(similarity[0][0]) * 100, 2)


def calculate_match_score(resume_text: str, jd_text: str) -> dict:
    """
    Calculate overall match score combining:
    - Semantic similarity (60% weight)
    - Skill match (40% weight)
    """
    # 1. Semantic similarity score
    semantic_score = calculate_semantic_similarity(resume_text, jd_text)

    # 2. Skill match score
    skill_result = analyze_skills(resume_text, jd_text)
    jd_skills = skill_result["jd_skills"]
    matched_skills = skill_result["matched_skills"]

    skill_score = round(
        len(matched_skills) / len(jd_skills) * 100
        if jd_skills else 0, 2
    )

    # 3. Weighted final score
    final_score = round(
        (semantic_score * 0.6) + (skill_score * 0.4), 2
    )

    return {
        "final_score": final_score,
        "semantic_score": semantic_score,
        "skill_score": skill_score,
        "matched_skills": matched_skills,
        "missing_skills": skill_result["missing_skills"],
        "resume_skills": skill_result["resume_skills"],
        "jd_skills": jd_skills
    }
