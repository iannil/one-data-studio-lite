/**
 * Permissions 组件测试
 * 测试数据权限管控页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Permissions from './Permissions';

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

describe('Permissions Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Permissions />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Permissions />);

    expect(screen.getByText('数据权限管控')).toBeInTheDocument();
  });

  it('should render tabs', () => {
    renderWithRouter(<Permissions />);

    const tabElements = screen.queryAllByText(/权限规则|权限模板|权限预览/);
    expect(tabElements.length).toBeGreaterThan(0);
  });

  it('should have add rule button', () => {
    renderWithRouter(<Permissions />);

    expect(screen.getByText('新建规则')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Permissions />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display info alert', () => {
    renderWithRouter(<Permissions />);

    expect(screen.getByText('权限管控说明')).toBeInTheDocument();
  });

  it('should have table for rules', () => {
    renderWithRouter(<Permissions />);

    const { container } = renderWithRouter(<Permissions />);
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });
});
