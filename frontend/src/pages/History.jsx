import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import "./History.css";

const defaultUserId = 1;
const defaultJdId = 1;

const formatDate = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

function History() {
  const navigate = useNavigate();
  useEffect(() => {
    const authUser = localStorage.getItem("authUser");
    if (!authUser) navigate("/");
  }, [navigate]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [jobDescriptions, setJobDescriptions] = useState([]);
  const [selectedJd, setSelectedJd] = useState(null);
  const [selectedForCompare, setSelectedForCompare] = useState([]);

  useEffect(() => {
    let mounted = true;
    const fetchJobData = async () => {
      try {
        const userId = Number(localStorage.getItem("userId") || defaultUserId);

        // fetch user's JDs
        const jdsRes = await api.get(`job-descriptions/${userId}`);
        const jds = Array.isArray(jdsRes?.data) ? jdsRes.data : [];
        if (!mounted) return;
        setJobDescriptions(jds);
        const jdToUse = jds[0]?.id || defaultJdId;
        setSelectedJd(jdToUse);
      } catch (err) {
        console.warn("Failed to fetch job descriptions.", err);
        setError("Unable to load job descriptions right now.");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchJobData();
    return () => (mounted = false);
  }, []);

  // when selectedJd changes, fetch versions and comparison
  useEffect(() => {
    if (!selectedJd) return;
    let mounted = true;
    const fetchVersions = async () => {
      setLoading(true);
      try {
        const userId = Number(localStorage.getItem("userId") || defaultUserId);
        const historyRes = await api.get(`version-history/${userId}/${selectedJd}`);
        const compareRes = await api.get(`version-compare/${userId}/${selectedJd}`).catch((err) => {
          if (err.response?.status === 400) return null;
          throw err;
        });

        if (!mounted) return;
        const versions = Array.isArray(historyRes?.data?.versions) ? historyRes.data.versions : [];
        setHistory(versions);
        setComparison(compareRes?.data || null);
        setSelectedForCompare([]);
      } catch (err) {
        console.warn("Failed to fetch resume history.", err);
        setError("Unable to load version history right now.");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchVersions();
    return () => (mounted = false);
  }, [selectedJd]);

  return (
    <div className="history-page">
      <main className="history-main">
        <h1>Resume Versions</h1>
        <p className="sub">Compare different resume versions for the same job description side by side.</p>

        <section className="history-block">
          {error && <div className="message error-message">{error}</div>}

          {comparison && (
            <div className="comparison-summary">
              <h2>Version comparison</h2>
              <p>
                Version {comparison.latest_version} improved from {comparison.previous_version} by {comparison.improvement}%.
              </p>
              <div className="comparison-grid">
                <article className="comparison-card">
                  <span className="comparison-label">Previous</span>
                  <h3>Version {comparison.previous_version}</h3>
                  <div className="score-pill">{comparison.previous_score ?? "—"}%</div>
                  <ul>
                    {(comparison.previous_missing_skills || []).slice(0, 6).map((skill) => (
                      <li key={skill}>{skill}</li>
                    ))}
                  </ul>
                </article>

                <article className="comparison-card latest">
                  <span className="comparison-label">Latest</span>
                  <h3>Version {comparison.latest_version}</h3>
                  <div className="score-pill">{comparison.latest_score ?? "—"}%</div>
                  <ul>
                    {(comparison.still_missing_skills || []).slice(0, 6).map((skill) => (
                      <li key={skill}>{skill}</li>
                    ))}
                  </ul>
                </article>
              </div>
            </div>
          )}

          <div className="history-list">
            {loading ? (
              <div className="empty-state">Loading versions…</div>
            ) : history.length === 0 ? (
              <div className="empty-state">No resume versions found for this job description yet.</div>
            ) : (
              <>
                <div className="jd-select">
                  <label>Select Job Description:</label>
                  <select value={selectedJd || ""} onChange={(e) => setSelectedJd(Number(e.target.value))}>
                    {jobDescriptions.map((jd) => (
                      <option key={jd.id} value={jd.id}>{jd.title || `(JD ${jd.id})`}</option>
                    ))}
                  </select>
                </div>

                {history.map((version) => (
                <article className="history-card" key={version.resume_version_id || version.version_no}>
                  <div className="history-card-main">
                    <div>
                      <h3>Version {version.version_no}</h3>
                      <p>{version.file_name}</p>
                      <p className="history-date">{formatDate(version.uploaded_at)}</p>
                    </div>
                    <div className="score-pill">{version.score ?? "—"}%</div>
                  </div>

                  <div className="history-card-meta">
                    <div>
                      <h4>Matched skills</h4>
                      <p>{(version.matched_skills || []).join(", ") || "—"}</p>
                    </div>
                    <div>
                      <h4>Missing skills</h4>
                      <p>{(version.missing_skills || []).join(", ") || "—"}</p>
                    </div>
                    <div className="history-card-actions">
                      <label>
                        <input
                          type="checkbox"
                          value={version.resume_version_id}
                          checked={selectedForCompare.includes(version.resume_version_id)}
                          onChange={(e) => {
                            const id = version.resume_version_id;
                            setSelectedForCompare((prev) => {
                              if (prev.includes(id)) return prev.filter((x) => x !== id);
                              return prev.length < 2 ? [...prev, id] : prev;
                            });
                          }}
                        /> Compare
                      </label>
                    </div>
                  </div>
                </article>
                ))}

                <div style={{marginTop:12}}>
                  <button
                    disabled={selectedForCompare.length !== 2}
                    onClick={async () => {
                      try {
                        setLoading(true);
                        const res = await api.post("compare-resumes", {
                          resume_a_id: selectedForCompare[0],
                          resume_b_id: selectedForCompare[1],
                        });
                        setComparison(res.data.comparison || res.data);
                      } catch (err) {
                        setError(getErrorMessage(err, "Comparison failed"));
                      } finally {
                        setLoading(false);
                      }
                    }}
                  >Compare Selected</button>
                </div>
              </>
            )}
          </div>
        </section>
        {comparison && (
          <section style={{marginTop:16}} className="comparison-output">
            <h2>Comparison Result</h2>
            {typeof comparison === "string" ? (
              <pre style={{whiteSpace:'pre-wrap'}}>{comparison}</pre>
            ) : (
              <div>
                <p>Previous score: {comparison.previous_score ?? "—"}</p>
                <p>Latest score: {comparison.latest_score ?? "—"}</p>
                <p>Improved: {String(comparison.improved)}</p>
                <h4>Newly added skills</h4>
                <ul>{(comparison.newly_added_skills || []).map((s) => <li key={s}>{s}</li>)}</ul>
                <h4>Still missing skills</h4>
                <ul>{(comparison.still_missing_skills || []).map((s) => <li key={s}>{s}</li>)}</ul>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default History;