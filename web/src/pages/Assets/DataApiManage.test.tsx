/**
 * DataApiManage 组件测试
 * 测试数据API管理页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DataApiManage from './DataApiManage';

// Mock data-api API
const mockGetDatasetSchemaV1 = vi.fn();
const mockQueryDatasetV1 = vi.fn();
const mockSubscribeDatasetV1 = vi.fn();
vi.mock('../../api/data-api', () => ({
  getDatasetSchemaV1: () => mockGetDatasetSchemaV1(),
  queryDatasetV1: () => mockQueryDatasetV1(),
  subscribeDatasetV1: () => mockSubscribeDatasetV1(),
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

describe('DataApiManage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<DataApiManage />);

    expect(container.querySelector('[data-testid="data-api-page"]')).toBeInTheDocument();
  });

  it('should render dataset input', () => {
    renderWithRouter(<DataApiManage />);

    expect(screen.getByPlaceholderText('数据集 ID')).toBeInTheDocument();
  });

  it('should handle dataset input changes', () => {
    renderWithRouter(<DataApiManage />);

    const input = screen.getByPlaceholderText('数据集 ID');
    fireEvent.change(input, { target: { value: 'test-dataset' } });

    expect(input).toHaveValue('test-dataset');
  });

  it('should have fetch schema button', () => {
    renderWithRouter(<DataApiManage />);

    expect(screen.getByText('获取 Schema')).toBeInTheDocument();
  });

  it('should have subscribe button', () => {
    renderWithRouter(<DataApiManage />);

    // Check for subscribe button using testid
    const subscribeButton = screen.queryByTestId('subscribe-button');
    expect(subscribeButton).toBeInTheDocument();
  });

  it('should render tabs', () => {
    renderWithRouter(<DataApiManage />);

    expect(screen.getByText('Schema')).toBeInTheDocument();
    expect(screen.getByText('查询测试')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<DataApiManage />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should render page title', () => {
    renderWithRouter(<DataApiManage />);

    expect(screen.getByText('数据 API 管理')).toBeInTheDocument();
  });
});
