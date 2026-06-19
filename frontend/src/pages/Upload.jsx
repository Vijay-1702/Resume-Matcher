import { useState } from "react";
import api from "../services/api";
import "./Upload.css";

function Upload() {
  const [resume, setResume] = useState(null);
  const [jd, setJd] = useState(null);
  const [jdInputMode, setJdInputMode] = useState("text");
  const [jdText, setJdText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleUpload = async () => {
    setError("");
    setSuccess("");

    // Validate resume
    if (!resume) {
      setError("Please select a resume file.");
      return;
    }

    // Validate JD
    if (jdInputMode === "text" && !jdText.trim()) {
      setError("Please enter a job description.");
      return;
    }

    if (jdInputMode === "file" && !jd) {
      setError("Please select a job description file.");
      return;
    }

    setLoading(true);

    try {
      // Upload resume
      const resumeFormData = new FormData();
      resumeFormData.append("file", resume);
      await api.post("/upload/resume", resumeFormData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // Upload JD
      if (jdInputMode === "text") {
        await api.post("/upload/job-description/text", {
          text: jdText,
        });
      } else {
        const jdFormData = new FormData();
        jdFormData.append("file", jd);
        await api.post("/upload/job-description", jdFormData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      setSuccess("Files uploaded successfully! Redirecting to results...");
      setTimeout(() => {
        window.location.href = "/results";
      }, 1500);
    } catch (err) {
      setError(
        err.response?.data?.message ||
          "Upload failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-page">
      <main className="upload-main">
        <div>
          <h1>Upload Resume & Job Description</h1>
          <p>
            Choose your resume and paste or upload your job description to begin 
            the matching process. Supported file formats are PDF, DOC, DOCX, and TXT.
          </p>
        </div>

        <section className="upload-block">
          {error && <div className="message error-message">{error}</div>}
          {success && <div className="message success-message">{success}</div>}

          <div className="upload-control">
            <h3>Resume Upload</h3>
            <label htmlFor="resume-upload">Select resume</label>
            <input
              id="resume-upload"
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={(e) => setResume(e.target.files[0])}
            />
            <div className="file-meta">
              <span>
                {resume ? resume.name : "No resume selected yet."}
              </span>
              {resume && <span>{(resume.size / 1024).toFixed(1)} KB</span>}
            </div>
          </div>

          <div className="upload-control">
            <h3>Job Description</h3>
            
            <div className="input-mode-toggle">
              <button
                className={`toggle-btn ${jdInputMode === "text" ? "active" : ""}`}
                onClick={() => setJdInputMode("text")}
              >
                Text
              </button>
              <button
                className={`toggle-btn ${jdInputMode === "file" ? "active" : ""}`}
                onClick={() => setJdInputMode("file")}
              >
                File
              </button>
            </div>

            {jdInputMode === "text" ? (
              <div className="text-input-wrapper">
                <textarea
                  id="jd-text-input"
                  className="jd-textarea"
                  placeholder="Paste your job description here..."
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                  rows="8"
                />
                <div className="text-meta">
                  <span>{jdText.length} characters</span>
                </div>
              </div>
            ) : (
              <>
                <label htmlFor="jd-upload">Select job description</label>
                <input
                  id="jd-upload"
                  type="file"
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={(e) => setJd(e.target.files[0])}
                />
                <div className="file-meta">
                  <span>{jd ? jd.name : "No job description selected yet."}</span>
                  {jd && <span>{(jd.size / 1024).toFixed(1)} KB</span>}
                </div>
              </>
            )}
          </div>
        </section>

        <button
          className="upload-submit-btn"
          onClick={handleUpload}
          disabled={loading}
        >
          {loading ? "Uploading..." : "Start Matching"}
        </button>

        <p className="upload-footnote">
          After uploading both files, you can proceed to the matcher page to view
          results.
        </p>
      </main>
    </div>
  );
}

export default Upload;