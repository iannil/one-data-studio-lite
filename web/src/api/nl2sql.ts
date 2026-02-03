/**
 * NL2SQL 自然语言转 SQL API
 *
 * API 规范:
 * - v1 版本使用统一的 ApiResponse 格式
 * - 保留旧版 API 以确保向后兼容
 */

import client from './client';
import type { ApiResponse } from './types';

// 重新导出统一类型
export type { ApiResponse };

// ============================================================
// 类型定义
// ============================================================

export interface NL2SQLQueryRequest {
  query: string;
  database?: string;
  context?: string;
}

export interface NL2SQLQueryResponse {
  sql: string;
  generated_sql?: string;
  explanation?: string;
  confidence?: number;
  tables?: string[];
  columns?: string[];
  rows?: Array<Array<string | number | boolean | null>>;
  row_count?: number;
  execution_time_ms?: number;
  success?: boolean;
}

export interface TableInfo {
  name: string;
  table_name?: string;
  schema?: string;
  database?: string;
  comment?: string;
  columns?: Array<{
    name: string;
    type: string;
    data_type?: string;
    description?: string;
    comment?: string;
  }>;
}

export interface ExplainRequest {
  sql: string;
  database?: string;
}

export interface ExplainResponse {
  sql: string;
  explanation: string;
  steps?: string[];
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/** 自然语言查询 */
export async function queryV1(request: NL2SQLQueryRequest): Promise<ApiResponse<NL2SQLQueryResponse>> {
  const resp = await client.post<ApiResponse<NL2SQLQueryResponse>>(
    '/api/proxy/nl2sql/v1/query',
    request
  );
  return resp.data;
}

/** SQL 解释 */
export async function explainV1(params: ExplainRequest): Promise<ApiResponse<ExplainResponse>> {
  const resp = await client.post<ApiResponse<ExplainResponse>>(
    '/api/proxy/nl2sql/v1/explain',
    params
  );
  return resp.data;
}

/** 获取表列表 */
export async function getTablesV1(): Promise<ApiResponse<TableInfo[]>> {
  const resp = await client.get<ApiResponse<TableInfo[]>>(
    '/api/proxy/nl2sql/v1/tables'
  );
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

import { NL2SQLQueryRequest as LegacyQueryRequest, NL2SQLQueryResponse as LegacyQueryResponse, TableInfo as LegacyTableInfo } from '../types';

// 自然语言查询
export const query = async (request: LegacyQueryRequest): Promise<LegacyQueryResponse> => {
  const response = await client.post<LegacyQueryResponse>('/api/proxy/nl2sql/api/nl2sql/query', request);
  return response.data;
};

// SQL 解释
export const explain = async (sql: string, database?: string): Promise<{ sql: string; explanation: string }> => {
  const response = await client.post('/api/proxy/nl2sql/api/nl2sql/explain', { sql, database });
  return response.data;
};

// 获取表列表
export const getTables = async (): Promise<LegacyTableInfo[]> => {
  const response = await client.get<LegacyTableInfo[]>('/api/proxy/nl2sql/api/nl2sql/tables');
  return response.data;
};
