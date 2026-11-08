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
          <h1 className="text-2xl font-bold text-white">Compliance Alerts Triage</h1>
          <p className="text-sm text-gray-400">Review and manage compliance anomalies detected across data pipelines.</p>
        </div>
        <button
          onClick={fetchAlerts}
          className="mt-4 flex items-center space-x-2 rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700 sm:mt-0 border border-gray-700 transition"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {actionMessage && (
        <div className="flex items-center space-x-3 rounded-lg bg-emerald-500/10 p-4 border border-emerald-500/30 text-emerald-400 text-sm">
          <CheckCircle className="h-5 w-5 flex-shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Filters Bar */}
      <div className="flex flex-wrap gap-4 rounded-xl bg-gray-900 p-4 border border-gray-800">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Filter by Severity</label>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Filter by Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="REVIEWED">REVIEWED</option>
            <option value="CLOSED">CLOSED</option>
          </select>
        </div>
      </div>

      {/* Alerts Table */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading compliance alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center text-gray-400 space-y-2">
            <AlertTriangle className="mx-auto h-8 w-8 text-gray-500" />
            <p>No compliance alerts found matching your filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-3">Alert ID</th>
                  <th className="px-6 py-3">Severity</th>
                  <th className="px-6 py-3">Description</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {alerts.map((alert: any) => (
                  <tr key={alert.id || alert.alert_id} className="hover:bg-gray-800/50">
                    <td className="px-6 py-4 font-mono text-xs text-indigo-400">{alert.id || alert.alert_id}</td>
                    <td className="px-6 py-4">
                      <span className={`rounded-full px-3 py-1 text-xs font-semibold border ${
                        alert.severity === 'HIGH' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                      }`}>
                        {alert.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4">{alert.description || alert.message}</td>
                    <td className="px-6 py-4">
                      <span className="font-semibold text-gray-200">{alert.status}</span>
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        onClick={() => handleUpdateStatus(alert.id || alert.alert_id, 'REVIEWED')}
                        className="rounded bg-indigo-600/20 px-3 py-1 text-xs font-medium text-indigo-400 hover:bg-indigo-600/30 border border-indigo-500/30 transition"
                      >
                        Mark Reviewed
                      </button>
                      <button
                        onClick={() => handleUpdateStatus(alert.id || alert.alert_id, 'CLOSED')}
                        className="rounded bg-emerald-600/20 px-3 py-1 text-xs font-medium text-emerald-400 hover:bg-emerald-600/30 border border-emerald-500/30 transition"
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