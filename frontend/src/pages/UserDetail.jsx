import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { userService } from '../services/userService';
import { faceService } from '../services/faceService';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';

const UserDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [encodings, setEncodings] = useState([]);
  const [userLoading, setUserLoading] = useState(true);
  const [encodingsLoading, setEncodingsLoading] = useState(true);
  const [faceFile, setFaceFile] = useState(null);
  const [faceUploading, setFaceUploading] = useState(false);
  const [faceError, setFaceError] = useState('');
  const [faceSuccess, setFaceSuccess] = useState('');
  const fileInputRef = useRef(null);

  const fetchUser = useCallback(async () => {
    try {
      const response = await userService.getById(id);
      setUser(response.data);
    } catch {
      console.error('Failed to fetch user');
    } finally {
      setUserLoading(false);
    }
  }, [id]);

  const fetchEncodings = useCallback(async () => {
    setEncodingsLoading(true);
    try {
      const response = await faceService.getEncodings(id);
      setEncodings(response.data.items || []);
    } catch {
      setEncodings([]);
    } finally {
      setEncodingsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchUser();
    fetchEncodings();
  }, [fetchUser, fetchEncodings]);

  const handleDelete = async () => {
    if (!window.confirm('Confirmer la désactivation de cet utilisateur ?')) return;
    try {
      await userService.delete(id);
      navigate('/employees');
    } catch {
      console.error('Failed to delete user');
    }
  };

  const handleDeleteEncoding = async (encodingId) => {
    if (!window.confirm('Supprimer cet encodage facial ?')) return;
    try {
      await faceService.deleteEncoding(encodingId);
      fetchEncodings();
    } catch {
      console.error('Failed to delete encoding');
    }
  };

  const handleFaceUpload = async (e) => {
    e.preventDefault();
    if (!faceFile) return;

    setFaceError('');
    setFaceSuccess('');
    setFaceUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', faceFile);
      await faceService.uploadForUser(id, formData);
      setFaceSuccess('Encodage facial ajouté avec succès.');
      setFaceFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchEncodings();
    } catch (err) {
      setFaceError(err.response?.data?.detail || 'Erreur lors de l\'upload');
    } finally {
      setFaceUploading(false);
    }
  };

  if (userLoading) return <Spinner />;
  if (!user) return <p className="text-gray-500">Utilisateur non trouvé</p>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">{user.full_name}</h1>
        <Button variant="secondary" onClick={() => navigate('/employees')}>
          Retour
        </Button>
      </div>

      {/* User info */}
      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-700 border-b pb-2">Informations</h2>
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
              {user.created_at ? new Date(user.created_at).toLocaleDateString('fr-FR') : '-'}
            </p>
          </div>
        </div>
      </div>

      {/* Face encodings */}
      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-700 border-b pb-2">
          Encodages faciaux
          {!encodingsLoading && (
            <span className="ml-2 text-sm font-normal text-gray-400">({encodings.length})</span>
          )}
        </h2>

        {encodingsLoading ? (
          <Spinner />
        ) : encodings.length === 0 ? (
          <p className="text-sm text-gray-400">Aucun encodage enregistré.</p>
        ) : (
          <ul className="divide-y">
            {encodings.map((enc) => (
              <li key={enc.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm text-gray-700">Encodage</p>
                  <p className="text-xs text-gray-400">
                    {enc.created_at
                      ? new Date(enc.created_at).toLocaleString('fr-FR')
                      : enc.id}
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteEncoding(enc.id)}
                  className="text-sm text-red-500 hover:text-red-700"
                >
                  Supprimer
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Upload new face photo */}
        <form onSubmit={handleFaceUpload} className="space-y-3 pt-2 border-t">
          <p className="text-sm font-medium text-gray-700">Ajouter une photo du visage</p>

          {faceError && (
            <div className="bg-red-50 text-red-700 px-3 py-2 rounded text-sm">{faceError}</div>
          )}
          {faceSuccess && (
            <div className="bg-green-50 text-green-700 px-3 py-2 rounded text-sm">{faceSuccess}</div>
          )}

          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-3 text-center cursor-pointer hover:border-primary-400 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            {faceFile ? (
              <p className="text-sm text-gray-700">{faceFile.name}</p>
            ) : (
              <p className="text-sm text-gray-400">Sélectionner JPEG ou PNG</p>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            onChange={(e) => { setFaceFile(e.target.files[0] || null); setFaceSuccess(''); }}
            className="hidden"
          />

          <Button type="submit" disabled={!faceFile || faceUploading} loading={faceUploading}>
            Enregistrer l'encodage
          </Button>
        </form>
      </div>

      {/* Danger zone */}
      {user.is_active && (
        <div className="flex gap-3">
          <Button variant="danger" onClick={handleDelete}>
            Désactiver le compte
          </Button>
        </div>
      )}
    </div>
  );
};

export default UserDetail;
