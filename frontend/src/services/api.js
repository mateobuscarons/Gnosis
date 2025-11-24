/**
 * API Service - Backend communication layer
 * Base URL: http://localhost:8000
 */

const API_BASE = 'http://localhost:8000';

// Helper function for fetch with error handling
async function apiCall(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API call failed: ${endpoint}`, error);
    throw error;
  }
}

// API Methods
export const api = {
  // Health check
  async healthCheck() {
    return apiCall('/');
  },

  // Get session state
  async getSession() {
    return apiCall('/session');
  },

  // Setup - Generate learning path
  async setup(learningGoal, experienceLevel) {
    return apiCall('/setup', {
      method: 'POST',
      body: JSON.stringify({
        learning_goal: learningGoal,
        experience_level: experienceLevel,
      }),
    });
  },

  // Approve learning path and generate challenges
  async approvePath(learningPath) {
    return apiCall('/path/approve', {
      method: 'POST',
      body: JSON.stringify({
        learning_path: learningPath,
      }),
    });
  },

  // Get challenge content
  async getChallenge(moduleNumber, challengeNumber) {
    return apiCall(`/challenge/${moduleNumber}/${challengeNumber}`);
  },

  // Submit code
  async submitCode(moduleNumber, challengeNumber, code) {
    return apiCall(`/challenge/${moduleNumber}/${challengeNumber}/submit`, {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  },

  // Get progress
  async getProgress() {
    return apiCall('/progress');
  },

  // Get all challenges metadata (titles, descriptions)
  async getChallengesMetadata() {
    return apiCall('/challenges/metadata');
  },

  // Get cached challenges
  async getCachedChallenges() {
    return apiCall('/challenges/cached');
  },

  // Reset system (for testing)
  async reset() {
    return apiCall('/reset', { method: 'DELETE' });
  },
};
