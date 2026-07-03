import axios from "axios";

const api = axios.create({
  baseURL: "https://resume-matcher-uq8e.onrender.com/api",
});

export default api;