/**
 * DolphinScheduler 任务调度 API
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

export interface Project {
  code: number;
  name: string;
  description?: string;
}

export interface ProcessDefinition {
  code: number;
  name: string;
  description?: string;
  releaseState?: 'ONLINE' | 'OFFLINE';
}

export interface Schedule {
  id: number;
  processDefinitionCode: number;
  releaseState: 'ONLINE' | 'OFFLINE';
  crontab: string;
}

export interface TaskInstance {
  id: number;
  name: string;
  state: string;
  startTime?: string;
  endTime?: string;
}

export interface TaskLog {
  log: string;
  taskInstanceId: number;
}

export interface ListParams {
  pageNo?: number;
  pageSize?: number;
  searchVal?: string;
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/** 获取项目列表 */
export async function getProjectsV1(): Promise<ApiResponse<Project[]>> {
  const resp = await client.get<ApiResponse<Project[]>>('/api/proxy/ds/v1/projects', {
    params: { pageNo: 1, pageSize: 100 },
  });
  return resp.data;
}

/** 获取流程定义列表 */
export async function getProcessDefinitionsV1(
  projectCode: string,
  params?: ListParams
): Promise<ApiResponse<ProcessDefinition[]>> {
  const resp = await client.get<ApiResponse<ProcessDefinition[]>>(
    `/api/proxy/ds/v1/projects/${projectCode}/process-definition`,
    { params }
  );
  return resp.data;
}

/** 获取调度列表 */
export async function getSchedulesV1(
  projectCode: string,
  processDefinitionCode?: string
): Promise<ApiResponse<Schedule[]>> {
  const resp = await client.get<ApiResponse<Schedule[]>>(
    `/api/proxy/ds/v1/projects/${projectCode}/schedules`,
    {
      params: processDefinitionCode ? { processDefinitionCode } : undefined,
    }
  );
  return resp.data;
}

/** 上线/下线调度 */
export async function updateScheduleStateV1(
  projectCode: string,
  scheduleId: number,
  releaseState: 'ONLINE' | 'OFFLINE'
): Promise<ApiResponse<{ success: boolean }>> {
  const resp = await client.post<ApiResponse<{ success: boolean }>>(
    `/api/proxy/ds/v1/projects/${projectCode}/schedules/${scheduleId}/online`,
    null,
    {
      params: { releaseState },
    }
  );
  return resp.data;
}

/** 获取任务实例列表 */
export async function getTaskInstancesV1(
  projectCode: string,
  params?: ListParams & { stateType?: string }
): Promise<ApiResponse<TaskInstance[]>> {
  const resp = await client.get<ApiResponse<TaskInstance[]>>(
    `/api/proxy/ds/v1/projects/${projectCode}/task-instances`,
    { params }
  );
  return resp.data;
}

/** 获取任务实例日志 */
export async function getTaskLogV1(
  projectCode: string,
  taskInstanceId: number
): Promise<ApiResponse<TaskLog>> {
  const resp = await client.get<ApiResponse<TaskLog>>(
    `/api/proxy/ds/v1/projects/${projectCode}/task-instances/${taskInstanceId}/log`
  );
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/** 获取项目列表 */
export async function getProjects() {
  const resp = await client.get('/api/proxy/ds/projects', {
    params: { pageNo: 1, pageSize: 100 },
  });
  return resp.data;
}

/** 获取流程定义列表 */
export async function getProcessDefinitions(projectCode: string, params?: ListParams) {
  const resp = await client.get(`/api/proxy/ds/projects/${projectCode}/process-definition`, { params });
  return resp.data;
}

/** 获取调度列表 */
export async function getSchedules(projectCode: string, processDefinitionCode?: string) {
  const resp = await client.get(`/api/proxy/ds/projects/${projectCode}/schedules`, {
    params: processDefinitionCode ? { processDefinitionCode } : undefined,
  });
  return resp.data;
}

/** 上线/下线调度 */
export async function updateScheduleState(
  projectCode: string,
  scheduleId: number,
  releaseState: 'ONLINE' | 'OFFLINE'
) {
  const resp = await client.post(`/api/proxy/ds/projects/${projectCode}/schedules/${scheduleId}/online`, null, {
    params: { releaseState },
  });
  return resp.data;
}

/** 获取任务实例列表 */
export async function getTaskInstances(projectCode: string, params?: ListParams & { stateType?: string }) {
  const resp = await client.get(`/api/proxy/ds/projects/${projectCode}/task-instances`, { params });
  return resp.data;
}

/** 获取任务实例日志 */
export async function getTaskLog(projectCode: string, taskInstanceId: number) {
  const resp = await client.get(`/api/proxy/ds/projects/${projectCode}/task-instances/${taskInstanceId}/log`);
  return resp.data;
}
