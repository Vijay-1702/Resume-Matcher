import { useState } from "react";
import "./Upload.css";

function Upload() {
  const [resume, setResume] = useState(null);
  const [jd, setJd] = useState(null);
  const [jdInputMode, setJdInputMode] = useState("text");
  const [jdText, setJdText] = useState("");

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

        <p className="upload-footnote">
          After uploading both files, you can proceed to the matcher page to view
          results.
        </p>
      </main>
    </div>
  );
}

export default Upload;