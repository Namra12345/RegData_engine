import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, LogOut, User as UserIcon } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5 text-slate-900 shadow-sm md:px-6">
      <div className="flex items-center space-x-3">
        <Shield className="h-7 w-7 text-indigo-600" />
        <span className="text-lg font-bold tracking-tight text-slate-900 md:text-xl">RegData Engine</span>
      </div>

      <div className="flex items-center space-x-3 md:space-x-6">
        {user && (
          <div className="flex items-center space-x-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 md:px-4 md:py-2">
            <UserIcon className="h-5 w-5 text-indigo-600" />
            <div className="text-sm">
              <p className="font-semibold text-slate-800">{user.username}</p>
              <p className="text-xs uppercase tracking-wider text-indigo-700">{user.role}</p>
            </div>
          </div>
        )}

        <button
          onClick={logout}
          className="flex items-center space-x-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100 focus:outline-none focus:ring-2 focus:ring-rose-300"
          title="Logout"
        >
          <LogOut className="h-4 w-4" />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
};