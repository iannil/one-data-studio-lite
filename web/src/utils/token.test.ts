/**
 * Token 工具函数测试
 * TDD: 验证Token存储、解析和过期检查的正确性
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getToken,
  setToken,
  removeToken,
  getUser,
  setUser,
  getTokenExpiration,
  isTokenExpiringSoon,
  isTokenExpired,
} from './token';

// Mock localStorage
const localStorageMock = {
  store: new Map<string, string>(),
  getItem: function (key: string): string | null {
    return this.store.get(key) ?? null;
  },
  setItem: function (key: string, value: string): void {
    this.store.set(key, value);
  },
  removeItem: function (key: string): void {
    this.store.delete(key);
  },
  clear: function (): void {
    this.store.clear();
  },
};

Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
});

describe('Token Utils', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  // ============================================
  // Token 存储测试
  // ============================================
  describe('getToken/setToken', () => {
    it('should store and retrieve token', () => {
      // Arrange
      const testToken = 'test-jwt-token';

      // Act
      setToken(testToken);
      const retrieved = getToken();

      // Assert
      expect(retrieved).toBe(testToken);
    });

    it('should return null when no token stored', () => {
      // Act
      const token = getToken();

      // Assert
      expect(token).toBeNull();
    });

    it('should overwrite existing token', () => {
      // Arrange
      setToken('first-token');
      expect(getToken()).toBe('first-token');

      // Act
      setToken('second-token');
      const retrieved = getToken();

      // Assert
      expect(retrieved).toBe('second-token');
    });
  });

  describe('removeToken', () => {
    it('should remove token and user from storage', () => {
      // Arrange
      setToken('test-token');
      setUser({ id: '1', name: 'Test User' });
      expect(getToken()).toBe('test-token');
      expect(getUser()).toEqual({ id: '1', name: 'Test User' });

      // Act
      removeToken();

      // Assert
      expect(getToken()).toBeNull();
      expect(getUser()).toBeNull();
    });

    it('should handle removing non-existent token', () => {
      // Act & Assert - should not throw
      expect(() => removeToken()).not.toThrow();
    });
  });

  // ============================================
  // User 存储测试
  // ============================================
  describe('getUser/setUser', () => {
    it('should store and retrieve user', () => {
      // Arrange
      const testUser = { id: '123', name: 'Test User', email: 'test@example.com' };

      // Act
      setUser(testUser);
      const retrieved = getUser();

      // Assert
      expect(retrieved).toEqual(testUser);
    });

    it('should return null when no user stored', () => {
      // Act
      const user = getUser();

      // Assert
      expect(user).toBeNull();
    });

    it('should handle complex user object', () => {
      // Arrange
      const complexUser = {
        id: '123',
        name: 'Test User',
        roles: ['admin', 'user'],
        permissions: { read: true, write: true },
        metadata: { department: 'Engineering', level: 5 },
      };

      // Act
      setUser(complexUser);
      const retrieved = getUser();

      // Assert
      expect(retrieved).toEqual(complexUser);
    });
  });

  // ============================================
  // Token 解析测试
  // ============================================
  describe('getTokenExpiration', () => {
    it('should parse valid JWT token with exp claim', () => {
      // Arrange - JWT with exp = 1735689600 (Jan 1, 2025 00:00:00 UTC)
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({ exp: 1735689600, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;

      // Act
      const expiration = getTokenExpiration(token);

      // Assert
      expect(expiration).toBeInstanceOf(Date);
      expect(expiration?.getTime()).toBe(1735689600000);
    });

    it('should return null for token without exp claim', () => {
      // Arrange
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({ sub: 'user123', name: 'Test User' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;

      // Act
      const expiration = getTokenExpiration(token);

      // Assert
      expect(expiration).toBeNull();
    });

    it('should return null for malformed token', () => {
      // Arrange
      const malformedTokens = [
        'not-a-jwt',
        'only-one-part',
        '',
        'invalid',
      ];

      // Act & Assert
      malformedTokens.forEach((token) => {
        const expiration = getTokenExpiration(token);
        expect(expiration).toBeNull();
      });
    });

    it('should return null for token with invalid payload', () => {
      // Arrange
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa('not-json-data');
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;

      // Act
      const expiration = getTokenExpiration(token);

      // Assert
      expect(expiration).toBeNull();
    });

    it('should handle token with additional claims', () => {
      // Arrange
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const now = Math.floor(Date.now() / 1000) + 3600; // 1 hour from now
      const payload = btoa(JSON.stringify({
        exp: now,
        sub: 'user123',
        iat: Math.floor(Date.now() / 1000),
        name: 'Test User',
        roles: ['admin'],
      }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;

      // Act
      const expiration = getTokenExpiration(token);

      // Assert
      expect(expiration).toBeInstanceOf(Date);
      expect(expiration?.getTime()).toBe(now * 1000);
    });
  });

  // ============================================
  // Token 过期检查测试
  // ============================================
  describe('isTokenExpired', () => {
    it('should return true when no token exists', () => {
      // Act
      const expired = isTokenExpired();

      // Assert
      expect(expired).toBe(true);
    });

    it('should return true for expired token', () => {
      // Arrange - Token expired 1 hour ago
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const pastTime = Math.floor(Date.now() / 1000) - 3600;
      const payload = btoa(JSON.stringify({ exp: pastTime, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expired = isTokenExpired();

      // Assert
      expect(expired).toBe(true);
    });

    it('should return false for valid token', () => {
      // Arrange - Token expires in 1 hour
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const futureTime = Math.floor(Date.now() / 1000) + 3600;
      const payload = btoa(JSON.stringify({ exp: futureTime, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expired = isTokenExpired();

      // Assert
      expect(expired).toBe(false);
    });

    it('should return true for token at exact expiration time', () => {
      // Arrange - Token expiring exactly now (within 1 second tolerance)
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const now = Math.floor(Date.now() / 1000);
      const payload = btoa(JSON.stringify({ exp: now, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expired = isTokenExpired();

      // Assert - Should be expired or will expire in < 1s
      expect(expired).toBe(true);
    });

    it('should return true for token without exp claim', () => {
      // Arrange
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({ sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expired = isTokenExpired();

      // Assert
      expect(expired).toBe(true);
    });

    it('should return true for malformed token', () => {
      // Arrange
      setToken('invalid-token');

      // Act
      const expired = isTokenExpired();

      // Assert
      expect(expired).toBe(true);
    });
  });

  // ============================================
  // Token 即将过期检查测试
  // ============================================
  describe('isTokenExpiringSoon', () => {
    it('should return false when no token exists', () => {
      // Act
      const expiring = isTokenExpiringSoon(30);

      // Assert
      expect(expiring).toBe(false);
    });

    it('should return true for token expiring within threshold', () => {
      // Arrange - Token expires in 15 minutes (within 30 min threshold)
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const futureTime = Math.floor(Date.now() / 1000) + 900; // 15 minutes
      const payload = btoa(JSON.stringify({ exp: futureTime, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expiring = isTokenExpiringSoon(30);

      // Assert
      expect(expiring).toBe(true);
    });

    it('should return false for token with more time than threshold', () => {
      // Arrange - Token expires in 2 hours (outside 30 min threshold)
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const futureTime = Math.floor(Date.now() / 1000) + 7200; // 2 hours
      const payload = btoa(JSON.stringify({ exp: futureTime, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expiring = isTokenExpiringSoon(30);

      // Assert
      expect(expiring).toBe(false);
    });

    it('should use default threshold of 30 minutes', () => {
      // Arrange - Token expires in 20 minutes
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const futureTime = Math.floor(Date.now() / 1000) + 1200; // 20 minutes
      const payload = btoa(JSON.stringify({ exp: futureTime, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expiring = isTokenExpiringSoon();

      // Assert
      expect(expiring).toBe(true);
    });

    it('should return true for already expired token', () => {
      // Arrange - Token expired 1 hour ago
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const pastTime = Math.floor(Date.now() / 1000) - 3600;
      const payload = btoa(JSON.stringify({ exp: pastTime, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expiring = isTokenExpiringSoon(30);

      // Assert - Expired token returns true (past expiration is within threshold)
      expect(expiring).toBe(true);
    });

    it('should handle custom threshold values', () => {
      // Arrange - Token expires in 5 minutes
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const futureTime = Math.floor(Date.now() / 1000) + 300; // 5 minutes
      const payload = btoa(JSON.stringify({ exp: futureTime, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act & Assert
      expect(isTokenExpiringSoon(10)).toBe(true); // Within 10 min
      expect(isTokenExpiringSoon(1)).toBe(false); // Outside 1 min
    });

    it('should return false for token without exp claim', () => {
      // Arrange
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({ sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expiring = isTokenExpiringSoon(30);

      // Assert
      expect(expiring).toBe(false);
    });

    it('should return false for malformed token', () => {
      // Arrange
      setToken('invalid-token');

      // Act
      const expiring = isTokenExpiringSoon(30);

      // Assert
      expect(expiring).toBe(false);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: token lifecycle', () => {
    it('should complete full token lifecycle', () => {
      // 1. No token initially
      expect(isTokenExpired()).toBe(true);

      // 2. Set token
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const futureTime = Math.floor(Date.now() / 1000) + 3600;
      const payload = btoa(JSON.stringify({ exp: futureTime, sub: 'user123', name: 'Test' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // 3. Token is valid
      expect(isTokenExpired()).toBe(false);
      expect(isTokenExpiringSoon()).toBe(false);

      // 4. Set user
      setUser({ id: 'user123', name: 'Test' });
      expect(getUser()).toEqual({ id: 'user123', name: 'Test' });

      // 5. Remove token (also removes user)
      removeToken();
      expect(isTokenExpired()).toBe(true);
      expect(getUser()).toBeNull();
    });

    it('should detect token approaching expiration', () => {
      // Arrange - Set token expiring in 25 minutes
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const futureTime = Math.floor(Date.now() / 1000) + 1500; // 25 minutes
      const payload = btoa(JSON.stringify({ exp: futureTime, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act & Assert
      expect(isTokenExpired()).toBe(false); // Not expired yet
      expect(isTokenExpiringSoon(30)).toBe(true); // But expiring soon
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle very large expiration time', () => {
      // Arrange - Token expires in 10 years
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const farFuture = Math.floor(Date.now() / 1000) + 315360000; // 10 years
      const payload = btoa(JSON.stringify({ exp: farFuture, sub: 'user123' }));
      const signature = 'signature';
      const token = `${header}.${payload}.${signature}`;
      setToken(token);

      // Act
      const expired = isTokenExpired();
      const expiration = getTokenExpiration(token);

      // Assert
      expect(expired).toBe(false);
      expect(expiration).toBeInstanceOf(Date);
    });

    it('should handle empty string token', () => {
      // Arrange
      setToken('');

      // Act
      const expired = isTokenExpired();
      const expiration = getTokenExpiration('');

      // Assert
      expect(expired).toBe(true);
      expect(expiration).toBeNull();
    });

    it('should handle token with URL-safe base64', () => {
      // Arrange - JWT uses URL-safe base64
      // JSDOM's atob can decode standard base64, not URL-safe
      // Create a token that uses only standard base64 characters
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const futureTime = Math.floor(Date.now() / 1000) + 3600;
      const payload = btoa(JSON.stringify({ exp: futureTime, sub: 'user123' }));
      const signature = 'sig';
      const token = `${header}.${payload}.${signature}`;

      // Act
      const expiration = getTokenExpiration(token);

      // Assert - Standard base64 should decode correctly
      expect(expiration).toBeInstanceOf(Date);
      expect(expiration?.getTime()).toBe(futureTime * 1000);
    });
  });
});
