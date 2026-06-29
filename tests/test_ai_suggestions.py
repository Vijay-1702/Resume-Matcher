from app.ai_suggestions import generate_suggestions


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModel:
    def __init__(self):
        self.prompts = []

    def generate_content(self, prompt):
        self.prompts.append(prompt)
        return FakeResponse(
            '["Add Python to your skills section and show it in a project.", "Rewrite your fraud-detection project with metrics and business impact.", "Rephrase your backend experience with stronger action verbs and results.", "Add keywords like ETL, Kafka, and AWS to your summary.", "Add a certification or measurable outcome to strengthen the profile."]'
        )


def test_generate_suggestions_uses_resume_experience_and_projects(monkeypatch):
    fake_model = FakeModel()
    monkeypatch.setattr("app.ai_suggestions.model", fake_model)

    suggestions = generate_suggestions(
        matched_skills=["Python"],
        missing_skills=["Kafka", "AWS"],
        score=84,
        jd_title="Data Engineer",
        resume_text="Built a fraud-detection dashboard using Python and SQL. Led a team on an ETL pipeline project. Worked as a backend engineer for two years.",
    )

    assert len(suggestions) == 5
    prompt = fake_model.prompts[0]
    assert "experience" in prompt.lower()
    assert "projects" in prompt.lower()
    assert "experience bullets and project descriptions" in prompt.lower()
