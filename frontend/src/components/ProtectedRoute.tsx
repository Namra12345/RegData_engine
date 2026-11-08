import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 text-slate-900">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-rose-700">403 - Access Forbidden</h1>
          <p className="mt-2 text-slate-600">Your role ({user.role}) does not have clearance for this view.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};