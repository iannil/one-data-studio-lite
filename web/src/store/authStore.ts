import { create } from 'zustand';
import { User } from '../types';
import { login as loginApi, logout as logoutApi } from '../api/auth';
import { getToken, setToken, removeToken, getUser, setUser } from '../utils/token';

// 是否启用 Cookie 认证（httpOnly Cookie 存储 Token）
// 生产环境推荐启用，更安全（防止 XSS 窃取 Token）
const USE_COOKIE_AUTH = import.meta.env.VITE_USE_COOKIE_AUTH !== 'false';

/**
 * 安全的错误消息映射
 * 将原始错误转换为通用消息，避免暴露内部系统信息
 */
function getSafeAuthError(error: unknown): string {
  // 记录详细错误到控制台（仅开发环境）
  if (import.meta.env.DEV) {
    console.error('Auth error:', error);
  }

  // HTTP 状态码错误映射
  const status = (error as { response?: { status?: number } })?.response?.status;
  const errorMessages: Record<number, string> = {
    400: '请求参数错误',
    401: '用户名或密码错误',
    403: '没有权限访问',
    404: '资源不存在',
    429: '请求过于频繁，请稍后再试',
    500: '服务暂时不可用，请稍后再试',
    502: '服务连接失败',
    503: '服务暂时不可用',
    504: '请求超时',
  };

  if (status && errorMessages[status]) {
    return errorMessages[status];
  }

  // 网络错误
  if ((error as Error)?.message?.includes('Network Error')) {
    return '网络连接失败，请检查网络设置';
  }

  // 默认通用消息
  return '登录失败，请稍后再试';
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: getToken(),
  user: getUser() as User | null,
  isAuthenticated: !!getToken(),
  loading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const response = await loginApi(username, password);
      if (response.success) {
        // Cookie 认证模式下，Token 由服务器通过 httpOnly Cookie 返回
        // 不再存储到 localStorage（更安全）
        if (!USE_COOKIE_AUTH) {
          setToken(response.token);
        }
        setUser(response.user as unknown as Record<string, unknown>);
        set({
          token: response.token,
          user: response.user,
          isAuthenticated: true,
          loading: false,
        });
        return true;
      } else {
        set({ error: response.message, loading: false });
        return false;
      }
    } catch (error) {
      // 使用安全的错误消息，避免暴露内部信息
      const safeMessage = getSafeAuthError(error);
      set({ error: safeMessage, loading: false });
      return false;
    }
  },

  logout: async () => {
    try {
      await logoutApi();
    } catch {
      // 忽略登出错误
    }
    // Cookie 认证模式下，服务器会清除 httpOnly Cookie
    // 前端只需清除本地存储的用户信息
    removeToken();
    set({
      token: null,
      user: null,
      isAuthenticated: false,
    });
  },

  checkAuth: () => {
    const token = getToken();
    const user = getUser() as User | null;
    set({
      token,
      user,
      isAuthenticated: !!token || !!user,  // 有用户信息即视为已认证
    });
  },
}));
