import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, AlertTriangle, Activity, FileText, Lock, Server } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { name: 'Overview', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Compliance Alerts', path: '/alerts', icon: AlertTriangle },
    { name: 'Pipeline Health', path: '/quality', icon: Activity },
    { name: 'Audit & Reports', path: '/audit', icon: FileText },
    { name: 'Security & RBAC', path: '/security', icon: Lock },
  ];

  return (
    <aside className="w-64 border-r border-gray-800 bg-gray-900 text-gray-300 flex flex-col justify-between p-4">
      <nav className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Governance Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <Icon className="h-5 w-5" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="rounded-lg bg-gray-800/50 p-3 border border-gray-800 text-xs text-gray-400">
        <div className="flex items-center space-x-2 text-indigo-400 font-semibold mb-1">
          <Server className="h-4 w-4" />
          <span>AWS Athena / Neon</span>
        </div>
        <p>Live Data Stream Connected</p>
      </div>
    </aside>
  );
};