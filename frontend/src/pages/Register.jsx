import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: '',
    fullName: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }

    setLoading(true);
    try {
      await register(form.email, form.fullName, form.password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || "Échec de l'inscription");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Inscription</h2>
      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Nom complet"
          type="text"
          value={form.fullName}
          onChange={handleChange('fullName')}
          placeholder="Jean Dupont"
          required
        />
        <Input
          label="Email"
          type="email"
          value={form.email}
          onChange={handleChange('email')}
          placeholder="vous@exemple.com"
          required
        />
        <Input
          label="Mot de passe"
          type="password"
          value={form.password}
          onChange={handleChange('password')}
          placeholder="Min. 8 caractères"
          required
          minLength={8}
        />
        <Input
          label="Confirmer le mot de passe"
          type="password"
          value={form.confirmPassword}
          onChange={handleChange('confirmPassword')}
          placeholder="••••••••"
          required
        />
        <Button type="submit" loading={loading} className="w-full">
          S&apos;inscrire
        </Button>
      </form>
      <p className="text-center text-sm text-gray-500 mt-6">
        Déjà un compte ?{' '}
        <Link to="/login" className="text-primary-600 hover:underline">
          Se connecter
        </Link>
      </p>
    </div>
  );
};

export default Register;
