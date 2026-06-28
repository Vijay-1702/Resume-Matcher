import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


def _build_resume_context(resume_text: str) -> str:
    if not resume_text:
        return "No resume text was provided."

    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    experience_lines = [
        line for line in lines
        if any(keyword in line.lower() for keyword in ["experience", "work", "internship", "responsible", "developed", "built", "led", "managed"])
    ][:8]
    project_lines = [
        line for line in lines
        if any(keyword in line.lower() for keyword in ["project", "portfolio", "built", "developed", "implemented", "created", "designed"])
    ][:8]

    context_parts = ["Resume highlights:"]
    if experience_lines:
        context_parts.append("Experience-focused lines:\n- " + "\n- ".join(experience_lines))
    if project_lines:
        context_parts.append("Project-focused lines:\n- " + "\n- ".join(project_lines))
    return "\n\n".join(context_parts)


def generate_suggestions(
    matched_skills: list,
    missing_skills: list,
    score: float,
    jd_title: str = "the target role",
    resume_text: str = ""
) -> list:

    resume_preview = resume_text[:4000] if resume_text else "Not provided"
    resume_context = _build_resume_context(resume_text)

    prompt = f"""
You are an expert ATS resume coach reviewing a student's resume for a specific job.

Job Role: {jd_title}
Current ATS Match Score: {score}%

Skills Already Matched: {', '.join(matched_skills) if matched_skills else 'None'}
Missing Skills (from JD): {', '.join(missing_skills) if missing_skills else 'None'}

Resume Content (for context):
{resume_preview}

Resume Experience and Project Context:
{resume_context}

Based on the resume's actual experience bullets and project descriptions, the missing skills, and the job role, give exactly 5 specific actionable suggestions:

1. One suggestion about MISSING SKILLS — which specific skill to add and how to demonstrate it
2. One suggestion about PROJECTS — how to rewrite or improve an existing project description to match the JD
3. One suggestion about EXPERIENCE — how to rephrase experience bullets using stronger action verbs and metrics
4. One suggestion about ATS OPTIMIZATION — specific keywords from the JD to add
5. One suggestion about OVERALL IMPACT — quantifiable achievements or certifications to add

Rules:
- Be specific to THIS resume and THIS job role
- Mention exact skills, tools, project names, or experience areas if visible
- Prioritize the resume's experience and projects content; do not ignore them
- Each suggestion max 2 sentences
- Do NOT give generic advice

Return ONLY a JSON array of exactly 5 strings, no markdown, no extra text.
["suggestion1", "suggestion2", "suggestion3", "suggestion4", "suggestion5"]
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(text)
        return suggestions[:5]

    except Exception as e:
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