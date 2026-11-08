import React, { useEffect, useState } from 'react';
import { apiService } from '../api/services';
import { Activity, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const QualityPage: React.FC = () => {
  const [health, setHealth] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiService.getPipelineHealth(),
      apiService.getDataQualityMetrics(),
    ])
      .then(([healthRes, metricsRes]) => {
        setHealth(healthRes.items || healthRes);
        setMetrics(metricsRes.items || metricsRes);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Pipeline Health & Data Quality</h1>
        <p className="mt-1 text-sm text-slate-600">Real-time execution batch telemetry and quarantine error distributions.</p>
      </div>

      {loading ? (
        <div className="p-8 text-center text-sm text-slate-500">Loading pipeline telemetry...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Pipeline Health */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center space-x-3 mb-4">
              <Activity className="h-6 w-6 text-indigo-600" />
              <h3 className="text-lg font-semibold text-slate-900">Pipeline Execution Health</h3>
            </div>
            {health.length === 0 ? (
              <p className="text-sm text-slate-500">No health telemetry records available.</p>
            ) : (
              <div className="space-y-3">
                {health.map((item: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div>
                      <p className="font-semibold text-slate-900">Batch ID: {item.batch_id || 'N/A'}</p>
                      <p className="text-xs text-slate-500">Processed: {item.execution_time || item.timestamp || 'Recent'}</p>
                    </div>
                    <span className="flex items-center space-x-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>{item.status || 'SUCCESS'}</span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Data Quality Metrics */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center space-x-3 mb-4">
              <ShieldAlert className="h-6 w-6 text-amber-600" />
              <h3 className="text-lg font-semibold text-slate-900">Quarantine Error Distribution</h3>
            </div>
            {metrics.length === 0 ? (
              <p className="text-sm text-slate-500">No quarantine metrics available.</p>
            ) : (
              <div className="space-y-3">
                {metrics.map((item: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div>
                      <p className="font-semibold text-slate-900">Date: {item.quarantine_date || item.date || 'N/A'}</p>
                      <p className="text-xs text-amber-700">Error Type: {item.error_type || 'Validation Failure'}</p>
                    </div>
                    <span className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm font-bold text-slate-800">
                      {item.error_count || item.count || 0} issues
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};