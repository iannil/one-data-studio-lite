/**
 * Apache Superset BI 分析 API
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

export interface Dashboard {
  id: number;
  dashboard_title?: string;
  title?: string;
  description?: string;
  slug?: string;
  url?: string;
  published?: boolean;
  created_by?: {
    id: number;
    username?: string;
    first_name?: string;
    last_name?: string;
  };
  changed_on?: string;
  changed_on_delta_humanized?: string;
}

export interface Chart {
  id: number;
  slice_name?: string;
  chart_name?: string;
  description?: string;
  viz_type?: string;
  datasource_name_text?: string;
  datasource?: { id: number; name: string };
  created_by?: {
    id: number;
    username?: string;
    first_name?: string;
    last_name?: string;
  };
  changed_on?: string;
  changed_on_delta_humanized?: string;
}

export interface Dataset {
  id: number;
  table_name: string;
  schema?: string;
  database?: { id: number; name: string };
}

export interface ListParams {
  page?: number;
  page_size?: number;
  q?: string;
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/** 获取仪表板列表 */
export async function getDashboardsV1(params?: ListParams): Promise<ApiResponse<Dashboard[]>> {
  const resp = await client.get<ApiResponse<Dashboard[]>>('/api/proxy/superset/v1/dashboards', { params });
  return resp.data;
}

/** 获取仪表板详情 */
export async function getDashboardV1(id: number): Promise<ApiResponse<Dashboard>> {
  const resp = await client.get<ApiResponse<Dashboard>>(`/api/proxy/superset/v1/dashboards/${id}`);
  return resp.data;
}

/** 获取图表列表 */
export async function getChartsV1(params?: ListParams): Promise<ApiResponse<Chart[]>> {
  const resp = await client.get<ApiResponse<Chart[]>>('/api/proxy/superset/v1/charts', { params });
  return resp.data;
}

/** 获取图表详情 */
export async function getChartV1(id: number): Promise<ApiResponse<Chart>> {
  const resp = await client.get<ApiResponse<Chart>>(`/api/proxy/superset/v1/charts/${id}`);
  return resp.data;
}

/** 获取数据集列表 */
export async function getDatasetsV1(params?: Pick<ListParams, 'page' | 'page_size'>): Promise<ApiResponse<Dataset[]>> {
  const resp = await client.get<ApiResponse<Dataset[]>>('/api/proxy/superset/v1/datasets', { params });
  return resp.data;
}

/** 获取数据集详情 */
export async function getDatasetV1(id: number): Promise<ApiResponse<Dataset>> {
  const resp = await client.get<ApiResponse<Dataset>>(`/api/proxy/superset/v1/datasets/${id}`);
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/** 获取仪表板列表 */
export async function getDashboards(params?: ListParams) {
  const resp = await client.get('/api/proxy/superset/api/v1/dashboard/', { params });
  return resp.data;
}

/** 获取仪表板详情 */
export async function getDashboard(id: number) {
  const resp = await client.get(`/api/proxy/superset/api/v1/dashboard/${id}`);
  return resp.data;
}

/** 获取图表列表 */
export async function getCharts(params?: ListParams) {
  const resp = await client.get('/api/proxy/superset/api/v1/chart/', { params });
  return resp.data;
}

/** 获取图表详情 */
export async function getChart(id: number) {
  const resp = await client.get(`/api/proxy/superset/api/v1/chart/${id}`);
  return resp.data;
}

/** 获取数据集列表 */
export async function getDatasets(params?: Pick<ListParams, 'page' | 'page_size'>) {
  const resp = await client.get('/api/proxy/superset/api/v1/dataset/', { params });
  return resp.data;
}
