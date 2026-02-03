/**
 * React Hooks for API Calls
 *
 * Provides unified hooks for making API calls with loading states, error handling,
 * and automatic cleanup.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { message } from 'antd';
import type { ApiResponse } from '../api/types';

/**
 * Request state interface
 */
export interface RequestState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * API Error interface with detailed error information
 */
export interface ApiError {
  code: string;
  message: string;
  detail?: string;
  request_id?: string;
  context?: Record<string, unknown>;
  status?: number;
}

/**
 * Options for useApiCall hook
 */
export interface UseApiCallOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
  showError?: boolean;
  successMessage?: string;
  errorMessage?: string;
  retry?: boolean;
  maxRetries?: number;
}

/**
 * Error code to message mapping
 */
const ERROR_MESSAGES: Record<string, string> = {
  VALIDATION_ERROR: '参数错误，请检查输入',
  NOT_FOUND: '请求的资源不存在',
  PERMISSION_DENIED: '权限不足，无法完成操作',
  UNAUTHENTICATED: '请先登录',
  RATE_LIMIT_EXCEEDED: '请求过于频繁，请稍后再试',
  SERVICE_UNAVAILABLE: '服务暂时不可用，请稍后再试',
  AUTH_INVALID_TOKEN: '登录已过期，请重新登录',
  AUTH_TOKEN_EXPIRED: '登录已过期，请重新登录',
  AUTH_INVALID_CREDENTIALS: '用户名或密码错误',
  DATABASE_ERROR: '数据库操作失败',
  EXTERNAL_SERVICE_ERROR: '外部服务调用失败',
  UNKNOWN_ERROR: '操作失败，请稍后再试',
};

/**
 * Normalize error from API response
 */
function normalizeError(error: unknown): ApiError {
  // Already an ApiError
  if (typeof error === 'object' && error !== null && 'code' in error) {
    return error as ApiError;
  }

  // API response format
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const err = error as { response: { data?: ApiError; status?: number } };
    if (err.response.data) {
      return {
        ...err.response.data,
        status: err.response.status,
      };
    }
  }

  // Network error
  if (error instanceof Error) {
    if (error.message.includes('timeout') || error.message.includes('ECONNABORTED')) {
      return {
        code: 'SERVICE_UNAVAILABLE',
        message: '请求超时，请检查网络连接',
        status: 408,
      };
    }
    if (error.message.includes('Network Error') || error.message.includes('ERR_NETWORK')) {
      return {
        code: 'SERVICE_UNAVAILABLE',
        message: '网络连接失败，请检查网络设置',
        status: 0,
      };
    }
    return {
      code: 'UNKNOWN_ERROR',
      message: error.message || '未知错误',
    };
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: '未知错误',
  };
}

/**
 * Get user-friendly error message
 */
function getErrorMessage(error: ApiError, customMessage?: string): string {
  if (customMessage) return customMessage;
  return ERROR_MESSAGES[error.code] || error.message || '操作失败';
}

/**
 * Handle authentication errors
 */
function handleAuthError(error: ApiError) {
  if (error.code === 'AUTH_INVALID_TOKEN' || error.code === 'AUTH_TOKEN_EXPIRED') {
    // Clear local storage
    localStorage.removeItem('token');
    localStorage.removeItem('user');

    // Redirect to login
    const currentPath = window.location.pathname;
    if (currentPath !== '/login') {
      window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
    }
  }
}

/**
 * Hook for making API calls with loading and error states
 *
 * @example
 * ```tsx
 * const { data, loading, error, execute } = useApiCall({
 *   onSuccess: (data) => {
 *     // Handle success
 *   },
 *   showError: true,
 * });
 *
 * useEffect(() => {
 *   execute(() => getUserInfo(userId));
 * }, [userId, execute]);
 * ```
 */
