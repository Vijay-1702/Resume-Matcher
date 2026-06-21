import { useEffect, useState } from "react";
import api from "../services/api";
import "./History.css";

const sampleHistory = [
  { resume_version_id: 1, version_no: 1, file_name: "resume_v1.pdf", uploaded_at: "2026-06-18T10:12:00", score: 74 },
  { resume_version_id: 2, version_no: 2, file_name: "resume_v2.pdf", uploaded_at: "2026-06-20T15:03:00", score: 81 },
];

function History() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [history, setHistory] = useState(sampleHistory);

  useEffect(() => {
    let mounted = true;
    const fetchHistory = async () => {
      try {
        // Replace userId=1 with dynamic user when available
        const res = await api.get("/api/resume/history/1");
        if (!mounted) return;
        if (res?.data) {
          // Data from backend doesn't include score currently; keep score undefined
          setHistory(res.data.map((v) => ({ ...v, score: v.score ?? "—" })));
        }
      } catch (err) {
        console.warn("Failed to fetch resume history, using sample.", err);
        setError("");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchHistory();
    return () => (mounted = false);
  }, []);

  return (
    <div className="history-page">
      <main className="history-main">
        <h1>Resume Versions</h1>
        <p className="sub">All uploaded resume versions for this user.</p>

        <section className="history-block">
          {error && <div className="message error-message">{error}</div>}

          <div className="history-table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>File</th>
                  <th>Uploaded</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {(history || []).map((v) => (
                  <tr key={v.resume_version_id}>
                    <td>v{v.version_no}</td>
                    <td>{v.file_name}</td>
                    <td>{new Date(v.uploaded_at).toLocaleString()}</td>
                    <td>{v.score ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

export default History;