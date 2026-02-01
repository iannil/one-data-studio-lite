/**
 * Metadata Sync 元数据同步 API 测试
 * TDD: 验证元数据同步相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getMappingsV1,
  getMappingV1,
  createMappingV1,
  updateMappingV1,
  deleteMappingV1,
  triggerSyncV1,
  sendMetadataEventV1,
  createDolphinSchedulerMapping,
  createSeaTunnelMapping,
  createHopMapping,
  toggleMapping,
  // Legacy API
  getMappings,
  getMapping,
  createMapping,
  updateMapping,
  deleteMapping,
  triggerSync,
  sendMetadataEvent,
} from './metadata-sync';
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

import client from './client';
const mockClient = vi.mocked(client);

describe('Metadata Sync API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('getMappingsV1', () => {
      it('should return all mappings', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 'map-1',
              source_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
              target_task_type: 'dolphinscheduler',
              target_task_id: 'task-1',
              trigger_on: ['CREATE', 'UPDATE'],
              auto_update_config: true,
              enabled: true,
            },
            {
              id: 'map-2',
              source_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,orders,PROD)',
              target_task_type: 'seatunnel',
              target_task_id: 'task-2',
              trigger_on: ['SCHEMA_CHANGE'],
              auto_update_config: false,
              enabled: true,
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getMappingsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/metadata-sync/v1/mappings');
        expect(result.data).toHaveLength(2);
      });

      it('should handle empty mappings list', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        const result = await getMappingsV1();

        // Assert
        expect(result.data).toEqual([]);
      });
    });

    describe('getMappingV1', () => {
      it('should return single mapping by ID', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'map-1',
            source_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
            target_task_type: 'dolphinscheduler',
            target_task_id: 'task-1',
            trigger_on: ['CREATE', 'UPDATE'],
            auto_update_config: true,
            enabled: true,
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getMappingV1('map-1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/metadata-sync/v1/mappings/map-1');
        expect(result.data.id).toBe('map-1');
      });
    });

    describe('createMappingV1', () => {
      it('should create new mapping', async () => {
        // Arrange
        const newMapping = {
          source_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,products,PROD)',
          target_task_type: 'hop' as const,
          target_task_id: 'task-3',
          trigger_on: ['CREATE'] as const,
          auto_update_config: true,
        };
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'map-3',
            ...newMapping,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createMappingV1(newMapping);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/metadata-sync/v1/mappings', newMapping);
        expect(result.data.id).toBeDefined();
      });
    });

    describe('updateMappingV1', () => {
      it('should update existing mapping', async () => {
        // Arrange
        const updateData = {
          auto_update_config: false,
          enabled: false,
        };
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'map-1',
            source_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
            target_task_type: 'dolphinscheduler',
            target_task_id: 'task-1',
            trigger_on: ['CREATE', 'UPDATE'],
            auto_update_config: false,
            enabled: false,
          },
        };
        mockClient.put.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await updateMappingV1('map-1', updateData);

        // Assert
        expect(mockClient.put).toHaveBeenCalledWith('/api/proxy/metadata-sync/v1/mappings/map-1', updateData);
        expect(result.data.enabled).toBe(false);
      });
    });

    describe('deleteMappingV1', () => {
      it('should delete mapping', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { message: 'Mapping deleted' },
        };
        mockClient.delete.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await deleteMappingV1('map-1');

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/metadata-sync/v1/mappings/map-1');
        expect(result.data.message).toBe('Mapping deleted');
      });
    });

    describe('triggerSyncV1', () => {
      it('should trigger full sync', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            message: 'Sync completed',
            affected_tasks: ['task-1', 'task-2'],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await triggerSyncV1();

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/metadata-sync/v1/sync');
        expect(result.data.success).toBe(true);
      });
    });

    describe('sendMetadataEventV1', () => {
      it('should send metadata change event', async () => {
        // Arrange
        const event = {
          entity_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
          change_type: 'UPDATE' as const,
          changed_fields: ['email', 'phone'],
          new_schema: { columns: [] },
        };
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            message: 'Event processed',
            affected_tasks: ['task-1'],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await sendMetadataEventV1(event);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/metadata-sync/v1/webhook', event);
        expect(result.data.success).toBe(true);
      });
    });
  });

  // ============================================
  // 便捷函数测试
  // ============================================
  describe('convenience functions', () => {
    describe('createDolphinSchedulerMapping', () => {
      it('should create DolphinScheduler mapping with defaults', async () => {
        // Arrange
        const mockResponse = {
          id: 'map-ds-1',
          source_urn: 'urn:li:dataset:test',
          target_task_type: 'dolphinscheduler',
          target_task_id: 'ds-task-1',
          trigger_on: ['CREATE', 'UPDATE', 'SCHEMA_CHANGE'],
          auto_update_config: true,
          enabled: true,
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createDolphinSchedulerMapping('urn:li:dataset:test', 'ds-task-1');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/mappings', {
          source_urn: 'urn:li:dataset:test',
          target_task_type: 'dolphinscheduler',
          target_task_id: 'ds-task-1',
          trigger_on: ['CREATE', 'UPDATE', 'SCHEMA_CHANGE'],
          auto_update_config: true,
          enabled: true,
        });
      });

      it('should create DolphinScheduler mapping with custom trigger', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            id: 'map-ds-2',
            source_urn: 'urn:li:dataset:test',
            target_task_type: 'dolphinscheduler',
            target_task_id: 'ds-task-1',
            trigger_on: ['CREATE'],
            auto_update_config: true,
            enabled: true,
            description: 'Test mapping',
          },
        });

        // Act
        const result = await createDolphinSchedulerMapping(
          'urn:li:dataset:test',
          'ds-task-1',
          ['CREATE'],
          'Test mapping'
        );

        // Assert
        expect(result.description).toBe('Test mapping');
      });
    });

    describe('createSeaTunnelMapping', () => {
      it('should create SeaTunnel mapping', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            id: 'map-st-1',
            source_urn: 'urn:li:dataset:test',
            target_task_type: 'seatunnel',
            target_task_id: 'st-task-1',
            trigger_on: ['CREATE', 'UPDATE', 'SCHEMA_CHANGE'],
            auto_update_config: true,
            enabled: true,
          },
        });

        // Act
        const result = await createSeaTunnelMapping('urn:li:dataset:test', 'st-task-1');

        // Assert
        expect(mockClient.post).toHaveBeenCalled();
        expect(result.target_task_type).toBe('seatunnel');
      });
    });

    describe('createHopMapping', () => {
      it('should create Hop mapping', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            id: 'map-hop-1',
            source_urn: 'urn:li:dataset:test',
            target_task_type: 'hop',
            target_task_id: 'hop-task-1',
            trigger_on: ['CREATE', 'UPDATE', 'SCHEMA_CHANGE'],
            auto_update_config: true,
            enabled: true,
          },
        });

        // Act
        const result = await createHopMapping('urn:li:dataset:test', 'hop-task-1');

        // Assert
        expect(mockClient.post).toHaveBeenCalled();
        expect(result.target_task_type).toBe('hop');
      });
    });

    describe('toggleMapping', () => {
      it('should enable mapping', async () => {
        // Arrange
        mockClient.put.mockResolvedValue({
          data: {
            id: 'map-1',
            source_urn: 'urn:li:dataset:test',
            target_task_type: 'dolphinscheduler',
            target_task_id: 'task-1',
            trigger_on: ['CREATE'],
            auto_update_config: true,
            enabled: true,
          },
        });

        // Act
        const result = await toggleMapping('map-1', true);

        // Assert
        expect(mockClient.put).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/mappings/map-1', {
          enabled: true,
        });
        expect(result.enabled).toBe(true);
      });

      it('should disable mapping', async () => {
        // Arrange
        mockClient.put.mockResolvedValue({
          data: {
            id: 'map-1',
            enabled: false,
          },
        });

        // Act
        const result = await toggleMapping('map-1', false);

        // Assert
        expect(result.enabled).toBe(false);
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle special characters in mapping ID', async () => {
      // Arrange
      const mappingIdWithSpecialChars = 'map-2024_test@example';
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: mappingIdWithSpecialChars,
            source_urn: 'urn:li:dataset:test',
            target_task_type: 'dolphinscheduler',
            target_task_id: 'task-1',
            trigger_on: ['CREATE'],
            auto_update_config: true,
          },
        },
      });

      // Act
      const result = await getMappingV1(mappingIdWithSpecialChars);

      // Assert
      expect(result.data.id).toBe(mappingIdWithSpecialChars);
    });

    it('should handle empty change fields', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            message: 'Event processed',
            affected_tasks: [],
          },
        },
      });

      // Act
      const result = await sendMetadataEventV1({
        entity_urn: 'urn:li:dataset:test',
        change_type: 'UPDATE',
      });

      // Assert
      expect(result.data.affected_tasks).toEqual([]);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: metadata sync workflow', () => {
    it('should create mapping and trigger sync', async () => {
      // Step 1: Create mapping
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 'map-1',
            source_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
            target_task_type: 'dolphinscheduler',
            target_task_id: 'task-1',
            trigger_on: ['CREATE', 'UPDATE'],
            auto_update_config: true,
            enabled: true,
          },
        },
      });

      const mapping = await createMappingV1({
        source_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
        target_task_type: 'dolphinscheduler',
        target_task_id: 'task-1',
        trigger_on: ['CREATE', 'UPDATE'],
        auto_update_config: true,
      });
      expect(mapping.data.id).toBeDefined();

      // Step 2: Trigger sync
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            message: 'Sync completed',
            affected_tasks: ['task-1'],
          },
        },
      });

      const syncResult = await triggerSyncV1();
      expect(syncResult.data.success).toBe(true);
    });

    it('should send event and verify task triggered', async () => {
      // Send schema change event
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            message: 'Event processed',
            affected_tasks: ['task-1', 'task-2'],
          },
        },
      });

      const result = await sendMetadataEventV1({
        entity_urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,users,PROD)',
        change_type: 'SCHEMA_CHANGE',
        changed_fields: ['email'],
        new_schema: {
          columns: [
            { name: 'id', type: 'INTEGER' },
            { name: 'email', type: 'VARCHAR', length: 255 }, // Changed
          ],
        },
      });

      expect(result.data.affected_tasks).toHaveLength(2);
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('getMappings', () => {
      it('should return mappings list', async () => {
        // Arrange
        const mockResponse = [
          { id: 'map-1', source_urn: 'urn:li:dataset:test', target_task_type: 'dolphinscheduler' },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getMappings();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/mappings');
        expect(result).toHaveLength(1);
      });
    });

    describe('getMapping', () => {
      it('should return single mapping', async () => {
        // Arrange
        const mockResponse = {
          id: 'map-1',
          source_urn: 'urn:li:dataset:test',
          target_task_type: 'dolphinscheduler',
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getMapping('map-1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/mappings/map-1');
        expect(result.id).toBe('map-1');
      });
    });

    describe('createMapping', () => {
      it('should create mapping', async () => {
        // Arrange
        const newMapping = {
          source_urn: 'urn:li:dataset:test',
          target_task_type: 'hop' as const,
          target_task_id: 'task-1',
          trigger_on: ['CREATE'] as const,
          auto_update_config: true,
        };
        const mockResponse = { id: 'map-1', ...newMapping };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createMapping(newMapping);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/mappings', newMapping);
        expect(result.id).toBe('map-1');
      });
    });

    describe('updateMapping', () => {
      it('should update mapping', async () => {
        // Arrange
        const updateData = { enabled: false };
        const mockResponse = { id: 'map-1', enabled: false };
        mockClient.put.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await updateMapping('map-1', updateData);

        // Assert
        expect(mockClient.put).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/mappings/map-1', updateData);
        expect(result.enabled).toBe(false);
      });
    });

    describe('deleteMapping', () => {
      it('should delete mapping', async () => {
        // Arrange
        const mockResponse = { message: 'Mapping deleted' };
        mockClient.delete.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await deleteMapping('map-1');

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/mappings/map-1');
        expect(result.message).toBe('Mapping deleted');
      });
    });

    describe('triggerSync', () => {
      it('should trigger sync', async () => {
        // Arrange
        const mockResponse = {
          success: true,
          message: 'Sync completed',
          affected_tasks: ['task-1'],
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await triggerSync();

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/sync');
        expect(result.success).toBe(true);
      });
    });

    describe('sendMetadataEvent', () => {
      it('should send metadata event', async () => {
        // Arrange
        const event = {
          entity_urn: 'urn:li:dataset:test',
          change_type: 'UPDATE' as const,
        };
        const mockResponse = {
          success: true,
          message: 'Event processed',
          affected_tasks: [],
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await sendMetadataEvent(event);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/metadata/api/metadata/webhook', event);
        expect(result.success).toBe(true);
      });
    });
  });
});
