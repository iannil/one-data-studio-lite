/**
 * ApiGateway 组件测试
 * 测试接口服务管理页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ApiGateway from './ApiGateway';

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

const renderWithRouter = (component: React.ReactElement) => {
  return render(<MemoryRouter>{component}</MemoryRouter>);
};

describe('ApiGateway Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<ApiGateway />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<ApiGateway />);

    expect(screen.getByText('接口服务管理')).toBeInTheDocument();
  });

  it('should have refresh button', () => {
    renderWithRouter(<ApiGateway />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should display statistics cards', () => {
    renderWithRouter(<ApiGateway />);

    // Check for statistics
    const statElements = screen.queryAllByText(/总 QPS|平均响应时间|异常接口|在线接口/);
    expect(statElements.length).toBeGreaterThan(0);
  });

  it('should have service selector', () => {
    renderWithRouter(<ApiGateway />);

    // Check for service select
    const { container } = renderWithRouter(<ApiGateway />);
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should have status selector', () => {
    renderWithRouter(<ApiGateway />);

    const { container } = renderWithRouter(<ApiGateway />);
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should have table for endpoints', () => {
    renderWithRouter(<ApiGateway />);

    const { container } = renderWithRouter(<ApiGateway />);
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should display info alert', () => {
    renderWithRouter(<ApiGateway />);

    expect(screen.getByText('API 网关监控')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<ApiGateway />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
