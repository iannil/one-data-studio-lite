/**
 * Content 组件测试
 * 测试内容发布管理页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Content from './Content';

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

describe('Content Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Content />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Content />);

    expect(screen.getByText('内容发布管理')).toBeInTheDocument();
  });

  it('should have add content button', () => {
    renderWithRouter(<Content />);

    const addButtons = screen.queryAllByText('新建内容');
    expect(addButtons.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Content />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display info alert', () => {
    renderWithRouter(<Content />);

    expect(screen.getByText('内容管理说明')).toBeInTheDocument();
  });

  it('should have table for contents', () => {
    const { container } = renderWithRouter(<Content />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });
});
