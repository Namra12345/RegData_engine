import React, { useEffect, useState } from 'react';
import { apiService } from '../api/services';
import { AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchAlerts = () => {
    setLoading(true);
    apiService.getAlerts(severityFilter, statusFilter)
      .then((data) => {
        setAlerts(data.items || data);
        setLoading(false);
      })
      .catch(() => {
        setAlerts([]);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchAlerts();
  }, [severityFilter, statusFilter]);

  const handleUpdateStatus = async (alertId: string, newStatus: string) => {
    try {
      await apiService.updateAlertStatus(alertId, newStatus);
      setActionMessage(`Alert ${alertId} successfully updated to ${newStatus}`);
      fetchAlerts();
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update alert status (Permission denied or invalid ID)');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Compliance Alerts Triage</h1>
          <p className="mt-1 text-sm text-slate-600">Review and manage compliance anomalies detected across data pipelines.</p>
        </div>
        <button
          onClick={fetchAlerts}
          className="mt-4 flex items-center space-x-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 sm:mt-0"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {actionMessage && (
        <div className="flex items-center space-x-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          <CheckCircle className="h-5 w-5 flex-shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Filters Bar */}
      <div className="flex flex-wrap gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-600">Filter by Severity</label>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          >
            <option value="">All Severities</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-600">Filter by Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="REVIEWED">REVIEWED</option>
            <option value="CLOSED">CLOSED</option>
          </select>
        </div>
      </div>

      {/* Alerts Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">Loading compliance alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="space-y-2 p-12 text-center text-slate-500">
            <AlertTriangle className="mx-auto h-8 w-8 text-slate-400" />
            <p>No compliance alerts found matching your filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-6 py-3">Alert ID</th>
                  <th className="px-6 py-3">Severity</th>
                  <th className="px-6 py-3">Description</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {alerts.map((alert: any) => (
                  <tr key={alert.id || alert.alert_id} className="transition-colors odd:bg-white even:bg-slate-50/60 hover:bg-indigo-50/60">
                    <td className="px-6 py-3.5 font-mono text-xs text-indigo-700">{alert.id || alert.alert_id}</td>
                    <td className="px-6 py-4">
                      <span className={`rounded-full px-3 py-1 text-xs font-semibold border ${
                        alert.severity === 'HIGH' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-amber-200 bg-amber-50 text-amber-700'
                      }`}>
                        {alert.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4">{alert.description || alert.message}</td>
                    <td className="px-6 py-3.5">
                      <span className="font-semibold text-slate-700">{alert.status}</span>
                    </td>
                    <td className="space-x-2 px-6 py-3.5 text-right">
                      <button
                        onClick={() => handleUpdateStatus(alert.id || alert.alert_id, 'REVIEWED')}
                        className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100"
                      >
                        Mark Reviewed
                      </button>
                      <button
                        onClick={() => handleUpdateStatus(alert.id || alert.alert_id, 'CLOSED')}
                        className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition hover:bg-emerald-100"
                      >
                        Close
                      </button>
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