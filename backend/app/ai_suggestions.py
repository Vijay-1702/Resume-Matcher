from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)


def generate_suggestions(
    matched_skills: list,
    missing_skills: list,
    score: float,
    jd_title: str = "the target role",
    resume_experience: str = "",
    required_experience: str = "",
    resume_projects: list = None,
    resume_certifications: list = None,
    resume_education: str = ""
) -> list:

    resume_projects = resume_projects or []
    resume_certifications = resume_certifications or []

    prompt = f"""
You are an expert ATS resume reviewer and career coach.

Analyze this resume against the target job description.

Target Role:
{jd_title}

Overall Match Score:
{score}%

Required Experience:
{required_experience if required_experience else "Not specified"}

Candidate Experience:
{resume_experience if resume_experience else "Not specified"}

Matched Skills:
{", ".join(matched_skills) if matched_skills else "None"}

Missing Skills:
{", ".join(missing_skills) if missing_skills else "None"}

Projects:
{chr(10).join(resume_projects) if resume_projects else "None"}

Certifications:
{", ".join(resume_certifications) if resume_certifications else "None"}

Education:
{resume_education if resume_education else "Not specified"}

Generate EXACTLY 5 suggestions.

Prioritize suggestions in this order:

1. Experience
- If required experience is missing or weak, recommend gaining relevant experience through internships, freelance work, research, open-source contributions, or substantial projects.

2. Missing Skills
- Mention specific missing technologies and explain how to demonstrate them.

3. Projects
- Recommend adding or improving projects that align with the job requirements.
- Suggest including measurable outcomes and relevant technologies.

4. Resume Content
- Recommend improvements to achievements, quantified impact, ATS keywords, certifications, education, or formatting if appropriate.

Rules:

- Suggestions must be personalized.
- Mention specific technologies whenever possible.
- Avoid generic advice.
- Maximum 2 sentences each.
- Return ONLY a valid JSON array.
- No markdown.
- No explanations.
- Exactly 5 strings.

Example:

[
"Gain hands-on experience with Docker by deploying one of your projects using Docker Compose.",
"Add a REST API project using Spring Boot and MySQL to better match backend requirements.",
"..."
]
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = response.text.strip()

        text = (
            text.replace("```json", "")
            .replace("```", "")
            .strip()
        )

        suggestions = json.loads(text)

        if not isinstance(suggestions, list):
            raise ValueError("Gemini did not return a JSON array.")

        return suggestions[:5]

    except Exception as e:
        print("Gemini Error:", e)

        fallback = []

        if required_experience:
            fallback.append(
                "Strengthen your experience section by highlighting internships, freelance work, open-source contributions, or projects that closely match the job requirements."
            )

        for skill in missing_skills[:2]:
            fallback.append(
                f"Learn and demonstrate '{skill}' through a practical project and add it to your resume."
            )

        fallback.append(
            "Include measurable achievements in your projects, such as performance improvements, user count, accuracy, or deployment results."
        )

        fallback.append(
            "Tailor your resume to the job description by emphasizing relevant experience, technical skills, and ATS-friendly keywords."
        )

        while len(fallback) < 5:
            fallback.append(
                "Improve your resume by aligning your experience, projects, and skills more closely with the target role."
            )

        return fallback[:5]