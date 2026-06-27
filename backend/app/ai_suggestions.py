import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_suggestions(
    matched_skills: list,
    missing_skills: list,
    score: float,
    jd_title: str = "the target role"
) -> list:
    prompt = f"""
You are an expert resume coach helping a student improve their resume.

Job Role: {jd_title}
Current Match Score: {score}%
Skills Already Present: {', '.join(matched_skills) if matched_skills else 'None'}
Missing Skills: {', '.join(missing_skills) if missing_skills else 'None'}

Give exactly 5 specific, actionable suggestions to improve this resume.
Each suggestion must:
- Be specific (mention exact skills, tools, or sections)
- Be actionable (tell them exactly what to do)
- Be concise (1-2 sentences max)

Return ONLY a JSON array of 5 strings, no other text.
Example format:
["suggestion 1", "suggestion 2", "suggestion 3", "suggestion 4", "suggestion 5"]
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean up response
        text = text.replace("```json", "").replace("```", "").strip()

        import json
        suggestions = json.loads(text)
        return suggestions[:5]

    except Exception as e:
        # Fallback suggestions if API fails
        fallback = []
        for skill in missing_skills[:3]:
            fallback.append(
                f"Add '{skill}' to your skills section and include a project that demonstrates it."
            )
        fallback.append("Quantify your achievements with metrics (e.g., 'improved accuracy by 20%').")
        fallback.append("Use strong action verbs like 'Developed', 'Architected', 'Optimized' in bullet points.")
        return fallback[:5]