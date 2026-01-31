import client from './client';
import { AuditEvent, AuditStats, PaginationParams } from '../types';

export interface AuditQueryParams extends PaginationParams {
  subsystem?: string;
  event_type?: string;
  user?: string;
}

// 查询审计日志
export const getLogs = async (params: AuditQueryParams = {}): Promise<AuditEvent[]> => {
  const response = await client.get<AuditEvent[]>('/api/proxy/audit/api/audit/logs', { params });
  return response.data;
};

// 获取单条日志
export const getLog = async (logId: string): Promise<AuditEvent> => {
  const response = await client.get<AuditEvent>(`/api/proxy/audit/api/audit/logs/${logId}`);
  return response.data;
};

// 获取审计统计
export const getStats = async (): Promise<AuditStats> => {
  const response = await client.get<AuditStats>('/api/proxy/audit/api/audit/stats');
  return response.data;
};

// 导出审计日志
export const exportLogs = async (
  format: 'csv' | 'json',
  query: AuditQueryParams = {}
): Promise<Blob> => {
  const response = await client.post(
    '/api/proxy/audit/api/audit/export',
    { format, query },
    { responseType: 'blob' }
  );
  return response.data;
};
