import json
import logging
import os
import re
from typing import List

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
except ImportError:
    genai = None


# ---------------------------------------------------
# Logger
# ---------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Gemini Client
# ---------------------------------------------------

API_KEY = os.getenv("GEMINI_API_KEY")

client = None

if genai and API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
        logger.info("Gemini Client Initialized")
    except Exception as e:
        logger.error(f"Gemini Initialization Failed : {e}")
        client = None


# ---------------------------------------------------
# Remove Duplicates while preserving order
# ---------------------------------------------------

def remove_duplicates(items: List[str]) -> List[str]:

    seen = set()
    unique = []

    for item in items:

        cleaned = " ".join(item.split()).strip()

        if not cleaned:
            continue

        key = cleaned.lower()

        if key in seen:
            continue

        seen.add(key)
        unique.append(cleaned)

    return unique


# ---------------------------------------------------
# Validate Gemini Response
# ---------------------------------------------------

def validate_json_response(text: str) -> List[str]:

    try:

        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

        data = json.loads(text)

        if not isinstance(data, list):
            return []

        clean = []

        for item in data:

            if isinstance(item, str):
                clean.append(item.strip())

        return remove_duplicates(clean)

    except Exception as e:

        logger.error(f"JSON Parsing Error : {e}")

        return []


# ---------------------------------------------------
# Helper Functions
# ---------------------------------------------------

def format_skills(skills):

    if not skills:
        return "None"

    return ", ".join(skills)


def format_projects(projects):

    if not projects:
        return "None"

    return "\n".join(projects)


def format_certifications(certs):

    if not certs:
        return "None"

    return ", ".join(certs)


# ---------------------------------------------------
# Smart Fallback Builder
# ---------------------------------------------------

def build_fallback(
        matched_skills,
        missing_skills,
        jd_title,
        required_experience):

    suggestions = []

    if required_experience:

        suggestions.append(
            f"The role expects {required_experience} of experience. "
            "If you don't meet it yet, strengthen your resume with internships, freelance work, research projects, or open-source contributions."
        )

    for skill in missing_skills[:2]:

        suggestions.append(
            f"Build a real-world project using {skill} and clearly demonstrate it in your resume with measurable outcomes."
        )

    suggestions.append(
        "Rewrite your project descriptions using action verbs and include measurable achievements such as accuracy improvements, deployment metrics, response time reductions, or user impact."
    )

    suggestions.append(
        f"Tailor your resume specifically for the {jd_title} position by naturally incorporating ATS keywords from the job description."
    )

    suggestions.append(
        "Add GitHub links, deployment links, certifications, and technical achievements to improve recruiter confidence."
    )

    return remove_duplicates(suggestions)[:5]

    # ---------------------------------------------------
# Prompt Builder
# ---------------------------------------------------

