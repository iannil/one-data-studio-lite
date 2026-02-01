/**
 * Cube-Studio AI 平台 API
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

// Pipeline 相关
export interface Pipeline {
  id: number;
  name: string;
  describe?: string;
  description?: string;
  status?: string;
  created_by?: string | { username?: string };
  changed_on?: string;
  created_at?: string;
}

export interface PipelineRunResult {
  success: boolean;
  run_id?: string;
  message?: string;
}

export interface ListParams {
  page?: number;
  page_size?: number;
}

export interface PipelineRunParams {
  run_configuration?: string;
  parameters?: Record<string, unknown>;
  variables?: Record<string, unknown>;
}

// 模型推理相关
export interface ModelInfo {
  name: string;
  modified_at?: string;
  size?: number;
}

export interface ModelsListResponse {
  models: string[];
  details: ModelInfo[];
}

export interface ModelInferenceRequest {
  model_name: string;
  prompt: string;
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  stream?: boolean;
}

export interface ModelInferenceResponse {
  model: string;
  response: string;
  done: boolean;
  context?: number[];
}

export interface ChatMessage {
  role: string;
  content: string;
}

export interface ChatCompletionRequest extends ModelInferenceRequest {
  messages?: ChatMessage[];
}

// 数据管理相关
export interface DataSource {
  id?: string;
  name: string;
  type: string;
  connection_params?: Record<string, unknown>;
  description?: string;
  status?: string;
}

export interface DataSourceCreateParams {
  name: string;
  type: string;
  connection_params: Record<string, unknown>;
  description?: string;
}

export interface Dataset {
  id?: string;
  name: string;
  description?: string;
  type?: string;
  size?: number;
  rows?: number;
  created_at?: string;
}

// Notebook 相关
export interface Notebook {
  name: string;
  path?: string;
  type?: string;
  created_at?: string;
}

export interface NotebookCreateParams {
  name: string;
  description?: string;
  kernel_type?: string;
  parent_folder?: string;
}

// 监控相关
export interface ServiceStatus {
  url: string;
  status: 'online' | 'offline' | 'unknown';
}

export interface ServicesStatusResponse {
  services: {
    cube_studio: ServiceStatus;
    ollama: ServiceStatus;
    prometheus: ServiceStatus;
    grafana: ServiceStatus;
  };
}

export interface MetricsResponse {
  metrics?: unknown[];
  note?: string;
}

export interface AlertsResponse {
  alerts?: unknown[];
  note?: string;
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

// ------------------------------------------------------------
// Pipeline API
// ------------------------------------------------------------

/** 获取 Pipeline 列表 */
export async function getPipelinesV1(params?: ListParams): Promise<ApiResponse<Pipeline[]>> {
  const resp = await client.get<ApiResponse<Pipeline[]>>('/api/proxy/cubestudio/v1/pipelines', { params });
  return resp.data;
}

/** 获取 Pipeline 详情 */
export async function getPipelineV1(id: number): Promise<ApiResponse<Pipeline>> {
  const resp = await client.get<ApiResponse<Pipeline>>(`/api/proxy/cubestudio/v1/pipelines/${id}`);
  return resp.data;
}

/** 运行 Pipeline */
export async function runPipelineV1(id: number, params?: PipelineRunParams): Promise<ApiResponse<PipelineRunResult>> {
  const resp = await client.post<ApiResponse<PipelineRunResult>>(
    `/api/proxy/cubestudio/v1/pipelines/${id}/run`,
    params || {}
  );
  return resp.data;
}

/** 删除 Pipeline */
export async function deletePipelineV1(id: number): Promise<ApiResponse<{ message: string }>> {
  const resp = await client.delete<ApiResponse<{ message: string }>>(`/api/proxy/cubestudio/v1/pipelines/${id}`);
  return resp.data;
}

// ------------------------------------------------------------
// 模型推理 API
// ------------------------------------------------------------

/** 获取可用模型列表 */
export async function listModelsV1(): Promise<ApiResponse<ModelsListResponse>> {
  const resp = await client.get<ApiResponse<ModelsListResponse>>('/api/proxy/cubestudio/v1/models');
  return resp.data;
}

/** 模型推理（Completion API） */
export async function modelInferenceV1(request: ModelInferenceRequest): Promise<ApiResponse<ModelInferenceResponse>> {
  const resp = await client.post<ApiResponse<ModelInferenceResponse>>(
    '/api/proxy/cubestudio/v1/models/inference',
    request
  );
  return resp.data;
}

