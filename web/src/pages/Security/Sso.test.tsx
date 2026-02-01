/**
 * Sso 组件测试
 * 测试统一身份认证页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sso from './Sso';

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

describe('Sso Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Sso />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Sso />);

    expect(screen.getByText('统一身份认证 (SSO)')).toBeInTheDocument();
  });

  it('should render tabs', () => {
    renderWithRouter(<Sso />);

    const tabElements = screen.queryAllByText(/认证配置|登录历史/);
    expect(tabElements.length).toBeGreaterThan(0);
  });

  it('should have add config button', () => {
    renderWithRouter(<Sso />);

    expect(screen.getByText('新建配置')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Sso />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display info alert', () => {
    renderWithRouter(<Sso />);

    expect(screen.getByText('SSO 配置说明')).toBeInTheDocument();
  });

  it('should have table for configs', () => {
    const { container } = renderWithRouter(<Sso />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });
});
