import { useState } from "react";

function Upload() {
  const [resume, setResume] = useState(null);
  const [jd, setJd] = useState(null);

  return (
    <div>
      <h1>Upload Resume & Job Description</h1>

      <div>
        <h3>Resume Upload</h3>

        <input
          type="file"
          accept=".pdf,.doc,.docx"
          onChange={(e) => setResume(e.target.files[0])}
        />

        {resume && <p>{resume.name}</p>}
      </div>

      <br />

      <div>
        <h3>Job Description Upload</h3>

        <input
          type="file"
          accept=".pdf,.doc,.docx,.txt"
          onChange={(e) => setJd(e.target.files[0])}
        />

        {jd && <p>{jd.name}</p>}
      </div>
    </div>
  );
}

export default Upload;