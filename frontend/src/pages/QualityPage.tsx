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
        <h1 className="text-2xl font-bold text-white">Pipeline Health & Data Quality</h1>
        <p className="text-sm text-gray-400">Real-time execution batch telemetry and quarantine error distributions.</p>
      </div>

      {loading ? (
        <div className="p-8 text-center text-gray-400">Loading pipeline telemetry...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Pipeline Health */}
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 shadow-xl">
            <div className="flex items-center space-x-3 mb-4">
              <Activity className="h-6 w-6 text-indigo-400" />
              <h3 className="text-lg font-semibold text-white">Pipeline Execution Health</h3>
            </div>
            {health.length === 0 ? (
              <p className="text-sm text-gray-400">No health telemetry records available.</p>
            ) : (
              <div className="space-y-3">
                {health.map((item: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg bg-gray-800/50 p-4 border border-gray-800">
                    <div>
                      <p className="font-semibold text-white">Batch ID: {item.batch_id || 'N/A'}</p>
                      <p className="text-xs text-gray-400">Processed: {item.execution_time || item.timestamp || 'Recent'}</p>
                    </div>
                    <span className="flex items-center space-x-1 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>{item.status || 'SUCCESS'}</span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Data Quality Metrics */}
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 shadow-xl">
            <div className="flex items-center space-x-3 mb-4">
              <ShieldAlert className="h-6 w-6 text-yellow-400" />
              <h3 className="text-lg font-semibold text-white">Quarantine Error Distribution</h3>
            </div>
            {metrics.length === 0 ? (
              <p className="text-sm text-gray-400">No quarantine metrics available.</p>
            ) : (
              <div className="space-y-3">
                {metrics.map((item: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg bg-gray-800/50 p-4 border border-gray-800">
                    <div>
                      <p className="font-semibold text-white">Date: {item.quarantine_date || item.date || 'N/A'}</p>
                      <p className="text-xs text-yellow-400">Error Type: {item.error_type || 'Validation Failure'}</p>
                    </div>
                    <span className="rounded-lg bg-gray-800 px-3 py-1 text-sm font-bold text-white border border-gray-700">
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