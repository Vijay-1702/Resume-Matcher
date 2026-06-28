import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Results from "./pages/Results";
import History from "./pages/History";
import Sidebar from "./components/Sidebar";
import "./components/Sidebar.css";

function ProtectedRoute({ element }) {
  const authUser = localStorage.getItem("authUser");
  return authUser ? element : <Navigate to="/" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Sidebar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/upload" element={<ProtectedRoute element={<Upload />} />} />
          <Route path="/results" element={<ProtectedRoute element={<Results />} />} />
          <Route path="/history" element={<ProtectedRoute element={<History />} />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;