/**
 * 审计日志 API 测试
 * TDD: 验证审计日志相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getLogs, getLog, getStats, exportLogs } from './audit';
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

describe('Audit API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // 查询审计日志测试
  // ============================================
  describe('getLogs', () => {
    it('should return audit logs list', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [
          {
            id: '1',
            user: 'admin',
            subsystem: 'portal',
            event_type: 'login',
            timestamp: '2024-02-01T10:00:00Z',
            details: { ip: '192.168.1.1' },
          },
          {
            id: '2',
            user: 'user1',
            subsystem: 'nl2sql',
            event_type: 'query',
            timestamp: '2024-02-01T10:05:00Z',
            details: { sql: 'SELECT * FROM users' },
          },
        ],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLogs();

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/audit/v1/logs', { params: {} });
      expect(result).toHaveLength(2);
      expect(result[0].user).toBe('admin');
      expect(result[0].event_type).toBe('login');
    });

    it('should filter logs by subsystem', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [
          {
            id: '1',
            user: 'admin',
            subsystem: 'portal',
            event_type: 'login',
            timestamp: '2024-02-01T10:00:00Z',
          },
        ],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLogs({ subsystem: 'portal' });

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/audit/v1/logs', {
        params: { subsystem: 'portal' },
      });
      expect(result).toHaveLength(1);
    });

    it('should filter logs by event type', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [
          {
            id: '2',
            user: 'user1',
            subsystem: 'nl2sql',
            event_type: 'query',
            timestamp: '2024-02-01T10:05:00Z',
          },
        ],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLogs({ event_type: 'query' });

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/audit/v1/logs', {
        params: { event_type: 'query' },
      });
    });

    it('should support pagination', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [
          {
            id: '1',
            user: 'admin',
            subsystem: 'portal',
            event_type: 'login',
            timestamp: '2024-02-01T10:00:00Z',
          },
        ],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLogs({ page: 2, page_size: 20 });

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/audit/v1/logs', {
        params: { page: 2, page_size: 20 },
      });
    });

    it('should return empty array when no logs found', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLogs();

      // Assert
      expect(result).toEqual([]);
    });
  });

  // ============================================
  // 获取单条日志测试
  // ============================================
  describe('getLog', () => {
    it('should return single log by ID', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          id: '123',
          user: 'admin',
          subsystem: 'portal',
          event_type: 'login',
          timestamp: '2024-02-01T10:00:00Z',
          details: { ip: '192.168.1.1', browser: 'Chrome' },
        },
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLog('123');

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/audit/v1/logs/123');
      expect(result.id).toBe('123');
      expect(result.user).toBe('admin');
      expect(result.details?.ip).toBe('192.168.1.1');
    });

    it('should handle 404 for non-existent log', async () => {
      // Arrange
      const mockResponse = {
        code: 404,
        message: 'Log not found',
        data: null,
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act & Assert
      await expect(getLog('non-existent')).rejects.toThrow();
    });
  });

  // ============================================
  // 审计统计测试
  // ============================================
  describe('getStats', () => {
    it('should return audit statistics', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          total_events: 1000,
          events_by_subsystem: {
            portal: 300,
            nl2sql: 250,
            sensitive: 200,
            metadata_sync: 150,
            data_api: 100,
          },
          events_by_type: {
            login: 50,
            query: 400,
            scan: 150,
            export: 100,
          },
          events_today: 50,
        },
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getStats();

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/audit/v1/stats');
      expect(result.total_events).toBe(1000);
      expect(result.events_by_subsystem?.portal).toBe(300);
      expect(result.events_by_type?.query).toBe(400);
    });

    it('should return zero stats when no events', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          total_events: 0,
          events_by_subsystem: {},
          events_by_type: {},
          events_today: 0,
        },
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getStats();

      // Assert
      expect(result.total_events).toBe(0);
    });
  });

  // ============================================
  // 导出审计日志测试
  // ============================================
  describe('exportLogs', () => {
    it('should export logs as CSV', async () => {
      // Arrange
      const mockBlob = new Blob(['csv,data'], { type: 'text/csv' });
      mockClient.post.mockResolvedValue({ data: mockBlob });

      // Act
      const result = await exportLogs('csv');

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/proxy/audit/v1/export',
        { format: 'csv', query: {} },
        { responseType: 'blob' }
      );
      expect(result).toBeInstanceOf(Blob);
    });

    it('should export logs as JSON', async () => {
      // Arrange
      const mockBlob = new Blob(['{"json":"data"}'], { type: 'application/json' });
      mockClient.post.mockResolvedValue({ data: mockBlob });

      // Act
      const result = await exportLogs('json');

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/proxy/audit/v1/export',
        { format: 'json', query: {} },
        { responseType: 'blob' }
      );
      expect(result).toBeInstanceOf(Blob);
    });

    it('should export logs with filters', async () => {
      // Arrange
      const mockBlob = new Blob(['csv,data'], { type: 'text/csv' });
      mockClient.post.mockResolvedValue({ data: mockBlob });

      // Act
      const result = await exportLogs('csv', { subsystem: 'portal', user: 'admin' });

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/proxy/audit/v1/export',
        {
          format: 'csv',
          query: { subsystem: 'portal', user: 'admin' },
        },
        { responseType: 'blob' }
      );
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle special characters in log ID', async () => {
      // Arrange
      const logIdWithSpecialChars = 'log-2024_test@example';
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: {
          id: logIdWithSpecialChars,
          user: 'admin',
          subsystem: 'portal',
          event_type: 'login',
          timestamp: '2024-02-01T10:00:00Z',
        },
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLog(logIdWithSpecialChars);

      // Assert
      expect(result.id).toBe(logIdWithSpecialChars);
    });

    it('should handle very large page size', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLogs({ page: 1, page_size: 10000 });

      // Assert
      expect(result).toEqual([]);
    });

    it('should handle negative page number', async () => {
      // Arrange
      const mockResponse = {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: [],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getLogs({ page: -1 });

      // Assert - API handles invalid input
      expect(result).toEqual([]);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: audit workflow', () => {
    it('should get stats and then query logs', async () => {
      // First get stats
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            total_events: 100,
            events_by_subsystem: { portal: 50, nl2sql: 50 },
            events_by_type: { login: 20, query: 80 },
            events_today: 10,
          },
        },
      });

      const stats = await getStats();
      expect(stats.total_events).toBe(100);

      // Then query logs
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: '1',
              user: 'admin',
              subsystem: 'portal',
              event_type: 'login',
              timestamp: '2024-02-01T10:00:00Z',
            },
          ],
        },
      });

      const logs = await getLogs({ subsystem: 'portal' });
      expect(logs).toHaveLength(1);
      expect(logs[0].subsystem).toBe('portal');
    });

    it('should query logs and then export', async () => {
      // Query logs first
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: '1',
              user: 'admin',
              subsystem: 'portal',
              event_type: 'login',
              timestamp: '2024-02-01T10:00:00Z',
            },
          ],
        },
      });

      const logs = await getLogs({ user: 'admin' });
      expect(logs).toHaveLength(1);

      // Export same query
      const mockBlob = new Blob(['csv,data'], { type: 'text/csv' });
      mockClient.post.mockResolvedValue({ data: mockBlob });

      const exportedData = await exportLogs('csv', { user: 'admin' });
      expect(exportedData).toBeInstanceOf(Blob);
    });
  });
});
