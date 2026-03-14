export interface DataSource {
  id: string;
  name: string;
  description?: string;
  type: 'postgresql' | 'mysql' | 'oracle' | 'sqlserver' | 'sqlite' | 'csv' | 'excel' | 'json' | 'api';
  connection_config: Record<string, any>;
  status: 'active' | 'inactive' | 'error' | 'testing';
  last_connected_at?: string;
  created_at: string;
  created_by?: string;
}

export interface MetadataTable {
  id: string;
  source_id: string;
  schema_name?: string;
  table_name: string;
  description?: string;
  ai_description?: string;
  tags: string[];
  row_count?: number;
  version: number;
  created_at: string;
  columns: MetadataColumn[];
}

export interface MetadataColumn {
  id: string;
  table_id: string;
  column_name: string;
  data_type: string;
  nullable: boolean;
  is_primary_key: boolean;
  default_value?: string;
  description?: string;
  ai_inferred_meaning?: string;
  ai_data_category?: string;
  tags: string[];
  standard_mapping?: string;
  ordinal_position: number;
}

export interface ETLPipeline {
  id: string;
  name: string;
  description?: string;
  status: 'draft' | 'active' | 'paused' | 'archived';
  source_type: string;
  source_config: Record<string, any>;
  target_type: string;
  target_config: Record<string, any>;
  schedule_cron?: string;
  is_scheduled: boolean;
  tags: string[];
  version: number;
  created_at: string;
  created_by?: string;
  steps: ETLStep[];
}

export interface ETLStep {
  id: string;
  pipeline_id: string;
  name: string;
  step_type: string;
  config: Record<string, any>;
  order: number;
  is_enabled: boolean;
  description?: string;
}

export interface ETLExecution {
  id: string;
  pipeline_id: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  rows_input: number;
  rows_output: number;
  rows_error: number;
  error_message?: string;
  step_metrics?: Record<string, any>;
}

export interface DataAsset {
  id: string;
  name: string;
  description?: string;
  asset_type: 'table' | 'view' | 'report' | 'dashboard' | 'api' | 'file';
  source_table?: string;
  source_schema?: string;
  source_database?: string;
  owner_id?: string;
  department?: string;
  access_level: 'public' | 'internal' | 'restricted' | 'confidential';
  tags: string[];
  category?: string;
  domain?: string;
  ai_summary?: string;
  value_score?: number;
  usage_count: number;
  last_accessed_at?: string;
  is_active: boolean;
  is_certified: boolean;
  certified_by?: string;
  certified_at?: string;
  created_at: string;
}

export interface AlertRule {
  id: string;
  name: string;
  description?: string;
  metric_sql: string;
  metric_name: string;
  condition: string;
  threshold: number;
  severity: 'info' | 'warning' | 'critical';
  check_interval_minutes: number;
  cooldown_minutes: number;
  is_enabled: boolean;
  notification_channels: string[];
  notification_config?: Record<string, any>;
  created_at: string;
  created_by?: string;
}

export interface Alert {
  id: string;
  rule_id: string;
  severity: 'info' | 'warning' | 'critical';
  status: 'active' | 'acknowledged' | 'resolved';
  message: string;
  current_value: number;
  threshold_value: number;
  triggered_at: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution_note?: string;
}
