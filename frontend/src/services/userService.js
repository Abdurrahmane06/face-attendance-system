import api from './api';

/**
 * Service for user management API calls (admin).
 */
export const userService = {
  /**
   * List users with pagination and search.
   * @param {object} params - { page, limit, search, department }
   * @returns {Promise}
   */
  list: (params = {}) => api.get('/users', { params }),

  /**
   * Get user by ID.
   * @param {string} id
   * @returns {Promise}
   */
  getById: (id) => api.get(`/users/${id}`),

  /**
   * Create a new user.
   * @param {object} data - { email, full_name, password, role, department }
   * @returns {Promise}
   */
  create: (data) => api.post('/users', data),

  /**
   * Update a user.
   * @param {string} id
   * @param {object} data - { full_name, email, role, department, is_active }
   * @returns {Promise}
   */
  update: (id, data) => api.put(`/users/${id}`, data),

  /**
   * Soft-delete a user.
   * @param {string} id
   * @returns {Promise}
   */
  delete: (id) => api.delete(`/users/${id}`),

  /**
   * Upload profile photo for a user.
   * @param {string} id
   * @param {FormData} formData
   * @returns {Promise}
   */
  uploadPhoto: (id, formData) =>
    api.post(`/users/${id}/photo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};
