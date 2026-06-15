import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import DashboardKPI from '../components/DashboardKPI';
import AttendanceChart from '../components/charts/AttendanceChart';
import PresenceDonut from '../components/charts/PresenceDonut';
import Spinner from '../components/ui/Spinner';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.get('/dashboard/stats');
      setStats(response.data);
    } catch {
      console.error('Failed to fetch dashboard stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Tableau de bord</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <DashboardKPI
          title="Total utilisateurs"
          value={stats?.total_users || 0}
          color="blue"
        />
        <DashboardKPI
          title="Présents aujourd'hui"
          value={stats?.present_today || 0}
          color="green"
        />
        <DashboardKPI
          title="Absents aujourd'hui"
          value={stats?.absent_today || 0}
          color="red"
        />
        <DashboardKPI
          title="Retards aujourd'hui"
          value={stats?.late_today || 0}
          color="yellow"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">
            Présences (7 derniers jours)
          </h3>
          <AttendanceChart data={stats?.attendance_last_7_days || []} />
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">
            Répartition aujourd'hui
          </h3>
          <PresenceDonut
            present={stats?.present_today || 0}
            absent={stats?.absent_today || 0}
            late={stats?.late_today || 0}
          />
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-4">
          Derniers pointages
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-3 font-medium">Utilisateur</th>
                <th className="pb-3 font-medium">Heure</th>
                <th className="pb-3 font-medium">Statut</th>
              </tr>
            </thead>
            <tbody>
              {(stats?.recent_checkins || []).map((checkin, idx) => (
                <tr key={idx} className="border-b last:border-0">
                  <td className="py-3 text-gray-800">{checkin.user_name}</td>
                  <td className="py-3 text-gray-600">
                    {checkin.time
                      ? new Date(checkin.time).toLocaleTimeString('fr-FR')
                      : '-'}
                  </td>
                  <td className="py-3">
                    <span
                      className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${
                        checkin.status === 'PRESENT'
                          ? 'bg-green-100 text-green-700'
                          : checkin.status === 'LATE'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {checkin.status === 'PRESENT'
                        ? 'Présent'
                        : checkin.status === 'LATE'
                        ? 'Retard'
                        : 'Absent'}
                    </span>
                  </td>
                </tr>
              ))}
              {(stats?.recent_checkins || []).length === 0 && (
                <tr>
                  <td colSpan={3} className="py-6 text-center text-gray-400">
                    Aucun pointage aujourd'hui
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
