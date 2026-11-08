import React, { useEffect, useState } from 'react';
import { apiService } from '../api/services';
import { Database, CheckCircle2, Layers, Activity } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiService.getDailySummary()
      .then((data) => {
        setSummary(data.items || data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'Failed to fetch Athena daily summary');
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Athena Analytics Dashboard</h1>
        <p className="text-sm text-gray-400">Live operational metrics and daily transaction aggregates from AWS Athena.</p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 p-4 border border-red-500/30 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-gray-900 p-6 border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Data Source</p>
              <p className="mt-1 text-lg font-bold text-white">AWS Athena / S3</p>
            </div>
            <Database className="h-8 w-8 text-indigo-400" />
          </div>
        </div>

        <div className="rounded-xl bg-gray-900 p-6 border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Pipeline Status</p>
              <p className="mt-1 text-lg font-bold text-emerald-400">Active & Operational</p>
            </div>
            <CheckCircle2 className="h-8 w-8 text-emerald-400" />
          </div>
        </div>

        <div className="rounded-xl bg-gray-900 p-6 border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">PII Protection</p>
              <p className="mt-1 text-lg font-bold text-indigo-400">Role-Based Masking</p>
            </div>
            <Activity className="h-8 w-8 text-indigo-400" />
          </div>
        </div>

        <div className="rounded-xl bg-gray-900 p-6 border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Metadata Store</p>
              <p className="mt-1 text-lg font-bold text-white">Neon PostgreSQL</p>
            </div>
            <Layers className="h-8 w-8 text-purple-400" />
          </div>
        </div>
      </div>

      {/* Daily Summary Table */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden shadow-xl">
        <div className="border-b border-gray-800 px-6 py-4">
          <h3 className="text-lg font-semibold text-white">Daily Transaction Summary (`v_daily_summary`)</h3>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading live Athena data...</div>
        ) : summary.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No summary records found in Athena.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-3">Date</th>
                  <th className="px-6 py-3">Total Transactions</th>
                  <th className="px-6 py-3">Total Volume</th>
                  <th className="px-6 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {summary.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-800/50">
                    <td className="px-6 py-4 font-medium text-white">{row.transaction_date || row.date || 'N/A'}</td>
                    <td className="px-6 py-4">{row.total_count || row.count || 0}</td>
                    <td className="px-6 py-4">${row.total_volume || row.volume || '0.00'}</td>
                    <td className="px-6 py-4">
                      <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
                        Verified
                      </span>
                    </td>
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