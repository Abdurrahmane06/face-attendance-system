import React from 'react';

const colorMap = {
  blue: { bg: 'bg-blue-50', text: 'text-blue-600', icon: 'text-blue-500' },
  green: { bg: 'bg-green-50', text: 'text-green-600', icon: 'text-green-500' },
  red: { bg: 'bg-red-50', text: 'text-red-600', icon: 'text-red-500' },
  yellow: { bg: 'bg-yellow-50', text: 'text-yellow-600', icon: 'text-yellow-500' },
};

const DashboardKPI = ({ title, value, color = 'blue' }) => {
  const style = colorMap[color] || colorMap.blue;

  return (
    <div className={`${style.bg} rounded-xl p-5`}>
      <p className={`text-sm font-medium ${style.text}`}>{title}</p>
      <p className={`text-3xl font-bold ${style.text} mt-1`}>{value}</p>
    </div>
  );
};

export default DashboardKPI;
