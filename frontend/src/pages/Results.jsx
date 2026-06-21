import { useEffect, useState } from "react";
import api from "../services/api";
import "./Results.css";

const sample = {
  score: 78,
  matchedSkills: ["React", "JavaScript", "Node.js", "REST APIs"],
  missingSkills: ["Docker", "Kubernetes", "GraphQL"],
};

function Results() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(sample);

  useEffect(() => {
    let mounted = true;
    const fetchResults = async () => {
      try {
        const res = await api.get("/results");
        if (!mounted) return;
        // Expecting shape: { score, matchedSkills, missingSkills }
        if (res?.data) setData(res.data);
      } catch (err) {
        console.warn("Could not fetch results, using sample data.", err);
        setError("");
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
        </section>

        <div className="results-actions">
          <button
            className="upload-submit-btn"
            onClick={() => (window.location.href = "/upload")}
          >
            Upload New
          </button>
        </div>
      </main>
    </div>
  );
}

export default Results;