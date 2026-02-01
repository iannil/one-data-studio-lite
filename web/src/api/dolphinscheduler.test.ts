/**
 * DolphinScheduler 任务调度 API 测试
 * TDD: 验证任务调度相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getProjectsV1,
  getProcessDefinitionsV1,
  getSchedulesV1,
  updateScheduleStateV1,
  getTaskInstancesV1,
  getTaskLogV1,
  getProjects,
  getProcessDefinitions,
  getSchedules,
  updateScheduleState,
  getTaskInstances,
  getTaskLog,
} from './dolphinscheduler';
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

describe('DolphinScheduler API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('getProjectsV1', () => {
      it('should return projects list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            { code: 1, name: 'ETL Project', description: 'Data ETL workflows' },
            { code: 2, name: 'ML Project', description: 'Machine Learning pipelines' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getProjectsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/v1/projects', {
          params: { pageNo: 1, pageSize: 100 },
        });
        expect(result.data).toHaveLength(2);
      });
    });

    describe('getProcessDefinitionsV1', () => {
      it('should return process definitions', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              code: 101,
              name: 'Daily ETL',
              description: 'Daily data extraction',
              releaseState: 'ONLINE',
            },
            {
              code: 102,
              name: 'Hourly Sync',
              description: 'Hourly data sync',
              releaseState: 'OFFLINE',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getProcessDefinitionsV1('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/v1/projects/1/process-definition', {
          params: undefined,
        });
        expect(result.data).toHaveLength(2);
      });

      it('should support pagination', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await getProcessDefinitionsV1('1', { pageNo: 2, pageSize: 20 });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/v1/projects/1/process-definition', {
          params: { pageNo: 2, pageSize: 20 },
        });
      });
    });

    describe('getSchedulesV1', () => {
      it('should return schedules', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 1,
              processDefinitionCode: 101,
              releaseState: 'ONLINE',
              crontab: '0 0 2 * * ?',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getSchedulesV1('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/v1/projects/1/schedules', {
          params: undefined,
        });
        expect(result.data).toHaveLength(1);
      });

      it('should filter by process definition code', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await getSchedulesV1('1', '101');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/v1/projects/1/schedules', {
          params: { processDefinitionCode: '101' },
        });
      });
    });

    describe('updateScheduleStateV1', () => {
      it('should set schedule online', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { success: true },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await updateScheduleStateV1('1', 1, 'ONLINE');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/ds/v1/projects/1/schedules/1/online',
          null,
          { params: { releaseState: 'ONLINE' } }
        );
        expect(result.data.success).toBe(true);
      });

      it('should set schedule offline', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { success: true },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await updateScheduleStateV1('1', 1, 'OFFLINE');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/ds/v1/projects/1/schedules/1/online',
          null,
          { params: { releaseState: 'OFFLINE' } }
        );
      });
    });

    describe('getTaskInstancesV1', () => {
      it('should return task instances', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 1,
              name: 'Extract Data',
              state: 'SUCCESS',
              startTime: '2024-02-01T02:00:00Z',
              endTime: '2024-02-01T02:15:00Z',
            },
            {
              id: 2,
              name: 'Transform Data',
              state: 'RUNNING',
              startTime: '2024-02-01T02:15:00Z',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getTaskInstancesV1('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/v1/projects/1/task-instances', {
          params: undefined,
        });
        expect(result.data).toHaveLength(2);
      });

      it('should filter by state type', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await getTaskInstancesV1('1', { stateType: 'success' });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/v1/projects/1/task-instances', {
          params: { stateType: 'success' },
        });
      });
    });

    describe('getTaskLogV1', () => {
      it('should return task log', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            log: '[INFO] Starting task...\n[INFO] Task completed successfully',
            taskInstanceId: 1,
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getTaskLogV1('1', 1);

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith(
          '/api/proxy/ds/v1/projects/1/task-instances/1/log'
        );
        expect(result.data.log).toContain('Starting task');
      });
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('getProjects', () => {
      it('should return projects list', async () => {
        // Arrange
        const mockResponse = {
          result: [
            { code: 1, name: 'Project 1' },
            { code: 2, name: 'Project 2' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getProjects();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/projects', {
          params: { pageNo: 1, pageSize: 100 },
        });
        expect(result.result).toHaveLength(2);
      });
    });

    describe('getProcessDefinitions', () => {
      it('should return process definitions', async () => {
        // Arrange
        const mockResponse = {
          result: [{ code: 101, name: 'Process 1' }],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getProcessDefinitions('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/projects/1/process-definition', {
          params: undefined,
        });
      });
    });

    describe('getSchedules', () => {
      it('should return schedules', async () => {
        // Arrange
        const mockResponse = {
          result: [{ id: 1, processDefinitionCode: 101, releaseState: 'ONLINE' }],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getSchedules('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/projects/1/schedules', {
          params: undefined,
        });
      });
    });

    describe('updateScheduleState', () => {
      it('should update schedule state', async () => {
        // Arrange
        const mockResponse = {
          success: true,
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await updateScheduleState('1', 1, 'ONLINE');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/ds/projects/1/schedules/1/online', null, {
          params: { releaseState: 'ONLINE' },
        });
      });
    });

    describe('getTaskInstances', () => {
      it('should return task instances', async () => {
        // Arrange
        const mockResponse = {
          result: [{ id: 1, name: 'Task 1', state: 'SUCCESS' }],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getTaskInstances('1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/projects/1/task-instances', {
          params: undefined,
        });
      });
    });

    describe('getTaskLog', () => {
      it('should return task log', async () => {
        // Arrange
        const mockResponse = {
          log: 'Task log content',
          taskInstanceId: 1,
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getTaskLog('1', 1);

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/ds/projects/1/task-instances/1/log');
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty projects list', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getProjectsV1();

      // Assert
      expect(result.data).toEqual([]);
    });

    it('should handle special characters in project code', async () => {
      // Arrange
      const projectCodeWithSpecialChars = 'project-2024_test@example';
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getProcessDefinitionsV1(projectCodeWithSpecialChars);

      // Assert
      expect(result.data).toEqual([]);
    });

    it('should handle very large page size', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getProcessDefinitionsV1('1', { pageNo: 1, pageSize: 10000 });

      // Assert
      expect(result.data).toEqual([]);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: scheduling workflow', () => {
    it('should get project, process definitions, and schedules', async () => {
      // Step 1: Get projects
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [{ code: 1, name: 'ETL Project' }],
        },
      });

      const projects = await getProjectsV1();
      expect(projects.data).toHaveLength(1);
      const projectCode = projects.data[0].code.toString();

      // Step 2: Get process definitions
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [{ code: 101, name: 'Daily ETL', releaseState: 'ONLINE' }],
        },
      });

      const processes = await getProcessDefinitionsV1(projectCode);
      expect(processes.data).toHaveLength(1);

      // Step 3: Get schedules
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [{ id: 1, processDefinitionCode: 101, releaseState: 'ONLINE', crontab: '0 0 2 * * ?' }],
        },
      });

      const schedules = await getSchedulesV1(projectCode);
      expect(schedules.data).toHaveLength(1);
    });
  });
});
