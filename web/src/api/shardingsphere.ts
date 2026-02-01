/**
 * ShardingSphere 数据脱敏 API
 *
 * API 规范:
 * - v1 版本使用统一的 ApiResponse 格式
 * - 保留旧版 API 以确保向后兼容
 */

import client from './client';
import type { ApiResponse } from './types';
import { isSuccessResponse } from './types';

// ============================================================
// 类型定义
// ============================================================

/** 脱敏算法类型 */
export type MaskAlgorithmType =
  | 'KEEP_FIRST_N_LAST_M'
  | 'KEEP_FROM_X_TO_Y'
  | 'MASK_FIRST_N_LAST_M'
  | 'MASK_FROM_X_TO_Y'
  | 'MASK_BEFORE_SPECIAL_CHARS'
  | 'MASK_AFTER_SPECIAL_CHARS'
  | 'GENERIC_TABLE_RANDOM_REPLACE'
  | 'MD5';

/** 脱敏算法属性 */
export interface AlgorithmProps {
  'first-n'?: string;
  'last-m'?: string;
  'from-x'?: string;
  'to-y'?: string;
  'replace-char'?: string;
  'special-chars'?: string;
  [key: string]: string | undefined;
}

/** 脱敏规则 */
export interface MaskRule {
  id?: string;
  table_name: string;
  column_name: string;
  algorithm_type: MaskAlgorithmType;
  algorithm_props: AlgorithmProps;
  enabled?: boolean;
  synced?: boolean;
  created_at?: string;
  updated_at?: string;
}

/** 脱敏算法信息 */
export interface AlgorithmInfo {
  type: MaskAlgorithmType;
  description: string;
  required_props: string[];
}

/** 预设脱敏方案 */
export interface MaskPreset {
  name: string;
  description: string;
  algorithm_type: MaskAlgorithmType;
  algorithm_props: AlgorithmProps;
  applicable_types: string[];
}

/** 创建规则请求 */
export interface CreateMaskRuleRequest {
  table_name: string;
  column_name: string;
  algorithm_type: MaskAlgorithmType;
  algorithm_props: AlgorithmProps;
}

/** 批量创建规则请求 */
export interface BatchCreateRequest {
  rules: CreateMaskRuleRequest[];
}

