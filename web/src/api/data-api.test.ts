/**
 * Data API 数据资产 API 网关测试
 * TDD: 验证数据资产API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  searchAssetsV1,
  getAssetDetailV1,
  getDatasetSchemaV1,
  queryDatasetV1,
  subscribeDatasetV1,
  getSubscriptionsV1,
  searchAssets,
  getAssetDetail,
  getDatasetSchema,
  queryDataset,
  subscribeDataset,
  getSubscriptions,
} from './data-api';
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

describe('Data API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('searchAssetsV1', () => {
      it('should return data assets list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: '1',
              name: 'users',
              type: 'table',
              description: 'User data',
              schema: 'public',
              database: 'production',
              tags: ['PII', 'core'],
            },
            {
              id: '2',
              name: 'orders',
              type: 'table',
              description: 'Order data',
              schema: 'public',
              database: 'production',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchAssetsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/v1/assets/search', {
          params: undefined,
        });
        expect(result.data).toHaveLength(2);
      });

      it('should search by keyword', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await searchAssetsV1({ keyword: 'user' });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/v1/assets/search', {
          params: { keyword: 'user' },
        });
      });

      it('should filter by type', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await searchAssetsV1({ type: 'table' });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/v1/assets/search', {
          params: { type: 'table' },
        });
      });

      it('should support pagination', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await searchAssetsV1({ page: 2, page_size: 20 });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/v1/assets/search', {
          params: { page: 2, page_size: 20 },
        });
      });
    });

    describe('getAssetDetailV1', () => {
      it('should return asset detail', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: '1',
            name: 'users',
            type: 'table',
            description: 'User data',
            schema: 'public',
            database: 'production',
            tags: ['PII', 'core'],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getAssetDetailV1('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/v1/assets/1');
        expect(result.data.name).toBe('users');
      });
    });

    describe('getDatasetSchemaV1', () => {
      it('should return dataset schema', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: '1',
            name: 'users',
            columns: [
              { name: 'id', type: 'INTEGER', nullable: false, description: 'Primary key' },
              { name: 'name', type: 'VARCHAR', nullable: false, description: 'User name' },
              { name: 'email', type: 'VARCHAR', nullable: true, description: 'Email address' },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDatasetSchemaV1('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/v1/data/1/schema');
        expect(result.data.columns).toHaveLength(3);
        expect(result.data.columns[0].name).toBe('id');
      });
    });

    describe('queryDatasetV1', () => {
      it('should execute SQL query', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            columns: ['id', 'name', 'email'],
            rows: [
              [1, 'Alice', 'alice@example.com'],
              [2, 'Bob', 'bob@example.com'],
            ],
            total: 2,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await queryDatasetV1('1', {
          sql: 'SELECT * FROM users LIMIT 10',
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/data-api/v1/data/1/query', {
          sql: 'SELECT * FROM users LIMIT 10',
        });
        expect(result.data.total).toBe(2);
      });

      it('should query with limit', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: { columns: [], rows: [], total: 0 },
          },
        });

        // Act
        const result = await queryDatasetV1('1', { limit: 100 });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/data-api/v1/data/1/query', {
          limit: 100,
        });
      });
    });

    describe('subscribeDatasetV1', () => {
      it('should subscribe to dataset', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'sub-1',
            dataset_id: '1',
            subscriber: 'admin',
            created_at: '2024-02-01T10:00:00Z',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await subscribeDatasetV1('1');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/data-api/v1/data/1/subscribe');
        expect(result.data.dataset_id).toBe('1');
      });
    });

    describe('getSubscriptionsV1', () => {
      it('should return subscriptions list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 'sub-1',
              dataset_id: '1',
              subscriber: 'admin',
              created_at: '2024-02-01T10:00:00Z',
            },
            {
              id: 'sub-2',
              dataset_id: '2',
              subscriber: 'admin',
              created_at: '2024-02-01T11:00:00Z',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getSubscriptionsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/v1/subscriptions');
        expect(result.data).toHaveLength(2);
      });
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('searchAssets', () => {
      it('should return assets list', async () => {
        // Arrange
        const mockResponse = {
          result: [
            { id: '1', name: 'users', type: 'table' },
            { id: '2', name: 'orders', type: 'table' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchAssets();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/api/assets/search', {
          params: undefined,
        });
        expect(result.result).toHaveLength(2);
      });
    });

    describe('getAssetDetail', () => {
      it('should return asset detail', async () => {
        // Arrange
        const mockResponse = { id: '1', name: 'users', type: 'table' };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getAssetDetail('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/api/assets/1');
        expect(result.name).toBe('users');
      });
    });

    describe('getDatasetSchema', () => {
      it('should return schema', async () => {
        // Arrange
        const mockResponse = {
          id: '1',
          name: 'users',
          columns: [{ name: 'id', type: 'INTEGER' }],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDatasetSchema('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/api/data/1/schema');
      });
    });

    describe('queryDataset', () => {
      it('should execute query', async () => {
        // Arrange
        const mockResponse = {
          columns: ['id'],
          rows: [[1]],
          total: 1,
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await queryDataset('1', { sql: 'SELECT 1' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/data-api/api/data/1/query', {
          sql: 'SELECT 1',
        });
      });
    });

    describe('subscribeDataset', () => {
      it('should subscribe', async () => {
        // Arrange
        const mockResponse = {
          id: 'sub-1',
          dataset_id: '1',
          created_at: '2024-02-01T10:00:00Z',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await subscribeDataset('1');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/data-api/api/data/1/subscribe');
      });
    });

    describe('getSubscriptions', () => {
      it('should return subscriptions', async () => {
        // Arrange
        const mockResponse = [
          { id: 'sub-1', dataset_id: '1' },
          { id: 'sub-2', dataset_id: '2' },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getSubscriptions();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/data-api/api/subscriptions');
        expect(result).toHaveLength(2);
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty search results', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await searchAssetsV1();

      // Assert
      expect(result.data).toEqual([]);
    });

    it('should handle empty query result', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { columns: [], rows: [], total: 0 },
        },
      });

      // Act
      const result = await queryDatasetV1('1', { sql: 'SELECT * FROM empty_table' });

      // Assert
      expect(result.data.total).toBe(0);
    });

    it('should handle special characters in asset ID', async () => {
      // Arrange
      const assetIdWithSpecialChars = 'table-2024_test@example';
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { id: assetIdWithSpecialChars, name: 'test' },
        },
      });

      // Act
      const result = await getAssetDetailV1(assetIdWithSpecialChars);

      // Assert
      expect(result.data.id).toBe(assetIdWithSpecialChars);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: data discovery workflow', () => {
    it('should search, get schema, and subscribe', async () => {
      // Step 1: Search assets
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: '1',
              name: 'users',
              type: 'table',
              description: 'User data',
            },
          ],
        },
      });

      const assets = await searchAssetsV1({ keyword: 'user' });
      expect(assets.data).toHaveLength(1);
      const assetId = assets.data[0].id;

      // Step 2: Get schema
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: assetId,
            name: 'users',
            columns: [
              { name: 'id', type: 'INTEGER' },
              { name: 'name', type: 'VARCHAR' },
            ],
          },
        },
      });

      const schema = await getDatasetSchemaV1(assetId);
      expect(schema.data.columns).toHaveLength(2);

      // Step 3: Subscribe
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'sub-1',
            dataset_id: assetId,
            created_at: '2024-02-01T10:00:00Z',
          },
        },
      });

      const subscription = await subscribeDatasetV1(assetId);
      expect(subscription.data.dataset_id).toBe(assetId);
    });
  });
});
