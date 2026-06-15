import React from 'react';
import Badge from './ui/Badge';

const UserCard = ({ user }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm p-5 flex items-center gap-4">
      <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center text-primary-600 font-bold text-lg">
        {user.full_name?.charAt(0).toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-800 truncate">{user.full_name}</p>
        <p className="text-sm text-gray-500 truncate">{user.email}</p>
        {user.department && (
          <p className="text-xs text-gray-400 mt-0.5">{user.department}</p>
        )}
      </div>
      <Badge variant={user.role === 'ADMIN' ? 'primary' : 'default'}>
        {user.role}
      </Badge>
    </div>
  );
};

export default UserCard;
