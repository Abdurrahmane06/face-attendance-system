import React, { useState } from 'react';
import { attendanceService } from '../services/attendanceService';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';

const Reports = () => {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchReport = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await attendanceService.monthlyReport(year, month);
      setReport(response.data);
    } catch {
      setError('Erreur lors du chargement du rapport');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const response = await attendanceService.exportCsv(month, year);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `attendance_${year}_${String(month).padStart(2, '0')}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      setError('Erreur lors de l\'export');
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Rapports</h1>

      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Mois</label>
          <select
            value={month}
            onChange={(e) => setMonth(parseInt(e.target.value))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={m}>
                {m.toString().padStart(2, '0')}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Année</label>
          <select
            value={year}
            onChange={(e) => setYear(parseInt(e.target.value))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {[year - 1, year, year + 1].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
        <Button onClick={fetchReport} loading={loading}>
          Générer le rapport
        </Button>
        {report && (
          <Button variant="secondary" onClick={handleExport}>
            Exporter CSV
          </Button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {loading && <Spinner />}

      {report && !loading && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
          <h3 className="text-lg font-semibold">
            Rapport - {month.toString().padStart(2, '0')}/{year}
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-blue-600">Utilisateurs</p>
              <p className="text-2xl font-bold text-blue-700">{report.total_users}</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-sm text-green-600">Taux moyen</p>
              <p className="text-2xl font-bold text-green-700">{report.average_daily_rate}%</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Jours ouvrés</p>
              <p className="text-2xl font-bold text-gray-700">{report.total_days}</p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-3 font-medium">Date</th>
                  <th className="pb-3 font-medium">Présents</th>
                  <th className="pb-3 font-medium">Absents</th>
                  <th className="pb-3 font-medium">Retards</th>
                  <th className="pb-3 font-medium">Taux</th>
                </tr>
              </thead>
              <tbody>
                {report.daily_stats.map((day) => (
                  <tr key={day.date} className="border-b last:border-0">
                    <td className="py-3">{new Date(day.date).toLocaleDateString('fr-FR')}</td>
                    <td className="py-3 text-green-600">{day.present}</td>
                    <td className="py-3 text-red-600">{day.absent}</td>
                    <td className="py-3 text-yellow-600">{day.late}</td>
                    <td className="py-3">{day.rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Reports;
