/**
 * API 响应处理工具
 *
 * 提供统一的响应处理函数和错误处理逻辑
 */

import type { ApiResponse, ErrorResponse, PageData, PaginatedResponse } from './types';
import { isSuccessResponse, ErrorCode } from './types';
import { removeToken } from '../utils/token';
import { message } from 'antd';

/**
 * Unwrap API response data safely
 * @param response Axios response containing ApiResponse<T>
 * @returns The unwrapped data (will throw for null/undefined in strict mode)
 * @throws Error if response is invalid or data is null/undefined when T doesn't allow it
 */
export function unwrapApiResponse<T>(response: { data: ApiResponse<T> | T }): T {
  const apiResponse = response.data;

  // Check if it's an ApiResponse format
  if (
    apiResponse &&
    typeof apiResponse === 'object' &&
    'code' in apiResponse &&
    'message' in apiResponse
  ) {
    const resp = apiResponse as ApiResponse<T>;
    if (isSuccessResponse(resp)) {
      // Explicitly check for null/undefined data in successful responses
      if (resp.data === null || resp.data === undefined) {
        throw new Error('API returned success but no data');
      }
      return resp.data as T;
    }
    throw new Error(resp.message || 'API request failed');
  }

  // Return as-is if not in ApiResponse format
  // Note: This assumes non-ApiResponse data is already the correct type
  return apiResponse as T;
}

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
      const error: Error & { code?: number; data?: unknown; detail?: string } = new Error(errorMsg);
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
 * HTTP 状态码对应的用户友好错误消息
 * 避免暴露内部系统信息
 */
const SAFE_ERROR_MESSAGES: Record<number, string> = {
  400: '请求参数错误，请检查输入',
  401: '登录已过期，请重新登录',
  403: '没有权限执行此操作',
  404: '请求的资源不存在',
  409: '数据冲突，请刷新后重试',
  422: '数据验证失败，请检查输入',
  429: '操作过于频繁，请稍后再试',
  500: '服务暂时不可用，请稍后再试',
  502: '服务连接失败，请稍后再试',
  503: '服务暂时不可用',
  504: '请求超时，请稍后再试',
};

/**
 * 获取安全的错误消息
 * 不暴露内部系统细节，仅返回用户友好的通用消息
 */
function getSafeErrorMessage(error: unknown): string {
  // 开发环境：记录详细错误到控制台
  if (import.meta.env.DEV) {
    console.error('API error:', error);
  }

  // 从响应中获取 HTTP 状态码
  let status: number | undefined;

  if (error && typeof error === 'object') {
    const err = error as {
      response?: { status?: number };
      status?: number;
      code?: number;
    };
    status = err.response?.status ?? err.status ?? err.code;
  }

  // 返回对应的安全消息
  if (status && SAFE_ERROR_MESSAGES[status]) {
    return SAFE_ERROR_MESSAGES[status];
  }

  // 网络错误
  if (error instanceof Error && error.message.includes('Network Error')) {
    return '网络连接失败，请检查网络设置';
  }

  // 请求超时
  if (error instanceof Error && error.message.includes('timeout')) {
    return '请求超时，请稍后再试';
  }

  // 默认通用消息
  return '操作失败，请稍后再试';
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

  const errorMsg = getSafeErrorMessage(error) || defaultMessage;

  if (showMessage) {
    message.error(errorMsg);
  }

  // 处理 401 错误 - 清除 Token 并跳转登录
  if (error && typeof error === 'object') {
    const err = error as { code?: number; status?: number; response?: { status?: number } };
    const status = err.response?.status ?? err.status ?? err.code;
    if (status === ErrorCode.UNAUTHORIZED || status === ErrorCode.TOKEN_EXPIRED || status === 401) {
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
