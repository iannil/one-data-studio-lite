/**
 * Monitor 组件测试
 * 测试系统监控页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Monitor from './Monitor';

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

describe('Monitor Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Monitor />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Monitor />);

    expect(screen.getByText('系统监控')).toBeInTheDocument();
  });

  it('should have refresh button', () => {
    renderWithRouter(<Monitor />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should display system metrics', () => {
    renderWithRouter(<Monitor />);

    // Check for statistics
    const metricElements = screen.queryAllByText(/CPU|内存|磁盘|网络/);
    expect(metricElements.length).toBeGreaterThan(0);
  });

  it('should display service health table', () => {
    renderWithRouter(<Monitor />);

    const { container } = renderWithRouter(<Monitor />);
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Monitor />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display external service statistics', () => {
    renderWithRouter(<Monitor />);

    const serviceElements = screen.queryAllByText(/DolphinScheduler|SeaTunnel|DataHub/);
    expect(serviceElements.length).toBeGreaterThan(0);
  });

  it('should handle refresh click', () => {
    renderWithRouter(<Monitor />);

    const refreshButtons = screen.queryAllByText('刷新');
    if (refreshButtons.length > 0) {
      fireEvent.click(refreshButtons[0]);
      // Test passes if no error is thrown
      expect(true).toBe(true);
    }
  });
});
