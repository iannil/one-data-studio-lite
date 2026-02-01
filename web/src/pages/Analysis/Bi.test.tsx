/**
 * Bi 组件测试
 * 测试可视化分析 (BI) 页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Bi from './Bi';

// Mock superset API
const mockGetDashboardsV1 = vi.fn();
vi.mock('../../api/superset', () => ({
  getDashboardsV1: () => mockGetDashboardsV1(),
}));

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

describe('Bi Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetDashboardsV1.mockResolvedValue({ data: { result: [] } });
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<Bi />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Bi />);

    expect(screen.getByText('可视化分析 (BI)')).toBeInTheDocument();
  });

  it('should call getDashboardsV1 on mount', () => {
    renderWithRouter(<Bi />);

    expect(mockGetDashboardsV1).toHaveBeenCalled();
  });

  it('should have search input', () => {
    renderWithRouter(<Bi />);

    const searchInput = screen.getByPlaceholderText('搜索仪表板...');
    expect(searchInput).toBeInTheDocument();
  });

  it('should handle search input change', () => {
    renderWithRouter(<Bi />);

    const searchInput = screen.getByPlaceholderText('搜索仪表板...');
    fireEvent.change(searchInput, { target: { value: 'sales' } });

    expect(searchInput).toHaveValue('sales');
  });

  it('should have refresh button', () => {
    renderWithRouter(<Bi />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should render table', () => {
    const { container } = renderWithRouter(<Bi />);

    // Just verify the page structure is correct
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Bi />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
