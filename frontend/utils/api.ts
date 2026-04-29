import axios from 'axios';

// Create axios instance with default configuration
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api',
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid, clear local storage and redirect to login
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const predictionAPI = {
  // Classify food image
  classifyImage: (formData: FormData) => {
    return api.post('/predict', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // Get food classes
  getFoodClasses: () => {
    return api.get('/predict/classes');
  },

  // Get classification history
  getClassificationHistory: (userId: string, page?: number, limit?: number) => {
    const params = new URLSearchParams();
    if (page) params.append('page', page.toString());
    if (limit) params.append('limit', limit.toString());
    params.append('user_id', userId);
    
    return api.get(`/predict/history?${params}`);
  },

  // Submit feedback on classification
  submitFeedback: (classificationId: string, isCorrect: boolean, correctLabel?: string) => {
    return api.post('/predict/feedback', {
      classification_id: classificationId,
      is_correct: isCorrect,
      correct_label: correctLabel,
    });
  },

  // Get prediction statistics
  getPredictionStats: (timeframe?: string) => {
    const params = timeframe ? `?timeframe=${timeframe}` : '';
    return api.get(`/predict/stats${params}`);
  },
};

export const userAPI = {
  // Register new user
  register: (userData: {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => {
    return api.post('/users/register', userData);
  },

  // Login user
  login: (credentials: { email: string; password: string }) => {
    return api.post('/users/login', credentials);
  },

  // Get user profile
  getProfile: () => {
    return api.get('/users/profile');
  },

  // Update user profile
  updateProfile: (profileData: {
    first_name?: string;
    last_name?: string;
    avatar_url?: string;
  }) => {
    return api.put('/users/profile', profileData);
  },
};

export const foodAPI = {
  // Get all food categories
  getFoodCategories: () => {
    return api.get('/foods');
  },

  // Get specific food category
  getFoodCategory: (id: string) => {
    return api.get(`/foods/${id}`);
  },

  // Get classifications for food category
  getFoodClassifications: (id: string, page?: number, limit?: number) => {
    const params = new URLSearchParams();
    if (page) params.append('page', page.toString());
    if (limit) params.append('limit', limit.toString());
    
    return api.get(`/foods/${id}/classifications?${params}`);
  },
};

// Health check
export const healthCheck = () => {
  return api.get('/health', { baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000' });
};

export default api;
