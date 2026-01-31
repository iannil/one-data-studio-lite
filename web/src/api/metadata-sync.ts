/**
 * Metadata Sync 元数据同步 API
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

/** 变更类型 */
export type ChangeType = 'CREATE' | 'UPDATE' | 'DELETE' | 'SCHEMA_CHANGE';

/** ETL 映射规则 */
export interface ETLMapping {
  id?: string;
  source_urn: string;
  target_task_type: 'dolphinscheduler' | 'seatunnel' | 'hop';
  target_task_id: string;
  trigger_on: ChangeType[];
  auto_update_config: boolean;
  description?: string;
  enabled?: boolean;
}

/** 同步结果 */
export interface SyncResult {
  success: boolean;
  message: string;
  affected_tasks?: string[];
  details?: Record<string, unknown>;
}

/** 元数据变更事件 */
export interface MetadataChangeEvent {
  event_id?: string;
  entity_urn: string;
  change_type: ChangeType;
  changed_fields?: string[];
  new_schema?: Record<string, unknown>;
  timestamp?: string;
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/**
 * 获取所有元数据映射规则
 */
export async function getMappingsV1(): Promise<ApiResponse<ETLMapping[]>> {
  const resp = await client.get<ApiResponse<ETLMapping[]>>('/api/proxy/metadata-sync/v1/mappings');
  return resp.data;
}

/**
 * 获取单个映射规则
 * @param mappingId 映射规则 ID
 */
export async function getMappingV1(mappingId: string): Promise<ApiResponse<ETLMapping>> {
  const resp = await client.get<ApiResponse<ETLMapping>>(
    `/api/proxy/metadata-sync/v1/mappings/${mappingId}`
  );
  return resp.data;
}

/**
 * 创建映射规则
 * @param mapping 映射规则配置
 */
export async function createMappingV1(mapping: Omit<ETLMapping, 'id'>): Promise<ApiResponse<ETLMapping>> {
  const resp = await client.post<ApiResponse<ETLMapping>>(
    '/api/proxy/metadata-sync/v1/mappings',
    mapping
  );
  return resp.data;
}

/**
 * 更新映射规则
 * @param mappingId 映射规则 ID
 * @param mapping 映射规则配置
 */
export async function updateMappingV1(
  mappingId: string,
  mapping: Partial<ETLMapping>
): Promise<ApiResponse<ETLMapping>> {
  const resp = await client.put<ApiResponse<ETLMapping>>(
    `/api/proxy/metadata-sync/v1/mappings/${mappingId}`,
    mapping
  );
  return resp.data;
}

/**
 * 删除映射规则
 * @param mappingId 映射规则 ID
 */
export async function deleteMappingV1(mappingId: string): Promise<ApiResponse<{ message: string }>> {
  const resp = await client.delete<ApiResponse<{ message: string }>>(
    `/api/proxy/metadata-sync/v1/mappings/${mappingId}`
  );
  return resp.data;
}

/**
 * 手动触发全量元数据同步
 */
export async function triggerSyncV1(): Promise<ApiResponse<SyncResult>> {
  const resp = await client.post<ApiResponse<SyncResult>>('/api/proxy/metadata-sync/v1/sync');
  return resp.data;
}

/**
 * 发送元数据变更事件（模拟 DataHub Webhook）
 * @param event 变更事件
 */
export async function sendMetadataEventV1(event: MetadataChangeEvent): Promise<ApiResponse<SyncResult>> {
  const resp = await client.post<ApiResponse<SyncResult>>(
    '/api/proxy/metadata-sync/v1/webhook',
    event
  );
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/**
 * 获取所有元数据映射规则
 */
export async function getMappings(): Promise<ETLMapping[]> {
  const resp = await client.get<ETLMapping[]>('/api/proxy/metadata/api/metadata/mappings');
  return resp.data;
}

/**
 * 获取单个映射规则
 * @param mappingId 映射规则 ID
 */
export async function getMapping(mappingId: string): Promise<ETLMapping> {
  const resp = await client.get<ETLMapping>(
    `/api/proxy/metadata/api/metadata/mappings/${mappingId}`
  );
  return resp.data;
}

/**
 * 创建映射规则
 * @param mapping 映射规则配置
 */
export async function createMapping(mapping: Omit<ETLMapping, 'id'>): Promise<ETLMapping> {
  const resp = await client.post<ETLMapping>(
    '/api/proxy/metadata/api/metadata/mappings',
    mapping
  );
  return resp.data;
}

/**
 * 更新映射规则
 * @param mappingId 映射规则 ID
 * @param mapping 映射规则配置
 */
export async function updateMapping(
  mappingId: string,
  mapping: Partial<ETLMapping>
): Promise<ETLMapping> {
  const resp = await client.put<ETLMapping>(
    `/api/proxy/metadata/api/metadata/mappings/${mappingId}`,
    mapping
  );
  return resp.data;
}

/**
 * 删除映射规则
 * @param mappingId 映射规则 ID
 */
export async function deleteMapping(mappingId: string): Promise<{ message: string }> {
  const resp = await client.delete<{ message: string }>(
    `/api/proxy/metadata/api/metadata/mappings/${mappingId}`
  );
  return resp.data;
}

/**
 * 手动触发全量元数据同步
 */
export async function triggerSync(): Promise<SyncResult> {
  const resp = await client.post<SyncResult>('/api/proxy/metadata/api/metadata/sync');
  return resp.data;
}

/**
 * 发送元数据变更事件（模拟 DataHub Webhook）
 * @param event 变更事件
 */
export async function sendMetadataEvent(event: MetadataChangeEvent): Promise<SyncResult> {
  const resp = await client.post<SyncResult>(
    '/api/proxy/metadata/api/metadata/webhook',
    event
  );
  return resp.data;
}

// ============================================================
// 便捷函数
// ============================================================

/**
 * 创建 DolphinScheduler 任务映射
 */
export async function createDolphinSchedulerMapping(
  sourceUrn: string,
  taskId: string,
  triggerOn: ChangeType[] = ['CREATE', 'UPDATE', 'SCHEMA_CHANGE'],
  description?: string
): Promise<ETLMapping> {
  return createMapping({
    source_urn: sourceUrn,
    target_task_type: 'dolphinscheduler',
    target_task_id: taskId,
    trigger_on: triggerOn,
    auto_update_config: true,
    description,
    enabled: true,
  });
}

/**
 * 创建 SeaTunnel 任务映射
 */
export async function createSeaTunnelMapping(
  sourceUrn: string,
  taskId: string,
  triggerOn: ChangeType[] = ['CREATE', 'UPDATE', 'SCHEMA_CHANGE'],
  description?: string
): Promise<ETLMapping> {
  return createMapping({
    source_urn: sourceUrn,
    target_task_type: 'seatunnel',
    target_task_id: taskId,
    trigger_on: triggerOn,
    auto_update_config: true,
    description,
    enabled: true,
  });
}

/**
 * 创建 Apache Hop 任务映射
 */
export async function createHopMapping(
  sourceUrn: string,
  taskId: string,
  triggerOn: ChangeType[] = ['CREATE', 'UPDATE', 'SCHEMA_CHANGE'],
  description?: string
): Promise<ETLMapping> {
  return createMapping({
    source_urn: sourceUrn,
    target_task_type: 'hop',
    target_task_id: taskId,
    trigger_on: triggerOn,
    auto_update_config: true,
    description,
    enabled: true,
  });
}

/**
 * 启用/禁用映射规则
 */
export async function toggleMapping(
  mappingId: string,
  enabled: boolean
): Promise<ETLMapping> {
  return updateMapping(mappingId, { enabled });
}
