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
    <aside className="flex w-56 shrink-0 flex-col justify-between border-r border-slate-200 bg-white p-3 text-slate-700 sm:w-64 sm:p-4">
      <nav className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
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
                    ? 'bg-indigo-50 text-indigo-700 shadow-sm ring-1 ring-indigo-100'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              <Icon className="h-5 w-5" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
        <div className="mb-1 flex items-center space-x-2 font-semibold text-indigo-700">
          <Server className="h-4 w-4" />
          <span>AWS Athena / Neon</span>
        </div>
        <p>Live Data Stream Connected</p>
      </div>
    </aside>
  );
};