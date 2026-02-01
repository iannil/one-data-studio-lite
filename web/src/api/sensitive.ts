import client from './client';
import type { ApiResponse } from './types';
import { SensitiveScanRequest, SensitiveScanReport, DetectionRule } from '../types';
import { unwrapApiResponse } from './utils';

// ============================================================
// 类型定义
// ============================================================

/** 扫描并应用脱敏规则请求 */
export interface ScanAndApplyRequest {
  table_name: string;
  database?: string;
  sample_size?: number;
  auto_apply?: boolean;
}

/** 已应用的脱敏规则 */
export interface AppliedRule {
  table_name: string;
  column_name: string;
  algorithm_type: string;
  algorithm_props: Record<string, string>;
  sensitive_type: string;
  error?: string;
}

/** 跳过的规则 */
export interface SkippedRule {
  table_name: string;
  column_name: string;
  reason?: string;
  detected_types?: string[];
  error?: string;
}

/** 扫描并应用脱敏规则响应 */
export interface ScanAndApplyResponse {
  report: SensitiveScanReport;
  applied_rules: AppliedRule[];
  skipped_rules: SkippedRule[];
}

// ============================================================
// v1 版本 API（推荐使用，统一响应格式）
// ============================================================

/**
 * 扫描敏感数据
 */
export const scan = async (request: SensitiveScanRequest): Promise<SensitiveScanReport> => {
  const response = await client.post<ApiResponse<SensitiveScanReport>>(
    '/api/proxy/sensitive/v1/scan',
    request
  );
  return unwrapApiResponse(response);
};

/**
 * LLM 分类
 */
export const classify = async (
  dataSamples: unknown[],
  context?: string
): Promise<{ analysis: string }> => {
  const response = await client.post<ApiResponse<{ analysis: string }>>(
    '/api/proxy/sensitive/v1/classify',
    { data_samples: dataSamples, context }
  );
  return unwrapApiResponse(response);
};

/**
 * 获取检测规则列表
 */
export const getRules = async (): Promise<DetectionRule[]> => {
  const response = await client.get<ApiResponse<DetectionRule[]>>(
    '/api/proxy/sensitive/v1/rules'
  );
  return unwrapApiResponse(response);
};

/**
 * 获取单个检测规则
 */
export const getRule = async (ruleId: string): Promise<DetectionRule> => {
  const response = await client.get<ApiResponse<DetectionRule>>(
    `/api/proxy/sensitive/v1/rules/${ruleId}`
  );
  return unwrapApiResponse(response);
};

/**
 * 添加检测规则
 */
export const addRule = async (rule: Omit<DetectionRule, 'id'>): Promise<DetectionRule> => {
  const response = await client.post<ApiResponse<DetectionRule>>(
    '/api/proxy/sensitive/v1/rules',
    rule
  );
  return unwrapApiResponse(response);
};

/**
 * 删除检测规则
 */
export const deleteRule = async (ruleId: string): Promise<{ message: string }> => {
  const response = await client.delete<ApiResponse<{ message: string }>>(
    `/api/proxy/sensitive/v1/rules/${ruleId}`
  );
  return unwrapApiResponse(response);
};

/**
 * 获取扫描报告列表
 */
export const getReports = async (
  page: number = 1,
  pageSize: number = 20
): Promise<SensitiveScanReport[]> => {
  const response = await client.get<ApiResponse<SensitiveScanReport[]>>(
    '/api/proxy/sensitive/v1/reports',
    { params: { page, page_size: pageSize } }
  );
  return unwrapApiResponse(response);
};

/**
 * 获取单个扫描报告
 */
export const getReport = async (reportId: string): Promise<SensitiveScanReport> => {
  const response = await client.get<ApiResponse<SensitiveScanReport>>(
    `/api/proxy/sensitive/v1/reports/${reportId}`
  );
  return unwrapApiResponse(response);
};

/**
 * 扫描敏感数据并自动应用脱敏规则
 *
 * 工作流程：
 * 1. 扫描表，识别敏感字段
 * 2. 根据敏感类型匹配脱敏算法
 * 3. 调用 ShardingSphere API 创建脱敏规则
 */
export const scanAndApply = async (
  request: ScanAndApplyRequest
): Promise<ScanAndApplyResponse> => {
  const response = await client.post<ApiResponse<ScanAndApplyResponse>>(
    '/api/proxy/sensitive/v1/scan-and-apply',
    request
  );
  return unwrapApiResponse(response);
};

// ============================================================
// 便捷函数
// ============================================================

/**
 * 扫描表并自动应用所有可匹配的脱敏规则
 * @param tableName 表名
 */
export const autoProtectTable = async (tableName: string): Promise<ScanAndApplyResponse> => {
  return scanAndApply({
    table_name: tableName,
    auto_apply: true,
    sample_size: 100,
  });
};

/**
 * 仅扫描表（不自动应用规则）
 * @param tableName 表名
 */
export const scanTableOnly = async (tableName: string): Promise<ScanAndApplyResponse> => {
  return scanAndApply({
    table_name: tableName,
    auto_apply: false,
  });
};