def build_prompt(
    matched_skills,
    missing_skills,
    score,
    jd_title,
    resume_experience,
    required_experience,
    resume_projects,
    resume_certifications,
    resume_education,
):

    return f"""
You are a Senior Technical Recruiter at Microsoft, Google and Amazon.

You have over 20 years of experience screening resumes using ATS systems and conducting technical interviews.

Your responsibility is to identify why a resume does or does not match a particular Job Description and recommend improvements that will maximize interview chances.

==================================================
TARGET ROLE
==================================================

Role:
{jd_title}

Current ATS Match Score:
{score}%

==================================================
EXPERIENCE
==================================================

Required Experience:
{required_experience if required_experience else "Not Mentioned"}

Candidate Experience:
{resume_experience if resume_experience else "Not Mentioned"}

==================================================
MATCHED SKILLS
==================================================

{format_skills(matched_skills)}

==================================================
MISSING SKILLS
==================================================

{format_skills(missing_skills)}

==================================================
PROJECTS
==================================================

{format_projects(resume_projects)}

==================================================
CERTIFICATIONS
==================================================

{format_certifications(resume_certifications)}

==================================================
EDUCATION
==================================================

{resume_education if resume_education else "Not Mentioned"}

==================================================
YOUR TASK
==================================================

Deeply analyze the resume.

Think step-by-step like:

1. ATS Scanner
2. Technical Recruiter
3. Hiring Manager
4. Team Lead

Do NOT summarize the resume.

Find the biggest weaknesses preventing the candidate from getting shortlisted.

==================================================
PRIORITY
==================================================

Priority 1
Experience Gap

• Compare candidate experience against required experience.

• If candidate has less experience,
recommend internships,
research work,
freelancing,
personal projects,
or open-source contributions.

==================================================

Priority 2
Skill Gap

• Compare skills.

• Mention ONLY the highest impact missing skills.

• Explain WHY those skills matter.

• Suggest HOW to learn them.

==================================================

Priority 3
Projects

Recommend projects that directly improve this resume.

Mention technologies.

Mention deployment.

Mention measurable outcomes.

Bad Example:

"Improve projects."

Good Example:

"Build an end-to-end Resume Matcher using FastAPI, PostgreSQL, Docker and SBERT. Deploy it on Render and include evaluation metrics such as ATS accuracy and response time."

==================================================

Priority 4
ATS Optimization

Recommend:

• Missing keywords

• Better bullet points

• Better achievements

• Better action verbs

• Better formatting

==================================================

Priority 5
Career Growth

Recommend certifications only if they are genuinely valuable.

Recommend GitHub improvements.

Recommend portfolio improvements.

Recommend deployment improvements.

==================================================

VERY IMPORTANT RULES

Each suggestion MUST:

✔ be personalized

✔ mention actual technologies whenever possible

✔ explain WHY it helps

✔ explain HOW to improve

✔ be practical

✔ avoid generic advice

✔ avoid repeating previous suggestions

✔ maximum 2 sentences

✔ recruiter-quality

✔ ATS-friendly

✔ unique

==================================================

GOOD EXAMPLES

"The job requires Docker, but your resume does not demonstrate containerization. Containerize your FastAPI application with Docker and deploy it so recruiters can verify your deployment skills."

"The resume mentions Machine Learning but lacks measurable impact. Include model accuracy, F1-score, inference latency, dataset size, and deployment details to demonstrate production readiness."

"The JD requires AWS experience. Deploy one of your AI projects using EC2, S3, and Docker, then include the GitHub repository and live deployment link."

==================================================

Return ONLY valid JSON.

Exactly five strings.

Example:

[
"Suggestion 1",
"Suggestion 2",
"Suggestion 3",
"Suggestion 4",
"Suggestion 5"
]

No markdown.

No numbering.

No explanation.

No extra text.
"""

# ---------------------------------------------------
# Main AI Suggestion Generator
# ---------------------------------------------------

def generate_suggestions(
    matched_skills,
    missing_skills,
    score,
    jd_title="Target Role",
    resume_experience="",
    required_experience="",
    resume_projects=None,
    resume_certifications=None,
    resume_education="",
):

    resume_projects = resume_projects or []
    resume_certifications = resume_certifications or []

    # ----------------------------
    # If Gemini client isn't available
    # ----------------------------
    if client is None:

        logger.warning("Gemini client unavailable. Using fallback suggestions.")

        return build_fallback(
            matched_skills,
            missing_skills,
            jd_title,
            required_experience,
        )

    # ----------------------------
    # Build Prompt
    # ----------------------------
    prompt = build_prompt(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        score=score,
        jd_title=jd_title,
        resume_experience=resume_experience,
        required_experience=required_experience,
        resume_projects=resume_projects,
        resume_certifications=resume_certifications,
        resume_education=resume_education,
    )

    # ----------------------------
    # Retry Logic
    # ----------------------------
    MAX_RETRIES = 3

    for attempt in range(MAX_RETRIES):

        try:

            logger.info(f"Generating AI Suggestions (Attempt {attempt+1})")

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            if response is None:
                raise Exception("Empty response received.")

            if not hasattr(response, "text"):
                raise Exception("Gemini response has no text.")

            ai_text = response.text.strip()

            logger.info("Gemini Response Received Successfully.")

            suggestions = validate_json_response(ai_text)

            if len(suggestions) < 5:

                logger.warning(
                    f"Gemini returned only {len(suggestions)} suggestions."
                )

                fallback = build_fallback(
                    matched_skills,
                    missing_skills,
                    jd_title,
                    required_experience,
                )

                suggestions.extend(fallback)

            suggestions = remove_duplicates(suggestions)

            return suggestions[:5]

        except Exception as e:

            logger.error(f"Gemini Attempt {attempt+1} Failed")

            logger.exception(e)

    # ----------------------------
    # Complete Failure
    # ----------------------------

    logger.warning("Using Smart Fallback Suggestions.")

    return build_fallback(
        matched_skills,
        missing_skills,
        jd_title,
        required_experience,
    )