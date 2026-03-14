/**
 * Monitoring Store - Zustand state management for monitoring and alerting
 */

import { create } from 'zustand';
import { monitoringApi } from '@/services/api/monitoring';

// Types
export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical';
export type AlertState = 'firing' | 'resolved' | 'pending' | 'silenced';
export type MetricOperator = 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq';
export type NotificationChannel = 'email' | 'webhook' | 'slack' | 'pagerduty';

export interface AlertCondition {
  metric_name: string;
  operator: MetricOperator;
  threshold: number;
  labels?: Record<string, string>;
  duration_seconds: number;
}

export interface AlertRule {
  id: string;
  name: string;
  description: string;
  severity: AlertSeverity;
  enabled: boolean;
  conditions: AlertCondition[];
  condition_operator: 'AND' | 'OR';
  notification_channels: NotificationChannel[];
  notification_recipients: string[];
  notification_template?: string;
  evaluation_interval_seconds: number;
  resolve_timeout_seconds?: number;
  state: AlertState;
  firing_since?: string;
  alert_count: number;
  last_evaluated?: string;
  last_notification?: string;
  silenced_until?: string;
  silence_tags: string[];
}

export interface Alert {
  id: string;
  rule_id: string;
  rule_name: string;
  severity: AlertSeverity;
  message: string;
  labels: Record<string, string>;
  firing: boolean;
  started_at: string;
  resolved_at?: string;
  notified: boolean;
}

export interface MetricValue {
  name: string;
  value: number;
  labels?: Record<string, string>;
  timestamp: string;
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

interface MonitoringState {
  // Alert Rules
  rules: AlertRule[];
  rulesLoading: boolean;
  rulesError: string | null;

  // Alerts
  alerts: Alert[];
  alertsLoading: boolean;
  alertsError: string | null;

  // Metrics
  metricsText: string;
  metricsLoading: boolean;

  // System Metrics
  systemMetrics: SystemMetrics | null;

  // Actions
  fetchRules: () => Promise<void>;
  fetchAlerts: () => Promise<void>;
  fetchMetrics: () => Promise<void>;
  fetchSystemMetrics: () => Promise<void>;
  createRule: (rule: Partial<AlertRule>) => Promise<void>;
  updateRule: (id: string, rule: Partial<AlertRule>) => Promise<void>;
  deleteRule: (id: string) => Promise<void>;
  toggleRule: (id: string, enabled: boolean) => Promise<void>;
  resolveAlert: (id: string) => Promise<void>;
  silenceAlert: (id: string, durationMinutes?: number) => Promise<void>;
}

export const useMonitoringStore = create<MonitoringState>((set, get) => ({
  // Initial state
  rules: [],
  rulesLoading: false,
  rulesError: null,
  alerts: [],
  alertsLoading: false,
  alertsError: null,
  metricsText: '',
  metricsLoading: false,
  systemMetrics: null,

  // Fetch alert rules
  fetchRules: async () => {
    set({ rulesLoading: true, rulesError: null });
    try {
      const response = await monitoringApi.listRules();
      set({ rules: response.data || [], rulesLoading: false });
    } catch (error: any) {
      set({
        rulesError: error.message || 'Failed to fetch alert rules',
        rulesLoading: false,
      });
    }
  },

  // Fetch active alerts
  fetchAlerts: async () => {
    set({ alertsLoading: true, alertsError: null });
    try {
      const response = await monitoringApi.getActiveAlerts();
      set({ alerts: response.data || [], alertsLoading: false });
    } catch (error: any) {
      set({
        alertsError: error.message || 'Failed to fetch alerts',
        alertsLoading: false,
      });
    }
  },

  // Fetch Prometheus metrics
  fetchMetrics: async () => {
    set({ metricsLoading: true });
    try {
      const response = await monitoringApi.getMetrics();
      set({ metricsText: response.data || '', metricsLoading: false });
    } catch (error) {
      set({ metricsLoading: false });
    }
  },

  // Fetch system metrics summary
  fetchSystemMetrics: async () => {
    try {
      const response = await monitoringApi.getSystemMetrics();
      set({ systemMetrics: response.data });
    } catch (error) {
      console.error('Failed to fetch system metrics:', error);
    }
  },

  // Create alert rule
  createRule: async (rule) => {
    try {
      await monitoringApi.createRule(rule);
      await get().fetchRules();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to create alert rule');
    }
  },

  // Update alert rule
  updateRule: async (id, rule) => {
    try {
      await monitoringApi.updateRule(id, rule);
      await get().fetchRules();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to update alert rule');
    }
  },

  // Delete alert rule
  deleteRule: async (id) => {
    try {
      await monitoringApi.deleteRule(id);
      await get().fetchRules();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to delete alert rule');
    }
  },

  // Toggle rule enabled state
  toggleRule: async (id, enabled) => {
    try {
      await monitoringApi.updateRule(id, { enabled });
      await get().fetchRules();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to toggle alert rule');
    }
  },

  // Resolve alert
  resolveAlert: async (id) => {
    try {
      await monitoringApi.resolveAlert(id);
      await get().fetchAlerts();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to resolve alert');
    }
  },

  // Silence alert
  silenceAlert: async (id, durationMinutes) => {
    try {
      await monitoringApi.silenceAlert(id, durationMinutes);
      await get().fetchAlerts();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to silence alert');
    }
  },
}));
