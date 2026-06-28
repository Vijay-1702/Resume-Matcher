import { NavLink, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import "./Sidebar.css";

export default function Sidebar() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const raw = localStorage.getItem("authUser");
    try {
      setUser(raw ? JSON.parse(raw) : null);
    } catch (e) {
      setUser(null);
    }

    const onStorage = () => {
      const r = localStorage.getItem("authUser");
      try {
        setUser(r ? JSON.parse(r) : null);
      } catch (e) {
        setUser(null);
      }
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("authUser");
    localStorage.removeItem("sessionId");
    navigate("/");
  };

  if (!user) return null;

  const displayName = user.username || user.name || user.email || "User";

  return (
    <div className="sidebar-container">
      <div className="sidebar-trigger" aria-hidden>
        <span className="bar" />
        <span className="bar" />
        <span className="bar" />
      </div>

      <aside className="app-sidebar">
        <div className="sidebar-header">
          <div className="avatar">{displayName.charAt(0).toUpperCase()}</div>
          <div className="user-name">{displayName}</div>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/upload" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            Upload
          </NavLink>
          <NavLink to="/results" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            Results
          </NavLink>
          <NavLink to="/history" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            History
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </aside>
    </div>
  );
}
