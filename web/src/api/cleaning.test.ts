/**
 * AI Cleaning 数据清洗 API 测试
 * TDD: 验证数据清洗规则推荐API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  analyzeQualityV1,
  recommendRulesV1,
  getCleaningRulesV1,
  generateConfigV1,
  analyzeQuality,
  recommendRules,
  getCleaningRules,
  generateConfig,
} from './cleaning';
import { ErrorCode } from './types';

// Mock axios client
vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import client from './client';
const mockClient = vi.mocked(client);

describe('Cleaning API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('analyzeQualityV1', () => {
      it('should return quality analysis result', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'users',
            total_rows: 10000,
            quality_score: 0.85,
            issues: [
              {
                column: 'email',
                issue_type: 'INVALID_FORMAT',
                count: 150,
                percentage: 1.5,
              },
              {
                column: 'phone',
                issue_type: 'MISSING_VALUES',
                count: 500,
                percentage: 5.0,
              },
            ],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await analyzeQualityV1({ table_name: 'users' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cleaning/v1/analyze', {
          table_name: 'users',
        });
        expect(result.data.quality_score).toBe(0.85);
        expect(result.data.issues).toHaveLength(2);
      });

      it('should analyze with database parameter', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'orders',
            total_rows: 5000,
            quality_score: 0.92,
            issues: [],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await analyzeQualityV1({
          table_name: 'orders',
          database: 'production',
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cleaning/v1/analyze', {
          table_name: 'orders',
          database: 'production',
        });
      });

      it('should analyze with custom sample size', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'products',
            total_rows: 1000,
            quality_score: 0.95,
            issues: [],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await analyzeQualityV1({
          table_name: 'products',
          sample_size: 5000,
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cleaning/v1/analyze', {
          table_name: 'products',
          sample_size: 5000,
        });
      });
    });

    describe('recommendRulesV1', () => {
      it('should return recommended cleaning rules', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'users',
            recommended_rules: [
              {
                name: 'Remove Invalid Emails',
                description: 'Filter rows with invalid email format',
                type: 'FILTER',
                config: {
                  column: 'email',
                  pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
                },
              },
              {
                name: 'Fill Missing Phones',
                description: 'Replace null phone values with default',
                type: 'REPLACE',
                config: {
                  column: 'phone',
                  default_value: 'UNKNOWN',
                },
              },
            ],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await recommendRulesV1({ table_name: 'users' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cleaning/v1/recommend', {
          table_name: 'users',
        });
        expect(result.data.recommended_rules).toHaveLength(2);
        expect(result.data.recommended_rules[0].type).toBe('FILTER');
      });

      it('should return empty recommendations when no issues found', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'clean_table',
            recommended_rules: [],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await recommendRulesV1({ table_name: 'clean_table' });

        // Assert
        expect(result.data.recommended_rules).toEqual([]);
      });
    });

    describe('getCleaningRulesV1', () => {
      it('should return all cleaning rule templates', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              name: 'Remove Duplicates',
              description: 'Remove duplicate rows based on key columns',
              type: 'DEDUPLICATION',
              config: { keys: ['id'] },
            },
            {
              name: 'Normalize Dates',
              description: 'Convert date strings to ISO format',
              type: 'NORMALIZATION',
              config: { format: 'ISO8601' },
            },
            {
              name: 'Remove Outliers',
              description: 'Filter statistical outliers',
              type: 'FILTER',
              config: { method: 'IQR' },
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getCleaningRulesV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cleaning/v1/rules');
        expect(result.data).toHaveLength(3);
        expect(result.data[0].type).toBe('DEDUPLICATION');
      });
    });

    describe('generateConfigV1', () => {
      it('should generate SeaTunnel config', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            config: `
env {
  parallelism = 2
}

source {
  MySQL-CDC {
    hostname = "localhost"
  }
}

transform {
  Filter {
    field = "email"
            }
}

sink {
  Console {}
}
            `,
            format: 'seatunnel',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await generateConfigV1({
          table_name: 'users',
          rules: ['remove_invalid_emails', 'normalize_phones'],
          output_format: 'seatunnel',
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cleaning/v1/generate-config', {
          table_name: 'users',
          rules: ['remove_invalid_emails', 'normalize_phones'],
          output_format: 'seatunnel',
        });
        expect(result.data.config).toContain('env');
        expect(result.data.config).toContain('transform');
      });

      it('should generate Hop config', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            config: '<?xml version="1.0"?><transformation/>',
            format: 'hop',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await generateConfigV1({
          table_name: 'users',
          rules: ['normalize_dates'],
          output_format: 'hop',
        });

        // Assert
        expect(result.data.format).toBe('hop');
        expect(result.data.config).toContain('<?xml');
      });

      it('should default to seatunnel format', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            config: 'seatunnel config',
            format: 'seatunnel',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await generateConfigV1({
          table_name: 'users',
          rules: ['rule1'],
        });

        // Assert
        expect(result.data.format).toBe('seatunnel');
      });
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('analyzeQuality', () => {
      it('should return analysis result', async () => {
        // Arrange
        const mockResponse = {
          table_name: 'users',
          total_rows: 1000,
          quality_score: 0.9,
          issues: [],
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await analyzeQuality({ table_name: 'users' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cleaning/api/cleaning/analyze', {
          table_name: 'users',
        });
        expect(result.quality_score).toBe(0.9);
      });
    });

    describe('recommendRules', () => {
      it('should return recommended rules', async () => {
        // Arrange
        const mockResponse = {
          table_name: 'users',
          recommended_rules: [
            { name: 'Rule 1', type: 'FILTER', config: {} },
          ],
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await recommendRules({ table_name: 'users' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cleaning/api/cleaning/recommend', {
          table_name: 'users',
        });
      });
    });

    describe('getCleaningRules', () => {
      it('should return rule templates', async () => {
        // Arrange
        const mockResponse = [
          { name: 'Rule 1', type: 'FILTER', config: {} },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getCleaningRules();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cleaning/api/cleaning/rules');
        expect(result).toHaveLength(1);
      });
    });

    describe('generateConfig', () => {
      it('should generate config', async () => {
        // Arrange
        const mockResponse = {
          config: 'config content',
          format: 'seatunnel',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await generateConfig({
          table_name: 'users',
          rules: ['rule1'],
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cleaning/api/cleaning/generate-config', {
          table_name: 'users',
          rules: ['rule1'],
        });
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty table name', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({
        data: { code: 40002, message: '表名不能为空', data: null },
      });

      // Act
      const result = await analyzeQualityV1({ table_name: '' });

      // Assert - returns error response
      expect(result).toBeDefined();
    });

    it('should handle very large sample size', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'users',
            total_rows: 1000,
            quality_score: 1.0,
            issues: [],
          },
        },
      });

      // Act
      const result = await analyzeQualityV1({
        table_name: 'users',
        sample_size: 1000000000,
      });

      // Assert
      expect(result.data.quality_score).toBeDefined();
    });

    it('should handle zero quality score', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'bad_table',
            total_rows: 100,
            quality_score: 0.0,
            issues: [
              { column: 'all', issue_type: 'ALL_INVALID', count: 100, percentage: 100 },
            ],
          },
        },
      });

      // Act
      const result = await analyzeQualityV1({ table_name: 'bad_table' });

      // Assert
      expect(result.data.quality_score).toBe(0.0);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: cleaning workflow', () => {
    it('should analyze, recommend, and generate config', async () => {
      // Step 1: Analyze quality
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'users',
            total_rows: 10000,
            quality_score: 0.75,
            issues: [
              { column: 'email', issue_type: 'INVALID_FORMAT', count: 200, percentage: 2.0 },
            ],
          },
        },
      });

      const analysis = await analyzeQualityV1({ table_name: 'users' });
      expect(analysis.data.quality_score).toBe(0.75);

      // Step 2: Get recommendations
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            table_name: 'users',
            recommended_rules: [
              {
                name: 'Fix Email Format',
                type: 'NORMALIZE',
                config: { column: 'email' },
              },
            ],
          },
        },
      });

      const recommendations = await recommendRulesV1({ table_name: 'users' });
      expect(recommendations.data.recommended_rules).toHaveLength(1);

      // Step 3: Generate config
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            config: 'transform { Filter { field = "email" } }',
            format: 'seatunnel',
          },
        },
      });

      const config = await generateConfigV1({
        table_name: 'users',
        rules: ['fix_email_format'],
        output_format: 'seatunnel',
      });
      expect(config.data.config).toContain('transform');
    });
  });
});
