import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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

const SkillGroup = ({ title, skills, tone = "neutral" }) => (
  <div className="skills-col">
    <h3>{title}</h3>
    <div className="skills-list">
      {(skills || []).length ? (
        skills.map((skill, index) => (
          <span key={`${title}-${skill}-${index}`} className={`skill-chip ${tone}`}>
            {skill}
          </span>
        ))
      ) : (
        <span className="skill-empty">No skills found yet.</span>
      )}
    </div>
  </div>
);

function Results() {
  const navigate = useNavigate();
  useEffect(() => {
    const authUser = localStorage.getItem("authUser");
    if (!authUser) navigate("/");
  }, [navigate]);
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
    // fetch user's job descriptions for save options
    (async () => {
      try {
        const rawUser = localStorage.getItem("authUser");
        if (!rawUser) return;
        const user = JSON.parse(rawUser);
        const jdRes = await api.get(`job-descriptions/${user.id}`);
        setJobDescriptions(jdRes.data || []);
      } catch (e) {
        // ignore
      }
    })();
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
            <div>
              <span>Skill Match</span>
              <strong>{loading ? "--" : `${data.skillScore ?? 0}%`}</strong>
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
          <div style={{display:'flex', alignItems:'center', gap:12}}>
            <button className="upload-submit-btn" type="button" onClick={openSaveDialog}>
              {resumeSaved ? "Resume Saved" : "Save Resume"}
            </button>
            <button className="results-secondary-btn" type="button" onClick={() => { window.location.href = "/history"; }}>
              Resume History
            </button>
          </div>

          {showSavePanel && (
            <div className="save-modal-backdrop" role="presentation" onClick={closeSaveDialog}>
              <div
                className="save-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="save-modal-title"
                aria-describedby="save-modal-description"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="save-modal-header">
                  <div>
                    <p className="save-modal-kicker">Save resume</p>
                    <h3 id="save-modal-title">Choose where to save this version</h3>
                  </div>
                  <button className="save-modal-close" type="button" onClick={closeSaveDialog} aria-label="Close save dialog">
                    ×
                  </button>
                </div>

                <p id="save-modal-description" className="save-modal-description">
                  Save to an existing job description or create a new one before storing this resume version.
                </p>

                <div className="save-mode-switch">
                  <label className={saveMode === 'existing' ? 'active' : ''}>
                    <input type="radio" name="save-mode" checked={saveMode === 'existing'} onChange={() => setSaveMode('existing')} />
                    Existing JD
                  </label>
                  <label className={saveMode === 'new' ? 'active' : ''}>
                    <input type="radio" name="save-mode" checked={saveMode === 'new'} onChange={() => setSaveMode('new')} />
                    Create new JD
                  </label>
                </div>

                {saveMode === 'existing' ? (
                  <div className="save-modal-field">
                    <label htmlFor="save-existing-jd">Select a job description</label>
                    <select
                      id="save-existing-jd"
                      value={selectedJd || ''}
                      onChange={(e) => setSelectedJd(Number(e.target.value))}
                    >
                      <option value="">Select a job description...</option>
                      {jobDescriptions.map((jd) => (
                        <option key={jd.id} value={jd.id}>
                          {jd.title || `(JD ${jd.id})`}
                        </option>
                      ))}
                    </select>
                    {!jobDescriptions.length && <p className="save-modal-help">No saved JDs found. Switch to create a new one.</p>}
                  </div>
                ) : (
                  <div className="save-modal-field">
                    <label htmlFor="save-new-jd">New JD title</label>
                    <input
                      id="save-new-jd"
                      placeholder="e.g. Frontend Engineer"
                      value={newJdTitle}
                      onChange={(e) => setNewJdTitle(e.target.value)}
                    />
                    <p className="save-modal-help">The resume will be saved under a new job description with the current JD text.</p>
                  </div>
                )}

                <div className="save-modal-actions">
                  <button className="upload-submit-btn" type="button" onClick={handleSaveResume}>
                    Confirm Save
                  </button>
                  <button className="results-secondary-btn" type="button" onClick={closeSaveDialog}>
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
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

        {saveMessage && <div className="message success-message">{saveMessage}</div>}
      </main>
    </div>
  );
}

export default Results;
