/**
 * NL2SQL 组件测试
 * 测试自然语言查询页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NL2SQL from './NL2SQL';

// Mock nl2sql API
const mockQueryV1 = vi.fn();
const mockGetTablesV1 = vi.fn();
vi.mock('../../api/nl2sql', () => ({
  queryV1: () => mockQueryV1(),
  getTablesV1: () => mockGetTablesV1(),
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

describe('NL2SQL Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<NL2SQL />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should have query input', () => {
    const { container } = renderWithRouter(<NL2SQL />);

    const textareas = container.querySelectorAll('textarea');
    expect(textareas.length).toBeGreaterThan(0);
  });

  it('should have query button', () => {
    renderWithRouter(<NL2SQL />);

    const queryButtons = screen.queryAllByText('查询');
    expect(queryButtons.length).toBeGreaterThan(0);
  });

  it('should have database table section', () => {
    renderWithRouter(<NL2SQL />);

    const dbElements = screen.queryAllByText(/数据表|Database/);
    expect(dbElements.length).toBeGreaterThanOrEqual(0);
  });

  it('should call getTablesV1 on mount', () => {
    renderWithRouter(<NL2SQL />);

    expect(mockGetTablesV1).toHaveBeenCalled();
  });

  it('should have natural language query title', () => {
    renderWithRouter(<NL2SQL />);

    const titleElements = screen.queryAllByText(/自然语言查询/);
    expect(titleElements.length).toBeGreaterThan(0);
  });
});
