/**
 * Standards 组件测试
 * 测试数据标准管理页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Standards from './Standards';

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

describe('Standards Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<Standards />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Standards />);

    expect(screen.getByText('数据标准管理')).toBeInTheDocument();
  });

  it('should render tabs', () => {
    renderWithRouter(<Standards />);

    // Use queryAllByText since tabs may render multiple elements
    const tabElements = screen.queryAllByText(/标准列表|校验规则|标准模板/);
    expect(tabElements.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Standards />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should have search input', () => {
    renderWithRouter(<Standards />);

    const searchInput = screen.getByPlaceholderText(/搜索标准名称/);
    expect(searchInput).toBeInTheDocument();
  });

  it('should handle search input change', () => {
    renderWithRouter(<Standards />);

    const searchInput = screen.getByPlaceholderText(/搜索标准名称/);
    fireEvent.change(searchInput, { target: { value: 'naming' } });

    expect(searchInput).toHaveValue('naming');
  });

  it('should display info alert', () => {
    renderWithRouter(<Standards />);

    expect(screen.getByText('数据标准管理说明')).toBeInTheDocument();
  });

  it('should have table with columns', () => {
    renderWithRouter(<Standards />);

    // Check for table columns using queryAllByText
    const codeElements = screen.queryAllByText('编码');
    expect(codeElements.length).toBeGreaterThan(0);
  });

  it('should have add standard button', () => {
    renderWithRouter(<Standards />);

    // Check for the button text
    const addButtons = screen.queryAllByText('新建标准');
    expect(addButtons.length).toBeGreaterThan(0);
  });
});
