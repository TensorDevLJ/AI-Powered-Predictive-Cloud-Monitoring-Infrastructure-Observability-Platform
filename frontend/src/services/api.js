import axios from "axios";

// Reads VITE_API_URL from the environment (see frontend/.env.example).
// Falls back to localhost only for zero-config local development - a
// production/Docker build must set VITE_API_URL at build time, otherwise
// the browser will try to call 127.0.0.1:8000 regardless of where the
// real backend is deployed.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API ERROR:", error);

    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");

      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => api.post("/auth/register", data),

  login: (username, password) => {
    const formData = new URLSearchParams();

    formData.append("username", username);
    formData.append("password", password);

    return api.post("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
  },

  getMe: () => api.get("/auth/me"),
};

export const metricsAPI = {
  getCPU: (id) => api.get(`/metrics/cpu/${id}`),
  getMemory: (id) => api.get(`/metrics/memory/${id}`),
  getDisk: (id) => api.get(`/metrics/disk/${id}`),
  getNetwork: (id) => api.get(`/metrics/network/${id}`),
  getAll: (id) => api.get(`/metrics/all/${id}`),
  getDashboardSummary: () =>
    api.get("/metrics/dashboard/summary"),
};

export const instancesAPI = {
  list: () => api.get("/instances/"),
  get: (id) => api.get(`/instances/${id}`),
  create: (data) => api.post("/instances/", data),
  update: (id, data) => api.put(`/instances/${id}`, data),
  delete: (id) => api.delete(`/instances/${id}`),
  getAlerts: (id) =>
    api.get(`/instances/${id}/alerts`),
};

export const mlAPI = {
  getSummary: (id) =>
    api.get(`/ml/dashboard/ml-summary/${id}`),

  detectAnomaly: (id) =>
    api.get(`/ml/anomaly/detect/${id}`),

  predictCPU: (id) =>
    api.get(`/ml/cpu/predict/${id}`),

  predictMemory: (id) =>
    api.get(`/ml/memory/predict/${id}`),

  getHealthScore: (id) =>
    api.get(`/ml/health-score/${id}`),

  predictFailure: (id) =>
    api.get(`/ml/failure/predict/${id}`),

  getAutoscaleRecommendation: (id) =>
    api.get(`/ml/autoscale/recommend/${id}`),
};

export default api;