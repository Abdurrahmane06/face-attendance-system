import api from './api';

/**
 * Service for authentication API calls.
 */
export const authService = {
  /** Register a new user (backend always assigns USER role). */
  register: (email, fullName, password) =>
    api.post('/auth/register', { email, full_name: fullName, password }),

  /**
   * Login with email and password.
   * @param {string} email
   * @param {string} password
   * @returns {Promise}
   */
  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  /**
   * Refresh access token.
   * @param {string} refreshToken
   * @returns {Promise}
   */
  refresh: (refreshToken) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),

  /**
   * Logout (revoke refresh token).
   * @param {string} refreshToken
   * @returns {Promise}
   */
  logout: (refreshToken) =>
    api.post('/auth/logout', { refresh_token: refreshToken }),

  /**
   * Get current user profile.
   * @returns {Promise}
   */
  getMe: () => api.get('/auth/me'),
};
