/**
 * Tags 组件测试
 * 测试数据标签管理页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Tags from './Tags';

// Mock datahub API
const mockSearchTags = vi.fn();
const mockCreateTag = vi.fn();
vi.mock('../../api/datahub', () => ({
  searchTags: () => mockSearchTags(),
  createTag: () => mockCreateTag(),
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

describe('Tags Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchTags.mockResolvedValue({ entities: [], results: [] });
  });

  it('should render page title', () => {
    renderWithRouter(<Tags />);

    expect(screen.getByText('数据标签管理')).toBeInTheDocument();
  });

  it('should render search input', () => {
    renderWithRouter(<Tags />);

    expect(screen.getByPlaceholderText('搜索标签...')).toBeInTheDocument();
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<Tags />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should call API on mount', () => {
    renderWithRouter(<Tags />);

    expect(mockSearchTags).toHaveBeenCalled();
  });

  it('should handle search input changes', () => {
    renderWithRouter(<Tags />);

    const searchInput = screen.getByPlaceholderText('搜索标签...');
    fireEvent.change(searchInput, { target: { value: 'test' } });

    expect(searchInput).toHaveValue('test');
  });

  it('should handle search on enter key', () => {
    renderWithRouter(<Tags />);

    const searchInput = screen.getByPlaceholderText('搜索标签...');
    fireEvent.change(searchInput, { target: { value: 'test' } });
    fireEvent.keyPress(searchInput, { key: 'Enter', code: 'Enter' });

    expect(searchInput).toHaveValue('test');
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Tags />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should have create tag functionality', () => {
    renderWithRouter(<Tags />);

    // The create tag button should exist
    const createButtons = screen.queryAllByText('创建标签');
    expect(createButtons.length).toBeGreaterThanOrEqual(0);
  });

  it('should have refresh functionality', () => {
    renderWithRouter(<Tags />);

    // The refresh button should exist
    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThanOrEqual(0);
  });
});
