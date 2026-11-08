import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, LogOut, User as UserIcon } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-800 bg-gray-900 px-6 text-white shadow-md">
      <div className="flex items-center space-x-3">
        <Shield className="h-8 w-8 text-indigo-400" />
        <span className="text-xl font-bold tracking-wide">RegData Engine</span>
      </div>

      <div className="flex items-center space-x-6">
        {user && (
          <div className="flex items-center space-x-3 rounded-lg bg-gray-800 px-4 py-2 border border-gray-700">
            <UserIcon className="h-5 w-5 text-indigo-400" />
            <div className="text-sm">
              <p className="font-semibold">{user.username}</p>
              <p className="text-xs text-indigo-300 uppercase tracking-wider">{user.role}</p>
            </div>
          </div>
        )}

        <button
          onClick={logout}
          className="flex items-center space-x-2 rounded-lg bg-red-600/20 px-3 py-2 text-sm font-medium text-red-400 transition hover:bg-red-600/30 border border-red-500/30"
          title="Logout"
        >
          <LogOut className="h-4 w-4" />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
};