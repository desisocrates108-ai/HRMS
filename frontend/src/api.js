import axios from 'axios';

const API = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  headers: { 'Content-Type': 'application/json' }
});

// Add auth token to all requests
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('servall_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Format error details and handle 401
API.interceptors.response.use(
  (response) => response,
  (error) => {
    // Format validation error details to strings
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      if (typeof detail !== 'string') {
        error.response.data.detail = Array.isArray(detail)
          ? detail.map(d => (d && typeof d.msg === 'string' ? d.msg : JSON.stringify(d))).join(', ')
          : String(detail);
      }
    }
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('servall_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default API;
