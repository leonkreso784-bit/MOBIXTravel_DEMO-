/**
 * MOBIX - API Client Module
 * Rukuje svim API pozivima prema backendu
 */

import { CONFIG } from './config.js';
import { state } from './state.js';

class APIClient {
  constructor() {
    this.baseURL = CONFIG.API_BASE;
  }

  // Helper method za API pozive
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (state.authToken) {
      headers['Authorization'] = `Bearer ${state.authToken}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // Auth API
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${this.baseURL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    return await response.json();
  }

  async register(userData) {
    return this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData)
    });
  }

  async submitSurvey(surveyData) {
    return this.request('/api/auth/survey', {
      method: 'POST',
      body: JSON.stringify(surveyData)
    });
  }

  async getProfile() {
    return this.request('/api/auth/profile');
  }

  async updateProfile(profileData) {
    return this.request('/api/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData)
    });
  }

  async uploadProfileImage(formData) {
    const response = await fetch(`${this.baseURL}/api/auth/profile/image`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${state.authToken}`
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Image upload failed');
    }

    return await response.json();
  }

  async deleteProfileImage() {
    return this.request('/api/auth/profile/image', {
      method: 'DELETE'
    });
  }

  async deleteAccount() {
    return this.request('/api/auth/profile', {
      method: 'DELETE'
    });
  }

  // Chat API
  async sendMessage(message, sessionId) {
    return this.request('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        session_id: sessionId
      })
    });
  }

  // Places API
  async searchPlaces(query) {
    return this.request(`/api/places/search?q=${encodeURIComponent(query)}`);
  }

  // Plan API
  async createPlan(planData) {
    return this.request('/api/plan', {
      method: 'POST',
      body: JSON.stringify(planData)
    });
  }

  async getPlans() {
    return this.request('/api/plan');
  }
}

// Export singleton instance
export const api = new APIClient();
export default api;
