import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AuthLayout from '../layouts/AuthLayout';
import MainLayout from '../layouts/MainLayout';
import ProtectedRoute from '../components/ProtectedRoute';
import Login from '../pages/Login';
import Register from '../pages/Register';
import Dashboard from '../pages/Dashboard';
import Users from '../pages/Users';
import UserDetail from '../pages/UserDetail';
import Attendance from '../pages/Attendance';
import FaceRecognition from '../pages/FaceRecognition';
import Reports from '../pages/Reports';
import NotFound from '../pages/NotFound';
import { useAuth } from '../hooks/useAuth';
import Spinner from '../components/ui/Spinner';

// Redirect to the appropriate home page based on role.
const RoleRedirect = () => {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === 'ADMIN' ? '/dashboard' : '/pointage'} replace />;
};

const AppRouter = () => {
  return (
    <Routes>
      {/* ── Public auth pages ───────────────────────────────── */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* ── Any authenticated user ───────────────────────────── */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/pointage" element={<FaceRecognition />} />
      </Route>

      {/* ── Admin-only pages ─────────────────────────────────── */}
      <Route
        element={
          <ProtectedRoute requiredRole="ADMIN">
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/employees" element={<Users />} />
        <Route path="/employees/:id" element={<UserDetail />} />
        <Route path="/attendance" element={<Attendance />} />
        <Route path="/reports" element={<Reports />} />
      </Route>

      {/* ── Default: role-based redirect ─────────────────────── */}
      <Route path="/" element={<RoleRedirect />} />
      <Route path="/404" element={<NotFound />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
};

export default AppRouter;
