/**
 * Invoices 组件测试
 * 测试财务开票信息页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Invoices from './Invoices';

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

describe('Invoices Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Invoices />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Invoices />);

    expect(screen.getByText('财务开票信息')).toBeInTheDocument();
  });

  it('should render tabs', () => {
    renderWithRouter(<Invoices />);

    const tabElements = screen.queryAllByText(/发票列表|开票申请|审核管理/);
    expect(tabElements.length).toBeGreaterThan(0);
  });

  it('should have apply button', () => {
    renderWithRouter(<Invoices />);

    const applyButtons = screen.queryAllByText('开票申请');
    expect(applyButtons.length).toBeGreaterThan(0);
  });

  it('should have export button', () => {
    renderWithRouter(<Invoices />);

    expect(screen.getByText('导出')).toBeInTheDocument();
  });

  it('should have search input', () => {
    renderWithRouter(<Invoices />);

    const searchInput = screen.getByPlaceholderText(/搜索发票号/);
    expect(searchInput).toBeInTheDocument();
  });

  it('should handle search input change', () => {
    renderWithRouter(<Invoices />);

    const searchInput = screen.getByPlaceholderText(/搜索发票号/);
    fireEvent.change(searchInput, { target: { value: '12345678' } });

    expect(searchInput).toHaveValue('12345678');
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Invoices />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display statistics cards', () => {
    renderWithRouter(<Invoices />);

    // Check for statistics
    const statElements = screen.queryAllByText(/待审核|本月已完成|本月开票金额/);
    expect(statElements.length).toBeGreaterThan(0);
  });
});
