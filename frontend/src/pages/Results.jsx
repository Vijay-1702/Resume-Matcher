import { useEffect, useState } from "react";
import api from "../services/api";
import "./Results.css";

const getErrorMessage = (err, fallback) =>
  err.response?.data?.message ||
  err.response?.data?.detail ||
  err.message ||
  fallback;

const formatSkillList = (skills) => {
  if (!skills?.length) return "";
  const visibleSkills = skills.slice(0, 4).join(", ");
  return skills.length > 4 ? `${visibleSkills}, and ${skills.length - 4} more` : visibleSkills;
};

const normalizeRecommendations = (source) => {
  if (!Array.isArray(source)) return [];

  return source
    .map((item) => {
      if (typeof item === "string") {
        return { title: item, detail: "Prioritize this update before your next application." };
      }

      return {
        title: item.title || item.recommendation || item.summary || "Resume improvement",
        detail: item.detail || item.description || item.reason || "Use the job description as the source of truth.",
      };
    })
    .filter((item) => item.title);
};

const buildRecommendations = (data, score) => {
  const provided = normalizeRecommendations(data?.recommendations || data?.ai_suggestions || data?.aiSuggestions);
  if (provided.length) return provided.slice(0, 4);

  const missingSkills = data?.missingSkills || [];
  const recommendations = [];

  if (missingSkills.length) {
    recommendations.push({
      title: "Add missing role keywords",
      detail: `Work in relevant experience for ${formatSkillList(missingSkills)} where it reflects your background.`,
    });
  }

  if ((data?.skillScore ?? 0) < 70) {
    recommendations.push({
      title: "Strengthen the skills section",
      detail: "Group technical skills by category and mirror the job description terminology where accurate.",
    });
  }

  if ((data?.semanticScore ?? 0) < 70) {
    recommendations.push({
      title: "Align bullets with job outcomes",
      detail: "Rewrite key bullets to emphasize responsibilities, impact, and measurable results from the target role.",
    });
  }

  if (score >= 80) {
    recommendations.push({
      title: "Polish for recruiter scanning",
      detail: "Keep the strongest matched skills high on the page and tighten any bullets that do not support this role.",
    });
  }

  return recommendations.length
    ? recommendations.slice(0, 4)
    : [
        {
          title: "Resume is well aligned",
          detail: "Review formatting, dates, and role-specific examples before submitting.",
        },
      ];
};

function Results() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [resumeSaved, setResumeSaved] = useState(false);
  const [data, setData] = useState({
    score: 0,
    matchedSkills: [],
    missingSkills: [],
  });

  useEffect(() => {
    let mounted = true;
    const fetchResults = async () => {
      try {
        // Get session_id from localStorage
        const sessionId = localStorage.getItem("sessionId");
        
        if (!sessionId) {
          setError("No active session. Please upload files first.");
          setLoading(false);
          return;
        }

        // Fetch results from workflow endpoint
        const res = await api.get(`/workflow/results?session_id=${sessionId}`);
        
        if (!mounted) return;
        
        if (res?.data?.success) {
          setData({
            score: res.data.score || 0,
            matchedSkills: res.data.matchedSkills || [],
            missingSkills: res.data.missingSkills || [],
            semanticScore: res.data.semanticScore,
            skillScore: res.data.skillScore,
            resumeSkills: res.data.resumeSkills,
            jdSkills: res.data.jdSkills,
            recommendations: res.data.recommendations,
            ai_suggestions: res.data.ai_suggestions,
            aiSuggestions: res.data.aiSuggestions,
          });
        } else {
          setError(res?.data?.message || "Failed to fetch results");
        }
      } catch (err) {
        console.error("Error fetching results:", err);
        setError(getErrorMessage(err, "Failed to load results. Please try again."));
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchResults();
    return () => (mounted = false);
  }, []);

  const score = Math.min(100, Math.max(0, data?.score ?? 0));
  const recommendations = buildRecommendations(data, score);

  return (
    <div className="results-page">
      <main className="results-main">
        <div className="results-header">
          <h1>Match Results</h1>
          <p className="sub">Overview of how your resume compares to the job description.</p>
        </div>

        {error && <div className="message error-message">{error}</div>}

        <section className="results-block">
          <div className="score-panel">
            <h2>Resume Score</h2>
            <div className="score-meter" aria-hidden>
              <div className="score-fill" style={{ width: `${score}%` }} />
            </div>
            <div className="score-value">{loading ? "Loading..." : `${score}%`}</div>
          </div>

          <div className="score-breakdown">
            <div>
              <span>Semantic Match</span>
              <strong>{loading ? "--" : `${data.semanticScore ?? 0}%`}</strong>
            </div>
            <div>
              <span>Skill Match</span>
              <strong>{loading ? "--" : `${data.skillScore ?? 0}%`}</strong>
            </div>
          </div>

          <div className="skills-panel">
            <div className="skills-col">
              <h3>Matched Skills</h3>
              <div className="skills-list">
                {(data?.matchedSkills || []).map((s, i) => (
                  <span key={i} className="skill-chip matched">
                    {s}
                  </span>
                ))}
              </div>
            </div>

            <div className="skills-col">
              <h3>Missing Skills</h3>
              <ul className="missing-list">
                {(data?.missingSkills || []).map((m, i) => (
                  <li key={i} className="missing-item">
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="skills-panel extracted-panel">
            <div className="skills-col">
              <h3>Resume Skills Extracted</h3>
              <div className="skills-list">
                {(data?.resumeSkills || []).map((s, i) => (
                  <span key={i} className="skill-chip extracted">
                    {s}
                  </span>
                ))}
              </div>
            </div>

            <div className="skills-col">
              <h3>JD Skills Extracted</h3>
              <div className="skills-list">
                {(data?.jdSkills || []).map((s, i) => (
                  <span key={i} className="skill-chip extracted">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <section className="suggestions-card" aria-labelledby="suggestions-title">
            <div className="suggestions-heading">
              <p className="section-kicker">Suggestions Card</p>
              <h2 id="suggestions-title">Improvement Recommendations</h2>
            </div>

            <div className="recommendations-list">
              {loading ? (
                <div className="recommendation-item">
                  <span className="recommendation-index">--</span>
                  <div>
                    <h3>Loading recommendations</h3>
                    <p>Preparing resume improvement guidance.</p>
                  </div>
                </div>
              ) : (
                recommendations.map((item, index) => (
                  <article className="recommendation-item" key={`${item.title}-${index}`}>
                    <span className="recommendation-index">{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <h3>{item.title}</h3>
                      <p>{item.detail}</p>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </section>

        <div className="results-actions">
          <button
            className="upload-submit-btn"
            type="button"
            onClick={() => setResumeSaved(true)}
          >
            {resumeSaved ? "Resume Saved" : "Save Resume"}
          </button>
          <button
            className="results-secondary-btn"
            type="button"
            onClick={() => {
              window.location.href = "/history";
            }}
          >
            Resume History
          </button>
          <button
            className="upload-submit-btn"
            type="button"
            onClick={() => {
              localStorage.removeItem("sessionId");
              window.location.href = "/upload";
            }}
          >
            Upload New
          </button>
        </div>
      </main>
    </div>
  );
}

export default Results;
