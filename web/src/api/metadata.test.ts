/**
 * 元数据管理 API 测试 - OpenMetadata 适配
 *
 * 测试后端适配 OpenMetadata API 后的前端 API 调用
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
} from './metadata';
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

describe('Metadata API (OpenMetadata)', () => {
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
                type: 'table',
                name: 'users',
                _openmetadata: { fqn: 'mysql.default.users' },
              },
              {
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,orders,PROD)',
                type: 'table',
                name: 'orders',
                _openmetadata: { fqn: 'mysql.default.orders' },
              },
            ],
            total: 2,
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchEntitiesV1({ entity: 'dataset', query: 'user' });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities', {
          params: {
            entity: 'dataset',
            query: 'user',
            start: 0,
            count: 20,
          },
        });
        expect(result.data.entities).toHaveLength(2);
      });

      it('should use default parameters', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
        });

        // Act
        await searchEntitiesV1({ entity: 'dataset' });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities', {
          params: {
            entity: 'dataset',
            query: '*',
            start: 0,
            count: 20,
          },
        });
      });

      it('should support pagination', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
        });

        // Act
        await searchEntitiesV1({ entity: 'dataset', query: '*', start: 20, count: 10 });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities', {
          params: {
            entity: 'dataset',
            query: '*',
            start: 20,
            count: 10,
          },
        });
      });
    });

    describe('getEntityAspectV1', () => {
      it('should return entity aspect with schema', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
            aspect: 'schemaMetadata',
            schemaMetadata: {
              schemaName: 'users',
              platform: 'mysql',
              fields: [
                { fieldPath: 'id', nativeDataType: 'INTEGER', nullable: false },
                { fieldPath: 'name', nativeDataType: 'VARCHAR', nullable: true },
                { fieldPath: 'email', nativeDataType: 'VARCHAR', nullable: true },
              ],
            },
            fields: [
              { fieldPath: 'id', nativeDataType: 'INTEGER', nullable: false },
              { fieldPath: 'name', nativeDataType: 'VARCHAR', nullable: true },
              { fieldPath: 'email', nativeDataType: 'VARCHAR', nullable: true },
            ],
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
        expect(result.data.fields).toHaveLength(3);
      });
    });

    describe('getLineageV1', () => {
      it('should return incoming lineage (upstream)', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,fact_sales,PROD)',
            relationships: [
              {
                entity: 'table',
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,dim_user,PROD)',
                type: 'DownstreamOf',
              },
              {
                entity: 'table',
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,dim_product,PROD)',
                type: 'DownstreamOf',
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

      it('should return outgoing lineage (downstream)', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,dim_user,PROD)',
            relationships: [
              {
                entity: 'table',
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,fact_sales,PROD)',
                type: 'UpstreamOf',
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
      it('should search tags using dedicated endpoint', async () => {
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
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchTagsV1('PII');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/tags/search', {
          params: { query: 'PII' },
        });
        expect(result.data.entities).toHaveLength(1);
      });

      it('should search all tags when no query provided', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
        });

        // Act
        await searchTagsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/tags/search', {
          params: { query: '*' },
        });
      });
    });

    describe('createTagV1', () => {
      it('should create new tag via OpenMetadata API', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:tag:CONFIDENTIAL',
            name: 'CONFIDENTIAL',
            description: 'Confidential data',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createTagV1('CONFIDENTIAL', 'Confidential data');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/tags', null, {
          params: { name: 'CONFIDENTIAL', description: 'Confidential data' },
        });
        expect(result.data.name).toBe('CONFIDENTIAL');
      });

      it('should create tag without description', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: { urn: 'urn:li:tag:PUBLIC', name: 'PUBLIC' } },
        });

        // Act
        await createTagV1('PUBLIC');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/tags', null, {
          params: { name: 'PUBLIC', description: '' },
        });
      });
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('searchEntities', () => {
      it('should return search results and extract data', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            entities: [
              { urn: 'urn:li:dataset:users', type: 'table', name: 'users' },
            ],
            total: 1,
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchEntities({ entity: 'dataset', query: 'user' });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities', {
          params: {
            entity: 'dataset',
            query: 'user',
            start: 0,
            count: 20,
          },
        });
        // Legacy API should extract data from ApiResponse
        expect(result.entities).toHaveLength(1);
      });
    });

    describe('getEntityAspect', () => {
      it('should return entity aspect and extract data', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:dataset:users',
            aspect: 'schemaMetadata',
            fields: [{ fieldPath: 'id', nativeDataType: 'INTEGER' }],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getEntityAspect('urn:li:dataset:users', 'schemaMetadata');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/aspects', {
          params: { urn: 'urn:li:dataset:users', aspect: 'schemaMetadata' },
        });
        expect(result.fields).toHaveLength(1);
      });
    });

    describe('getLineage', () => {
      it('should return lineage and extract data', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: 'urn:li:dataset:fact',
            relationships: [{ entity: 'table', urn: 'urn:li:dataset:dim' }],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getLineage('urn:li:dataset:fact', 'INCOMING');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/relationships', {
          params: { urn: 'urn:li:dataset:fact', direction: 'INCOMING' },
        });
        expect(result.relationships).toHaveLength(1);
      });
    });

    describe('searchTags', () => {
      it('should search tags and extract data', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            entities: [{ urn: 'urn:li:tag:PII', name: 'PII' }],
            total: 1,
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await searchTags('PII');

        // Assert
        expect(result.entities).toHaveLength(1);
      });
    });

    describe('createTag', () => {
      it('should create tag and extract data', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { urn: 'urn:li:tag:TEST', name: 'TEST' },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createTag('TEST', 'Test tag');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/datahub/v1/tags', null, {
          params: { name: 'TEST', description: 'Test tag' },
        });
        expect(result.name).toBe('TEST');
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty search query', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
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
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { entities: [], total: 0 } },
      });

      // Act
      await searchEntitiesV1({ entity: 'dataset', start: 10000, count: 1000 });

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/datahub/v1/entities', {
        params: {
          entity: 'dataset',
          query: '*',
          start: 10000,
          count: 1000,
        },
      });
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: metadata workflow', () => {
    it('should search entity, get aspect, and query lineage', async () => {
      // Step 1: Search for dataset
      mockClient.get.mockResolvedValueOnce({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            entities: [
              {
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,fact_sales,PROD)',
                type: 'table',
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
      mockClient.get.mockResolvedValueOnce({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: datasetUrn,
            aspect: 'schemaMetadata',
            schemaMetadata: {
              schemaName: 'fact_sales',
              platform: 'mysql',
              fields: [
                { fieldPath: 'sales_id', nativeDataType: 'BIGINT' },
                { fieldPath: 'amount', nativeDataType: 'DECIMAL' },
              ],
            },
            fields: [
              { fieldPath: 'sales_id', nativeDataType: 'BIGINT' },
              { fieldPath: 'amount', nativeDataType: 'DECIMAL' },
            ],
          },
        },
      });

      const aspect = await getEntityAspectV1(datasetUrn, 'schemaMetadata');
      expect(aspect.data.aspect).toBe('schemaMetadata');

      // Step 3: Get lineage
      mockClient.get.mockResolvedValueOnce({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            urn: datasetUrn,
            relationships: [
              {
                entity: 'table',
                urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,raw_sales,PROD)',
                type: 'DownstreamOf',
              },
            ],
          },
        },
      });

      const lineage = await getLineageV1({ urn: datasetUrn, direction: 'INCOMING' });
      expect(lineage.data.relationships).toHaveLength(1);
    });
  });

  // ============================================
  // OpenMetadata 特定功能测试
  // ============================================
  describe('OpenMetadata specific features', () => {
    it('should include OpenMetadata metadata in entity response', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          entities: [
            {
              urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
              type: 'table',
              name: 'users',
              _openmetadata: {
                id: 'abc-123-uuid',
                fqn: 'mysql.default.users',
              },
            },
          ],
          total: 1,
        },
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await searchEntitiesV1({ entity: 'dataset' });

      // Assert
      expect(result.data.entities[0]._openmetadata).toBeDefined();
      expect(result.data.entities[0]._openmetadata.fqn).toBe('mysql.default.users');
    });
  });
});
