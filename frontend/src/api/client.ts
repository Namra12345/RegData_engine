import axios from 'axios';

// Point to your FastAPI backend running on port 8000
const API_BASE_URL = `http://${window.location.hostname}:8000/api`;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to automatically attach JWT Bearer token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('regdata_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token expiration / unauthorized access
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('regdata_token');
      localStorage.removeItem('regdata_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);