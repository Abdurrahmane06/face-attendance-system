import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const COLORS = {
  present: '#22c55e',
  absent: '#ef4444',
  late: '#eab308',
};

const PresenceDonut = ({ present = 0, absent = 0, late = 0 }) => {
  const data = [
    { name: 'Présents', value: present, color: COLORS.present },
    { name: 'Absents', value: absent, color: COLORS.absent },
    { name: 'Retards', value: late, color: COLORS.late },
  ].filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[300px] text-gray-400">
        Aucune donnée aujourd'hui
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={70}
          outerRadius={110}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default PresenceDonut;
