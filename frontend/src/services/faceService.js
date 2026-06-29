import api from './api';

const MULTIPART = { headers: { 'Content-Type': 'multipart/form-data' } };

export const faceService = {
  /** Upload current user's own face encoding. */
  upload: (formData) => api.post('/face/upload', formData, MULTIPART),

  /** Admin: upload face encoding on behalf of another user. */
  uploadForUser: (userId, formData) =>
    api.post(`/face/upload/${userId}`, formData, MULTIPART),

  /** Match a captured frame against stored encodings. */
  recognize: (formData) => api.post('/face/recognize', formData, MULTIPART),

  /** List active encodings for a user. */
  getEncodings: (userId) => api.get(`/face/encodings/${userId}`),

  /** Soft-delete a face encoding. */
  deleteEncoding: (encodingId) => api.delete(`/face/encodings/${encodingId}`),
};
