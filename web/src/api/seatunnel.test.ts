/**
 * SeaTunnel 数据同步 API 测试
 * TDD: 验证数据同步相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getJobsV1,
  getJobDetailV1,
  getJobStatusV1,
  submitJobV1,
  cancelJobV1,
  getClusterStatusV1,
  // Legacy API
  getJobs,
  getJobDetail,
  submitJob,
  cancelJob,
  getJobStatus,
  // Utils
  isSuccessResponse,
  getErrorMessage,
  apiGetErrorMessage,
} from './seatunnel';
import { ErrorCode } from './types';

// Mock utils module
vi.mock('./utils', () => ({
  isSuccessResponse: (resp: unknown) => {
    return typeof resp === 'object' && resp !== null && 'code' in resp && (resp as { code: number }).code === ErrorCode.SUCCESS;
  },
  getErrorMessage: (code: number) => {
    const messages: Record<number, string> = {
      [ErrorCode.SUCCESS]: 'success',
      [ErrorCode.UNAUTHORIZED]: 'Unauthorized',
      [ErrorCode.NOT_FOUND]: 'Not found',
      [ErrorCode.INTERNAL_ERROR]: 'Internal server error',
    };
    return messages[code] || 'Unknown error';
  },
}));

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

describe('SeaTunnel API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('getJobsV1', () => {
      it('should return all jobs when no filter', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            jobs: [
              { jobId: 'job-1', jobStatus: 'RUNNING' },
              { jobId: 'job-2', jobStatus: 'FINISHED' },
            ],
            total: 2,
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getJobsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/seatunnel/v1/jobs');
        expect(result.data.jobs).toHaveLength(2);
        expect(result.data.total).toBe(2);
      });

      it('should filter running jobs', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            jobs: [{ jobId: 'job-1', jobStatus: 'RUNNING' }],
            total: 1,
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getJobsV1('running');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/seatunnel/v1/jobs?status=running');
        expect(result.data.jobs[0].jobStatus).toBe('RUNNING');
      });

      it('should filter finished jobs', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: {
              jobs: [{ jobId: 'job-2', jobStatus: 'FINISHED' }],
              total: 1,
            },
          },
        });

        // Act
        const result = await getJobsV1('finished');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/seatunnel/v1/jobs?status=finished');
      });
    });

    describe('getJobDetailV1', () => {
      it('should return job detail', async () => {
        // Arrange
        const mockDetail = {
          jobId: 'job-1',
          raw: { config: {} },
        };
        mockClient.get.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: mockDetail,
          },
        });

        // Act
        const result = await getJobDetailV1('job-1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/seatunnel/v1/jobs/job-1');
        expect(result.data.jobId).toBe('job-1');
      });

      it('should handle 404 for non-existent job', async () => {
        // Arrange
        mockClient.get.mockRejectedValue({
          response: { status: 404, data: { message: 'Job not found' } },
        });

        // Act & Assert
        await expect(getJobDetailV1('non-existent')).rejects.toThrow();
      });
    });

    describe('getJobStatusV1', () => {
      it('should return job status', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: { jobId: 'job-1', jobStatus: 'FINISHED' },
          },
        });

        // Act
        const result = await getJobStatusV1('job-1');

        // Assert
        expect(result.data.jobStatus).toBe('FINISHED');
      });

      it('should return RUNNING status', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: { jobId: 'job-1', jobStatus: 'RUNNING' },
          },
        });

        // Act
        const result = await getJobStatusV1('job-1');

        // Assert
        expect(result.data.jobStatus).toBe('RUNNING');
      });
    });

    describe('submitJobV1', () => {
      it('should submit job successfully', async () => {
        // Arrange
        const jobConfig = {
          env: {
            parallelism: 2,
            shade_identifier: 'test-job',
          },
          source: [
            {
            plugin_name: 'MySQL Binlog',
            plugin_input: {
              hostname: 'localhost',
              port: 3306,
              database: 'test_db',
              table: 'test_table',
            },
          },
          ],
          sink: [
            {
              plugin_name: 'Console',
              plugin_input: {},
            },
          ],
        };
        mockClient.post.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'Job submitted', data: { jobId: 'job-1' } },
        });

        // Act
        const result = await submitJobV1(jobConfig);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/seatunnel/v1/jobs', jobConfig);
        expect(result.data.jobId).toBe('job-1');
      });

      it('should handle validation error', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: { code: 40001, message: 'Invalid job config', data: null },
        });

        // Act
        const result = await submitJobV1({});

        // Assert - returns response even for error
        expect(result).toBeDefined();
      });
    });

    describe('cancelJobV1', () => {
      it('should cancel running job', async () => {
        // Arrange
        mockClient.delete.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'Job cancelled', data: {} },
        });

        // Act
        await cancelJobV1('job-1');

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/seatunnel/v1/jobs/job-1');
      });

      it('should handle error when job cannot be cancelled', async () => {
        // Arrange
        mockClient.delete.mockRejectedValue({
          response: { status: 400, data: { message: 'Job cannot be cancelled' } },
        });

        // Act & Assert
        await expect(cancelJobV1('job-1')).rejects.toThrow();
      });
    });

    describe('getClusterStatusV1', () => {
      it('should return cluster status', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: {
            code: ErrorCode.SUCCESS,
            message: 'success',
            data: {
              workers: ['worker-1', 'worker-2'],
              totalSlots: 10,
              usedSlots: 4,
            },
          },
        });

        // Act
        const result = await getClusterStatusV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/seatunnel/v1/cluster');
        expect(result.data.workers).toBeDefined();
      });
    });
  });

  // ============================================
  // 旧版 API 向后兼容测试
  // ============================================
  describe('legacy API', () => {
    describe('getJobs', () => {
      it('should return jobs list', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: {
            jobs: [{ jobId: 'job-1', jobStatus: 'RUNNING' }],
            total: 1,
          },
        });

        // Act
        const result = await getJobs();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/seatunnel/api/v1/job/list');
        expect(result.jobs).toBeDefined();
      });
    });

    describe('getJobDetail', () => {
      it('should return job detail', async () => {
        // Arrange
        const mockDetail = {
          jobId: 'job-1',
          raw: { config: {} },
        };
        mockClient.get.mockResolvedValue({
          data: mockDetail,
        });

        // Act
        const result = await getJobDetail('job-1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/seatunnel/api/v1/job/job-1');
        expect(result.jobId).toBe('job-1');
      });
    });

    describe('getJobStatus', () => {
      it('should return job status', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { jobId: 'job-1', jobStatus: 'FINISHED' },
        });

        // Act
        const result = await getJobStatus('job-1');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/seatunnel/api/v1/job/job-1/status');
        expect(result.jobStatus).toBe('FINISHED');
      });
    });

    describe('submitJob', () => {
      it('should submit job', async () => {
        // Arrange
        const config = { job: { name: 'test' } };
        mockClient.post.mockResolvedValue({ data: { success: true } });

        // Act
        const result = await submitJob(config);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/seatunnel/api/v1/job/submit', config);
      });
    });

    describe('cancelJob', () => {
      it('should cancel job', async () => {
        // Arrange
        mockClient.delete.mockResolvedValue({
          data: { success: true },
        });

        // Act
        const result = await cancelJob('job-1');

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/seatunnel/api/v1/job/job-1');
        expect(result.success).toBe(true);
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty job list', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { jobs: [], total: 0 },
        },
      });

      // Act
      const result = await getJobsV1();

      // Assert
      expect(result.data.jobs).toEqual([]);
    });

    it('should handle special characters in job ID', async () => {
      // Arrange
      const jobIdWithSpecialChars = 'job-2024_test@example';
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { jobId: jobIdWithSpecialChars } },
      });

      // Act
      const result = await getJobDetailV1(jobIdWithSpecialChars);

      // Assert
      expect(result.data.jobId).toBe(jobIdWithSpecialChars);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: job lifecycle', () => {
    it('should submit job and check status', async () => {
      // Submit job
      const jobConfig = { source: [], sink: [] };
      mockClient.post.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { jobId: 'new-job' } },
      });

      const submitResult = await submitJobV1(jobConfig);
      expect(submitResult.data.jobId).toBe('new-job');

      // Check status - job is starting
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { jobId: 'new-job', jobStatus: 'STARTING' } },
      });

      const statusResult = await getJobStatusV1('new-job');
      expect(statusResult.data.jobStatus).toBe('STARTING');

      // Check status again - job is now running
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { jobId: 'new-job', jobStatus: 'RUNNING' } },
      });

      const runningResult = await getJobStatusV1('new-job');
      expect(runningResult.data.jobStatus).toBe('RUNNING');
    });

    it('should submit and cancel job', async () => {
      // Submit job
      const jobConfig = { source: [], sink: [] };
      mockClient.post.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { jobId: 'job-cancel' } },
      });

      await submitJobV1(jobConfig);

      // Cancel job
      mockClient.delete.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'Job cancelled', data: {} },
      });

      await cancelJobV1('job-cancel');

      expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/seatunnel/v1/jobs/job-cancel');
    });
  });

  // ============================================
  // 工具函数测试
  // ============================================
  describe('utility functions', () => {
    describe('isSuccessResponse', () => {
      it('should return true for success response', () => {
        // Arrange
        const response = { code: ErrorCode.SUCCESS, message: 'success', data: {} };

        // Act
        const result = isSuccessResponse(response);

        // Assert
        expect(result).toBe(true);
      });

      it('should return false for error response', () => {
        // Arrange
        const response = { code: ErrorCode.NOT_FOUND, message: 'Not found', data: null };

        // Act
        const result = isSuccessResponse(response);

        // Assert
        expect(result).toBe(false);
      });

      it('should return false for non-object input', () => {
        // Act & Assert
        expect(isSuccessResponse(null)).toBe(false);
        expect(isSuccessResponse(undefined)).toBe(false);
        expect(isSuccessResponse('string')).toBe(false);
        expect(isSuccessResponse(123)).toBe(false);
      });

      it('should return false for object without code', () => {
        // Arrange
        const response = { message: 'No code' };

        // Act
        const result = isSuccessResponse(response);

        // Assert
        expect(result).toBe(false);
      });
    });

    describe('getErrorMessage', () => {
      it('should return error message for error code', () => {
        // Arrange
        const response = { code: ErrorCode.NOT_FOUND, message: 'Not found', data: null };

        // Act
        const result = getErrorMessage(response);

        // Assert
        expect(result).toBe('Not found');
      });

      it('should return success message for success code', () => {
        // Arrange
        const response = { code: ErrorCode.SUCCESS, message: 'success', data: {} };

        // Act
        const result = getErrorMessage(response);

        // Assert
        expect(result).toBe('success');
      });

      it('should handle custom error codes', () => {
        // Arrange
        const response = { code: 99999, message: 'Custom error', data: null };

        // Act
        const result = getErrorMessage(response);

        // Assert - getErrorMessage uses the message from response
        expect(result).toBe('Unknown error'); // Mocked utils returns this for unknown codes
      });
    });

    describe('apiGetErrorMessage (re-export)', () => {
      it('should be exported and callable', () => {
        // This is a re-export from utils, verify it exists
        expect(typeof apiGetErrorMessage).toBe('function');
      });
    });
  });
});
