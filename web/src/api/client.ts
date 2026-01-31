import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getToken, removeToken, setToken, isTokenExpiringSoon } from '../utils/token';
import type { ApiResponse } from './types';

// 创建 Axios 实例（开发环境通过 Vite 代理，生产环境需要配置 VITE_API_BASE_URL）
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 类型安全的响应获取
export async function getResponseData<T>(response: Promise<ApiResponse<T>>): Promise<T> {
  const resp = await response;
  if (resp.code === 20000 && resp.data !== undefined) {
    return resp.data;
  }
  throw new Error(resp.message || '请求失败');
}

// Token刷新状态
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

const subscribeTokenRefresh = (cb: (token: string) => void) => {
  refreshSubscribers.push(cb);
};

const onTokenRefreshed = (token: string) => {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
};

// 刷新Token
const refreshTokenRequest = async (): Promise<string | null> => {
  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_BASE_URL || ''}/auth/refresh`,
      {},
      {
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      }
    );
    if (response.data.success && response.data.token) {
      return response.data.token;
    }
    return null;
  } catch {
    return null;
  }
};

// 请求拦截器 - 注入 Token，检查Token是否需要刷新
client.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const token = getToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;

      // 检查Token是否即将过期，自动刷新（排除refresh和login请求）
      const url = config.url || '';
      if (!url.includes('/auth/refresh') && !url.includes('/auth/login') && isTokenExpiringSoon(30)) {
        if (!isRefreshing) {
          isRefreshing = true;
          const newToken = await refreshTokenRequest();
          isRefreshing = false;

          if (newToken) {
            setToken(newToken);
            config.headers.Authorization = `Bearer ${newToken}`;
            onTokenRefreshed(newToken);
          }
        } else {
          // 等待Token刷新完成
          return new Promise((resolve) => {
            subscribeTokenRefresh((newToken: string) => {
              config.headers.Authorization = `Bearer ${newToken}`;
              resolve(config);
            });
          });
        }
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 处理错误
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // 只有认证相关的 401 才跳转登录页
    // 代理请求的 401 (来自后端服务) 不应该清除用户 token
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      // 只有 /auth 相关接口返回 401 才清除 token
      if (url.startsWith('/auth') || url === '/api/subsystems') {
        removeToken();
        window.location.href = '/login';
      }
      // 代理请求的 401 只是提示错误，不清除 token
    }
    return Promise.reject(error);
  }
);

export default client;
