import client from './client';
import { LoginResponse, Subsystem } from '../types';

interface RefreshTokenResponse {
  success: boolean;
  token?: string;
  message: string;
}

/** 聚合健康检查响应 */
export interface AggregatedHealthResponse {
  status: 'healthy' | 'degraded';
  portal: string;
  unhealthy_count: number;
  subsystems: Array<{
    name: string;
    display_name: string;
    status: 'online' | 'offline';
  }>;
  internal_services: Array<{
    name: string;
    display_name: string;
    url: string;
    status: 'healthy' | 'unhealthy';
    error?: string;
  }>;
}

/** Token 验证响应 */
export interface TokenValidationResponse {
  valid: boolean;
  code?: number;
  message?: string;
  user_id?: string;
  username?: string;
  display_name?: string;
  roles?: string[];
  permissions?: string[];
  expires_at?: number;
  issued_at?: number;
}

/** 用户信息响应 */
export interface UserInfoResponse {
  user_id: string;
  username: string;
  display_name: string;
  email?: string;
  role: string;
  roles: string[];
  permissions: string[];
}

/** 密码重置请求 */
export interface PasswordResetRequest {
  email: string;
}

/** 验证码验证请求 */
export interface VerifyCodeRequest {
  email: string;
  code: string;
}

/** 密码重置确认请求 */
export interface ResetPasswordConfirmRequest {
  email: string;
  code: string;
  new_password: string;
}

/** 修改密码请求 */
export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

// ============================================================
// 认证 API
// ============================================================

/** 登录 */
export const login = async (username: string, password: string): Promise<LoginResponse> => {
  const response = await client.post<LoginResponse>('/auth/login', {
    username,
    password,
  });
  return response.data;
};

/** 登出 */
export const logout = async (): Promise<void> => {
  await client.post('/auth/logout');
};

/** 刷新 Token */
export const refreshToken = async (): Promise<RefreshTokenResponse> => {
  const response = await client.post<RefreshTokenResponse>('/auth/refresh');
  return response.data;
};

/** 验证 Token */
export const validateToken = async (): Promise<TokenValidationResponse> => {
  const response = await client.get<TokenValidationResponse>('/auth/validate');
  return response.data;
};

/** 获取当前用户信息 */
export const getUserInfo = async (): Promise<UserInfoResponse> => {
  const response = await client.get<UserInfoResponse>('/auth/userinfo');
  return response.data;
};

/** 撤销 Token */
export const revokeToken = async (): Promise<{ success: boolean; message: string }> => {
  const response = await client.post<{ success: boolean; message: string }>('/auth/revoke');
  return response.data;
};

// ============================================================
// 密码管理 API
// ============================================================

/** 发送密码重置验证码 */
export const sendPasswordResetCode = async (email: string): Promise<{ success: boolean; message: string }> => {
  const response = await client.post<{ success: boolean; message: string }>('/auth/password/reset/code', { email });
  return response.data;
};

/** 验证重置验证码 */
export const verifyResetCode = async (email: string, code: string): Promise<{ success: boolean; valid: boolean; message: string }> => {
  const response = await client.post<{ success: boolean; valid: boolean; message: string }>('/auth/password/reset/verify', { email, code });
  return response.data;
};

/** 确认密码重置 */
export const resetPassword = async (email: string, code: string, new_password: string): Promise<{ success: boolean; message: string }> => {
  const response = await client.post<{ success: boolean; message: string }>('/auth/password/reset/confirm', { email, code, new_password });
  return response.data;
};

/** 修改密码 (需要旧密码) */
export const changePassword = async (old_password: string, new_password: string): Promise<{ success: boolean; message: string }> => {
  const response = await client.post<{ success: boolean; message: string }>('/auth/password/change', { old_password, new_password });
  return response.data;
};

// ============================================================
// 系统状态 API
// ============================================================

/** 获取子系统列表 */
export const getSubsystems = async (): Promise<Subsystem[]> => {
  const response = await client.get<Subsystem[]>('/api/subsystems');
  return response.data;
};

/** 健康检查 */
export const healthCheck = async (): Promise<{ status: string; service: string }> => {
  const response = await client.get('/health');
  return response.data;
};

/** 聚合健康检查 - 检查所有子系统和内部服务 */
export const healthCheckAll = async (): Promise<AggregatedHealthResponse> => {
  const response = await client.get<AggregatedHealthResponse>('/health/all');
  return response.data;
};

/** 安全配置检查 */
export const securityCheck = async (): Promise<{
  security_level: string;
  security_message: string;
  score: number;
  max_score: number;
  is_production: boolean;
  environment: string;
  token_status: Record<string, boolean>;
  warnings: string[];
  recommendations: string[];
}> => {
  const response = await client.get('/security/check');
  return response.data;
};
