/**
 * 敏感数据检测 API 测试
 * TDD: 验证敏感数据检测相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  scan,
  classify,
  getRules,
  getRule,
  addRule,
  deleteRule,
  getReports,
  getReport,
  scanAndApply,
  autoProtectTable,
  scanTableOnly,
} from './sensitive';
import { ErrorCode } from './types';

// Mock axios client
vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import client from './client';
const mockClient = vi.mocked(client);

describe('Sensitive API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // 扫描敏感数据测试
  // ============================================
  describe('scan', () => {
    it('should return scan report', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report_id: 'report-1',
          table_name: 'users',
          scan_time: '2024-02-01T10:00:00Z',
          columns: [
            {
              column_name: 'email',
              sensitive_type: 'EMAIL',
              confidence: 0.98,
              sample_values: ['test@example.com'],
            },
            {
              column_name: 'phone',
              sensitive_type: 'PHONE',
              confidence: 0.95,
              sample_values: ['13800138000'],
            },
          ],
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await scan({ table_name: 'users', database: 'production' });

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/sensitive/v1/scan', {
        table_name: 'users',
        database: 'production',
      });
      expect(result.columns).toHaveLength(2);
      expect(result.columns[0].sensitive_type).toBe('EMAIL');
    });

    it('should handle scan with sample size', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report_id: 'report-2',
          table_name: 'orders',
          scan_time: '2024-02-01T10:00:00Z',
          columns: [],
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await scan({ table_name: 'orders', sample_size: 500 });

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/sensitive/v1/scan', {
        table_name: 'orders',
        sample_size: 500,
      });
    });
  });

  // ============================================
  // LLM 分类测试
  // ============================================
  describe('classify', () => {
    it('should classify data samples', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          analysis: 'The data contains personal identifiable information (PII)',
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await classify(
        ['John Doe', 'johndoe@example.com', '555-1234'],
        'user profile data'
      );

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/sensitive/v1/classify', {
        data_samples: ['John Doe', 'johndoe@example.com', '555-1234'],
        context: 'user profile data',
      });
      expect(result.analysis).toContain('PII');
    });

    it('should classify without context', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          analysis: 'Mixed data types detected',
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await classify(['data1', 'data2']);

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/sensitive/v1/classify', {
        data_samples: ['data1', 'data2'],
        context: undefined,
      });
    });
  });

  // ============================================
  // 检测规则测试
  // ============================================
  describe('getRules', () => {
    it('should return all detection rules', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [
          {
            id: 'rule-1',
            name: 'Email Detection',
            pattern: '\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b',
            sensitive_type: 'EMAIL',
            enabled: true,
          },
          {
            id: 'rule-2',
            name: 'Phone Detection',
            pattern: '\\b1[3-9]\\d{9}\\b',
            sensitive_type: 'PHONE',
            enabled: true,
          },
        ],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getRules();

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/sensitive/v1/rules');
      expect(result).toHaveLength(2);
      expect(result[0].sensitive_type).toBe('EMAIL');
    });
  });

  describe('getRule', () => {
    it('should return single rule by ID', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          id: 'rule-1',
          name: 'Email Detection',
          pattern: '\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b',
          sensitive_type: 'EMAIL',
          enabled: true,
        },
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getRule('rule-1');

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/sensitive/v1/rules/rule-1');
      expect(result.id).toBe('rule-1');
      expect(result.sensitive_type).toBe('EMAIL');
    });
  });

  describe('addRule', () => {
    it('should add new detection rule', async () => {
      // Arrange
      const newRule = {
        name: 'ID Card Detection',
        pattern: '\\b\\d{17}[\\dXx]\\b',
        sensitive_type: 'ID_CARD',
        enabled: true,
      };
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          id: 'rule-3',
          ...newRule,
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await addRule(newRule);

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/sensitive/v1/rules', newRule);
      expect(result.id).toBeDefined();
      expect(result.name).toBe('ID Card Detection');
    });
  });

  describe('deleteRule', () => {
    it('should delete detection rule', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          message: 'Rule deleted successfully',
        },
      };
      mockClient.delete.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await deleteRule('rule-1');

      // Assert
      expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/sensitive/v1/rules/rule-1');
      expect(result.message).toBe('Rule deleted successfully');
    });
  });

  // ============================================
  // 扫描报告测试
  // ============================================
  describe('getReports', () => {
    it('should return paginated reports', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [
          {
            report_id: 'report-1',
            table_name: 'users',
            scan_time: '2024-02-01T10:00:00Z',
            total_columns: 5,
            sensitive_columns: 2,
          },
          {
            report_id: 'report-2',
            table_name: 'orders',
            scan_time: '2024-02-01T11:00:00Z',
            total_columns: 10,
            sensitive_columns: 3,
          },
        ],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getReports(1, 20);

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/sensitive/v1/reports', {
        params: { page: 1, page_size: 20 },
      });
      expect(result).toHaveLength(2);
    });

    it('should use default pagination', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      await getReports();

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/sensitive/v1/reports', {
        params: { page: 1, page_size: 20 },
      });
    });
  });

  describe('getReport', () => {
    it('should return single report by ID', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report_id: 'report-1',
          table_name: 'users',
          scan_time: '2024-02-01T10:00:00Z',
          columns: [
            {
              column_name: 'email',
              sensitive_type: 'EMAIL',
              confidence: 0.98,
            },
          ],
        },
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getReport('report-1');

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/sensitive/v1/reports/report-1');
      expect(result.report_id).toBe('report-1');
    });
  });

  // ============================================
  // 扫描并应用脱敏规则测试
  // ============================================
  describe('scanAndApply', () => {
    it('should scan and apply masking rules', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report: {
            report_id: 'report-1',
            table_name: 'users',
            scan_time: '2024-02-01T10:00:00Z',
            columns: [
              { column_name: 'email', sensitive_type: 'EMAIL', confidence: 0.98 },
            ],
          },
          applied_rules: [
            {
              table_name: 'users',
              column_name: 'email',
              algorithm_type: 'MASK',
              algorithm_props: { mask_from: 1, mask_to: 10 },
              sensitive_type: 'EMAIL',
            },
          ],
          skipped_rules: [],
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await scanAndApply({
        table_name: 'users',
        auto_apply: true,
      });

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/sensitive/v1/scan-and-apply', {
        table_name: 'users',
        auto_apply: true,
      });
      expect(result.applied_rules).toHaveLength(1);
      expect(result.applied_rules[0].column_name).toBe('email');
    });

    it('should handle skipped rules', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report: {
            report_id: 'report-2',
            table_name: 'orders',
            scan_time: '2024-02-01T10:00:00Z',
            columns: [],
          },
          applied_rules: [],
          skipped_rules: [
            {
              table_name: 'orders',
              column_name: 'notes',
              reason: 'Column type is TEXT, cannot apply masking',
            },
          ],
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await scanAndApply({ table_name: 'orders' });

      // Assert
      expect(result.skipped_rules).toHaveLength(1);
      expect(result.skipped_rules[0].column_name).toBe('notes');
    });
  });

  // ============================================
  // 便捷函数测试
  // ============================================
  describe('autoProtectTable', () => {
    it('should auto protect table with defaults', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report: { report_id: 'report-1', table_name: 'users', columns: [] },
          applied_rules: [],
          skipped_rules: [],
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await autoProtectTable('users');

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/sensitive/v1/scan-and-apply', {
        table_name: 'users',
        auto_apply: true,
        sample_size: 100,
      });
    });
  });

  describe('scanTableOnly', () => {
    it('should scan table without auto apply', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report: { report_id: 'report-1', table_name: 'users', columns: [] },
          applied_rules: [],
          skipped_rules: [],
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await scanTableOnly('users');

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/sensitive/v1/scan-and-apply', {
        table_name: 'users',
        auto_apply: false,
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle special characters in rule ID', async () => {
      // Arrange
      const ruleIdWithSpecialChars = 'rule-2024_test@example';
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          id: ruleIdWithSpecialChars,
          name: 'Test Rule',
          pattern: 'test',
          sensitive_type: 'TEST',
          enabled: true,
        },
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getRule(ruleIdWithSpecialChars);

      // Assert
      expect(result.id).toBe(ruleIdWithSpecialChars);
    });

    it('should handle empty scan result', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report_id: 'report-empty',
          table_name: 'empty_table',
          scan_time: '2024-02-01T10:00:00Z',
          columns: [],
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await scan({ table_name: 'empty_table' });

      // Assert
      expect(result.columns).toEqual([]);
    });

    it('should handle very large sample size', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          report_id: 'report-1',
          table_name: 'users',
          scan_time: '2024-02-01T10:00:00Z',
          columns: [],
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await scan({ table_name: 'users', sample_size: 1000000 });

      // Assert
      expect(result.columns).toEqual([]);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: sensitive data workflow', () => {
    it('should scan, classify, and apply rules', async () => {
      // Step 1: Scan table
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            report_id: 'report-1',
            table_name: 'users',
            columns: [
              { column_name: 'email', sensitive_type: 'EMAIL', confidence: 0.98 },
            ],
          },
        },
      });

      const scanResult = await scan({ table_name: 'users' });
      expect(scanResult.columns).toHaveLength(1);

      // Step 2: Get rules
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 'rule-1',
              name: 'Email Detection',
              pattern: 'email_pattern',
              sensitive_type: 'EMAIL',
              enabled: true,
            },
          ],
        },
      });

      const rules = await getRules();
      expect(rules).toHaveLength(1);

      // Step 3: Scan and apply
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            report: scanResult,
            applied_rules: [
              {
                table_name: 'users',
                column_name: 'email',
                algorithm_type: 'MASK',
                sensitive_type: 'EMAIL',
              },
            ],
            skipped_rules: [],
          },
        },
      });

      const applyResult = await scanAndApply({
        table_name: 'users',
        auto_apply: true,
      });
      expect(applyResult.applied_rules).toHaveLength(1);
    });
  });
});