/** 同步结果 */
export interface SyncResult {
  success: boolean;
  synced_count: number;
  failed_count: number;
  errors: string[];
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/**
 * 获取所有脱敏规则
 */
export async function getMaskRulesV1(): Promise<ApiResponse<MaskRule[]>> {
  const resp = await client.get<ApiResponse<MaskRule[]>>('/api/proxy/shardingsphere/v1/mask-rules');
  return resp.data;
}

/**
 * 获取指定表的脱敏规则
 * @param tableName 表名
 */
export async function getTableRulesV1(tableName: string): Promise<ApiResponse<MaskRule[]>> {
  const resp = await client.get<ApiResponse<MaskRule[]>>(
    `/api/proxy/shardingsphere/v1/mask-rules/${encodeURIComponent(tableName)}`
  );
  return resp.data;
}

/**
 * 创建脱敏规则
 * @param rule 规则配置
 */
export async function createMaskRuleV1(rule: CreateMaskRuleRequest): Promise<ApiResponse<MaskRule>> {
  const resp = await client.post<ApiResponse<MaskRule>>('/api/proxy/shardingsphere/v1/mask-rules', rule);
  return resp.data;
}

/**
 * 更新脱敏规则
 * @param rule 规则配置（包含 table_name 和 column_name）
 */
export async function updateMaskRuleV1(rule: CreateMaskRuleRequest): Promise<ApiResponse<MaskRule>> {
  const resp = await client.put<ApiResponse<MaskRule>>('/api/proxy/shardingsphere/v1/mask-rules', rule);
  return resp.data;
}

/**
 * 删除表的脱敏规则
 * @param tableName 表名
 * @param columnName 可选，指定列名则只删除该列规则
 */
export async function deleteMaskRulesV1(
  tableName: string,
  columnName?: string
): Promise<ApiResponse<{ message: string }>> {
  const params = columnName ? { column_name: columnName } : undefined;
  const resp = await client.delete<ApiResponse<{ message: string }>>(
    `/api/proxy/shardingsphere/v1/mask-rules/${encodeURIComponent(tableName)}`,
    { params }
  );
  return resp.data;
}

/**
 * 批量创建脱敏规则
 * @param rules 规则列表
 */
export async function batchCreateRulesV1(
  rules: CreateMaskRuleRequest[]
): Promise<ApiResponse<{ created: number; skipped: number; errors: string[] }>> {
  const resp = await client.post<ApiResponse<{ created: number; skipped: number; errors: string[] }>>(
    '/api/proxy/shardingsphere/v1/mask-rules/batch',
    { rules }
  );
  return resp.data;
}

/**
 * 获取可用的脱敏算法列表
 */
export async function listAlgorithmsV1(): Promise<ApiResponse<AlgorithmInfo[]>> {
  const resp = await client.get<ApiResponse<AlgorithmInfo[]>>('/api/proxy/shardingsphere/v1/algorithms');
  return resp.data;
}

/**
 * 获取预设脱敏方案列表
 */
export async function listPresetsV1(): Promise<ApiResponse<MaskPreset[]>> {
  const resp = await client.get<ApiResponse<MaskPreset[]>>('/api/proxy/shardingsphere/v1/presets');
  return resp.data;
}

/**
 * 同步规则到 ShardingSphere Proxy
 * @param tableNames 可选，指定要同步的表名列表，为空则同步所有
 */
export async function syncRulesToProxyV1(tableNames?: string[]): Promise<ApiResponse<SyncResult>> {
  const resp = await client.post<ApiResponse<SyncResult>>('/api/proxy/shardingsphere/v1/sync', {
    table_names: tableNames,
  });
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/**
 * 获取所有脱敏规则
 */
export async function getMaskRules(): Promise<MaskRule[]> {
  const resp = await client.get<MaskRule[]>('/api/proxy/shardingsphere/mask-rules');
  return resp.data;
}

/**
 * 获取指定表的脱敏规则
 * @param tableName 表名
 */
export async function getTableRules(tableName: string): Promise<MaskRule[]> {
  const resp = await client.get<MaskRule[]>(
    `/api/proxy/shardingsphere/mask-rules/${encodeURIComponent(tableName)}`
  );
  return resp.data;
}

/**
 * 创建脱敏规则
 * @param rule 规则配置
 */
export async function createMaskRule(rule: CreateMaskRuleRequest): Promise<MaskRule> {
  const resp = await client.post<MaskRule>('/api/proxy/shardingsphere/mask-rules', rule);
  return resp.data;
}

/**
 * 更新脱敏规则
 * @param rule 规则配置（包含 table_name 和 column_name）
 */
export async function updateMaskRule(rule: CreateMaskRuleRequest): Promise<MaskRule> {
  const resp = await client.put<MaskRule>('/api/proxy/shardingsphere/mask-rules', rule);
  return resp.data;
}

/**
 * 删除表的脱敏规则
 * @param tableName 表名
 * @param columnName 可选，指定列名则只删除该列规则
 */
export async function deleteMaskRules(
  tableName: string,
  columnName?: string
): Promise<{ message: string }> {
  const params = columnName ? { column_name: columnName } : undefined;
  const resp = await client.delete<{ message: string }>(
    `/api/proxy/shardingsphere/mask-rules/${encodeURIComponent(tableName)}`,
    { params }
  );
  return resp.data;
}

/**
 * 批量创建脱敏规则
 * @param rules 规则列表
 */
export async function batchCreateRules(
  rules: CreateMaskRuleRequest[]
): Promise<{ created: number; skipped: number; errors: string[] }> {
  const resp = await client.post<{ created: number; skipped: number; errors: string[] }>(
    '/api/proxy/shardingsphere/mask-rules/batch',
    { rules }
  );
  return resp.data;
}

/**
 * 获取可用的脱敏算法列表
 */
export async function listAlgorithms(): Promise<AlgorithmInfo[]> {
  const resp = await client.get<AlgorithmInfo[]>('/api/proxy/shardingsphere/algorithms');
  return resp.data;
}

/**
 * 获取预设脱敏方案列表
 */
export async function listPresets(): Promise<MaskPreset[]> {
  const resp = await client.get<MaskPreset[]>('/api/proxy/shardingsphere/presets');
  return resp.data;
}

/**
 * 同步规则到 ShardingSphere Proxy
 * @param tableNames 可选，指定要同步的表名列表，为空则同步所有
 */
export async function syncRulesToProxy(tableNames?: string[]): Promise<SyncResult> {
  const resp = await client.post<SyncResult>('/api/proxy/shardingsphere/sync', {
    table_names: tableNames,
  });
  return resp.data;
}

// ============================================================
// 便捷函数
// ============================================================

/**
 * 应用预设方案到指定列
 * @param tableName 表名
 * @param columnName 列名
 * @param presetName 预设名称
 */
export async function applyPreset(
  tableName: string,
  columnName: string,
  presetName: string
): Promise<MaskRule> {
  const presetsResp = await listPresetsV1();
  if (!isSuccessResponse(presetsResp)) {
    throw new Error(presetsResp.message || '获取预设方案失败');
  }
  const preset = presetsResp.data?.find((p) => p.name === presetName);
  if (!preset) {
    throw new Error(`预设方案 "${presetName}" 不存在`);
  }
  const ruleResp = await createMaskRuleV1({
    table_name: tableName,
    column_name: columnName,
    algorithm_type: preset.algorithm_type,
    algorithm_props: preset.algorithm_props,
  });
  if (!isSuccessResponse(ruleResp) || !ruleResp.data) {
    throw new Error(ruleResp.message || '创建规则失败');
  }
  return ruleResp.data;
}

/**
 * 创建并立即同步规则
 * @param rule 规则配置
 */
export async function createAndSyncRule(rule: CreateMaskRuleRequest): Promise<{
  rule: MaskRule;
  sync: SyncResult;
}> {
  const ruleResp = await createMaskRuleV1(rule);
  if (!isSuccessResponse(ruleResp) || !ruleResp.data) {
    throw new Error(ruleResp.message || '创建规则失败');
  }
  const syncResp = await syncRulesToProxyV1([rule.table_name]);
  if (!isSuccessResponse(syncResp) || !syncResp.data) {
    throw new Error(syncResp.message || '同步规则失败');
  }
  return { rule: ruleResp.data, sync: syncResp.data };
}
