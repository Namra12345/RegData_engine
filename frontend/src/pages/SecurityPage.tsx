import React, { useEffect, useState } from 'react';
import { apiService } from '../api/services';
import { Lock, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const SecurityPage: React.FC = () => {
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiService.getSecurityStatus()
      .then((res) => setStatus(res))
      .catch((err) => setError(err.response?.data?.detail || 'Access restricted to administrators and compliance officers.'));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Security & RBAC Governance</h1>
        <p className="text-sm text-gray-400">Active security policies, clearance enforcement, and role permissions.</p>
      </div>

      {error ? (
        <div className="rounded-xl bg-red-500/10 p-6 border border-red-500/30 text-red-400 flex items-center space-x-3">
          <Lock className="h-6 w-6 flex-shrink-0" />
          <span>{error}</span>
        </div>
      ) : !status ? (
        <div className="p-8 text-center text-gray-400">Loading security configuration...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 shadow-xl space-y-4">
            <div className="flex items-center space-x-3">
              <ShieldCheck className="h-6 w-6 text-indigo-400" />
              <h3 className="text-lg font-semibold text-white">Active Policy Status</h3>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between rounded-lg bg-gray-800/50 p-3 border border-gray-800">
                <span className="text-gray-400">RBAC Enforcement</span>
                <span className="font-semibold text-emerald-400 flex items-center space-x-1">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{status.rbac_enforced ? 'Enabled' : 'Disabled'}</span>
                </span>
              </div>
              <div className="flex justify-between rounded-lg bg-gray-800/50 p-3 border border-gray-800">
                <span className="text-gray-400">PII Masking Pipeline</span>
                <span className="font-semibold text-emerald-400 flex items-center space-x-1">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{status.pii_masking_active ? 'Active' : 'Inactive'}</span>
                </span>
              </div>
              <div className="flex justify-between rounded-lg bg-gray-800/50 p-3 border border-gray-800">
                <span className="text-gray-400">Your Current Clearance</span>
                <span className="font-mono font-bold text-indigo-400 uppercase">{status.user_clearance}</span>
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 shadow-xl space-y-4">
            <div className="flex items-center space-x-3">
              <Lock className="h-6 w-6 text-purple-400" />
              <h3 className="text-lg font-semibold text-white">Supported RBAC Roles</h3>
            </div>
            <div className="flex flex-wrap gap-2 pt-2">
              {status.supported_roles?.map((role: string, idx: number) => (
                <span key={idx} className="rounded-lg bg-indigo-600/10 px-3 py-1.5 text-xs font-semibold text-indigo-400 border border-indigo-500/20 uppercase tracking-wider">
                  {role}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};