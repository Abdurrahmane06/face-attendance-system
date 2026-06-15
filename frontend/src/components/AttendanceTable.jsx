import React from 'react';
import Badge from './ui/Badge';

const statusMap = {
  PRESENT: { label: 'Présent', variant: 'green' },
  LATE: { label: 'Retard', variant: 'yellow' },
  ABSENT: { label: 'Absent', variant: 'red' },
};

const AttendanceTable = ({ records = [] }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b bg-gray-50">
            <th className="px-6 py-3 font-medium">Date</th>
            <th className="px-6 py-3 font-medium">Utilisateur</th>
            <th className="px-6 py-3 font-medium">Arrivée</th>
            <th className="px-6 py-3 font-medium">Départ</th>
            <th className="px-6 py-3 font-medium">Statut</th>
            <th className="px-6 py-3 font-medium">Méthode</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id} className="border-b last:border-0 hover:bg-gray-50">
              <td className="px-6 py-4 text-gray-800">
                {new Date(record.date).toLocaleDateString('fr-FR')}
              </td>
              <td className="px-6 py-4 font-medium text-gray-800">
                {record.user_name || record.user_id}
              </td>
              <td className="px-6 py-4 text-gray-600">
                {record.check_in
                  ? new Date(record.check_in).toLocaleTimeString('fr-FR')
                  : '-'}
              </td>
              <td className="px-6 py-4 text-gray-600">
                {record.check_out
                  ? new Date(record.check_out).toLocaleTimeString('fr-FR')
                  : '-'}
              </td>
              <td className="px-6 py-4">
                <Badge variant={statusMap[record.status]?.variant || 'default'}>
                  {statusMap[record.status]?.label || record.status}
                </Badge>
              </td>
              <td className="px-6 py-4 text-gray-600">{record.recognized_by}</td>
            </tr>
          ))}
          {records.length === 0 && (
            <tr>
              <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                Aucun enregistrement
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default AttendanceTable;
