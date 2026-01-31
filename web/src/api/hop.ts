/**
 * Apache Hop API - ETL 工作流与管道管理
 *
 * API 规范:
 * - v1 版本使用统一的 ApiResponse 格式
 * - 保留旧版 API 以确保向后兼容
 */

import client from './client';
import type { ApiResponse } from './types';
import { isSuccessResponse } from './utils';

// 重新导出统一类型
export type { ApiResponse };

// ============================================================
// 类型定义
// ============================================================

export interface RunRequest {
  run_configuration?: string;
  parameters?: Record<string, string>;
  variables?: Record<string, string>;
}

export interface RunResponse {
  success: boolean;
  message: string;
  execution_id?: string;
  details?: Record<string, unknown>;
}

export interface WorkflowInfo {
  name: string;
  description?: string;
  filename?: string;
  status?: string;
}

export interface PipelineInfo {
  name: string;
  description?: string;
  filename?: string;
  status?: string;
}

export interface ExecutionStatus {
  id: string;
  status: string;
  start_time?: string;
  end_time?: string;
  errors?: number;
  log?: string;
}

export interface ServerInfo {
  version?: string;
  status?: string;
  error?: string;
}

export interface RunConfiguration {
  name: string;
  description?: string;
}

// ============================================================
// 工作流 API
// ============================================================

/**
 * 列出所有工作流
 */
export async function listWorkflows(): Promise<{
  workflows: WorkflowInfo[];
  total: number;
}> {
  const resp = await client.get('/api/proxy/hop/workflows');
  return resp.data;
}

/**
 * 获取工作流详情
 */
export async function getWorkflow(name: string): Promise<WorkflowInfo> {
  const resp = await client.get(`/api/proxy/hop/workflows/${encodeURIComponent(name)}`);
  return resp.data;
}

/**
 * 执行工作流
 */
export async function runWorkflow(
  name: string,
  request?: RunRequest
): Promise<RunResponse> {
  const resp = await client.post(
    `/api/proxy/hop/workflows/${encodeURIComponent(name)}/run`,
    request || { run_configuration: 'local' }
  );
  return resp.data;
}

/**
 * 获取工作流执行状态
 */
export async function getWorkflowStatus(
  name: string,
  executionId: string
): Promise<ExecutionStatus> {
  const resp = await client.get(
    `/api/proxy/hop/workflows/${encodeURIComponent(name)}/status/${encodeURIComponent(executionId)}`
  );
  return resp.data;
}

/**
 * 停止工作流执行
 */
export async function stopWorkflow(
  name: string,
  executionId: string
): Promise<{ success: boolean; message: string }> {
  const resp = await client.post(
    `/api/proxy/hop/workflows/${encodeURIComponent(name)}/stop/${encodeURIComponent(executionId)}`
  );
  return resp.data;
}

// ============================================================
// 管道 API
// ============================================================

/**
 * 列出所有管道
 */
export async function listPipelines(): Promise<{
  pipelines: PipelineInfo[];
  total: number;
}> {
  const resp = await client.get('/api/proxy/hop/pipelines');
  return resp.data;
}

/**
 * 获取管道详情
 */
export async function getPipeline(name: string): Promise<PipelineInfo> {
  const resp = await client.get(`/api/proxy/hop/pipelines/${encodeURIComponent(name)}`);
  return resp.data;
}

/**
 * 执行管道
 */
export async function runPipeline(
  name: string,
  request?: RunRequest
): Promise<RunResponse> {
  const resp = await client.post(
    `/api/proxy/hop/pipelines/${encodeURIComponent(name)}/run`,
    request || { run_configuration: 'local' }
  );
  return resp.data;
}

/**
 * 获取管道执行状态
 */
export async function getPipelineStatus(
  name: string,
  executionId: string
): Promise<ExecutionStatus> {
  const resp = await client.get(
    `/api/proxy/hop/pipelines/${encodeURIComponent(name)}/status/${encodeURIComponent(executionId)}`
  );
  return resp.data;
}

/**
 * 停止管道执行
 */
export async function stopPipeline(
  name: string,
  executionId: string
): Promise<{ success: boolean; message: string }> {
  const resp = await client.post(
    `/api/proxy/hop/pipelines/${encodeURIComponent(name)}/stop/${encodeURIComponent(executionId)}`
  );
  return resp.data;
}

// ============================================================
// 服务器 API
// ============================================================

/**
 * 获取服务器状态
 */
export async function getServerStatus(): Promise<ServerInfo> {
  const resp = await client.get('/api/proxy/hop/server/status');
  return resp.data;
}

/**
 * 获取服务器信息
 */
export async function getServerInfo(): Promise<ServerInfo> {
  const resp = await client.get('/api/proxy/hop/server/info');
  return resp.data;
}

/**
 * 列出运行配置
 */
export async function listRunConfigurations(): Promise<{
  configurations: RunConfiguration[];
}> {
  const resp = await client.get('/api/proxy/hop/run-configurations');
  return resp.data;
}

// ============================================================
// 便捷函数
// ============================================================

/**
 * 执行工作流并等待完成
 */
export async function runWorkflowAndWait(
  name: string,
  request?: RunRequest,
  pollInterval = 2000,
  timeout = 300000
): Promise<ExecutionStatus> {
  const result = await runWorkflow(name, request);
  if (!result.success || !result.execution_id) {
    throw new Error(result.message || '启动工作流失败');
  }

  const executionId = result.execution_id;
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const status = await getWorkflowStatus(name, executionId);
    if (status.status === 'Finished' || status.status === 'Stopped' || status.status === 'Error') {
      return status;
    }
    await new Promise((resolve) => setTimeout(resolve, pollInterval));
  }

  throw new Error('执行超时');
}

/**
 * 执行管道并等待完成
 */
export async function runPipelineAndWait(
  name: string,
  request?: RunRequest,
  pollInterval = 2000,
  timeout = 300000
): Promise<ExecutionStatus> {
  const result = await runPipeline(name, request);
  if (!result.success || !result.execution_id) {
    throw new Error(result.message || '启动管道失败');
  }

  const executionId = result.execution_id;
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const status = await getPipelineStatus(name, executionId);
    if (status.status === 'Finished' || status.status === 'Stopped' || status.status === 'Error') {
      return status;
    }
    await new Promise((resolve) => setTimeout(resolve, pollInterval));
  }

  throw new Error('执行超时');
}
