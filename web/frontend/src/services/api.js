import axios from 'axios';

// Don't set baseURL - let Vite proxy handle it
// In development, Vite will proxy /api requests to localhost:8000
// In production, set VITE_API_URL environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Authentication API
export const authAPI = {
  login: async (username, password) => {
    const response = await api.post('/api/auth/login', { username, password });
    return response.data;
  },

  getMe: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/api/auth/logout');
    localStorage.removeItem('token');
    return response.data;
  },
};

// Statistics API
export const statsAPI = {
  getOverview: async () => {
    const response = await api.get('/api/stats/overview');
    return response.data;
  },

  getDownloadsTrend: async (days = 7) => {
    const response = await api.get(`/api/stats/downloads-trend?days=${days}`);
    return response.data;
  },

  getMediaTypes: async () => {
    const response = await api.get('/api/stats/media-types');
    return response.data;
  },

  getTopUsers: async (limit = 10) => {
    const response = await api.get(`/api/stats/top-users?limit=${limit}`);
    return response.data;
  },
};

// Downloads API
export const downloadsAPI = {
  getHistory: async (params = {}) => {
    const response = await api.get('/api/downloads/history', { params });
    return response.data;
  },

  getActive: async () => {
    const response = await api.get('/api/downloads/active');
    return response.data;
  },

  getDetails: async (downloadId) => {
    const response = await api.get(`/api/downloads/${downloadId}`);
    return response.data;
  },

  cancel: async (downloadId) => {
    const response = await api.delete(`/api/downloads/${downloadId}`);
    return response.data;
  },
};

// Users API
export const usersAPI = {
  list: async () => {
    const response = await api.get('/api/users/');
    return response.data;
  },

  create: async (userData) => {
    const response = await api.post('/api/users/', userData);
    return response.data;
  },

  getDetails: async (userId) => {
    const response = await api.get(`/api/users/${userId}`);
    return response.data;
  },

  update: async (userId, data) => {
    const response = await api.patch(`/api/users/${userId}`, data);
    return response.data;
  },

  delete: async (userId) => {
    const response = await api.delete(`/api/users/${userId}`);
    return response.data;
  },
};

// Settings API
export const settingsAPI = {
  get: async () => {
    const response = await api.get('/api/settings/');
    return response.data;
  },

  update: async (data) => {
    const response = await api.patch('/api/settings/', data);
    return response.data;
  },

  testTMDB: async () => {
    const response = await api.post('/api/settings/test-tmdb');
    return response.data;
  },
};

export default api;
