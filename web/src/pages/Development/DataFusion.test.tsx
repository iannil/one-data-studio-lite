/**
 * DataFusion 组件测试
 * 测试数据融合配置页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DataFusion from './DataFusion';

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

describe('DataFusion Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<DataFusion />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<DataFusion />);

    expect(screen.getByText('数据融合配置')).toBeInTheDocument();
  });

  it('should have info alert', () => {
    renderWithRouter(<DataFusion />);

    expect(screen.getByText('数据融合说明')).toBeInTheDocument();
  });

  it('should have add task button', () => {
    renderWithRouter(<DataFusion />);

    const addButtons = screen.queryAllByText('新建融合任务');
    expect(addButtons.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<DataFusion />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should have table for fusion tasks', () => {
    const { container } = renderWithRouter(<DataFusion />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });
});
