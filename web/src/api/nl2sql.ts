import client from './client';
import { NL2SQLQueryRequest, NL2SQLQueryResponse, TableInfo } from '../types';

// 自然语言查询
export const query = async (request: NL2SQLQueryRequest): Promise<NL2SQLQueryResponse> => {
  const response = await client.post<NL2SQLQueryResponse>('/api/nl2sql/query', request);
  return response.data;
};

// SQL 解释
export const explain = async (sql: string, database?: string): Promise<{ sql: string; explanation: string }> => {
  const response = await client.post('/api/nl2sql/explain', { sql, database });
  return response.data;
};

// 获取表列表
export const getTables = async (): Promise<TableInfo[]> => {
  const response = await client.get<TableInfo[]>('/api/nl2sql/tables');
  return response.data;
};
