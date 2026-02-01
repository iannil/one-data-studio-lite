/**
 * API 工具函数测试
 * TDD: 先写测试，验证 unwrapApiResponse 等核心函数的正确性
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ErrorCode } from './types';
import {
  unwrapApiResponse,
  handleResponse,
  handleApiError,
  handleBatchRequests,
  retryRequest,
  createApiHook,
} from './utils';

// Mock antd message
vi.mock('antd', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock token utils
vi.mock('../utils/token', () => ({
  removeToken: vi.fn(),
}));

import { message } from 'antd';
import { removeToken } from '../utils/token';

const mockMessage = vi.mocked(message);
const mockRemoveToken = vi.mocked(removeToken);

describe('unwrapApiResponse', () => {
  it('should unwrap data from successful ApiResponse', () => {
    const testData = { id: 1, name: 'test' };
    const response = {
      data: {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: testData,
        timestamp: Date.now(),
      },
    };

    const result = unwrapApiResponse(response);

    expect(result).toEqual(testData);
  });

  it('should throw error for failed ApiResponse', () => {
    const response = {
      data: {
        code: ErrorCode.UNAUTHORIZED,
        message: 'Unauthorized',
        timestamp: Date.now(),
      },
    };

    expect(() => unwrapApiResponse(response)).toThrow('Unauthorized');
  });

  it('should throw error with default message when message is empty', () => {
    const response = {
      data: {
        code: ErrorCode.INTERNAL_ERROR,
        message: '',
        timestamp: Date.now(),
      },
    };

    expect(() => unwrapApiResponse(response)).toThrow('API request failed');
  });

  it('should throw error when ApiResponse has null data', () => {
    const response = {
      data: {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: null,
        timestamp: Date.now(),
      },
    };

    expect(() => unwrapApiResponse(response)).toThrow('API returned success but no data');
  });

  it('should throw error when ApiResponse has undefined data', () => {
    const response = {
      data: {
        code: ErrorCode.SUCCESS,
        message: 'success',
        timestamp: Date.now(),
      },
    };

    expect(() => unwrapApiResponse(response)).toThrow('API returned success but no data');
  });

  it('should return raw data when not in ApiResponse format', () => {
    const rawData = { direct: 'data' };
    const response = {
      data: rawData,
    };

    const result = unwrapApiResponse(response);

    expect(result).toEqual(rawData);
  });

  it('should handle array data correctly', () => {
    const testArray = [{ id: 1 }, { id: 2 }];
    const response = {
      data: {
        code: ErrorCode.SUCCESS,
        message: 'success',
        data: testArray,
        timestamp: Date.now(),
      },
    };

    const result = unwrapApiResponse(response);

    expect(result).toEqual(testArray);
  });
});

describe('handleResponse', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return data on successful response', async () => {
    const testData = { result: 'success' };
    const promise = Promise.resolve({
      code: ErrorCode.SUCCESS,
      message: 'success',
      data: testData,
      timestamp: Date.now(),
    });

    const result = await handleResponse(promise);

    expect(result).toEqual(testData);
  });

  it('should show success message when showSuccess is true', async () => {
    const promise = Promise.resolve({
      code: ErrorCode.SUCCESS,
      message: 'Operation completed',
      data: null,
      timestamp: Date.now(),
    });

    await handleResponse(promise, { showSuccess: true });

    expect(mockMessage.success).toHaveBeenCalledWith('Operation completed');
  });

  it('should show custom success message', async () => {
    const promise = Promise.resolve({
      code: ErrorCode.SUCCESS,
      message: 'success',
      data: null,
      timestamp: Date.now(),
    });

    await handleResponse(promise, {
      showSuccess: true,
      successMessage: 'Custom message',
    });

    expect(mockMessage.success).toHaveBeenCalledWith('Custom message');
  });

  it('should show error message on failure', async () => {
    const promise = Promise.resolve({
      code: ErrorCode.INVALID_PARAMS,
      message: 'Invalid parameters',
      data: null,
      timestamp: Date.now(),
    });

    const result = await handleResponse(promise, {
      showError: true,
      throwOnError: false,
    });

    expect(mockMessage.error).toHaveBeenCalledWith('Invalid parameters');
    expect(result).toEqual({} as unknown);
  });

  it('should throw error when throwOnError is true', async () => {
    const promise = Promise.resolve({
      code: ErrorCode.UNAUTHORIZED,
      message: 'Unauthorized',
      data: null,
      timestamp: Date.now(),
    });

    await expect(
      handleResponse(promise, { throwOnError: true })
    ).rejects.toThrow('Unauthorized');
  });

  it('should use custom error message', async () => {
    const promise = Promise.resolve({
      code: ErrorCode.INTERNAL_ERROR,
      message: 'Internal error',
      data: null,
      timestamp: Date.now(),
    });

    await handleResponse(promise, {
      showError: true,
      errorMessage: 'Custom error',
    });

    expect(mockMessage.error).toHaveBeenCalledWith('Custom error');
  });
});

describe('handleApiError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show error message from Error object', () => {
    const error = new Error('Test error');
    handleApiError(error, { showMessage: true });

    expect(mockMessage.error).toHaveBeenCalledWith('Test error');
  });

  it('should show error message from string', () => {
    handleApiError('String error', { showMessage: true });

    expect(mockMessage.error).toHaveBeenCalledWith('String error');
  });

  it('should show error message from object with message property', () => {
    const error = { message: 'Object error' };
    handleApiError(error, { showMessage: true });

    expect(mockMessage.error).toHaveBeenCalledWith('Object error');
  });

  it('should use default message when error has no message', () => {
    handleApiError({}, { showMessage: true, defaultMessage: 'Default' });

    expect(mockMessage.error).toHaveBeenCalledWith('Default');
  });

  it('should not show message when showMessage is false', () => {
    handleApiError(new Error('Test'), { showMessage: false });

    expect(mockMessage.error).not.toHaveBeenCalled();
  });

  it('should remove token and redirect on 401', () => {
    const error = new Error('Unauthorized');
    (error as { code?: number }).code = ErrorCode.UNAUTHORIZED;

    // Spy on location.href assignment
    const hrefSetter = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
      configurable: true,
    });
    Object.defineProperty(window.location, 'href', {
      set: hrefSetter,
      configurable: true,
    });

    handleApiError(error, { showMessage: false });

    expect(mockRemoveToken).toHaveBeenCalled();
    expect(hrefSetter).toHaveBeenCalledWith('/login');
  });

  it('should remove token and redirect on 401 status', () => {
    const error = new Error('Unauthorized');
    (error as { status?: number }).status = 401;

    const hrefSetter = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
      configurable: true,
    });
    Object.defineProperty(window.location, 'href', {
      set: hrefSetter,
      configurable: true,
    });

    handleApiError(error, { showMessage: false });

    expect(mockRemoveToken).toHaveBeenCalled();
    expect(hrefSetter).toHaveBeenCalledWith('/login');
  });
});

describe('retryRequest', () => {
  it('should return result on first try', async () => {
    const fn = vi.fn().mockResolvedValue('success');
    const result = await retryRequest(fn, 3, 1);

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('should retry on failure and eventually succeed', async () => {
    const fn = vi.fn()
      .mockRejectedValueOnce(new Error('Fail 1'))
      .mockRejectedValueOnce(new Error('Fail 2'))
      .mockResolvedValue('success');

    const result = await retryRequest(fn, 3, 1);

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it('should throw error after max retries', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('Always fail'));

    await expect(retryRequest(fn, 3, 1)).rejects.toThrow('Always fail');
    expect(fn).toHaveBeenCalledTimes(3);
  });
});

describe('handleBatchRequests', () => {
  it('should process all requests successfully', async () => {
    const request1 = Promise.resolve({
      code: ErrorCode.SUCCESS,
      message: 'success',
      data: 'result1',
      timestamp: Date.now(),
    });
    const request2 = Promise.resolve({
      code: ErrorCode.SUCCESS,
      message: 'success',
      data: 'result2',
      timestamp: Date.now(),
    });

    const results = await handleBatchRequests([request1, request2]);

    expect(results).toEqual(['result1', 'result2']);
  });

  it('should return null for failed request when not stopping on error', async () => {
    const request1 = Promise.resolve({
      code: ErrorCode.SUCCESS,
      message: 'success',
      data: 'result1',
      timestamp: Date.now(),
    });
    const request2 = Promise.resolve({
      code: ErrorCode.INTERNAL_ERROR,
      message: 'Error',
      data: null,
      timestamp: Date.now(),
    });

    const results = await handleBatchRequests(
      [request1, request2],
      { stopOnError: false }
    );

    expect(results).toEqual(['result1', null]);
  });

  it('should stop on first error when stopOnError is true', async () => {
    const request1 = Promise.resolve({
      code: ErrorCode.SUCCESS,
      message: 'success',
      data: 'result1',
      timestamp: Date.now(),
    });
    const request2 = Promise.reject(new Error('Failed'));

    await expect(
      handleBatchRequests([request1, request2], { stopOnError: true })
    ).rejects.toThrow('Failed');
  });
});

describe('createApiHook', () => {
  it('should create a function that calls API and unwraps response', async () => {
    const apiFn = vi.fn().mockResolvedValue({
      code: ErrorCode.SUCCESS,
      message: 'success',
      data: { id: 1 },
      timestamp: Date.now(),
    });

    const hook = createApiHook(apiFn);
    const result = await hook();

    expect(result).toEqual({ id: 1 });
    expect(apiFn).toHaveBeenCalled();
  });
});
