/**
 * API 类型测试
 * 测试 ApiResponse 类型系统的正确性
 */

import { describe, it, expect } from 'vitest';
import {
  ErrorCode,
  isSuccessResponse,
  isErrorCode,
  getErrorMessage,
  createSuccessResponse,
  createErrorResponse,
  createPaginatedResponse,
  type ApiResponse,
} from './types';

describe('ErrorCode', () => {
  it('should have correct success code', () => {
    expect(ErrorCode.SUCCESS).toBe(20000);
  });

  it('should have correct unauthorized code', () => {
    expect(ErrorCode.UNAUTHORIZED).toBe(40100);
  });

  it('should have correct token expired code', () => {
    expect(ErrorCode.TOKEN_EXPIRED).toBe(40101);
  });

  it('should have correct not found code', () => {
    expect(ErrorCode.NOT_FOUND).toBe(40400);
  });
});

describe('isSuccessResponse', () => {
  it('should return true for success response', () => {
    const response: ApiResponse<string> = {
      code: ErrorCode.SUCCESS,
      message: 'success',
      data: 'test data',
      timestamp: Date.now(),
    };
    expect(isSuccessResponse(response)).toBe(true);
  });

  it('should return false for error response', () => {
    const response: ApiResponse<string> = {
      code: ErrorCode.UNAUTHORIZED,
      message: 'Unauthorized',
      timestamp: Date.now(),
    };
    expect(isSuccessResponse(response)).toBe(false);
  });

  it('should return false for non-success codes', () => {
    const errorCodes = [
      ErrorCode.INVALID_PARAMS,
      ErrorCode.NOT_FOUND,
      ErrorCode.INTERNAL_ERROR,
    ];

    errorCodes.forEach((code) => {
      const response: ApiResponse<null> = {
        code,
        message: 'error',
        data: null,
        timestamp: Date.now(),
      };
      expect(isSuccessResponse(response)).toBe(false);
    });
  });
});

describe('isErrorCode', () => {
  it('should return true when response code matches', () => {
    const response: ApiResponse<null> = {
      code: ErrorCode.NOT_FOUND,
      message: 'Not found',
      data: null,
      timestamp: Date.now(),
    };
    expect(isErrorCode(response, ErrorCode.NOT_FOUND)).toBe(true);
  });

  it('should return false when response code does not match', () => {
    const response: ApiResponse<null> = {
      code: ErrorCode.UNAUTHORIZED,
      message: 'Unauthorized',
      data: null,
      timestamp: Date.now(),
    };
    expect(isErrorCode(response, ErrorCode.NOT_FOUND)).toBe(false);
  });
});

describe('getErrorMessage', () => {
  it('should return correct message for known error codes', () => {
    expect(getErrorMessage(ErrorCode.SUCCESS)).toBe('操作成功');
    expect(getErrorMessage(ErrorCode.UNAUTHORIZED)).toBe('未授权');
    expect(getErrorMessage(ErrorCode.NOT_FOUND)).toBe('资源不存在');
  });

  it('should return unknown message for unknown error codes', () => {
    const unknownCode = 99999;
    expect(getErrorMessage(unknownCode)).toBe('未知错误');
  });
});

describe('createSuccessResponse', () => {
  it('should create success response with data', () => {
    const data = { id: 1, name: 'test' };
    const response = createSuccessResponse(data);

    expect(response.code).toBe(ErrorCode.SUCCESS);
    expect(response.message).toBe('success');
    expect(response.data).toEqual(data);
    expect(response.timestamp).toBeLessThanOrEqual(Date.now() / 1000);
  });

  it('should create success response with custom message', () => {
    const response = createSuccessResponse(null, 'Created');

    expect(response.code).toBe(ErrorCode.SUCCESS);
    expect(response.message).toBe('Created');
    expect(response.data).toBeNull();
  });
});

describe('createErrorResponse', () => {
  it('should create error response with code and message', () => {
    const response = createErrorResponse(
      ErrorCode.INVALID_PARAMS,
      '参数错误'
    );

    expect(response.code).toBe(ErrorCode.INVALID_PARAMS);
    expect(response.message).toBe('参数错误');
    expect(response.data).toBeNull();
    expect(response.timestamp).toBeLessThanOrEqual(Date.now() / 1000);
  });

  it('should use default message when not provided', () => {
    const response = createErrorResponse(ErrorCode.NOT_FOUND);

    expect(response.message).toBe('资源不存在');
  });

  it('should include detail when provided', () => {
    const detail = { field: 'email', error: 'Invalid format' };
    const response = createErrorResponse(
      ErrorCode.INVALID_PARAMS,
      undefined,
      detail
    );

    expect(response.detail).toEqual(detail);
  });
});

describe('createPaginatedResponse', () => {
  it('should create paginated response with correct defaults', () => {
    const items = [{ id: 1 }, { id: 2 }, { id: 3 }];
    const response = createPaginatedResponse(items, 3);

    expect(response.code).toBe(ErrorCode.SUCCESS);
    expect(response.data?.items).toEqual(items);
    expect(response.data?.total).toBe(3);
    expect(response.data?.page).toBe(1);
    expect(response.data?.page_size).toBe(10);
    expect(response.data?.pages).toBe(1);
  });

  it('should calculate pages correctly', () => {
    const items = Array.from({ length: 25 }, (_, i) => ({ id: i + 1 }));
    const response = createPaginatedResponse(items, 25, 1, 10);

    expect(response.data?.pages).toBe(3);
  });

  it('should handle zero pages when pageSize is 0', () => {
    const response = createPaginatedResponse([], 0, 1, 0);

    expect(response.data?.pages).toBe(0);
  });

  it('should use custom page parameters', () => {
    const items = [{ id: 1 }, { id: 2 }];
    const response = createPaginatedResponse(items, 2, 2, 5);

    expect(response.data?.page).toBe(2);
    expect(response.data?.page_size).toBe(5);
    expect(response.data?.pages).toBe(1);
  });

  it('should handle custom message', () => {
    const response = createPaginatedResponse([], 0, 1, 10, 'No results');

    expect(response.message).toBe('No results');
  });
});
