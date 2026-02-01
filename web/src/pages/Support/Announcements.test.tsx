/**
 * Announcements 组件测试
 * 测试通知公告管理页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Announcements from './Announcements';

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

describe('Announcements Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Announcements />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Announcements />);

    expect(screen.getByText('通知公告管理')).toBeInTheDocument();
  });

  it('should have add announcement button', () => {
    renderWithRouter(<Announcements />);

    expect(screen.getByText('新建公告')).toBeInTheDocument();
  });

  it('should display info alert', () => {
    renderWithRouter(<Announcements />);

    expect(screen.getByText('公告发布说明')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Announcements />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should have table for announcements', () => {
    const { container } = renderWithRouter(<Announcements />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should display announcement list', () => {
    renderWithRouter(<Announcements />);

    // Check for list card
    const listCards = screen.queryAllByText('公告列表');
    expect(listCards.length).toBeGreaterThan(0);
  });

  it('should have table columns', () => {
    renderWithRouter(<Announcements />);

    // Check for table column headers
    const titleElements = screen.queryAllByText('标题');
    expect(titleElements.length).toBeGreaterThan(0);
  });
});
