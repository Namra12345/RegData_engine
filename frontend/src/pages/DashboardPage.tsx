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
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Athena Analytics Dashboard</h1>
        <p className="mt-1 text-sm text-slate-600">Live operational metrics and daily transaction aggregates from AWS Athena.</p>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md md:p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Data Source</p>
              <p className="mt-1 text-lg font-bold text-slate-900">AWS Athena / S3</p>
            </div>
            <Database className="h-8 w-8 text-indigo-600" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md md:p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Pipeline Status</p>
              <p className="mt-1 text-lg font-bold text-emerald-700">Active & Operational</p>
            </div>
            <CheckCircle2 className="h-8 w-8 text-emerald-600" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md md:p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">PII Protection</p>
              <p className="mt-1 text-lg font-bold text-indigo-700">Role-Based Masking</p>
            </div>
            <Activity className="h-8 w-8 text-indigo-600" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md md:p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Metadata Store</p>
              <p className="mt-1 text-lg font-bold text-slate-900">Neon PostgreSQL</p>
            </div>
            <Layers className="h-8 w-8 text-violet-600" />
          </div>
        </div>
      </div>

      {/* Daily Summary Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-slate-900">Daily Transaction Summary (`v_daily_summary`)</h3>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">Loading live Athena data...</div>
        ) : summary.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">No summary records found in Athena.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-6 py-3">Date</th>
                  <th className="px-6 py-3">Total Transactions</th>
                  <th className="px-6 py-3">Total Volume</th>
                  <th className="px-6 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {summary.map((row, idx) => (
                  <tr key={idx} className="transition-colors odd:bg-white even:bg-slate-50/60 hover:bg-indigo-50/60">
                    <td className="px-6 py-3.5 font-medium text-slate-900">{row.transaction_date || row.date || 'N/A'}</td>
                    <td className="px-6 py-3.5">{row.total_count || row.count || 0}</td>
                    <td className="px-6 py-3.5">${row.total_volume || row.volume || '0.00'}</td>
                    <td className="px-6 py-3.5">
                      <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
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