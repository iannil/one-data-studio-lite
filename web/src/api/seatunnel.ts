/**
 * SeaTunnel 数据同步 API
 *
 * API 规范:
 * - v1 版本使用统一的 ApiResponse 格式
 * - 保留旧版 API 以确保向后兼容
 */

import client from './client';
import type { ApiResponse, ErrorCode } from './types';
import { isSuccessResponse, getErrorMessage as apiGetErrorMessage } from './utils';

/** SeaTunnel 任务状态 */
export type JobStatus =
  | 'RUNNING'
  | 'FINISHED'
  | 'FAILED'
  | 'CANCELED'
  | 'PENDING'
  | 'STARTING'
  | 'RESTARTING';

/** SeaTunnel 任务信息 */
export interface SeaTunnelJob {
  jobId: string;
  jobStatus: JobStatus;
  jobName?: string;
  createTime?: string;
  updateTime?: string;
  raw?: Record<string, unknown>;
}

/** 任务列表响应 */
export interface JobsListResponse {
  jobs: SeaTunnelJob[];
  total: number;
}

// 重新导出统一类型
export type { ApiResponse, ErrorCode };

// ============================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================

/**
 * 获取任务列表
 * @param status 状态过滤 (running/finished)，不传则返回全部
 */
export async function getJobsV1(status?: 'running' | 'finished'): Promise<ApiResponse<JobsListResponse>> {
  const params = status ? `?status=${status}` : '';
  const resp = await client.get(`/api/proxy/seatunnel/v1/jobs${params}`);
  return resp.data;
}

/**
 * 获取任务详情
 * @param jobId 任务 ID
 */
export async function getJobDetailV1(jobId: string): Promise<ApiResponse<{ jobId: string; raw: Record<string, unknown> }>> {
  const resp = await client.get(`/api/proxy/seatunnel/v1/jobs/${jobId}`);
  return resp.data;
}

/**
 * 获取任务状态
 * @param jobId 任务 ID
 */
export async function getJobStatusV1(jobId: string): Promise<ApiResponse<{ jobId: string; jobStatus: JobStatus }>> {
  const resp = await client.get(`/api/proxy/seatunnel/v1/jobs/${jobId}/status`);
  return resp.data;
}

/**
 * 提交新任务
 * @param config 任务配置
 */
export async function submitJobV1(config: Record<string, unknown>): Promise<ApiResponse> {
  const resp = await client.post('/api/proxy/seatunnel/v1/jobs', config);
  return resp.data;
}

/**
 * 取消任务
 * @param jobId 任务 ID
 */
export async function cancelJobV1(jobId: string): Promise<ApiResponse> {
  const resp = await client.delete(`/api/proxy/seatunnel/v1/jobs/${jobId}`);
  return resp.data;
}

/**
 * 获取集群状态
 */
export async function getClusterStatusV1(): Promise<ApiResponse<Record<string, unknown>>> {
  const resp = await client.get('/api/proxy/seatunnel/v1/cluster');
  return resp.data;
}

// ============================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================

/** 获取任务列表 */
export async function getJobs(): Promise<JobsListResponse> {
  const resp = await client.get('/api/proxy/seatunnel/api/v1/job/list');
  return resp.data;
}

/** 获取任务详情 */
export async function getJobDetail(jobId: string): Promise<{ jobId: string; raw: Record<string, unknown> }> {
  const resp = await client.get(`/api/proxy/seatunnel/api/v1/job/${jobId}`);
  return resp.data;
}

/** 提交任务 */
export async function submitJob(config: Record<string, unknown>): Promise<Record<string, unknown>> {
  const resp = await client.post('/api/proxy/seatunnel/api/v1/job/submit', config);
  return resp.data;
}

/** 取消任务 */
export async function cancelJob(jobId: string): Promise<Record<string, unknown>> {
  const resp = await client.delete(`/api/proxy/seatunnel/api/v1/job/${jobId}`);
  return resp.data;
}

/** 获取任务运行状态 */
export async function getJobStatus(jobId: string): Promise<{ jobId: string; jobStatus: JobStatus }> {
  const resp = await client.get(`/api/proxy/seatunnel/api/v1/job/${jobId}/status`);
  return resp.data;
}

// ============================================
// 工具函数（重新导出统一工具）
// ============================================

export { isSuccessResponse, getErrorMessage as apiGetErrorMessage };

/** 获取错误信息（便捷别名） */
export function getErrorMessage(response: ApiResponse): string {
  return apiGetErrorMessage(response);
}
