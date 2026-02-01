/**
 * Users 组件测试
 * 测试用户与组织管理页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Users from './Users';

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

describe('Users Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Users />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Users />);

    expect(screen.getByText('用户与组织管理')).toBeInTheDocument();
  });

  it('should render tabs', () => {
    renderWithRouter(<Users />);

    expect(screen.getByText(/用户管理/)).toBeInTheDocument();
    expect(screen.getByText('组织架构')).toBeInTheDocument();
    expect(screen.getByText(/角色管理/)).toBeInTheDocument();
  });

  it('should have add user button', () => {
    renderWithRouter(<Users />);

    expect(screen.getByText('新建用户')).toBeInTheDocument();
  });

  it('should have search input', () => {
    renderWithRouter(<Users />);

    const searchInput = screen.getByPlaceholderText(/搜索用户名/);
    expect(searchInput).toBeInTheDocument();
  });

  it('should handle search input change', () => {
    renderWithRouter(<Users />);

    const searchInput = screen.getByPlaceholderText(/搜索用户名/);
    fireEvent.change(searchInput, { target: { value: 'admin' } });

    expect(searchInput).toHaveValue('admin');
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Users />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should have refresh button', () => {
    renderWithRouter(<Users />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should display info alert', () => {
    renderWithRouter(<Users />);

    expect(screen.getByText('用户与组织管理说明')).toBeInTheDocument();
  });
});
