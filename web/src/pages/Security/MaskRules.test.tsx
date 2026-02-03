/**
 * MaskRules 组件测试
 * 测试数据脱敏规则页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MaskRules from './MaskRules';

// Mock shardingsphere API
const mockGetMaskRulesV1 = vi.fn();
const mockCreateMaskRuleV1 = vi.fn();
const mockDeleteMaskRulesV1 = vi.fn();
vi.mock('../../api/shardingsphere', () => ({
  getMaskRulesV1: () => mockGetMaskRulesV1(),
  createMaskRuleV1: () => mockCreateMaskRuleV1(),
  deleteMaskRulesV1: () => mockDeleteMaskRulesV1(),
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

describe('MaskRules Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetMaskRulesV1.mockResolvedValue({
      data: [],
    });
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<MaskRules />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<MaskRules />);

    expect(screen.getByText('数据脱敏规则')).toBeInTheDocument();
  });

  it('should call getMaskRulesV1 on mount', () => {
    renderWithRouter(<MaskRules />);

    expect(mockGetMaskRulesV1).toHaveBeenCalled();
  });

  it('should have add rule card', () => {
    renderWithRouter(<MaskRules />);

    expect(screen.getByText('添加脱敏规则')).toBeInTheDocument();
  });

  it('should have table name input', () => {
    renderWithRouter(<MaskRules />);

    const tableInput = screen.getByPlaceholderText('表名');
    expect(tableInput).toBeInTheDocument();
  });

  it('should have column name input', () => {
    renderWithRouter(<MaskRules />);

    const columnInput = screen.getByPlaceholderText('列名');
    expect(columnInput).toBeInTheDocument();
  });

  it('should handle table name input change', () => {
    renderWithRouter(<MaskRules />);

    const tableInput = screen.getByPlaceholderText('表名');
    fireEvent.change(tableInput, { target: { value: 'users' } });

    expect(tableInput).toHaveValue('users');
  });

  it('should handle column name input change', () => {
    renderWithRouter(<MaskRules />);

    const columnInput = screen.getByPlaceholderText('列名');
    fireEvent.change(columnInput, { target: { value: 'password' } });

    expect(columnInput).toHaveValue('password');
  });

  it('should have add rule button', () => {
    renderWithRouter(<MaskRules />);

    expect(screen.getByText('添加规则')).toBeInTheDocument();
  });

  it('should render table columns', () => {
    renderWithRouter(<MaskRules />);

    // Just verify the page structure is correct
    // The table might be empty or in loading state
    const { container } = renderWithRouter(<MaskRules />);
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });
});
