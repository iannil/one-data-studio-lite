const TOKEN_KEY = 'ods_token';
const USER_KEY = 'ods_user';

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const getUser = (): any | null => {
  const user = localStorage.getItem(USER_KEY);
  return user ? JSON.parse(user) : null;
};

export const setUser = (user: any): void => {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

// 解析JWT Token获取过期时间
export const getTokenExpiration = (token: string): Date | null => {
  try {
    const payload = token.split('.')[1];
    const decoded = JSON.parse(atob(payload));
    if (decoded.exp) {
      return new Date(decoded.exp * 1000);
    }
    return null;
  } catch {
    return null;
  }
};

// 检查Token是否即将过期（默认30分钟内）
export const isTokenExpiringSoon = (thresholdMinutes: number = 30): boolean => {
  const token = getToken();
  if (!token) return false;

  const expiration = getTokenExpiration(token);
  if (!expiration) return false;

  const now = new Date();
  const thresholdMs = thresholdMinutes * 60 * 1000;
  return (expiration.getTime() - now.getTime()) <= thresholdMs;
};

// 检查Token是否已过期
export const isTokenExpired = (): boolean => {
  const token = getToken();
  if (!token) return true;

  const expiration = getTokenExpiration(token);
  if (!expiration) return true;

  return new Date() >= expiration;
};
