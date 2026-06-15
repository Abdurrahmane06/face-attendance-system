import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';

const NotFound = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-primary-600">404</h1>
        <p className="text-xl text-gray-600 mt-4">Page non trouvée</p>
        <p className="text-gray-500 mt-2">La page que vous cherchez n'existe pas.</p>
        <Link to="/dashboard">
          <Button className="mt-6">Retour au tableau de bord</Button>
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
