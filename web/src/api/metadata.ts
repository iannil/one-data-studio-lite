/**
 * 元数据管理 API - OpenMetadata 适配
 *
 * 后端适配 OpenMetadata API，前端保持兼容性。
 * API 路径保持 /api/proxy/datahub 前缀以确保向后兼容。
 *
 * API 规范:
 * - v1 版本使用统一的 ApiResponse 格式
 * - 保留旧版 API 以确保向后兼容
 *
 * OpenMetadata 映射:
 * | 功能 | 原 DataHub API | OpenMetadata API |
 * |------|---------------|------------------|
 * | 搜索实体 | POST /entities?action=search | GET /api/v1/search/query |
 * | 获取 Schema | GET /aspects/v1 | GET /api/v1/tables/{fqn} |
 * | 获取血缘 | GET /relationships | GET /api/v1/lineage/{fqn} |
 * | 创建标签 | POST /entities?action=ingest | POST /api/v1/tags |
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
  schemaMetadata?: {
    schemaName?: string;
    platform?: string;
    fields?: SchemaField[];
  };
  fields?: SchemaField[];
  data?: Record<string, unknown>;
}

export interface SchemaField {
  fieldPath: string;
  nativeDataType: string;
  type?: string;
  description?: string;
  nullable?: boolean;
  tags?: string[];
}

export interface LineageParams {
  urn: string;
  direction: 'INCOMING' | 'OUTGOING';
}

export interface LineageRelationship {
  entity: string;
  urn: string;
  type?: string;
}

export interface LineageResult {
  urn: string;
  relationships: LineageRelationship[];
}

export interface TagProperties {
  name: string;
  description?: string;
}

/** 元数据实体基础类型 */
export interface MetadataEntity {
  urn?: string;
  type?: string;
  name?: string;
  description?: string;
  platform?: string;
  status?: string;
  /** OpenMetadata 原始数据 */
  _openmetadata?: {
    id?: string;
    fqn?: string;
  };
}

/** @deprecated 使用 MetadataEntity 替代 */
export type DataHubEntity = MetadataEntity;

/** 搜索结果响应 */
export interface SearchResults {
  entities?: MetadataEntity[];
  results?: MetadataEntity[];
  start?: number;
  count?: number;
  total?: number;
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/**
 * 搜索元数据实体
 *
 * 后端映射到 OpenMetadata: GET /api/v1/search/query
 */
export async function searchEntitiesV1(params: SearchParams): Promise<ApiResponse<SearchResults>> {
  const resp = await client.get<ApiResponse<SearchResults>>('/api/proxy/datahub/v1/entities', {
    params: {
      entity: params.entity,
      query: params.query || '*',
      start: params.start || 0,
      count: params.count || 20,
    },
  });
  return resp.data;
}

/**
 * 获取实体详情（Schema 等）
 *
 * 后端映射到 OpenMetadata: GET /api/v1/tables/{fqn}
 */
export async function getEntityAspectV1(urn: string, aspect: string): Promise<ApiResponse<EntityAspect>> {
  const resp = await client.get<ApiResponse<EntityAspect>>('/api/proxy/datahub/v1/aspects', {
    params: { urn, aspect },
  });
  return resp.data;
}

/**
 * 获取血缘关系
 *
 * 后端映射到 OpenMetadata: GET /api/v1/lineage/{fqn}
 */
export async function getLineageV1(params: LineageParams): Promise<ApiResponse<LineageResult>> {
  const resp = await client.get<ApiResponse<LineageResult>>('/api/proxy/datahub/v1/relationships', {
    params: { urn: params.urn, direction: params.direction },
  });
  return resp.data;
}

/**
 * 搜索标签
 *
 * 后端映射到 OpenMetadata: GET /api/v1/tags
 */
export async function searchTagsV1(query?: string): Promise<ApiResponse<SearchResults>> {
  const resp = await client.get<ApiResponse<SearchResults>>('/api/proxy/datahub/v1/tags/search', {
    params: { query: query || '*' },
  });
  return resp.data;
}

/**
 * 创建标签
 *
 * 后端映射到 OpenMetadata: POST /api/v1/tags
 */
export async function createTagV1(name: string, description?: string): Promise<ApiResponse<MetadataEntity>> {
  const resp = await client.post<ApiResponse<MetadataEntity>>('/api/proxy/datahub/v1/tags', null, {
    params: { name, description: description || '' },
  });
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/**
 * 搜索元数据实体
 * @deprecated 使用 searchEntitiesV1 替代
 */
export async function searchEntities(params: SearchParams): Promise<SearchResults> {
  const resp = await client.get('/api/proxy/datahub/v1/entities', {
    params: {
      entity: params.entity,
      query: params.query || '*',
      start: params.start || 0,
      count: params.count || 20,
    },
  });
  // 从 ApiResponse 中提取 data
  const apiResponse = resp.data as ApiResponse<SearchResults>;
  return (apiResponse.data || apiResponse) as SearchResults;
}

/**
 * 获取实体详情
 * @deprecated 使用 getEntityAspectV1 替代
 */
export async function getEntityAspect(urn: string, aspect: string): Promise<EntityAspect> {
  const resp = await client.get('/api/proxy/datahub/v1/aspects', {
    params: { urn, aspect },
  });
  // 从 ApiResponse 中提取 data
  const apiResponse = resp.data as ApiResponse<EntityAspect>;
  return (apiResponse.data || apiResponse) as EntityAspect;
}

/**
 * 获取血缘关系
 * @deprecated 使用 getLineageV1 替代
 */
export async function getLineage(urn: string, direction: 'INCOMING' | 'OUTGOING'): Promise<LineageResult> {
  const resp = await client.get('/api/proxy/datahub/v1/relationships', {
    params: { urn, direction },
  });
  // 从 ApiResponse 中提取 data
  const apiResponse = resp.data as ApiResponse<LineageResult>;
  return (apiResponse.data || apiResponse) as LineageResult;
}

/**
 * 搜索标签
 * @deprecated 使用 searchTagsV1 替代
 */
export async function searchTags(query?: string): Promise<SearchResults> {
  const resp = await client.get('/api/proxy/datahub/v1/tags/search', {
    params: { query: query || '*' },
  });
  // 从 ApiResponse 中提取 data
  const apiResponse = resp.data as ApiResponse<SearchResults>;
  return (apiResponse.data || apiResponse) as SearchResults;
}

/**
 * 创建标签
 * @deprecated 使用 createTagV1 替代
 */
export async function createTag(name: string, description?: string): Promise<MetadataEntity> {
  const resp = await client.post('/api/proxy/datahub/v1/tags', null, {
    params: { name, description: description || '' },
  });
  // 从 ApiResponse 中提取 data
  const apiResponse = resp.data as ApiResponse<MetadataEntity>;
  return (apiResponse.data || apiResponse) as MetadataEntity;
}