/** 对话补全（Chat API） */
export async function chatCompletionV1(request: ChatCompletionRequest): Promise<ApiResponse<ModelInferenceResponse>> {
  const resp = await client.post<ApiResponse<ModelInferenceResponse>>(
    '/api/proxy/cubestudio/v1/models/chat',
    request
  );
  return resp.data;
}

/** 快速对话 - 便捷函数 */
export async function quickChat(
  prompt: string,
  model: string = 'qwen2.5:7b',
  maxTokens: number = 2048
): Promise<string> {
  const resp = await chatCompletionV1({
    model_name: model,
    prompt,
    max_tokens: maxTokens,
    temperature: 0.1,
  });

  // 简单处理响应，实际使用可能需要处理流式响应
  if (resp.code === 20000 && resp.data) {
    const data = resp.data as unknown;
    if (typeof data === 'object' && 'response' in (data as object)) {
      return (data as { response: string }).response;
    }
    if (typeof data === 'object' && 'message' in (data as object)) {
      return (data as { message: string }).message;
    }
  }
  throw new Error(resp.message || '推理请求失败');
}

// ------------------------------------------------------------
// 数据管理 API
// ------------------------------------------------------------

/** 获取数据源列表 */
export async function listDataSourcesV1(): Promise<ApiResponse<{ data_sources: DataSource[] }>> {
  const resp = await client.get<ApiResponse<{ data_sources: DataSource[] }>>('/api/proxy/cubestudio/v1/data-sources');
  return resp.data;
}

/** 创建数据源 */
export async function createDataSourceV1(request: DataSourceCreateParams): Promise<ApiResponse<DataSource>> {
  const resp = await client.post<ApiResponse<DataSource>>('/api/proxy/cubestudio/v1/data-sources', request);
  return resp.data;
}

/** 获取数据集列表 */
export async function listDatasetsV1(params?: ListParams): Promise<ApiResponse<{ datasets: Dataset[] }>> {
  const resp = await client.get<ApiResponse<{ datasets: Dataset[] }>>('/api/proxy/cubestudio/v1/datasets', { params });
  return resp.data;
}

// ------------------------------------------------------------
// Notebook API
// ------------------------------------------------------------

/** 获取 Notebook 列表 */
export async function listNotebooksV1(path: string = '/'): Promise<ApiResponse<{ items: Notebook[] }>> {
  const resp = await client.get<ApiResponse<{ items: Notebook[] }>>(`/api/proxy/cubestudio/v1/notebooks?path=${encodeURIComponent(path)}`);
  return resp.data;
}

/** 创建 Notebook */
export async function createNotebookV1(request: NotebookCreateParams): Promise<ApiResponse<Notebook>> {
  const resp = await client.post<ApiResponse<Notebook>>('/api/proxy/cubestudio/v1/notebooks', request);
  return resp.data;
}

// ------------------------------------------------------------
// 监控告警 API
// ------------------------------------------------------------

/** 获取系统指标 */
export async function getMetricsV1(): Promise<ApiResponse<MetricsResponse>> {
  const resp = await client.get<ApiResponse<MetricsResponse>>('/api/proxy/cubestudio/v1/metrics');
  return resp.data;
}

/** 获取告警列表 */
export async function listAlertsV1(): Promise<ApiResponse<AlertsResponse>> {
  const resp = await client.get<ApiResponse<AlertsResponse>>('/api/proxy/cubestudio/v1/alerts');
  return resp.data;
}

/** 获取服务状态 */
export async function getServicesStatusV1(): Promise<ApiResponse<ServicesStatusResponse>> {
  const resp = await client.get<ApiResponse<ServicesStatusResponse>>('/api/proxy/cubestudio/v1/services/status');
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/** 获取 Pipeline 列表 */
export async function getPipelines(params?: ListParams) {
  const resp = await client.get('/api/proxy/cubestudio/pipeline_modelview/api/', { params });
  return resp.data;
}

/** 获取 Pipeline 详情 */
export async function getPipeline(id: number) {
  const resp = await client.get(`/api/proxy/cubestudio/pipeline_modelview/api/${id}`);
  return resp.data;
}

/** 运行 Pipeline */
export async function runPipeline(id: number) {
  const resp = await client.post(`/api/proxy/cubestudio/pipeline_modelview/api/${id}/run`);
  return resp.data;
}
