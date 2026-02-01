/**
 * Search 组件测试
 * 测试资产搜索页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Search from './Search';

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
  return {
    ...render(<MemoryRouter>{component}</MemoryRouter>),
  };
};

describe('Search Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render search page with title', () => {
    renderWithRouter(<Search />);

    expect(screen.getByText(/资产检索/)).toBeInTheDocument();
  });

  it('should render search input', () => {
    renderWithRouter(<Search />);

    const searchInput = screen.getByPlaceholderText('搜索资产名称、描述、标签...');
    expect(searchInput).toBeInTheDocument();
  });

  it('should render info alert', () => {
    renderWithRouter(<Search />);

    expect(screen.getByText(/全文搜索/)).toBeInTheDocument();
    expect(screen.getByText(/支持按资产名称、描述、标签、数据源类型进行检索/)).toBeInTheDocument();
  });

  it('should render all demo assets initially', () => {
    renderWithRouter(<Search />);

    expect(screen.getByText('user_info')).toBeInTheDocument();
    expect(screen.getByText('order_summary')).toBeInTheDocument();
    expect(screen.getByText('user_events_stream')).toBeInTheDocument();
    expect(screen.getByText('sales_dashboard')).toBeInTheDocument();
    expect(screen.getByText('data_quality_pipeline')).toBeInTheDocument();
    expect(screen.getByText('user_profile_api')).toBeInTheDocument();
  });

  it('should filter assets by search text', async () => {
    renderWithRouter(<Search />);

    const searchInput = screen.getByPlaceholderText('搜索资产名称、描述、标签...');

    fireEvent.change(searchInput, { target: { value: 'user' } });

    await waitFor(() => {
      expect(screen.getByText('user_info')).toBeInTheDocument();
      expect(screen.getByText('user_events_stream')).toBeInTheDocument();
      expect(screen.getByText('user_profile_api')).toBeInTheDocument();
    });
  });

  it('should filter assets by search text in description', async () => {
    renderWithRouter(<Search />);

    const searchInput = screen.getByPlaceholderText('搜索资产名称、描述、标签...');

    fireEvent.change(searchInput, { target: { value: '订单' } });

    await waitFor(() => {
      expect(screen.getByText('order_summary')).toBeInTheDocument();
    });
  });

  it('should show advanced filter button', () => {
    renderWithRouter(<Search />);

    expect(screen.getByText(/高级筛选/)).toBeInTheDocument();
  });

  it('should toggle advanced filter panel', async () => {
    renderWithRouter(<Search />);

    // Get the button containing "高级筛选"
    const filterButton = screen.getByText(/高级筛选/);

    // Initially should show "展开" (filterVisible is false by default)
    expect(screen.getByText(/高级筛选.*展开/)).toBeInTheDocument();

    fireEvent.click(filterButton);

    // After clicking, the button text should show "收起"
    await waitFor(() => {
      expect(screen.getByText(/高级筛选.*收起/)).toBeInTheDocument();
    });
  });

  it('should show popular tags', () => {
    renderWithRouter(<Search />);

    expect(screen.getByText('热门标签：')).toBeInTheDocument();
    // Use getAllByText since '用户' appears in both popular tags and demo data
    expect(screen.getAllByText('用户').length).toBeGreaterThan(0);
    expect(screen.getAllByText('订单').length).toBeGreaterThan(0);
    expect(screen.getAllByText('产品').length).toBeGreaterThan(0);
    expect(screen.getAllByText('销售').length).toBeGreaterThan(0);
  });

  it('should filter by tag when clicking popular tag', async () => {
    renderWithRouter(<Search />);

    // Get all elements with text '用户' and find the clickable tag
    const userTags = screen.getAllByText('用户');
    // Find the one that is a tag (checkable tag)
    const userTag = userTags.find(tag => tag.closest('.ant-tag-checkable'));

    if (userTag) {
      fireEvent.click(userTag);

      await waitFor(() => {
        expect(screen.getByText('已选：')).toBeInTheDocument();
      });
    }
  });

  it('should show asset count in results', () => {
    renderWithRouter(<Search />);

    expect(screen.getByText(/搜索结果 \(6\)/)).toBeInTheDocument();
  });

  it('should update search results count when filtering', async () => {
    renderWithRouter(<Search />);

    const searchInput = screen.getByPlaceholderText('搜索资产名称、描述、标签...');

    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    await waitFor(() => {
      expect(screen.getByText(/搜索结果 \(0\)/)).toBeInTheDocument();
    });
  });

  it('should clear search when input is cleared', async () => {
    renderWithRouter(<Search />);

    const searchInput = screen.getByPlaceholderText('搜索资产名称、描述、标签...') as HTMLInputElement;

    fireEvent.change(searchInput, { target: { value: 'test' } });

    await waitFor(() => {
      expect(searchInput.value).toBe('test');
    });

    fireEvent.change(searchInput, { target: { value: '' } });

    await waitFor(() => {
      expect(searchInput.value).toBe('');
    });
  });
});
