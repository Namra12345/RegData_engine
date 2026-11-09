import { apiClient } from './client';

export const apiService = {
  // Authentication
  login: async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const response = await apiClient.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/users/me');
    return response.data;
  },

  // Overview & Metrics
  getDailySummary: async () => {
    const response = await apiClient.get('/overview/summary');
    return response.data;
  },

  // Compliance Alerts
  getAlerts: async (severity?: string, status?: string) => {
    const params = new URLSearchParams();
    if (severity) params.append('severity', severity);
    if (status) params.append('status_filter', status);
    const response = await apiClient.get(`/alerts?${params.toString()}`);
    return response.data;
  },

  updateAlertStatus: async (alertId: string, status: string) => {
    const response = await apiClient.patch(`/alerts/${alertId}`, { status });
    return response.data;
  },

  // Quality & Health
  getPipelineHealth: async () => {
    const response = await apiClient.get('/quality/health');
    return response.data;
  },

  getDataQualityMetrics: async () => {
    const response = await apiClient.get('/quality/metrics');
    return response.data;
  },

  // Audit & Reports
  getAuditLogs: async () => {
    const response = await apiClient.get('/audit/logs');
    return response.data;
  },

  getReports: async () => {
    const response = await apiClient.get('/reports');
    return response.data;
  },

  // Transaction Trace
  traceTransaction: async (transactionId: string) => {
    const response = await apiClient.get(`/trace/${transactionId}`);
    return response.data;
  },

  // System Health
  getSystemHealth: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // Security Status
  getSecurityStatus: async () => {
    const response = await apiClient.get('/security/status');
    return response.data;
  },
};