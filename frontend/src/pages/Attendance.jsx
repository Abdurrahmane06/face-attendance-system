import React, { useState, useEffect, useCallback } from 'react';
import { attendanceService } from '../services/attendanceService';
import AttendanceTable from '../components/AttendanceTable';
import Input from '../components/ui/Input';
import Spinner from '../components/ui/Spinner';

const Attendance = () => {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const limit = 20;

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, limit };
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (statusFilter) params.status = statusFilter;
      const response = await attendanceService.getHistory(params);
      setRecords(response.data.items);
      setTotal(response.data.total);
    } catch {
      console.error('Failed to fetch attendance');
    } finally {
      setLoading(false);
    }
  }, [page, dateFrom, dateTo, statusFilter]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Historique des pointages</h1>

      <div className="flex flex-wrap gap-4">
        <Input
          type="date"
          value={dateFrom}
          onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
          label="Du"
        />
        <Input
          type="date"
          value={dateTo}
          onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
          label="Au"
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">Tous</option>
            <option value="PRESENT">Présent</option>
            <option value="LATE">Retard</option>
            <option value="ABSENT">Absent</option>
          </select>
        </div>
      </div>

      {loading ? (
        <Spinner />
      ) : (
        <>
          <AttendanceTable records={records} />
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">
                Page {page} sur {totalPages} ({total} total)
              </span>
              <div className="flex gap-2">
                <button
                  className="px-4 py-2 text-sm bg-white border rounded-lg disabled:opacity-50"
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Précédent
                </button>
                <button
                  className="px-4 py-2 text-sm bg-white border rounded-lg disabled:opacity-50"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Suivant
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Attendance;
