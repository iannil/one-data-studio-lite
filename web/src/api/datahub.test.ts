/**
 * DataHub 元数据管理 API 测试
 * TDD: 验证元数据管理相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  searchEntitiesV1,
  getEntityAspectV1,
  getLineageV1,
  searchTagsV1,
  createTagV1,
  searchEntities,
  getEntityAspect,
  getLineage,
  searchTags,
  createTag,
} from './datahub';
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

describe('DataHub API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('searchEntitiesV1', () => {
      it('should return search results', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            entities: [
              {
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
                type: 'dataset',
                name: 'users',
              },
              {
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,orders,PROD)',
                type: 'dataset',
                name: 'orders',
              },
            ],
            total: 2,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchEntitiesV1({ entity: 'dataset', query: 'user' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities?action=search', {
          entity: 'dataset',
          input: 'user',
          start: 0,
          count: 20,
        });
        expect(result.data.entities).toHaveLength(2);
      });

      it('should use default parameters', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
        });

        // Act
        await searchEntitiesV1({ entity: 'dataset' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities?action=search', {
          entity: 'dataset',
          input: '*',
          start: 0,
          count: 20,
        });
      });

      it('should support pagination', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
        });

        // Act
        await searchEntitiesV1({ entity: 'dataset', query: '*', start: 20, count: 10 });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities?action=search', {
          entity: 'dataset',
          input: '*',
          start: 20,
          count: 10,
        });
      });
    });

    describe('getEntityAspectV1', () => {
      it('should return entity aspect', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
            aspect: 'schemaMetadata',
            data: {
              schemaName: 'users',
              fields: [
                { name: 'id', type: 'INTEGER' },
                { name: 'name', type: 'VARCHAR' },
                { name: 'email', type: 'VARCHAR' },
              ],
            },
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getEntityAspectV1(
          'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
          'schemaMetadata'
        );

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/aspects', {
          params: {
            urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
            aspect: 'schemaMetadata',
          },
        });
        expect(result.data.aspect).toBe('schemaMetadata');
      });
    });

    describe('getLineageV1', () => {
      it('should return incoming lineage', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,fact_sales,PROD)',
            relationships: [
              {
                entity: 'dataset',
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,dim_user,PROD)',
              },
              {
                entity: 'dataset',
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,dim_product,PROD)',
              },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getLineageV1({
          urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,fact_sales,PROD)',
          direction: 'INCOMING',
        });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/relationships', {
          params: {
            urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,fact_sales,PROD)',
            direction: 'INCOMING',
          },
        });
        expect(result.data.relationships).toHaveLength(2);
      });

      it('should return outgoing lineage', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,dim_user,PROD)',
            relationships: [
              {
                entity: 'dataset',
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,fact_sales,PROD)',
              },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getLineageV1({
          urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,dim_user,PROD)',
          direction: 'OUTGOING',
        });

        // Assert
        expect(result.data.relationships).toHaveLength(1);
      });
    });

    describe('searchTagsV1', () => {
      it('should search tags', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            entities: [
              {
                urn: 'urn:li:tag:PII',
                type: 'tag',
                name: 'PII',
                description: 'Personal Identifiable Information',
              },
            ],
            total: 1,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchTagsV1('PII');

        // Assert
        expect(result.data.entities).toHaveLength(1);
      });

      it('should search all tags when no query provided', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
        });

        // Act
        await searchTagsV1();

        // Assert
        expect(mockClient.post).toHaveBeenCalled();
      });
    });

    describe('createTagV1', () => {
      it('should create new tag', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:tag:CONFIDENTIAL',
            type: 'tag',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createTagV1('CONFIDENTIAL', 'Confidential data');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities?action=ingest', {
          entity: {
            value: {
              'com.linkedin.tag.TagProperties': {
                name: 'CONFIDENTIAL',
                description: 'Confidential data',
              },
            },
          },
        });
        expect(result.data).toBeDefined();
      });

      it('should create tag without description', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: {} },
        });

        // Act
        await createTagV1('PUBLIC');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities?action=ingest', {
          entity: {
            value: {
              'com.linkedin.tag.TagProperties': {
                name: 'PUBLIC',
                description: '',
              },
            },
          },
        });
      });
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('searchEntities', () => {
      it('should return search results', async () => {
        // Arrange
        const mockResponse = {
          entities: [
            { urn: 'urn:li:dataset:users', type: 'dataset', name: 'users' },
          ],
          total: 1,
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchEntities({ entity: 'dataset', query: 'user' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/entities?action=search', {
          entity: 'dataset',
          input: 'user',
          start: 0,
          count: 20,
        });
      });
    });

    describe('getEntityAspect', () => {
      it('should return entity aspect', async () => {
        // Arrange
        const mockResponse = {
          urn: 'urn:li:dataset:users',
          aspect: 'schemaMetadata',
          data: { schemaName: 'users' },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getEntityAspect('urn:li:dataset:users', 'schemaMetadata');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/aspects/v1', {
          params: { urn: 'urn:li:dataset:users', aspect: 'schemaMetadata' },
        });
      });
    });

    describe('getLineage', () => {
      it('should return lineage', async () => {
        // Arrange
        const mockResponse = {
          urn: 'urn:li:dataset:fact',
          relationships: [{ entity: 'dataset', urn: 'urn:li:dataset:dim' }],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getLineage('urn:li:dataset:fact', 'INCOMING');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/relationships', {
          params: { urn: 'urn:li:dataset:fact', direction: 'INCOMING' },
        });
      });
    });

    describe('createTag', () => {
      it('should create tag', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({ data: { urn: 'urn:li:tag:TEST' } });

        // Act
        const result = await createTag('TEST', 'Test tag');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/entities?action=ingest', {
          entity: {
            value: {
              'com.linkedin.tag.TagProperties': {
                name: 'TEST',
                description: 'Test tag',
              },
            },
          },
        });
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty search query', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
      });

      // Act
      const result = await searchEntitiesV1({ entity: 'dataset', query: '' });

      // Assert - should use wildcard when empty
      expect(result.data.entities).toEqual([]);
    });

    it('should handle special characters in URN', async () => {
      // Arrange
      const specialUrn = 'urn:li:dataset:(urn:li:dataPlatform:postgresql,table-with-special.chars,PROD)';
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { urn: specialUrn, aspect: 'schemaMetadata' },
        },
      });

      // Act
      const result = await getEntityAspectV1(specialUrn, 'schemaMetadata');

      // Assert
      expect(result.data.urn).toBe(specialUrn);
    });

    it('should handle large pagination values', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
      });

      // Act
      await searchEntitiesV1({ entity: 'dataset', start: 10000, count: 1000 });

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities?action=search', {
        entity: 'dataset',
        input: '*',
        start: 10000,
        count: 1000,
      });
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: metadata workflow', () => {
    it('should search entity, get aspect, and query lineage', async () => {
      // Step 1: Search for dataset
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            entities: [
              {
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,fact_sales,PROD)',
                type: 'dataset',
                name: 'fact_sales',
              },
            ],
            total: 1,
          },
        },
      });

      const searchResult = await searchEntitiesV1({ entity: 'dataset', query: 'sales' });
      expect(searchResult.data.entities).toHaveLength(1);
      const datasetUrn = searchResult.data.entities[0].urn;

      // Step 2: Get schema aspect
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: datasetUrn,
            aspect: 'schemaMetadata',
            data: {
              schemaName: 'fact_sales',
              fields: [
                { name: 'sales_id', type: 'BIGINT' },
                { name: 'amount', type: 'DECIMAL' },
              ],
            },
          },
        },
      });

      const aspect = await getEntityAspectV1(datasetUrn, 'schemaMetadata');
      expect(aspect.data.aspect).toBe('schemaMetadata');

      // Step 3: Get lineage
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: datasetUrn,
            relationships: [
              {
                entity: 'dataset',
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,raw_sales,PROD)',
              },
            ],
          },
        },
      });

      const lineage = await getLineageV1({ urn: datasetUrn, direction: 'INCOMING' });
      expect(lineage.data.relationships).toHaveLength(1);
    });
  });
});
