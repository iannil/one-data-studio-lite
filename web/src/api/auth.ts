import client from './client';
import { LoginResponse, Subsystem } from '../types';

// 登录
export const login = async (username: string, password: string): Promise<LoginResponse> => {
  const response = await client.post<LoginResponse>('/auth/login', {
    username,
    password,
  });
  return response.data;
};

// 登出
export const logout = async (): Promise<void> => {
  await client.post('/auth/logout');
};

// 获取子系统列表
export const getSubsystems = async (): Promise<Subsystem[]> => {
  const response = await client.get<Subsystem[]>('/api/subsystems');
  return response.data;
};

// 健康检查
export const healthCheck = async (): Promise<{ status: string; service: string }> => {
  const response = await client.get('/health');
  return response.data;
};
