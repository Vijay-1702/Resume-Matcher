import { useEffect, useState } from "react";
import api from "../services/api";
import "./Results.css";

const getErrorMessage = (err, fallback) =>
  err.response?.data?.message ||
  err.response?.data?.detail ||
  err.message ||
  fallback;

function Results() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
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
        </section>

        <div className="results-actions">
          <button
            className="upload-submit-btn"
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
