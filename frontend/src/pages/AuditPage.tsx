import React, { useEffect, useState } from 'react';
import { apiService } from '../api/services';
import { Search, ShieldCheck } from 'lucide-react';

export const AuditPage: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [transactionId, setTransactionId] = useState('');
  const [traceResult, setTraceResult] = useState<any | null>(null);
  const [traceError, setTraceError] = useState<string | null>(null);

  useEffect(() => {
    apiService.getAuditLogs()
      .then((res) => setLogs(res.items || res))
      .catch(() => setLogs([]));
  }, []);

  const handleTrace = (e: React.FormEvent) => {
    e.preventDefault();
    setTraceError(null);
    setTraceResult(null);

    apiService.traceTransaction(transactionId.trim())
      .then((res) => setTraceResult(res.transaction))
      .catch((err) => setTraceError(err.response?.data?.detail || 'Transaction not found or access denied'));
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Audit Trail & Transaction Lineage</h1>
        <p className="mt-1 text-sm text-slate-600">Inspect governance audit logs and trace PII-masked records.</p>
      </div>

      {/* Transaction Trace Inspector */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-2 text-lg font-semibold text-slate-900">Transaction Lineage Inspector</h3>
        <p className="mb-4 text-xs text-slate-600">Enter a transaction ID to trace records across data layers with role-based PII masking applied.</p>
        
        <form onSubmit={handleTrace} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <input
              type="text"
              required
              value={transactionId}
              onChange={(e) => setTransactionId(e.target.value)}
              placeholder="e.g. TXN-984210"
              className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-10 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:ring-offset-2"
          >
            Trace Record
          </button>
        </form>

        {traceError && (
          <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {traceError}
          </div>
        )}

        {traceResult && (
          <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-indigo-800">
            <div className="mb-2 flex items-center space-x-2 font-sans font-semibold text-emerald-700">
              <ShieldCheck className="h-4 w-4" />
              <span>Record Retrieved (PII Masking Enforced)</span>
            </div>
            <pre>{JSON.stringify(traceResult, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Audit Logs Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-slate-900">Governance Audit Trail Logs</h3>
        </div>
        {logs.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">No audit logs found or insufficient clearance.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3">User</th>
                  <th className="px-6 py-3">Action</th>
                  <th className="px-6 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log: any, idx: number) => (
                  <tr key={idx} className="transition-colors odd:bg-white even:bg-slate-50/60 hover:bg-indigo-50/60">
                    <td className="px-6 py-3.5 font-mono text-xs text-slate-500">{log.timestamp || 'N/A'}</td>
                    <td className="px-6 py-3.5 font-semibold text-slate-900">{log.username || log.user || 'System'}</td>
                    <td className="px-6 py-3.5 text-indigo-700">{log.action}</td>
                    <td className="px-6 py-3.5">{log.details || log.message || 'Audit event recorded'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};