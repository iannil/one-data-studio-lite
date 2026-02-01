/**
 * NL2SQL API 测试
 * TDD: 验证自然语言转SQL API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { queryV1, explainV1, getTablesV1, query, explain, getTables } from './nl2sql';
import { ErrorCode } from './types';

// Mock axios client
vi.mock('./client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

import client from './client';
const mockClient = vi.mocked(client);

describe('NL2SQL API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('queryV1', () => {
      it('should return SQL and results for valid query', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            sql: 'SELECT * FROM users WHERE city = "Beijing"',
            explanation: 'Query users in Beijing',
            confidence: 0.95,
            tables: ['users'],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await queryV1({ query: '今天的销售额是多少？' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/nl2sql/v1/query', {
          query: '今天的销售额是多少？',
        });
        expect(result.data.sql).toContain('SELECT');
        expect(result.data.explanation).toBeDefined();
      });

      it('should handle query with database parameter', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            sql: 'SELECT COUNT(*) FROM orders',
            explanation: 'Count orders',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await queryV1({ query: '订单数量', database: 'production' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/nl2sql/v1/query', {
          query: '订单数量',
          database: 'production',
        });
        expect(result.data.sql).toBeDefined();
      });

      it('should handle query with context', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            sql: 'SELECT SUM(amount) FROM sales WHERE date = TODAY',
            explanation: 'Sum of sales for today',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await queryV1({
          query: '销售额',
          context: 'financial domain, daily aggregation',
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/nl2sql/v1/query', {
          query: '销售额',
          context: 'financial domain, daily aggregation',
        });
      });

      it('should handle empty query', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: { code: 40002, message: '查询内容不能为空', data: null },
        });

        // Act
        const result = await queryV1({ query: '' });

        // Assert - returns response even for validation error
        expect(result).toBeDefined();
      });
    });

    describe('explainV1', () => {
      it('should return explanation for SQL', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            sql: 'SELECT * FROM users WHERE age > 18',
            explanation: 'Selects all users who are adults',
            steps: ['Filter users by age', 'Return all columns'],
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await explainV1({ sql: 'SELECT * FROM users WHERE age > 18' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/nl2sql/v1/explain', {
          sql: 'SELECT * FROM users WHERE age > 18',
        });
        expect(result.data.explanation).toBe('Selects all users who are adults');
        expect(result.data.steps).toHaveLength(2);
      });

      it('should handle SQL with database parameter', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            sql: 'SELECT COUNT(*) FROM orders',
            explanation: 'Count all orders',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await explainV1({ sql: 'SELECT COUNT(*) FROM orders', database: 'analytics' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/nl2sql/v1/explain', {
          sql: 'SELECT COUNT(*) FROM orders',
          database: 'analytics',
        });
      });
    });

    describe('getTablesV1', () => {
      it('should return list of tables', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              name: 'users',
              schema: 'public',
              database: 'production',
              columns: [
                { name: 'id', type: 'INTEGER', description: 'Primary key' },
                { name: 'name', type: 'VARCHAR', description: 'User name' },
              ],
            },
            {
              name: 'orders',
              schema: 'public',
              database: 'production',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getTablesV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/nl2sql/v1/tables');
        expect(result.data).toHaveLength(2);
        expect(result.data[0].name).toBe('users');
        expect(result.data[0].columns).toHaveLength(2);
      });

      it('should handle empty table list', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        const result = await getTablesV1();

        // Assert
        expect(result.data).toEqual([]);
      });
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('query', () => {
      it('should return SQL result for query', async () => {
        // Arrange
        const mockResponse = {
          sql: 'SELECT * FROM users WHERE city = "Beijing"',
          result: [{ id: 1, name: 'Alice', city: 'Beijing' }],
          execution_time_ms: 150,
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await query({ query: '北京的用户' });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/nl2sql/api/nl2sql/query', {
          query: '北京的用户',
        });
        expect(result.sql).toContain('SELECT');
        expect(result.result).toHaveLength(1);
      });
    });

    describe('explain', () => {
      it('should return explanation for SQL', async () => {
        // Arrange
        const mockResponse = {
          sql: 'SELECT COUNT(*) FROM orders',
          explanation: 'Counts the total number of orders',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await explain('SELECT COUNT(*) FROM orders');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/nl2sql/api/nl2sql/explain', {
          sql: 'SELECT COUNT(*) FROM orders',
          database: undefined,
        });
        expect(result.explanation).toContain('orders');
      });

      it('should handle explain with database', async () => {
        // Arrange
        const mockResponse = {
          sql: 'SELECT * FROM products',
          explanation: 'Select all products',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await explain('SELECT * FROM products', 'inventory');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/nl2sql/api/nl2sql/explain', {
          sql: 'SELECT * FROM products',
          database: 'inventory',
        });
      });
    });

    describe('getTables', () => {
      it('should return table list', async () => {
        // Arrange
        const mockResponse = [
          { tableName: 'users', description: 'User table' },
          { tableName: 'orders', description: 'Order table' },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getTables();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/nl2sql/api/nl2sql/tables');
        expect(result).toHaveLength(2);
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle SQL injection attempt', async () => {
      // Arrange
      const maliciousQuery = "'; DROP TABLE users; --";
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { sql: '', explanation: '', warning: '检测到潜在的SQL注入' },
        },
      });

      // Act
      const result = await queryV1({ query: maliciousQuery });

      // Assert
      expect(result.data.warning).toBeDefined();
    });

    it('should handle special characters in query', async () => {
      // Arrange
      const queryWithSpecialChars = '查询包含"引号"和\'撇号\'的数据';
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { sql: 'SELECT * FROM test', explanation: 'test' },
        },
      });

      // Act
      const result = await queryV1({ query: queryWithSpecialChars });

      // Assert
      expect(result.data.sql).toBeDefined();
    });

    it('should handle multi-line query', async () => {
      // Arrange
      const multiLineQuery = `统计
      按
      分组
      的用户数`;
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { sql: 'SELECT * FROM users', explanation: 'test' },
        },
      });

      // Act
      const result = await queryV1({ query: multiLineQuery });

      // Assert
      expect(result.data.sql).toBeDefined();
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: query workflow', () => {
    it('should get tables and then query', async () => {
      // First get tables
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [{ name: 'users', columns: [{ name: 'id', type: 'INTEGER' }] }],
        },
      });

      const tables = await getTablesV1();
      expect(tables.data).toHaveLength(1);
      expect(tables.data[0].name).toBe('users');

      // Then query using table info
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { sql: 'SELECT COUNT(*) FROM users', explanation: 'Count users' },
        },
      });

      const queryResult = await queryV1({ query: '用户数量' });
      expect(queryResult.data.sql).toContain('users');
    });

    it('should explain SQL after querying', async () => {
      // Execute query
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { sql: 'SELECT COUNT(*) FROM orders', explanation: 'Count orders' },
        },
      });

      const queryResult = await queryV1({ query: '订单数量' });
      expect(queryResult.data.sql).toBeDefined();

      // Explain the generated SQL
      mockClient.post.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            sql: 'SELECT COUNT(*) FROM orders',
            explanation: 'This query counts the total number of records in the orders table',
            steps: ['Scan orders table', 'Count records'],
          },
        },
      });

      const explainResult = await explainV1({ sql: queryResult.data.sql });
      expect(explainResult.data.explanation).toContain('orders');
      expect(explainResult.data.steps).toBeDefined();
    });
  });
});
