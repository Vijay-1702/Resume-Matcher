from collections import Counter
import math
import re

try:
    from .skill_extractor import analyze_skills
except ImportError:  # pragma: no cover
    from backend.app.skill_extractor import analyze_skills


def calculate_keyword_similarity(text1: str, text2: str) -> float:
    """
    Calculate cosine similarity using keyword frequency.
    Lightweight replacement for SentenceTransformer.
    """

    words1 = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]*\b", text1.lower())
    words2 = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]*\b", text2.lower())

    if not words1 or not words2:
        return 0

    counts1 = Counter(words1)
    counts2 = Counter(words2)

    common_words = set(counts1) & set(counts2)

    numerator = sum(
        counts1[word] * counts2[word]
        for word in common_words
    )

    magnitude1 = math.sqrt(sum(v * v for v in counts1.values()))
    magnitude2 = math.sqrt(sum(v * v for v in counts2.values()))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0

    similarity = numerator / (magnitude1 * magnitude2)

    return round(similarity * 100, 2)


def calculate_match_score(resume_text: str, jd_text: str) -> dict:
    """
    Overall Match Score

    60% Keyword Similarity
    40% Skill Match
    """

    keyword_score = calculate_keyword_similarity(
        resume_text,
        jd_text,
    )

    skill_result = analyze_skills(
        resume_text,
        jd_text,
    )

    jd_skills = skill_result["jd_skills"]
    matched_skills = skill_result["matched_skills"]

    skill_score = round(
        (
            len(matched_skills) / len(jd_skills) * 100
        ) if jd_skills else 0,
        2,
    )

    final_score = round(
        (keyword_score * 0.6) +
        (skill_score * 0.4),
        2,
    )

    return {
        "final_score": final_score,
        "semantic_score": keyword_score,
        "skill_score": skill_score,
        "experience_score": 0,
        "education_score": 0,
        "matched_skills": matched_skills,
        "missing_skills": skill_result["missing_skills"],
        "resume_skills": skill_result["resume_skills"],
        "jd_skills": jd_skills,
    }