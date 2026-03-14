/**
 * Monitoring API Service
 */

import { apiClient } from '../client';

export interface AlertCondition {
  metric_name: string;
  operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq';
  threshold: number;
  labels?: Record<string, string>;
  duration_seconds: number;
}

export interface AlertRule {
  id: string;
  name: string;
  description: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  enabled: boolean;
  conditions: AlertCondition[];
  condition_operator: 'AND' | 'OR';
  notification_channels: ('email' | 'webhook' | 'slack' | 'pagerduty')[];
  notification_recipients: string[];
  notification_template?: string;
  evaluation_interval_seconds: number;
  resolve_timeout_seconds?: number;
}

export interface Alert {
  id: string;
  rule_id: string;
  rule_name: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  labels: Record<string, string>;
  firing: boolean;
  started_at: string;
  resolved_at?: string;
  notified: boolean;
}

export interface SystemMetrics {
  cpu: {
    usage_percent: number;
    cores: number;
  };
  memory: {
    total_bytes: number;
    used_bytes: number;
    usage_percent: number;
  };
  gpu: Array<{
    gpu_id: string;
    usage_percent: number;
    memory_usage_percent: number;
    temperature_celsius: number;
  }>;
  database: {
    connections_total: number;
    connections_in_use: number;
    connections_idle: number;
  };
}

export interface NotificationSettings {
  channels: ('email' | 'webhook' | 'slack' | 'pagerduty')[];
  email_recipients: string[];
  slack_webhook_url?: string;
  webhook_url?: string;
}

export const monitoringApi = {
  /**
   * Get Prometheus metrics text format
   */
  getMetrics: () =>
    apiClient.get<string>('/api/v1/monitoring/metrics', {
      responseType: 'text',
    }),

  /**
   * Get system metrics summary
   */
  getSystemMetrics: () =>
    apiClient.get<SystemMetrics>('/api/v1/monitoring/system'),

  /**
   * List all alert rules
   */
  listRules: (params?: { severity?: string; enabled_only?: boolean }) =>
    apiClient.get<AlertRule[]>('/api/v1/monitoring/rules', { params }),

  /**
   * Get a specific alert rule
   */
  getRule: (id: string) =>
    apiClient.get<AlertRule>(`/api/v1/monitoring/rules/${id}`),

  /**
   * Create a new alert rule
   */
  createRule: (rule: Partial<AlertRule>) =>
    apiClient.post<AlertRule>('/api/v1/monitoring/rules', rule),

  /**
   * Update an alert rule
   */
  updateRule: (id: string, rule: Partial<AlertRule>) =>
    apiClient.put<AlertRule>(`/api/v1/monitoring/rules/${id}`, rule),

  /**
   * Delete an alert rule
   */
  deleteRule: (id: string) =>
    apiClient.delete(`/api/v1/monitoring/rules/${id}`),

  /**
   * Test an alert rule (evaluate without saving)
   */
  testRule: (rule: Partial<AlertRule>) =>
    apiClient.post<{ triggered: boolean; message: string }>(
      '/api/v1/monitoring/rules/test',
      rule,
    ),

  /**
   * Get active alerts
   */
  getActiveAlerts: (params?: { severity?: string }) =>
    apiClient.get<Alert[]>('/api/v1/monitoring/alerts/active', { params }),

  /**
   * Get alert history
   */
  getAlertHistory: (params?: {
    rule_id?: string;
    limit?: number;
    offset?: number;
  }) =>
    apiClient.get<Alert[]>('/api/v1/monitoring/alerts/history', { params }),

  /**
   * Get a specific alert
   */
  getAlert: (id: string) =>
    apiClient.get<Alert>(`/api/v1/monitoring/alerts/${id}`),

  /**
   * Resolve an alert
   */
  resolveAlert: (id: string) =>
    apiClient.post<{ success: boolean }>(`/api/v1/monitoring/alerts/${id}/resolve`),

  /**
   * Silence an alert
   */
  silenceAlert: (id: string, duration_minutes?: number) =>
    apiClient.post<{ success: boolean }>(`/api/v1/monitoring/alerts/${id}/silence`, {
      duration_minutes,
    }),

  /**
   * Get notification settings
   */
  getNotificationSettings: () =>
    apiClient.get<NotificationSettings>('/api/v1/monitoring/notifications/settings'),

  /**
   * Update notification settings
   */
  updateNotificationSettings: (settings: Partial<NotificationSettings>) =>
    apiClient.put<NotificationSettings>(
      '/api/v1/monitoring/notifications/settings',
      settings,
    ),

  /**
   * Test notification
   */
  testNotification: (channel: 'email' | 'webhook' | 'slack') =>
    apiClient.post<{ success: boolean; message: string }>(
      '/api/v1/monitoring/notifications/test',
      { channel },
    ),

  /**
   * Get dashboard data
   */
  getDashboardData: (timeRange?: string) =>
    apiClient.get<{
      metrics: SystemMetrics;
      active_alerts: Alert[];
      recent_alerts: Alert[];
      rules_count: number;
      firing_count: number;
    }>('/api/v1/monitoring/dashboard', { params: { time_range: timeRange } }),

  /**
   * Get metric history
   */
  getMetricHistory: (metricName: string, params?: {
    start?: string;
    end?: string;
    step?: string;
    labels?: Record<string, string>;
  }) =>
    apiClient.get<Array<{ timestamp: string; value: number }>>(
      `/api/v1/monitoring/metrics/${metricName}/history`,
      { params },
    ),
};
