/**
 * DataHub 元数据管理 API
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

export interface SearchParams {
  entity: string;
  query?: string;
  start?: number;
  count?: number;
}

export interface EntityAspect {
  urn: string;
  aspect: string;
  data?: Record<string, unknown>;
}

export interface LineageParams {
  urn: string;
  direction: 'INCOMING' | 'OUTGOING';
}

export interface LineageResult {
  urn: string;
  relationships: Array<{
    entity: string;
    urn: string;
  }>;
}

export interface TagProperties {
  name: string;
  description?: string;
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/** 搜索 DataHub 实体 */
export async function searchEntitiesV1(params: SearchParams): Promise<ApiResponse<Record<string, unknown>>> {
  const resp = await client.post<ApiResponse<Record<string, unknown>>>('/api/proxy/datahub/v1/entities?action=search', {
    entity: params.entity,
    input: params.query || '*',
    start: params.start || 0,
    count: params.count || 20,
  });
  return resp.data;
}

/** 获取实体详情 */
export async function getEntityAspectV1(urn: string, aspect: string): Promise<ApiResponse<EntityAspect>> {
  const resp = await client.get<ApiResponse<EntityAspect>>(`/api/proxy/datahub/v1/aspects`, {
    params: { urn, aspect },
  });
  return resp.data;
}

/** 获取血缘关系 */
export async function getLineageV1(params: LineageParams): Promise<ApiResponse<LineageResult>> {
  const resp = await client.get<ApiResponse<LineageResult>>('/api/proxy/datahub/v1/relationships', {
    params: { urn: params.urn, direction: params.direction },
  });
  return resp.data;
}

/** 搜索标签 */
export async function searchTagsV1(query?: string): Promise<ApiResponse<Record<string, unknown>>> {
  return searchEntitiesV1({ entity: 'tag', query });
}

/** 创建标签 */
export async function createTagV1(name: string, description?: string): Promise<ApiResponse<Record<string, unknown>>> {
  const resp = await client.post<ApiResponse<Record<string, unknown>>>('/api/proxy/datahub/v1/entities?action=ingest', {
    entity: {
      value: {
        'com.linkedin.tag.TagProperties': {
          name,
          description: description || '',
        },
      },
    },
  });
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/** 搜索 DataHub 实体 */
export async function searchEntities(params: SearchParams) {
  const resp = await client.post('/api/proxy/datahub/entities?action=search', {
    entity: params.entity,
    input: params.query || '*',
    start: params.start || 0,
    count: params.count || 20,
  });
  return resp.data;
}

/** 获取实体详情 */
export async function getEntityAspect(urn: string, aspect: string) {
  const resp = await client.get(`/api/proxy/datahub/aspects/v1`, {
    params: { urn, aspect },
  });
  return resp.data;
}

/** 获取血缘关系 */
export async function getLineage(urn: string, direction: 'INCOMING' | 'OUTGOING') {
  const resp = await client.get('/api/proxy/datahub/relationships', {
    params: { urn, direction },
  });
  return resp.data;
}

/** 搜索标签 */
export async function searchTags(query?: string) {
  return searchEntities({ entity: 'tag', query });
}

/** 创建标签 */
export async function createTag(name: string, description?: string) {
  const resp = await client.post('/api/proxy/datahub/entities?action=ingest', {
    entity: {
      value: {
        'com.linkedin.tag.TagProperties': {
          name,
          description: description || '',
        },
      },
    },
  });
  return resp.data;
}
