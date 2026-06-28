import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import "./Home.css";

const getErrorMessage = (err, fallback) =>
  err.response?.data?.message ||
  err.response?.data?.detail ||
  err.message ||
  fallback;

const isValidPassword = (password) =>
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,}$/.test(password);

function Home() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("signin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const isSignup = mode === "signup";

  const handleModeChange = (nextMode) => {
    setMode(nextMode);
    setUsername("");
    setPassword("");
    setMessage("");
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    const trimmedUsername = username.trim();
    if (!trimmedUsername) {
      setError("Username is required.");
      return;
    }

    if (!password) {
      setError("Password is required.");
      return;
    }

    if (isSignup && !isValidPassword(password)) {
      setError("Password must be at least 8 characters with one uppercase letter, one lowercase letter, and one special character.");
      return;
    }

    setLoading(true);
    try {
      const endpoint = isSignup ? "auth/signup" : "auth/signin";
      const res = await api.post(endpoint, {
        username: trimmedUsername,
        password,
      });

      if (!res?.data?.success) {
        setError(res?.data?.message || "Authentication failed.");
        return;
      }

      localStorage.setItem("authUser", JSON.stringify(res.data.user));
      setMessage(isSignup ? "Account created. Opening upload page..." : "Signed in. Opening upload page...");
      setTimeout(() => navigate("/upload"), 500);
    } catch (err) {
      setError(getErrorMessage(err, "Authentication failed. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="auth-intro">
          <p className="auth-kicker">AI Resume Matcher</p>
          <h1 id="auth-title">{isSignup ? "Create your account" : "Welcome back"}</h1>
          <p>
            Sign in to upload your resume, compare it with a job description, and review your match results.
          </p>
        </div>

        <div className="auth-toggle" aria-label="Authentication mode">
          <button
            type="button"
            className={mode === "signin" ? "active" : ""}
            onClick={() => handleModeChange("signin")}
          >
            Sign In
          </button>
          <button
            type="button"
            className={mode === "signup" ? "active" : ""}
            onClick={() => handleModeChange("signup")}
          >
            Sign Up
          </button>
        </div>

        {error && <div className="auth-message error-message">{error}</div>}
        {message && <div className="auth-message success-message">{message}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Enter your Username"
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete={isSignup ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
          />

          {isSignup && (
            <p className={`password-rule ${password && isValidPassword(password) ? "valid" : ""}`}>
              Minimum 8 characters with uppercase, lowercase, and special character.
            </p>
          )}

          <button className="auth-submit" type="submit" disabled={loading}>
            {loading ? "Please wait..." : isSignup ? "Create Account" : "Sign In"}
          </button>
        </form>
      </section>
    </main>
  );
}

export default Home;
