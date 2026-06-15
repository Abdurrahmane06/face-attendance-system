import api from './api';

/**
 * Service for face recognition API calls.
 */
export const faceService = {
  /**
   * Upload a face image to register encoding.
   * @param {FormData} formData
   * @returns {Promise}
   */
  upload: (formData) =>
    api.post('/face/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  /**
   * Recognize a face from an uploaded image.
   * @param {FormData} formData
   * @returns {Promise}
   */
  recognize: (formData) =>
    api.post('/face/recognize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  /**
   * Get face encodings for a user.
   * @param {string} userId
   * @returns {Promise}
   */
  getEncodings: (userId) => api.get(`/face/encodings/${userId}`),

  /**
   * Delete a face encoding.
   * @param {string} encodingId
   * @returns {Promise}
   */
  deleteEncoding: (encodingId) => api.delete(`/face/encodings/${encodingId}`),
};
