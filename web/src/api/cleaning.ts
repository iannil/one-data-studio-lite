/**
 * AI Cleaning 数据清洗规则推荐 API
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

export interface AnalyzeQualityRequest {
  table_name: string;
  database?: string;
  sample_size?: number;
}

export interface AnalyzeQualityResult {
  table_name: string;
  total_rows: number;
  quality_score: number;
  issues: Array<{
    column: string;
    issue_type: string;
    count: number;
    percentage: number;
  }>;
}

export interface RecommendRulesRequest {
  table_name: string;
  database?: string;
}

export interface CleaningRule {
  id?: string;
  name: string;
  description: string;
  type: string;
  scenario?: string;
  config?: Record<string, unknown>;
}

/** Extended cleaning rule with recommendation metadata */
export interface CleaningRuleRecommendation extends CleaningRule {
  column?: string;
  confidence?: number;
}

export interface RecommendRulesResult {
  table_name: string;
  recommended_rules: CleaningRule[];
}

export interface GenerateConfigRequest {
  table_name: string;
  rules: string[];
  output_format?: 'seatunnel' | 'hop';
}

export interface GenerateConfigResult {
  config: string;
  format: string;
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/** 分析数据质量 */
export async function analyzeQualityV1(
  params: AnalyzeQualityRequest
): Promise<ApiResponse<AnalyzeQualityResult>> {
  const resp = await client.post<ApiResponse<AnalyzeQualityResult>>(
    '/api/proxy/cleaning/v1/analyze',
    params
  );
  return resp.data;
}

/** AI 推荐清洗规则 */
export async function recommendRulesV1(
  params: RecommendRulesRequest
): Promise<ApiResponse<RecommendRulesResult>> {
  const resp = await client.post<ApiResponse<RecommendRulesResult>>(
    '/api/proxy/cleaning/v1/recommend',
    params
  );
  return resp.data;
}

/** 获取清洗规则模板 */
export async function getCleaningRulesV1(): Promise<ApiResponse<CleaningRule[]>> {
  const resp = await client.get<ApiResponse<CleaningRule[]>>(
    '/api/proxy/cleaning/v1/rules'
  );
  return resp.data;
}

/** 生成 SeaTunnel Transform 配置 */
export async function generateConfigV1(
  params: GenerateConfigRequest
): Promise<ApiResponse<GenerateConfigResult>> {
  const resp = await client.post<ApiResponse<GenerateConfigResult>>(
    '/api/proxy/cleaning/v1/generate-config',
    params
  );
  return resp.data;
}

// ============================================================
// 旧版 API（向后兼容，逐步废弃）
// ============================================================

/** 分析数据质量 */
export async function analyzeQuality(params: AnalyzeQualityRequest) {
  const resp = await client.post('/api/proxy/cleaning/api/cleaning/analyze', params);
  return resp.data;
}

/** AI 推荐清洗规则 */
export async function recommendRules(params: RecommendRulesRequest) {
  const resp = await client.post('/api/proxy/cleaning/api/cleaning/recommend', params);
  return resp.data;
}

/** 获取清洗规则模板 */
export async function getCleaningRules() {
  const resp = await client.get('/api/proxy/cleaning/api/cleaning/rules');
  return resp.data;
}

/** 生成 SeaTunnel Transform 配置 */
export async function generateConfig(params: GenerateConfigRequest) {
  const resp = await client.post('/api/proxy/cleaning/api/cleaning/generate-config', params);
  return resp.data;
}
