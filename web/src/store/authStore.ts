import { create } from 'zustand';
import { User } from '../types';
import { login as loginApi, logout as logoutApi } from '../api/auth';
import { getToken, setToken, removeToken, getUser, setUser } from '../utils/token';

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
  user: getUser(),
  isAuthenticated: !!getToken(),
  loading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const response = await loginApi(username, password);
      if (response.success) {
        setToken(response.token);
        setUser(response.user);
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
    } catch (error: any) {
      const message = error.response?.data?.detail || '登录失败，请检查网络连接';
      set({ error: message, loading: false });
      return false;
    }
  },

  logout: async () => {
    try {
      await logoutApi();
    } catch {
      // 忽略登出错误
    }
    removeToken();
    set({
      token: null,
      user: null,
      isAuthenticated: false,
    });
  },

  checkAuth: () => {
    const token = getToken();
    const user = getUser();
    set({
      token,
      user,
      isAuthenticated: !!token,
    });
  },
}));
