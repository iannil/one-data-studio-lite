/**
 * 测试工具函数
 */

import { render, RenderOptions } from '@testing-library/react';
import { ReactElement } from 'react';

/**
 * 自定义渲染函数，可包含默认 providers
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, options);
}

/**
 * 创建 mock wrapper
 */
export function createMockWrapper(Component: React.ComponentType<any>) {
  return ({ children }: { children: React.ReactNode }) => {
    return <Component>{children}</Component>;
  };
}

/**
 * Mock 延迟函数
 */
export const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Mock API 响应
 */
export function mockApiResponse<T>(data: T, code = 20000, message = 'success') {
  return {
    code,
    message,
    data,
    timestamp: Math.floor(Date.now() / 1000),
  };
}

/**
 * Mock 错误响应
 */
export function mockErrorResponse(code: number, message: string) {
  return {
    code,
    message,
    data: null,
    timestamp: Math.floor(Date.now() / 1000),
  };
}
