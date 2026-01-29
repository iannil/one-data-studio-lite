import client from './client';
import { SensitiveScanRequest, SensitiveScanReport, DetectionRule } from '../types';

// 扫描敏感数据
export const scan = async (request: SensitiveScanRequest): Promise<SensitiveScanReport> => {
  const response = await client.post<SensitiveScanReport>('/api/sensitive/scan', request);
  return response.data;
};

// LLM 分类
export const classify = async (dataSamples: any[], context?: string): Promise<{ analysis: string }> => {
  const response = await client.post('/api/sensitive/classify', {
    data_samples: dataSamples,
    context,
  });
  return response.data;
};

// 获取检测规则列表
export const getRules = async (): Promise<DetectionRule[]> => {
  const response = await client.get<DetectionRule[]>('/api/sensitive/rules');
  return response.data;
};

// 添加检测规则
export const addRule = async (rule: Omit<DetectionRule, 'id'>): Promise<DetectionRule> => {
  const response = await client.post<DetectionRule>('/api/sensitive/rules', rule);
  return response.data;
};

// 获取扫描报告列表
export const getReports = async (): Promise<SensitiveScanReport[]> => {
  const response = await client.get<SensitiveScanReport[]>('/api/sensitive/reports');
  return response.data;
};
