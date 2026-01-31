/**
 * API 响应处理工具
 *
 * 提供统一的响应处理函数和错误处理逻辑
 */

import type { ApiResponse, ErrorCode, ErrorResponse } from './types';
import { isSuccessResponse } from './types';
import { removeToken } from '../utils/token';
import { message } from 'antd';

/**
 * 处理 API 响应
 * @param response API 响应对象
 * @param options 配置选项
 * @returns 处理后的数据或抛出错误
 */
export async function handleResponse<T>(
  response: Promise<ApiResponse<T>>,
  options: {
    successMessage?: string;
    errorMessage?: string;
    showSuccess?: boolean;
    showError?: boolean;
    throwOnError?: boolean;
  } = {}
): Promise<T> {
  const {
    successMessage,
    errorMessage,
    showSuccess = false,
    showError = true,
    throwOnError = false,
  } = options;

  try {
    const resp = await response;

    if (isSuccessResponse(resp)) {
      const data = resp.data as T;

      // 显示成功消息
      if (showSuccess && successMessage) {
        message.success(successMessage);
      } else if (showSuccess && resp.message && resp.message !== 'success') {
        message.success(resp.message);
      }

      return data;
    }

    // 错误处理
    const errorMsg = errorMessage || resp.message || '操作失败';

    if (showError) {
      message.error(errorMsg);
    }

    if (throwOnError) {
      const error: Error & { code?: number; data?: unknown } = new Error(errorMsg);
      error.code = resp.code;
      error.data = resp.data;
      error.detail = (resp as ErrorResponse).detail;
      throw error;
    }

    throw new Error(errorMsg);
  } catch (error) {
    // 如果是网络错误或其他异常
    if (throwOnError) {
      throw error;
    }
    // 返回空数据（根据类型可能需要调整）
    return {} as T;
  }
}

/**
 * 处理 API 错误
 * @param error 错误对象
 * @param options 配置选项
 */
export function handleApiError(
  error: unknown,
  options: {
    showMessage?: boolean;
    defaultMessage?: string;
  } = {}
): void {
  const { showMessage = true, defaultMessage = "操作失败" } = options;

  let message = defaultMessage;

  if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === 'string') {
    message = error;
  } else if (error && typeof error === 'object' && 'message' in error) {
    message = (error as { message?: string }).message || message;
  }

  if (showMessage) {
    message.error(message);
  }

  // 处理 401 错误 - 清除 Token 并跳转登录
  if (error && typeof error === 'object') {
    const err = error as { code?: number; status?: number };
    if (err.code === ErrorCode.UNAUTHORIZED || err.code === ErrorCode.TOKEN_EXPIRED || err.status === 401) {
      removeToken();
      window.location.href = '/login';
    }
  }
}

/**
 * 批量处理 API 请求
 * @param requests 请求 Promise 数组
 * @param options 配置选项
 */
export async function handleBatchRequests<T>(
  requests: Array<Promise<ApiResponse<T>>>,
  options: {
    stopOnError?: boolean;
    showSuccess?: boolean;
  } = {}
): Promise<Array<T | null>> {
  const { stopOnError = false, showSuccess = false } = options;

  const results: Array<T | null> = [];

  for (const request of requests) {
    try {
      const data = await handleResponse(request, {
        showSuccess,
        showError: true,
        throwOnError: true,
      });
      results.push(data);
    } catch (error) {
      if (stopOnError) {
        throw error;
      }
      results.push(null);
    }
  }

  return results;
}

/**
 * 创建 API 请求钩子（可扩展到 React Hooks）
 * @param apiFn API 函数
 * @param options 配置选项
 */
export function createApiHook<T>(
  apiFn: (...args: unknown[]) => Promise<ApiResponse<T>>,
  options?: {
    successMessage?: string;
    errorMessage?: string;
    showSuccess?: boolean;
    showError?: boolean;
  }
) {
  return async (...args: Parameters<typeof apiFn>): Promise<T> => {
    return handleResponse(apiFn(...args), options);
  };
}

/**
 * 请求状态管理
 */
export interface RequestState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * 创建请求状态
 */
export function createRequestState<T>(): RequestState<T> {
  return {
    data: null,
    loading: false,
    error: null,
  };
}

/**
 * 重试请求
 * @param fn 请求函数
 * @param maxRetries 最大重试次数，默认 3
 * @param delay 重试延迟（毫秒），默认 1000
 */
export async function retryRequest<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError: Error | null = null;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      // 最后一次重试失败，不再等待
      if (i === maxRetries - 1) {
        break;
      }

      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
    }
  }

  throw lastError || new Error('重试失败');
}

/**
 * 导出便捷类型和函数
 */
export type { PageData, PaginatedResponse, ErrorResponse, ApiResponse };
// 重新导出 types.ts 中的函数
export {
  ErrorCode,
  getErrorMessage,
  isSuccessResponse,
  isErrorCode,
  createSuccessResponse,
  createErrorResponse,
  createPaginatedResponse,
} from './types';
