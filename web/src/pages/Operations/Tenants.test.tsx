/**
 * Tenants 组件测试
 * 测试租户管理页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Tenants from './Tenants';

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

describe('Tenants Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Tenants />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Tenants />);

    expect(screen.getByText('租户管理')).toBeInTheDocument();
  });

  it('should have add tenant button', () => {
    renderWithRouter(<Tenants />);

    const addButtons = screen.queryAllByText('新建租户');
    expect(addButtons.length).toBeGreaterThan(0);
  });

  it('should have search input', () => {
    const { container } = renderWithRouter(<Tenants />);

    const inputs = container.querySelectorAll('input');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should have status and plan filters', () => {
    renderWithRouter(<Tenants />);

    const filterElements = screen.queryAllByText(/全部状态|全部套餐|正常|暂停|过期/);
    expect(filterElements.length).toBeGreaterThan(0);
  });

  it('should display statistics cards', () => {
    renderWithRouter(<Tenants />);

    const statElements = screen.queryAllByText(/总租户数|活跃租户|总用户数|总存储使用/);
    expect(statElements.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Tenants />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
