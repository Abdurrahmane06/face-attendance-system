import api from './api';

/**
 * Service for attendance API calls.
 */
export const attendanceService = {
  /**
   * Check in (arrival).
   * @param {string} userId
   * @param {string} [method='FACE']
   * @returns {Promise}
   */
  checkIn: (userId, method = 'FACE') =>
    api.post('/attendance/check-in', { user_id: userId, method }),

  /**
   * Check out (departure).
   * @param {string} userId
   * @returns {Promise}
   */
  checkOut: (userId) =>
    api.post('/attendance/check-out', { user_id: userId }),

  /**
   * Get attendance history with filters.
   * @param {object} params - { user_id, date_from, date_to, status, page, limit }
   * @returns {Promise}
   */
  getHistory: (params = {}) => api.get('/attendance', { params }),

  /**
   * Get a single attendance record.
   * @param {string} id
   * @returns {Promise}
   */
  getById: (id) => api.get(`/attendance/${id}`),

  /**
   * Update attendance record (admin).
   * @param {string} id
   * @param {object} data - { check_in, check_out, status, notes }
   * @returns {Promise}
   */
  update: (id, data) => api.put(`/attendance/${id}`, data),

  /**
   * Get daily report.
   * @param {string} date - YYYY-MM-DD
   * @returns {Promise}
   */
  dailyReport: (date) => api.get('/attendance/report/daily', { params: { report_date: date } }),

  /**
   * Get monthly report.
   * @param {number} year
   * @param {number} month
   * @returns {Promise}
   */
  monthlyReport: (year, month) =>
    api.get('/attendance/report/monthly', { params: { year, month } }),

  /**
   * Export attendance as CSV.
   * @param {number} month
   * @param {number} year
   * @returns {Promise}
   */
  exportCsv: (month, year) =>
    api.get('/attendance/report/export', {
      params: { month, year },
      responseType: 'blob',
    }),
};
