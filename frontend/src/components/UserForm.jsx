import React, { useRef, useState } from 'react';
import { userService } from '../services/userService';
import { faceService } from '../services/faceService';
import Button from './ui/Button';
import Input from './ui/Input';

const UserForm = ({ onSuccess, onCancel }) => {
  const [form, setForm] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'USER',
    department: '',
  });
  const [faceFile, setFaceFile] = useState(null);
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleFileChange = (e) => {
    setFaceFile(e.target.files[0] || null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setWarning('');
    setLoading(true);

    try {
      // Step 1: create the user account
      const { data: created } = await userService.create(form);

      // Step 2: optionally upload the face photo for encoding
      if (faceFile) {
        try {
          const formData = new FormData();
          formData.append('file', faceFile);
          await faceService.uploadForUser(created.id, formData);
        } catch (faceErr) {
          // User was created successfully — face upload failure is a non-fatal warning
          setWarning(
            `Compte créé, mais l'upload du visage a échoué : ${
              faceErr.response?.data?.detail || faceErr.message
            }`
          );
          onSuccess();
          return;
        }
      }

      onSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la création');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}
      {warning && (
        <div className="bg-yellow-50 text-yellow-700 px-4 py-3 rounded-lg text-sm">{warning}</div>
      )}

      <Input
        label="Nom complet"
        value={form.full_name}
        onChange={handleChange('full_name')}
        required
      />
      <Input
        label="Email"
        type="email"
        value={form.email}
        onChange={handleChange('email')}
        required
      />
      <Input
        label="Mot de passe"
        type="password"
        value={form.password}
        onChange={handleChange('password')}
        required
        minLength={8}
      />
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Rôle</label>
        <select
          value={form.role}
          onChange={handleChange('role')}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="USER">Utilisateur</option>
          <option value="ADMIN">Administrateur</option>
        </select>
      </div>
      <Input
        label="Département"
        value={form.department}
        onChange={handleChange('department')}
      />

      {/* Optional face photo — uploaded via POST /face/upload/{id} after user creation */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Photo du visage <span className="text-gray-400 font-normal">(optionnel)</span>
        </label>
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-primary-400 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          {faceFile ? (
            <p className="text-sm text-gray-700">{faceFile.name}</p>
          ) : (
            <p className="text-sm text-gray-400">Cliquer pour sélectionner une photo (JPEG/PNG)</p>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      <div className="flex gap-3 justify-end pt-2">
        <Button variant="secondary" onClick={onCancel} type="button">
          Annuler
        </Button>
        <Button type="submit" loading={loading}>
          Créer
        </Button>
      </div>
    </form>
  );
};

export default UserForm;
