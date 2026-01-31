/**
 * Data API 数据资产 API 网关
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

export interface DataAsset {
  id: string;
  name: string;
  type: string;
  description?: string;
  schema?: string;
  database?: string;
  tags?: string[];
}

export interface DatasetSchema {
  id: string;
  name: string;
  columns: Array<{
    name: string;
    type: string;
    nullable?: boolean;
    description?: string;
  }>;
}

export interface QueryResult {
  columns: string[];
  rows: Array<unknown[]>;
  total: number;
}

export interface Subscription {
  id: string;
  dataset_id: string;
  subscriber?: string;
  created_at: string;
}

export interface SearchAssetsParams {
  keyword?: string;
  type?: string;
  page?: number;
  page_size?: number;
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/** 搜索数据资产 */
export async function searchAssetsV1(
  params?: SearchAssetsParams
): Promise<ApiResponse<DataAsset[]>> {
  const resp = await client.get<ApiResponse<DataAsset[]>>(
    '/api/proxy/data-api/v1/assets/search',
    { params }
  );
  return resp.data;
}

/** 获取资产详情 */
export async function getAssetDetailV1(id: string): Promise<ApiResponse<DataAsset>> {
  const resp = await client.get<ApiResponse<DataAsset>>(
    `/api/proxy/data-api/v1/assets/${id}`
  );
  return resp.data;
}

/** 获取数据集 Schema */
export async function getDatasetSchemaV1(id: string): Promise<ApiResponse<DatasetSchema>> {
  const resp = await client.get<ApiResponse<DatasetSchema>>(
    `/api/proxy/data-api/v1/data/${id}/schema`
  );
  return resp.data;
}

/** 自定义查询 */
export async function queryDatasetV1(
  id: string,
  params: { sql?: string; limit?: number }
): Promise<ApiResponse<QueryResult>> {
  const resp = await client.post<ApiResponse<QueryResult>>(
    `/api/proxy/data-api/v1/data/${id}/query`,
    params
  );
  return resp.data;
}

/** 订阅数据集 */
export async function subscribeDatasetV1(id: string): Promise<ApiResponse<Subscription>> {
  const resp = await client.post<ApiResponse<Subscription>>(
    `/api/proxy/data-api/v1/data/${id}/subscribe`
  );
  return resp.data;
}

/** 获取订阅列表 */
export async function getSubscriptionsV1(): Promise<ApiResponse<Subscription[]>> {
  const resp = await client.get<ApiResponse<Subscription[]>>(
    '/api/proxy/data-api/v1/subscriptions'
  );
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/** 搜索数据资产 */
export async function searchAssets(params?: SearchAssetsParams) {
  const resp = await client.get('/api/proxy/data-api/api/assets/search', { params });
  return resp.data;
}

/** 获取资产详情 */
export async function getAssetDetail(id: string) {
  const resp = await client.get(`/api/proxy/data-api/api/assets/${id}`);
  return resp.data;
}

/** 获取数据集 Schema */
export async function getDatasetSchema(id: string) {
  const resp = await client.get(`/api/proxy/data-api/api/data/${id}/schema`);
  return resp.data;
}

/** 自定义查询 */
export async function queryDataset(id: string, params: { sql?: string; limit?: number }) {
  const resp = await client.post(`/api/proxy/data-api/api/data/${id}/query`, params);
  return resp.data;
}

/** 订阅数据集 */
export async function subscribeDataset(id: string) {
  const resp = await client.post(`/api/proxy/data-api/api/data/${id}/subscribe`);
  return resp.data;
}

/** 获取订阅列表 */
export async function getSubscriptions() {
  const resp = await client.get('/api/proxy/data-api/api/subscriptions');
  return resp.data;
}
