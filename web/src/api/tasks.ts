/**
 * Async Task System API
 *
 * For managing long-running operations like report generation, bulk imports, etc.
 */

import client from './client';
import type {
  AsyncTask,
  CreateTaskRequest,
  TaskListResponse,
  TaskQueryParams,
} from '../types/tasks';

// ============================================================
// 任务管理 API
// ============================================================

/** 创建异步任务 */
export async function createTask(request: CreateTaskRequest): Promise<{ success: boolean; task_id: string; message: string }> {
  const response = await client.post<{ success: boolean; task_id: string; message: string }>('/tasks', request);
  return response.data;
}

/** 获取任务详情 */
export async function getTask(taskId: string): Promise<AsyncTask> {
  const response = await client.get<AsyncTask>(`/tasks/${taskId}`);
  return response.data;
}

/** 查询任务列表 */
export async function queryTasks(params?: TaskQueryParams): Promise<TaskListResponse> {
  const response = await client.get<TaskListResponse>('/tasks', { params });
  return response.data;
}

/** 获取当前用户的任务 */
export async function getMyTasks(params?: Omit<TaskQueryParams, 'created_by'>): Promise<TaskListResponse> {
  const response = await client.get<TaskListResponse>('/tasks/my', { params });
  return response.data;
}

/** 取消任务 */
export async function cancelTask(taskId: string): Promise<{ success: boolean; message: string }> {
  const response = await client.post<{ success: boolean; message: string }>(`/tasks/${taskId}/cancel`);
  return response.data;
}

/** 重试失败的任务 */
export async function retryTask(taskId: string): Promise<{ success: boolean; task_id: string; message: string }> {
  const response = await client.post<{ success: boolean; task_id: string; message: string }>(`/tasks/${taskId}/retry`);
  return response.data;
}

/** 删除任务记录 */
export async function deleteTask(taskId: string): Promise<{ success: boolean; message: string }> {
  const response = await client.delete<{ success: boolean; message: string }>(`/tasks/${taskId}`);
  return response.data;
}

/** 下载任务结果文件 */
export function downloadTaskResult(taskId: string): string {
  return `${client.defaults.baseURL}/tasks/${taskId}/download`;
}

// ============================================================
// WebSocket 连接
// ============================================================

/** WebSocket 端点 */
export function getTaskWebSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = import.meta.env.VITE_API_BASE_URL
    ? new URL(import.meta.env.VITE_API_BASE_URL).host
    : window.location.host;
  return `${protocol}//${host}/tasks/ws`;
}
