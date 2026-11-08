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
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Security & RBAC Governance</h1>
        <p className="mt-1 text-sm text-slate-600">Active security policies, clearance enforcement, and role permissions.</p>
      </div>

      {error ? (
        <div className="flex items-center space-x-3 rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
          <Lock className="h-6 w-6 flex-shrink-0" />
          <span>{error}</span>
        </div>
      ) : !status ? (
        <div className="p-8 text-center text-sm text-slate-500">Loading security configuration...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center space-x-3">
              <ShieldCheck className="h-6 w-6 text-indigo-600" />
              <h3 className="text-lg font-semibold text-slate-900">Active Policy Status</h3>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="text-slate-600">RBAC Enforcement</span>
                <span className="flex items-center space-x-1 font-semibold text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{status.rbac_enforced ? 'Enabled' : 'Disabled'}</span>
                </span>
              </div>
              <div className="flex justify-between rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="text-slate-600">PII Masking Pipeline</span>
                <span className="flex items-center space-x-1 font-semibold text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{status.pii_masking_active ? 'Active' : 'Inactive'}</span>
                </span>
              </div>
              <div className="flex justify-between rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="text-slate-600">Your Current Clearance</span>
                <span className="font-mono font-bold uppercase text-indigo-700">{status.user_clearance}</span>
              </div>
            </div>
          </div>

          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center space-x-3">
              <Lock className="h-6 w-6 text-violet-600" />
              <h3 className="text-lg font-semibold text-slate-900">Supported RBAC Roles</h3>
            </div>
            <div className="flex flex-wrap gap-2 pt-2">
              {status.supported_roles?.map((role: string, idx: number) => (
                <span key={idx} className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-700">
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