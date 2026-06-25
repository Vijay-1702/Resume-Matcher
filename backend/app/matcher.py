from collections import Counter
import math
import re

from backend.app.skill_extractor import analyze_skills

try:
    from sentence_transformers import SentenceTransformer, util
except Exception:
    SentenceTransformer = None
    util = None

model = None


def get_model():
    global model
    if model is None and SentenceTransformer is not None:
        model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    return model


def calculate_keyword_similarity(text1: str, text2: str) -> float:
    words1 = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]*\b", text1.lower())
    words2 = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]*\b", text2.lower())

    if not words1 or not words2:
        return 0

    counts1 = Counter(words1)
    counts2 = Counter(words2)
    common_words = set(counts1) & set(counts2)
    numerator = sum(counts1[word] * counts2[word] for word in common_words)
    magnitude1 = math.sqrt(sum(value * value for value in counts1.values()))
    magnitude2 = math.sqrt(sum(value * value for value in counts2.values()))

    if not magnitude1 or not magnitude2:
        return 0

    return round((numerator / (magnitude1 * magnitude2)) * 100, 2)


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts using SBERT"""
    try:
        active_model = get_model()
        if active_model is None or util is None:
            return calculate_keyword_similarity(text1, text2)

        embedding1 = active_model.encode(text1, convert_to_tensor=True)
        embedding2 = active_model.encode(text2, convert_to_tensor=True)
        similarity = util.cos_sim(embedding1, embedding2)
        return round(float(similarity[0][0]) * 100, 2)
    except Exception:
        return calculate_keyword_similarity(text1, text2)


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
