import client from './client';
import type { ApiResponse } from './types';
import { AuditEvent, AuditStats, PaginationParams } from '../types';

export interface AuditQueryParams extends PaginationParams {
  subsystem?: string;
  event_type?: string;
  user?: string;
}

// 查询审计日志
export const getLogs = async (params: AuditQueryParams = {}): Promise<AuditEvent[]> => {
  const response = await client.get<ApiResponse<AuditEvent[]>>('/api/proxy/audit/v1/logs', { params });
  return response.data.data || [];
};

// 获取单条日志
export const getLog = async (logId: string): Promise<AuditEvent> => {
  const response = await client.get<ApiResponse<AuditEvent>>(`/api/proxy/audit/v1/logs/${logId}`);
  return response.data.data || response.data;
};

// 获取审计统计
export const getStats = async (): Promise<AuditStats> => {
  const response = await client.get<ApiResponse<AuditStats>>('/api/proxy/audit/v1/stats');
  return response.data.data || response.data;
};

// 导出审计日志
export const exportLogs = async (
  format: 'csv' | 'json',
  query: AuditQueryParams = {}
): Promise<Blob> => {
  const response = await client.post(
    '/api/proxy/audit/v1/export',
    { format, query },
    { responseType: 'blob' }
  );
  return response.data;
};
