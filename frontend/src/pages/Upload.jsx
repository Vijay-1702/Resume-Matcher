import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import "./Upload.css";

const workflowSteps = [
  "Resume Upload",
  "JD Upload",
  "Text Extraction",
  "Skill Extraction",
  "Matching",
  "Results Screen",
];

const getErrorMessage = (err, fallback) =>
  err.response?.data?.message ||
  err.response?.data?.detail ||
  err.message ||
  fallback;

function Upload() {
  const navigate = useNavigate();
  const [resume, setResume] = useState(null);
  const [jd, setJd] = useState(null);
  const [jdInputMode, setJdInputMode] = useState("text");
  const [jdText, setJdText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [currentStep, setCurrentStep] = useState(0);

  const handleUpload = async () => {
    setError("");
    setSuccess("");
    setCurrentStep(0);

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
      // Step 1: Upload resume
      setCurrentStep(1);
      const resumeFormData = new FormData();
      resumeFormData.append("file", resume);
      const resumeResponse = await api.post("/workflow/upload/resume", resumeFormData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (!resumeResponse.data.success) {
        setError(resumeResponse.data.message || "Failed to upload resume");
        setLoading(false);
        return;
      }

      const sessionId = resumeResponse.data.session_id;
      setCurrentStep(2);
      setSuccess("Resume uploaded. Processing job description...");

      // Step 2: Upload JD and get results
      let jdResponse;
      if (jdInputMode === "text") {
        jdResponse = await api.post(
          `/workflow/upload/job-description/text?session_id=${sessionId}`,
          { text: jdText }
        );
      } else {
        const jdFormData = new FormData();
        jdFormData.append("file", jd);
        jdResponse = await api.post(
          `/workflow/upload/job-description?session_id=${sessionId}`,
          jdFormData,
          { headers: { "Content-Type": "multipart/form-data" } }
        );
      }

      if (!jdResponse.data.success) {
        setError(jdResponse.data.message || "Failed to process job description");
        setLoading(false);
        return;
      }

      setCurrentStep(5);

      // Store session_id in localStorage for Results page
      localStorage.setItem("sessionId", sessionId);

      setSuccess("Match complete! Redirecting to results...");
      setTimeout(() => {
        setCurrentStep(6);
        navigate("/results");
      }, 1500);
    } catch (err) {
      const errorMessage = getErrorMessage(err, "Upload failed. Please try again.");
      setError(errorMessage);
      console.error("Upload error:", err);
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
            the matching process. Resumes support PDF and DOCX. Job descriptions
            support PDF, DOCX, TXT, or pasted text.
          </p>
        </div>

        <section className="upload-block">
          {error && <div className="message error-message">{error}</div>}
          {success && <div className="message success-message">{success}</div>}

          <ol className="workflow-steps" aria-label="Resume matching workflow">
            {workflowSteps.map((step, index) => {
              const stepNumber = index + 1;
              const status =
                currentStep > stepNumber
                  ? "complete"
                  : currentStep === stepNumber
                    ? "active"
                    : "";

              return (
                <li key={step} className={`workflow-step ${status}`}>
                  <span className="workflow-index">{stepNumber}</span>
                  <span>{step}</span>
                </li>
              );
            })}
          </ol>

          <div className="upload-control">
            <h3>Resume Upload</h3>
            <label htmlFor="resume-upload">Select resume</label>
            <input
              id="resume-upload"
              type="file"
              accept=".pdf,.docx"
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
          The app extracts text from both inputs, compares detected skills, calculates
          the match, and opens the results screen automatically.
        </p>
      </main>
    </div>
  );
}

export default Upload;