export function useApiCall<T = unknown>(
  options: UseApiCallOptions<T> = {}
): RequestState<T> & {
  execute: (fn: () => Promise<ApiResponse<T>>, opts?: UseApiCallOptions<T>) => Promise<T | null>;
  reset: () => void;
} {
  const { maxRetries = 3 } = options;

  const [state, setState] = useState<RequestState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const execute = useCallback(
    async (
      fn: () => Promise<ApiResponse<T>>,
      callOptions?: UseApiCallOptions<T>
    ): Promise<T | null> => {
      const mergedOptions = { ...options, ...callOptions };

      const attemptRequest = async (attempt: number): Promise<T | null> => {
        setState((prev) => ({ ...prev, loading: true, error: null }));

        try {
          const response = await fn();

          if (!isMounted.current) return null;

          if (response.code === 20000 && response.data !== undefined) {
            const data = response.data as T;

            setState({ data, loading: false, error: null });

            if (mergedOptions.successMessage) {
              message.success(mergedOptions.successMessage);
            }

            if (mergedOptions.onSuccess) {
              mergedOptions.onSuccess(data);
            }

            return data;
          }

          const apiError: ApiError = {
            code: response.code?.toString() || 'UNKNOWN_ERROR',
            message: response.message || '请求失败',
            detail: response.detail,
            request_id: response.request_id,
          };

          if (!isMounted.current) return null;

          setState({ data: null, loading: false, error: apiError.message });

          if (mergedOptions.showError !== false) {
            const errorMsg = getErrorMessage(apiError, mergedOptions.errorMessage);
            message.error(errorMsg);
          }

          if (mergedOptions.onError) {
            mergedOptions.onError(apiError);
          }

          handleAuthError(apiError);

          return null;
        } catch (err) {
          if (!isMounted.current) return null;

          const apiError = normalizeError(err);

          // Check if should retry
          const shouldRetry =
            mergedOptions.retry &&
            attempt < maxRetries &&
            ['SERVICE_UNAVAILABLE', 'UNKNOWN_ERROR'].includes(apiError.code);

          if (shouldRetry) {
            // Exponential backoff
            await new Promise((resolve) => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
            return attemptRequest(attempt + 1);
          }

          setState({ data: null, loading: false, error: apiError.message });

          if (mergedOptions.showError !== false) {
            const errorMsg = getErrorMessage(apiError, mergedOptions.errorMessage);
            message.error(errorMsg);
          }

          if (mergedOptions.onError) {
            mergedOptions.onError(apiError);
          }

          handleAuthError(apiError);

          return null;
        }
      };

      return attemptRequest(1);
    },
    [options, maxRetries]
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return {
    ...state,
    execute,
    reset,
  };
}

/**
 * Hook for making paginated API calls
 */
export interface PaginatedState<T> extends RequestState<T[]> {
  page: number;
  pageSize: number;
  total: number;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  refresh: () => Promise<void>;
}

export interface UsePaginatedApiOptions<T> extends UseApiCallOptions<T[]> {
  initialPage?: number;
  initialPageSize?: number;
}

export function usePaginatedApi<T = unknown>(
  fetchFn: (page: number, pageSize: number) => Promise<ApiResponse<T[] & { total?: number }>>,
  options: UsePaginatedApiOptions<T> = {}
): PaginatedState<T> {
  const { initialPage = 1, initialPageSize = 10, ...apiOptions } = options;

  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [total, setTotal] = useState(0);

  const { data, loading, error, execute } = useApiCall<T[] & { total?: number }>({
    ...apiOptions,
    onSuccess: (response) => {
      setTotal(response.total ?? response.length ?? 0);
      if (apiOptions.onSuccess) {
        apiOptions.onSuccess(response as T[]);
      }
    },
  });

  const refresh = useCallback(async () => {
    await execute(() => fetchFn(page, pageSize));
  }, [execute, fetchFn, page, pageSize]);

  useEffect(() => {
    refresh();
  }, [page, pageSize]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    data: data ?? [],
    loading,
    error,
    page,
    pageSize,
    total,
    setPage,
    setPageSize,
    refresh,
  };
}

/**
 * Hook for mutations (create, update, delete operations)
 */
export interface MutationState<T> {
  loading: boolean;
  error: string | null;
  data: T | null;
}

export interface UseMutationOptions<TData, TVariables = void> {
  onSuccess?: (data: TData, variables: TVariables) => void;
  onError?: (error: string, variables: TVariables) => void;
  showSuccess?: boolean;
  showError?: boolean;
  successMessage?: string;
  errorMessage?: string;
}

export function useMutation<TData = unknown, TVariables = void>(
  mutationFn: (variables: TVariables) => Promise<ApiResponse<TData>>,
  options: UseMutationOptions<TData, TVariables> = {}
): MutationState<TData> & {
  mutate: (variables: TVariables) => Promise<TData | null>;
  reset: () => void;
} {
  const { onSuccess, onError, showSuccess = false, showError = true, successMessage, errorMessage } = options;

  const [state, setState] = useState<MutationState<TData>>({
    loading: false,
    error: null,
    data: null,
  });

  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const mutate = useCallback(
    async (variables: TVariables): Promise<TData | null> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = await mutationFn(variables);

        if (response.code === 20000 && response.data !== undefined) {
          const data = response.data as TData;

          if (!isMounted.current) return data;

          setState({ data, loading: false, error: null });

          if (showSuccess && successMessage) {
            message.success(successMessage);
          }

          if (onSuccess) {
            onSuccess(data, variables);
          }

          return data;
        }

        const errorMsg = response.message || '操作失败';
        if (!isMounted.current) return null;

        setState({ data: null, loading: false, error: errorMsg });

        if (showError) {
          message.error(errorMessage || errorMsg);
        }

        if (onError) {
          onError(errorMsg, variables);
        }

        return null;
      } catch (error) {
        if (!isMounted.current) return null;

        const errorMsg = error instanceof Error ? error.message : '网络错误，请稍后重试';

        setState({ data: null, loading: false, error: errorMsg });

        if (showError) {
          message.error(errorMessage || errorMsg);
        }

        if (onError) {
          onError(errorMsg, variables);
        }

        return null;
      }
    },
    [mutationFn, onSuccess, onError, showSuccess, showError, successMessage, errorMessage]
  );

  const reset = useCallback(() => {
    setState({ loading: false, error: null, data: null });
  }, []);

  return {
    ...state,
    mutate,
    reset,
  };
}

/**
 * Hook for debounced API calls
 */
export function useDebouncedApiCall<T = unknown>(
  fn: () => Promise<ApiResponse<T>>,
  delay: number = 500
): RequestState<T> & { trigger: () => void } {
  const [state, setState] = useState<RequestState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const trigger = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    setState((prev) => ({ ...prev, loading: true }));

    timeoutRef.current = setTimeout(async () => {
      try {
        const response = await fn();

        if (response.code === 20000 && response.data !== undefined) {
          setState({ data: response.data as T, loading: false, error: null });
        } else {
          setState({ data: null, loading: false, error: response.message || '请求失败' });
        }
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : '网络错误';
        setState({ data: null, loading: false, error: errorMsg });
      }
    }, delay);
  }, [fn, delay]);

  return {
    ...state,
    trigger,
  };
}
