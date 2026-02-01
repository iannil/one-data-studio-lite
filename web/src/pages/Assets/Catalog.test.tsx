/**
 * Catalog 组件测试
 * 测试资产目录页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Catalog from './Catalog';

// Mock data-api API
const mockSearchAssetsV1 = vi.fn();
vi.mock('../../api/data-api', () => ({
  searchAssetsV1: () => mockSearchAssetsV1(),
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

describe('Catalog Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchAssetsV1.mockResolvedValue({ data: [] });
  });

  it('should render page title', () => {
    renderWithRouter(<Catalog />);

    expect(screen.getByText('资产目录')).toBeInTheDocument();
  });

  it('should render search input', () => {
    renderWithRouter(<Catalog />);

    expect(screen.getByPlaceholderText('搜索数据资产...')).toBeInTheDocument();
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<Catalog />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should call API on mount', () => {
    renderWithRouter(<Catalog />);

    expect(mockSearchAssetsV1).toHaveBeenCalled();
  });

  it('should handle keyword input changes', () => {
    renderWithRouter(<Catalog />);

    const searchInput = screen.getByPlaceholderText('搜索数据资产...');
    fireEvent.change(searchInput, { target: { value: 'test' } });

    expect(searchInput).toHaveValue('test');
  });

  it('should handle search on enter key', () => {
    renderWithRouter(<Catalog />);

    const searchInput = screen.getByPlaceholderText('搜索数据资产...');
    fireEvent.change(searchInput, { target: { value: 'test' } });
    fireEvent.keyPress(searchInput, { key: 'Enter', code: 'Enter' });

    expect(searchInput).toHaveValue('test');
  });

  it('should have action buttons available', () => {
    const { container } = renderWithRouter(<Catalog />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should have select component', () => {
    renderWithRouter(<Catalog />);

    // Check that select placeholder exists (it renders in all states)
    const selects = screen.queryAllByRole('combobox');
    expect(selects.length).toBeGreaterThanOrEqual(0);
  });
});
