import { useState, useCallback } from 'react';
import { attendanceService } from '../services/attendanceService';

/**
 * Hook for managing attendance operations.
 *
 * Provides check-in, check-out, and history fetching.
 *
 * @returns {{ attendance: Array, loading: boolean, error: string|null, checkIn: Function, checkOut: Function, fetchHistory: Function }}
 */
export const useAttendance = () => {
  const [attendance, setAttendance] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const checkIn = useCallback(async (userId, method = 'FACE') => {
    setLoading(true);
    setError(null);
    try {
      const response = await attendanceService.checkIn(userId, method);
      return response.data;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Check-in failed';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkOut = useCallback(async (userId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await attendanceService.checkOut(userId);
      return response.data;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Check-out failed';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async (params = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await attendanceService.getHistory(params);
      setAttendance(response.data.items || []);
      return response.data;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to fetch history';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return { attendance, loading, error, checkIn, checkOut, fetchHistory };
};
