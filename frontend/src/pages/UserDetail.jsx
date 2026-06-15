import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { userService } from '../services/userService';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';

const UserDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await userService.getById(id);
        setUser(response.data);
      } catch {
        console.error('Failed to fetch user');
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [id]);

  const handleDelete = async () => {
    if (!window.confirm('Confirmer la désactivation de cet utilisateur ?')) return;
    try {
      await userService.delete(id);
      navigate('/users');
    } catch {
      console.error('Failed to delete user');
    }
  };

  if (loading) return <Spinner />;
  if (!user) return <p className="text-gray-500">Utilisateur non trouvé</p>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">{user.full_name}</h1>
        <Button variant="secondary" onClick={() => navigate('/users')}>
          Retour
        </Button>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-gray-500">Email</label>
            <p className="text-gray-800">{user.email}</p>
          </div>
          <div>
            <label className="text-sm text-gray-500">Rôle</label>
            <p>
              <Badge variant={user.role === 'ADMIN' ? 'primary' : 'default'}>
                {user.role}
              </Badge>
            </p>
          </div>
          <div>
            <label className="text-sm text-gray-500">Département</label>
            <p className="text-gray-800">{user.department || '-'}</p>
          </div>
          <div>
            <label className="text-sm text-gray-500">Statut</label>
            <p>
              <Badge variant={user.is_active ? 'green' : 'red'}>
                {user.is_active ? 'Actif' : 'Inactif'}
              </Badge>
            </p>
          </div>
          <div>
            <label className="text-sm text-gray-500">Créé le</label>
            <p className="text-gray-800">
              {user.created_at
                ? new Date(user.created_at).toLocaleDateString('fr-FR')
                : '-'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        {user.is_active && (
          <Button variant="danger" onClick={handleDelete}>
            Désactiver le compte
          </Button>
        )}
      </div>
    </div>
  );
};

export default UserDetail;
