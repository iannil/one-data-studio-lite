/**
 * ShardingSphere 数据脱敏 API 测试
 * TDD: 验证数据脱敏相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getMaskRulesV1,
  getTableRulesV1,
  createMaskRuleV1,
  updateMaskRuleV1,
  deleteMaskRulesV1,
  batchCreateRulesV1,
  listAlgorithmsV1,
  listPresetsV1,
  syncRulesToProxyV1,
  getMaskRules,
  getTableRules,
  createMaskRule,
  updateMaskRule,
  deleteMaskRules,
  batchCreateRules,
  listAlgorithms,
  listPresets,
  syncRulesToProxy,
  applyPreset,
  createAndSyncRule,
} from './shardingsphere';
import { ErrorCode } from './types';

// Mock axios client
vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock utils module for isSuccessResponse
vi.mock('./utils', () => ({
  isSuccessResponse: (resp: unknown) => {
    return typeof resp === 'object' && resp !== null && 'code' in resp && (resp as { code: number }).code === ErrorCode.SUCCESS;
  },
}));

import client from './client';
const mockClient = vi.mocked(client);

describe('ShardingSphere API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('getMaskRulesV1', () => {
      it('should return all mask rules', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 'rule-1',
              table_name: 'users',
              column_name: 'email',
              algorithm_type: 'MASK_FIRST_N_LAST_M',
              algorithm_props: { 'first-n': '2', 'last-m': '2' },
              enabled: true,
              synced: true,
            },
            {
              id: 'rule-2',
              table_name: 'users',
              column_name: 'phone',
              algorithm_type: 'KEEP_FROM_X_TO_Y',
              algorithm_props: { 'from-x': '3', 'to-y': '7' },
              enabled: true,
              synced: true,
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getMaskRulesV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/mask-rules');
        expect(result.data).toHaveLength(2);
      });

      it('should handle empty rules list', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        const result = await getMaskRulesV1();

        // Assert
        expect(result.data).toEqual([]);
      });
    });

    describe('getTableRulesV1', () => {
      it('should return rules for specific table', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 'rule-1',
              table_name: 'users',
              column_name: 'email',
              algorithm_type: 'MD5',
              algorithm_props: {},
              enabled: true,
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getTableRulesV1('users');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/mask-rules/users');
        expect(result.data).toHaveLength(1);
      });

      it('should handle table name with special characters', async () => {
        // Arrange
        const tableName = 'table_with_special.chars';
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        const result = await getTableRulesV1(tableName);

        // Assert - table name should be encoded
        expect(result.data).toEqual([]);
      });
    });

    describe('createMaskRuleV1', () => {
      it('should create mask rule', async () => {
        // Arrange
        const newRule = {
          table_name: 'customers',
          column_name: 'ssn',
          algorithm_type: 'KEEP_FROM_X_TO_Y' as const,
          algorithm_props: { 'from-x': '1', 'to-y': '4' },
        };
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'rule-3',
            ...newRule,
            enabled: true,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createMaskRuleV1(newRule);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/mask-rules', newRule);
        expect(result.data.id).toBeDefined();
      });
    });

    describe('updateMaskRuleV1', () => {
      it('should update mask rule', async () => {
        // Arrange
        const updateRule = {
          table_name: 'users',
          column_name: 'email',
          algorithm_type: 'MD5' as const,
          algorithm_props: {},
        };
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'rule-1',
            ...updateRule,
            enabled: true,
          },
        };
        mockClient.put.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await updateMaskRuleV1(updateRule);

        // Assert
        expect(mockClient.put).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/mask-rules', updateRule);
        expect(result.data.algorithm_type).toBe('MD5');
      });
    });

    describe('deleteMaskRulesV1', () => {
      it('should delete all rules for table', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { message: 'Rules deleted' },
        };
        mockClient.delete.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await deleteMaskRulesV1('users');

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/mask-rules/users', {
          params: undefined,
        });
        expect(result.data.message).toBe('Rules deleted');
      });

      it('should delete specific column rule', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { message: 'Rule deleted' },
        };
        mockClient.delete.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await deleteMaskRulesV1('users', 'email');

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/mask-rules/users', {
          params: { column_name: 'email' },
        });
      });
    });

    describe('batchCreateRulesV1', () => {
      it('should create multiple rules', async () => {
        // Arrange
        const rules = [
          {
            table_name: 'users',
            column_name: 'email',
            algorithm_type: 'MD5' as const,
            algorithm_props: {},
          },
          {
            table_name: 'users',
            column_name: 'phone',
            algorithm_type: 'MASK_FIRST_N_LAST_M' as const,
            algorithm_props: { 'first-n': '3', 'last-m': '4' },
          },
        ];
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            created: 2,
            skipped: 0,
            errors: [],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await batchCreateRulesV1(rules);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/mask-rules/batch', {
          rules,
        });
        expect(result.data.created).toBe(2);
      });

      it('should handle partial failure', async () => {
        // Arrange
        const rules = [
          {
            table_name: 'users',
            column_name: 'email',
            algorithm_type: 'MD5' as const,
            algorithm_props: {},
          },
        ];
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            created: 0,
            skipped: 1,
            errors: ['Rule already exists'],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await batchCreateRulesV1(rules);

        // Assert
        expect(result.data.errors).toHaveLength(1);
      });
    });

    describe('listAlgorithmsV1', () => {
      it('should return available algorithms', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              type: 'MD5',
              description: 'MD5 hash algorithm',
              required_props: [],
            },
            {
              type: 'MASK_FIRST_N_LAST_M',
              description: 'Mask first N and last M characters',
              required_props: ['first-n', 'last-m'],
            },
            {
              type: 'KEEP_FROM_X_TO_Y',
              description: 'Keep characters from X to Y',
              required_props: ['from-x', 'to-y'],
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listAlgorithmsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/algorithms');
        expect(result.data).toHaveLength(3);
        expect(result.data[0].type).toBe('MD5');
      });
    });

    describe('listPresetsV1', () => {
      it('should return preset masking schemes', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              name: 'email_mask',
              description: 'Email masking',
              algorithm_type: 'KEEP_FROM_X_TO_Y',
              algorithm_props: { 'from-x': '2', 'to-y': '10', 'replace-char': '*' },
              applicable_types: ['VARCHAR', 'TEXT'],
            },
            {
              name: 'phone_mask',
              description: 'Phone number masking',
              algorithm_type: 'MASK_FIRST_N_LAST_M',
              algorithm_props: { 'first-n': '3', 'last-m': '4', 'replace-char': '*' },
              applicable_types: ['VARCHAR', 'TEXT'],
            },
            {
              name: 'ssn_hash',
              description: 'SSN hashing',
              algorithm_type: 'MD5',
              algorithm_props: {},
              applicable_types: ['VARCHAR', 'CHAR'],
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listPresetsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/presets');
        expect(result.data).toHaveLength(3);
        expect(result.data[0].name).toBe('email_mask');
      });
    });

    describe('syncRulesToProxyV1', () => {
      it('should sync all rules to proxy', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            synced_count: 5,
            failed_count: 0,
            errors: [],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await syncRulesToProxyV1();

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/sync', {
          table_names: undefined,
        });
        expect(result.data.synced_count).toBe(5);
      });

      it('should sync specific tables', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            synced_count: 2,
            failed_count: 0,
            errors: [],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await syncRulesToProxyV1(['users', 'orders']);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/shardingsphere/v1/sync', {
          table_names: ['users', 'orders'],
        });
      });
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('getMaskRules', () => {
      it('should return rules list', async () => {
        // Arrange
        const mockResponse = [
          { id: 'rule-1', table_name: 'users', column_name: 'email' },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getMaskRules();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/shardingsphere/mask-rules');
        expect(result).toHaveLength(1);
      });
    });

    describe('getTableRules', () => {
      it('should return rules for specific table', async () => {
        // Arrange
        const mockResponse = [
          { id: 'rule-1', table_name: 'users', column_name: 'email' },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getTableRules('users');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/shardingsphere/mask-rules/users');
        expect(result).toHaveLength(1);
      });
    });

    describe('createMaskRule', () => {
      it('should create rule', async () => {
        // Arrange
        const rule = {
          table_name: 'users',
          column_name: 'email',
          algorithm_type: 'MD5' as const,
          algorithm_props: {},
        };
        mockClient.post.mockResolvedValue({ data: { id: 'rule-1', ...rule } });

        // Act
        const result = await createMaskRule(rule);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/shardingsphere/mask-rules', rule);
      });
    });

    describe('updateMaskRule', () => {
      it('should update rule', async () => {
        // Arrange
        const rule = {
          table_name: 'users',
          column_name: 'email',
          algorithm_type: 'MD5' as const,
          algorithm_props: {},
        };
        mockClient.put.mockResolvedValue({ data: { id: 'rule-1', ...rule } });

        // Act
        const result = await updateMaskRule(rule);

        // Assert
        expect(mockClient.put).toHaveBeenCalledWith('/api/proxy/shardingsphere/mask-rules', rule);
      });
    });

    describe('deleteMaskRules', () => {
      it('should delete all rules for table', async () => {
        // Arrange
        mockClient.delete.mockResolvedValue({
          data: { message: 'Rules deleted' },
        });

        // Act
        const result = await deleteMaskRules('users');

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/shardingsphere/mask-rules/users', {
          params: undefined,
        });
        expect(result.message).toBe('Rules deleted');
      });

      it('should delete specific column rule', async () => {
        // Arrange
        mockClient.delete.mockResolvedValue({
          data: { message: 'Rule deleted' },
        });

        // Act
        const result = await deleteMaskRules('users', 'email');

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/shardingsphere/mask-rules/users', {
          params: { column_name: 'email' },
        });
      });
    });

    describe('batchCreateRules', () => {
      it('should batch create rules', async () => {
        // Arrange
        const rules = [
          {
            table_name: 'users',
            column_name: 'email',
            algorithm_type: 'MD5' as const,
            algorithm_props: {},
          },
        ];
        mockClient.post.mockResolvedValue({
          data: { created: 1, skipped: 0, errors: [] },
        });

        // Act
        const result = await batchCreateRules(rules);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/shardingsphere/mask-rules/batch', {
          rules,
        });
      });
    });

    describe('listAlgorithms', () => {
      it('should return available algorithms', async () => {
        // Arrange
        const mockResponse = [
          { type: 'MD5', description: 'MD5 hash algorithm', required_props: [] },
          { type: 'MASK_FIRST_N_LAST_M', description: 'Mask first N and last M', required_props: ['first-n', 'last-m'] },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listAlgorithms();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/shardingsphere/algorithms');
        expect(result).toHaveLength(2);
      });
    });

    describe('listPresets', () => {
      it('should return preset masking schemes', async () => {
        // Arrange
        const mockResponse = [
          {
            name: 'email_mask',
            description: 'Email masking',
            algorithm_type: 'KEEP_FROM_X_TO_Y',
            algorithm_props: { 'from-x': '2', 'to-y': '10' },
            applicable_types: ['VARCHAR'],
          },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listPresets();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/shardingsphere/presets');
        expect(result).toHaveLength(1);
      });
    });

    describe('syncRulesToProxy', () => {
      it('should sync rules', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: { success: true, synced_count: 1, failed_count: 0, errors: [] },
        });

        // Act
        const result = await syncRulesToProxy(['users']);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/shardingsphere/sync', {
          table_names: ['users'],
        });
      });
    });
  });

  // ============================================
  // 便捷函数测试
  // ============================================
  describe('convenience functions', () => {
    describe('applyPreset', () => {
      it('should apply preset to column', async () => {
        // Arrange
        // First call gets presets
        mockClient.get.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: [
              {
                name: 'email_mask',
                description: 'Email masking',
                algorithm_type: 'KEEP_FROM_X_TO_Y',
                algorithm_props: { 'from-x': '2', 'to-y': '10' },
                applicable_types: ['VARCHAR'],
              },
            ],
          },
        });
        // Second call creates rule
        mockClient.post.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: {
              id: 'rule-1',
              table_name: 'users',
              column_name: 'email',
              algorithm_type: 'KEEP_FROM_X_TO_Y',
              algorithm_props: { 'from-x': '2', 'to-y': '10' },
            },
          },
        });

        // Act
        const result = await applyPreset('users', 'email', 'email_mask');

        // Assert
        expect(result.table_name).toBe('users');
        expect(result.algorithm_type).toBe('KEEP_FROM_X_TO_Y');
      });

      it('should throw error when preset not found', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: [],
          },
        });

        // Act & Assert
        await expect(applyPreset('users', 'email', 'nonexistent')).rejects.toThrow('不存在');
      });
    });

    describe('createAndSyncRule', () => {
      it('should create and sync rule', async () => {
        // Arrange
        const ruleRequest = {
          table_name: 'users',
          column_name: 'email',
          algorithm_type: 'MD5' as const,
          algorithm_props: {},
        };
        // First call creates rule
        mockClient.post.mockResolvedValueOnce({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: {
              id: 'rule-1',
              ...ruleRequest,
            },
          },
        });
        // Second call syncs
        mockClient.post.mockResolvedValueOnce({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: {
              success: true,
              synced_count: 1,
              failed_count: 0,
              errors: [],
            },
          },
        });

        // Act
        const result = await createAndSyncRule(ruleRequest);

        // Assert
        expect(result.rule.table_name).toBe('users');
        expect(result.sync.success).toBe(true);
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty table name', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getTableRulesV1('');

      // Assert
      expect(result.data).toEqual([]);
    });

    it('should handle special characters in table name', async () => {
      // Arrange
      const tableName = 'table-with-special.chars';
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getTableRulesV1(tableName);

      // Assert
      expect(result.data).toEqual([]);
    });

    it('should handle empty algorithm props', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'rule-1',
            table_name: 'users',
            column_name: 'hash',
            algorithm_type: 'MD5',
            algorithm_props: {},
          },
        },
      });

      // Act
      const result = await createMaskRuleV1({
        table_name: 'users',
        column_name: 'hash',
        algorithm_type: 'MD5',
        algorithm_props: {},
      });

      // Assert
      expect(result.data.algorithm_props).toEqual({});
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: masking workflow', () => {
    it('should list presets, create rule, and sync', async () => {
      // Step 1: List presets
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              name: 'email_mask',
              algorithm_type: 'KEEP_FROM_X_TO_Y',
              algorithm_props: { 'from-x': '2', 'to-y': '10' },
              applicable_types: ['VARCHAR'],
            },
          ],
        },
      });

      const presets = await listPresetsV1();
      expect(presets.data).toHaveLength(1);
      const preset = presets.data[0];

      // Step 2: Create rule using preset
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'rule-1',
            table_name: 'users',
            column_name: 'email',
            algorithm_type: preset.algorithm_type,
            algorithm_props: preset.algorithm_props,
          },
        },
      });

      const rule = await createMaskRuleV1({
        table_name: 'users',
        column_name: 'email',
        algorithm_type: preset.algorithm_type,
        algorithm_props: preset.algorithm_props,
      });
      expect(rule.data.id).toBeDefined();

      // Step 3: Sync to proxy
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            synced_count: 1,
            failed_count: 0,
            errors: [],
          },
        },
      });

      const syncResult = await syncRulesToProxyV1(['users']);
      expect(syncResult.data.success).toBe(true);
    });
  });
});
