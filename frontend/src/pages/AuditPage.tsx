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
        <h1 className="text-2xl font-bold text-white">Audit Trail & Transaction Lineage</h1>
        <p className="text-sm text-gray-400">Inspect governance audit logs and trace PII-masked records.</p>
      </div>

      {/* Transaction Trace Inspector */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-white mb-2">Transaction Lineage Inspector</h3>
        <p className="text-xs text-gray-400 mb-4">Enter a transaction ID to trace records across data layers with role-based PII masking applied.</p>
        
        <form onSubmit={handleTrace} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
            <input
              type="text"
              required
              value={transactionId}
              onChange={(e) => setTransactionId(e.target.value)}
              placeholder="e.g. TXN-984210"
              className="w-full rounded-lg bg-gray-800 border border-gray-700 pl-10 pr-4 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow hover:bg-indigo-500 transition"
          >
            Trace Record
          </button>
        </form>

        {traceError && (
          <div className="mt-4 rounded-lg bg-red-500/10 p-3 border border-red-500/30 text-red-400 text-sm">
            {traceError}
          </div>
        )}

        {traceResult && (
          <div className="mt-4 rounded-lg bg-gray-800 p-4 border border-gray-700 font-mono text-xs text-indigo-300 overflow-x-auto">
            <div className="flex items-center space-x-2 text-emerald-400 mb-2 font-sans font-semibold">
              <ShieldCheck className="h-4 w-4" />
              <span>Record Retrieved (PII Masking Enforced)</span>
            </div>
            <pre>{JSON.stringify(traceResult, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Audit Logs Table */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden shadow-xl">
        <div className="border-b border-gray-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-white">Governance Audit Trail Logs</h3>
        </div>
        {logs.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No audit logs found or insufficient clearance.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3">User</th>
                  <th className="px-6 py-3">Action</th>
                  <th className="px-6 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {logs.map((log: any, idx: number) => (
                  <tr key={idx} className="hover:bg-gray-800/50">
                    <td className="px-6 py-4 font-mono text-xs text-gray-400">{log.timestamp || 'N/A'}</td>
                    <td className="px-6 py-4 font-semibold text-white">{log.username || log.user || 'System'}</td>
                    <td className="px-6 py-4 text-indigo-400">{log.action}</td>
                    <td className="px-6 py-4">{log.details || log.message || 'Audit event recorded'}</td>
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