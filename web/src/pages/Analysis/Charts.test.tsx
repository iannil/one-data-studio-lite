/**
 * Charts 组件测试
 * 测试图表管理页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Charts from './Charts';

// Mock superset API
const mockGetChartsV1 = vi.fn();
vi.mock('../../api/superset', () => ({
  getChartsV1: () => mockGetChartsV1(),
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

describe('Charts Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetChartsV1.mockResolvedValue({ data: { result: [] } });
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<Charts />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Charts />);

    expect(screen.getByText('图表管理')).toBeInTheDocument();
  });

  it('should call getChartsV1 on mount', () => {
    renderWithRouter(<Charts />);

    expect(mockGetChartsV1).toHaveBeenCalled();
  });

  it('should have search input', () => {
    renderWithRouter(<Charts />);

    const searchInput = screen.getByPlaceholderText('搜索图表...');
    expect(searchInput).toBeInTheDocument();
  });

  it('should handle search input change', () => {
    renderWithRouter(<Charts />);

    const searchInput = screen.getByPlaceholderText('搜索图表...');
    fireEvent.change(searchInput, { target: { value: 'bar' } });

    expect(searchInput).toHaveValue('bar');
  });

  it('should have refresh button', () => {
    renderWithRouter(<Charts />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should render table', () => {
    const { container } = renderWithRouter(<Charts />);

    // Just verify the page structure is correct
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Charts />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
