/**
 * 认证 API 测试
 * TDD: RED → GREEN → REFACTOR
 * 先写测试，验证认证相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  login,
  logout,
  refreshToken,
  validateToken,
  getUserInfo,
  revokeToken,
  getSubsystems,
  healthCheck,
  healthCheckAll,
  securityCheck,
} from './auth';
import { ErrorCode } from './types';
import { mockApiResponse } from '../test/utils';

// Mock axios client
vi.mock('./client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

import client from './client';

const mockClient = vi.mocked(client);

describe('auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // 登录测试
  // ============================================
  describe('login', () => {
    it('should return token and user info on successful login', async () => {
      // Arrange
      const mockResponse = {
        token: 'mock-jwt-token',
        user: {
          id: '1001',
          username: 'admin',
          displayName: '系统管理员',
        },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await login('admin', 'password123');

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/auth/login', {
        username: 'admin',
        password: 'password123',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should throw error on failed login', async () => {
      // Arrange
      mockClient.post.mockRejectedValue({
        response: { data: { code: 40100, message: '用户名或密码错误' } },
      });

      // Act & Assert
      await expect(login('admin', 'wrongpassword')).rejects.toThrow();
    });

    it('should handle network error', async () => {
      // Arrange
      mockClient.post.mockRejectedValue(new Error('Network error'));

      // Act & Assert
      await expect(login('admin', 'password')).rejects.toThrow('Network error');
    });
  });

  // ============================================
  // 登出测试
  // ============================================
  describe('logout', () => {
    it('should call logout endpoint', async () => {
      // Arrange
      mockClient.post.mockResolvedValue({ data: { success: true } });

      // Act
      await logout();

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/auth/logout');
    });

    it('should throw error on network failure', async () => {
      // Arrange
      mockClient.post.mockRejectedValue(new Error('Network error'));

      // Act & Assert
      await expect(logout()).rejects.toThrow('Network error');
    });
  });

  // ============================================
  // Token刷新测试
  // ============================================
  describe('refreshToken', () => {
    it('should return new token on successful refresh', async () => {
      // Arrange
      const mockResponse = {
        success: true,
        token: 'new-mock-token',
        message: 'Token refreshed',
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await refreshToken();

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/auth/refresh');
      expect(result.token).toBe('new-mock-token');
    });

    it('should return success false on invalid token', async () => {
      // Arrange
      const mockResponse = {
        success: false,
        message: 'Token invalid',
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await refreshToken();

      // Assert
      expect(result.success).toBe(false);
      expect(result.token).toBeUndefined();
    });
  });

  // ============================================
  // Token验证测试
  // ============================================
  describe('validateToken', () => {
    it('should return valid true for active token', async () => {
      // Arrange
      const mockResponse = {
        valid: true,
        user_id: '1001',
        username: 'admin',
        display_name: '系统管理员',
        roles: ['admin'],
        permissions: ['all'],
        expires_at: Date.now() + 3600000,
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await validateToken();

      // Assert
      expect(result.valid).toBe(true);
      expect(result.username).toBe('admin');
      expect(result.expires_at).toBeDefined();
    });

    it('should return valid false for expired token', async () => {
      // Arrange
      const mockResponse = {
        valid: false,
        code: 40101,
        message: 'Token expired',
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await validateToken();

      // Assert
      expect(result.valid).toBe(false);
    });

    it('should return valid false for invalid token', async () => {
      // Arrange
      const mockResponse = {
        valid: false,
        code: 40102,
        message: 'Token invalid',
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await validateToken();

      // Assert
      expect(result.valid).toBe(false);
    });
  });

  // ============================================
  // 用户信息测试
  // ============================================
  describe('getUserInfo', () => {
    it('should return user information', async () => {
      // Arrange
      const mockResponse = {
        user_id: '1001',
        username: 'admin',
        display_name: '系统管理员',
        role: 'admin',
        roles: ['admin', 'data_analyst'],
        permissions: ['read', 'write', 'delete'],
      };
      mockClient.get.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await getUserInfo();

      // Assert
      expect(mockClient.get).toHaveBeenCalledWith('/auth/userinfo');
      expect(result.username).toBe('admin');
      expect(result.roles).toContain('admin');
    });

    it('should throw error when not authenticated', async () => {
      // Arrange
      mockClient.get.mockRejectedValue({
        response: { status: 401, data: { message: 'Unauthorized' } },
      });

      // Act & Assert
      await expect(getUserInfo()).rejects.toThrow();
    });
  });

  // ============================================
  // Token撤销测试
  // ============================================
  describe('revokeToken', () => {
    it('should successfully revoke token', async () => {
      // Arrange
      const mockResponse = {
        success: true,
        message: 'Token revoked',
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await revokeToken();

      // Assert
      expect(mockClient.post).toHaveBeenCalledWith('/auth/revoke');
      expect(result.success).toBe(true);
    });

    it('should return false when token not found', async () => {
      // Arrange
      const mockResponse = {
        success: false,
        message: 'Token not found',
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await revokeToken();

      // Assert
      expect(result.success).toBe(false);
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty username', async () => {
      // Arrange
      mockClient.post.mockRejectedValue({
        response: { data: { code: 40002, message: '缺少必要参数' } },
      });

      // Act & Assert
      await expect(login('', 'password')).rejects.toThrow();
    });

    it('should handle empty password', async () => {
      // Arrange
      mockClient.post.mockRejectedValue({
        response: { data: { code: 40002, message: '缺少必要参数' } },
      });

      // Act & Assert
      await expect(login('admin', '')).rejects.toThrow();
    });

    it('should handle special characters in password', async () => {
      // Arrange
      const mockResponse = {
        token: 'mock-token',
        user: { id: '1', username: 'admin', displayName: 'Admin' },
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await login('admin', 'p@ssw0rd!"#$%');

      // Assert
      expect(result.token).toBe('mock-token');
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration scenarios', () => {
    it('should complete full login flow', async () => {
      // Step 1: Login
      const loginResponse = {
        token: 'mock-token',
        user: { id: '1', username: 'admin', displayName: 'Admin' },
      };
      mockClient.post.mockResolvedValue({ data: loginResponse });

      const loginResult = await login('admin', 'password');
      expect(loginResult.token).toBeDefined();

      // Step 2: Validate token
      const validateResponse = {
        valid: true,
        user_id: '1',
        username: 'admin',
      };
      mockClient.get.mockResolvedValue({ data: validateResponse });

      const validateResult = await validateToken();
      expect(validateResult.valid).toBe(true);

      // Step 3: Get user info
      const userInfoResponse = {
        user_id: '1',
        username: 'admin',
        display_name: 'Admin',
        roles: ['admin'],
      };
      mockClient.get.mockResolvedValue({ data: userInfoResponse });

      const userInfo = await getUserInfo();
      expect(userInfo.username).toBe('admin');
    });

    it('should handle refresh flow on expired token', async () => {
      // Token validation returns expired
      const expiredResponse = {
        valid: false,
        code: 40101,
        message: 'Token expired',
      };
      mockClient.get.mockResolvedValue({ data: expiredResponse });

      const validateResult = await validateToken();
      expect(validateResult.valid).toBe(false);

      // Refresh token
      const refreshResponse = {
        success: true,
        token: 'new-token',
        message: 'Refreshed',
      };
      mockClient.post.mockResolvedValue({ data: refreshResponse });

      const refreshResult = await refreshToken();
      expect(refreshResult.token).toBe('new-token');
    });
  });

  // ============================================
  // 系统状态 API 测试
  // ============================================
  describe('system status API', () => {
    describe('getSubsystems', () => {
      it('should return list of subsystems', async () => {
        // Arrange
        const mockResponse = [
          { id: 'planning', name: '数据规划', status: 'online' },
          { id: 'collection', name: '数据感知', status: 'online' },
          { id: 'development', name: '数据加工', status: 'online' },
        ];
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getSubsystems();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/subsystems');
        expect(result).toHaveLength(3);
        expect(result[0].name).toBe('数据规划');
      });

      it('should handle empty subsystems list', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({ data: [] });

        // Act
        const result = await getSubsystems();

        // Assert
        expect(result).toEqual([]);
      });
    });

    describe('healthCheck', () => {
      it('should return health status', async () => {
        // Arrange
        const mockResponse = {
          status: 'healthy',
          service: 'portal',
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await healthCheck();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/health');
        expect(result.status).toBe('healthy');
        expect(result.service).toBe('portal');
      });

      it('should return unhealthy status', async () => {
        // Arrange
        const mockResponse = {
          status: 'unhealthy',
          service: 'portal',
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await healthCheck();

        // Assert
        expect(result.status).toBe('unhealthy');
      });
    });

    describe('healthCheckAll', () => {
      it('should return aggregated health status for all services', async () => {
        // Arrange
        const mockResponse = {
          status: 'healthy',
          portal: 'online',
          unhealthy_count: 0,
          subsystems: [
            { name: 'planning', display_name: '数据规划', status: 'online' },
            { name: 'collection', display_name: '数据感知', status: 'online' },
          ],
          internal_services: [
            { name: 'metadata', display_name: '元数据服务', url: 'http://metadata:8013', status: 'healthy' },
            { name: 'nl2sql', display_name: '自然语言查询', url: 'http://nl2sql:8011', status: 'healthy' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await healthCheckAll();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/health/all');
        expect(result.status).toBe('healthy');
        expect(result.unhealthy_count).toBe(0);
        expect(result.subsystems).toHaveLength(2);
        expect(result.internal_services).toHaveLength(2);
      });

      it('should return degraded status when some services are unhealthy', async () => {
        // Arrange
        const mockResponse = {
          status: 'degraded',
          portal: 'online',
          unhealthy_count: 2,
          subsystems: [
            { name: 'planning', display_name: '数据规划', status: 'online' },
            { name: 'collection', display_name: '数据感知', status: 'offline' },
          ],
          internal_services: [
            { name: 'metadata', display_name: '元数据服务', url: 'http://metadata:8013', status: 'healthy' },
            {
              name: 'nl2sql',
              display_name: '自然语言查询',
              url: 'http://nl2sql:8011',
              status: 'unhealthy',
              error: 'Connection refused',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await healthCheckAll();

        // Assert
        expect(result.status).toBe('degraded');
        expect(result.unhealthy_count).toBe(2);
        expect(result.internal_services[1].error).toBe('Connection refused');
      });
    });

    describe('securityCheck', () => {
      it('should return security configuration and score', async () => {
        // Arrange
        const mockResponse = {
          security_level: 'high',
          security_message: 'Security configuration is good',
          score: 85,
          max_score: 100,
          is_production: false,
          environment: 'development',
          token_status: { jwt_enabled: true, https_required: false },
          warnings: ['HTTPS not enforced in development'],
          recommendations: ['Enable HTTPS for production'],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await securityCheck();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/security/check');
        expect(result.security_level).toBe('high');
        expect(result.score).toBe(85);
        expect(result.max_score).toBe(100);
        expect(result.is_production).toBe(false);
        expect(result.warnings).toHaveLength(1);
        expect(result.recommendations).toHaveLength(1);
      });

      it('should return production security status', async () => {
        // Arrange
        const mockResponse = {
          security_level: 'high',
          security_message: 'All security checks passed',
          score: 95,
          max_score: 100,
          is_production: true,
          environment: 'production',
          token_status: { jwt_enabled: true, https_required: true },
          warnings: [],
          recommendations: [],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await securityCheck();

        // Assert
        expect(result.is_production).toBe(true);
        expect(result.environment).toBe('production');
        expect(result.token_status.https_required).toBe(true);
        expect(result.warnings).toHaveLength(0);
      });

      it('should handle low security score', async () => {
        // Arrange
        const mockResponse = {
          security_level: 'low',
          security_message: 'Security configuration is weak',
          score: 30,
          max_score: 100,
          is_production: false,
          environment: 'development',
          token_status: { jwt_enabled: false, https_required: false },
          warnings: [
            'JWT authentication is disabled',
            'HTTPS is not enforced',
            'Default credentials in use',
          ],
          recommendations: [
            'Enable JWT authentication',
            'Enforce HTTPS',
            'Change default credentials',
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await securityCheck();

        // Assert
        expect(result.security_level).toBe('low');
        expect(result.score).toBe(30);
        expect(result.warnings).toHaveLength(3);
        expect(result.recommendations).toHaveLength(3);
      });
    });
  });
});
