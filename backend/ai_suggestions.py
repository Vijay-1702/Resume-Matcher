import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_suggestions(
    matched_skills: list,
    missing_skills: list,
    score: float,
    jd_title: str = "the target role",
    resume_text: str = ""
) -> list:
    resume_preview = resume_text[:4000] if resume_text else "Not provided"
    prompt = f"""
You are an expert ATS resume coach reviewing a student's resume for a specific job.

Job Role: {jd_title}
Current ATS Match Score: {score}%

Skills Already Matched: {', '.join(matched_skills) if matched_skills else 'None'}
Missing Skills (from JD): {', '.join(missing_skills) if missing_skills else 'None'}

Resume Content (for context):
{resume_preview}

Based on the resume's actual experience bullets and project descriptions, the missing skills, and the job role, give exactly 5 specific actionable suggestions.
Each suggestion must:
- be specific to the job role and resume
- mention a skill, project, experience, or impact area
- prioritize the resume's experience and projects content
- be no more than 2 sentences
- be written as a clear recommendation

Return ONLY a JSON array of exactly 5 strings, no markdown, no extra text.
["suggestion 1", "suggestion 2", "suggestion 3", "suggestion 4", "suggestion 5"]
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(text)
        return suggestions[:5]

    except Exception:
        fallback = []
        for skill in missing_skills[:2]:
            fallback.append(
                f"Add '{skill}' to your skills section and build a small project demonstrating it."
            )
        fallback.append(
            "Rewrite project descriptions using the XYZ formula: 'Accomplished X as measured by Y by doing Z'."
        )
        fallback.append(
            "Add metrics to experience bullets e.g. 'Improved model accuracy by 15% using hyperparameter tuning'."
        )
        fallback.append(
            "Add missing JD keywords naturally into your project descriptions to improve ATS score."
        )
        return fallback[:5]