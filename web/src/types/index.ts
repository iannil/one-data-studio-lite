// 用户信息
export interface User {
  user_id: string;
  username: string;
  role: string;
  display_name: string;
  email: string;
}

// 登录响应
export interface LoginResponse {
  success: boolean;
  token: string;
  user: User;
  message: string;
}

// 子系统信息
export interface Subsystem {
  name: string;
  display_name: string;
  url: string;
  status: 'online' | 'offline' | 'unknown';
  version: string;
}

// NL2SQL 查询请求
export interface NL2SQLQueryRequest {
  question: string;
  database?: string;
  max_rows?: number;
}

// NL2SQL 查询响应
export interface NL2SQLQueryResponse {
  success: boolean;
  question: string;
  generated_sql: string;
  explanation: string;
  columns: string[];
  rows: any[][];
  row_count: number;
  execution_time_ms: number;
}

// 表信息
export interface TableInfo {
  database: string;
  table_name: string;
  comment: string;
  columns: ColumnInfo[];
}

// 列信息
export interface ColumnInfo {
  name: string;
  data_type: string;
  comment: string;
  is_primary_key: boolean;
  is_nullable: boolean;
}

// 敏感数据扫描请求
export interface SensitiveScanRequest {
  table_name: string;
  database?: string;
  sample_size?: number;
}

// 敏感字段信息
export interface SensitiveField {
  column_name: string;
  sensitivity_level: 'low' | 'medium' | 'high' | 'critical';
  detected_types: string[];
  detection_method: string;
  sample_count: number;
  confidence: number;
}

// 敏感数据扫描报告
export interface SensitiveScanReport {
  id: string;
  table_name: string;
  scan_time: string;
  total_columns: number;
  sensitive_columns: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  fields: SensitiveField[];
}

// 检测规则
export interface DetectionRule {
  id: string;
  name: string;
  pattern: string;
  sensitivity_level: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  enabled: boolean;
}

// 审计事件
export interface AuditEvent {
  id: string;
  subsystem: string;
  event_type: string;
  user: string;
  action: string;
  resource?: string;
  status_code?: number;
  duration_ms?: number;
  ip_address?: string;
  user_agent?: string;
  details?: Record<string, any>;
  created_at: string;
}

// 审计统计
export interface AuditStats {
  total_events: number;
  events_by_subsystem: Record<string, number>;
  events_by_type: Record<string, number>;
  events_by_user: Record<string, number>;
  time_range_start: string | null;
  time_range_end: string | null;
}

// 分页请求
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

// API 错误响应
export interface ApiError {
  detail: string;
  code?: string;
}
