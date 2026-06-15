import React, { useState } from 'react';
import { userService } from '../services/userService';
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
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await userService.create(form);
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
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
