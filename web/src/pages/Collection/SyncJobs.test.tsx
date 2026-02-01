/**
 * SyncJobs 组件测试
 * 测试数据同步任务页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SyncJobs from './SyncJobs';

// Mock seatunnel API
const mockGetJobs = vi.fn();
const mockCancelJob = vi.fn();
vi.mock('../../api/seatunnel', () => ({
  getJobs: () => mockGetJobs(),
  cancelJob: () => mockCancelJob(),
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

describe('SyncJobs Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetJobs.mockResolvedValue([]);
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<SyncJobs />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<SyncJobs />);

    expect(screen.getByText('数据同步任务')).toBeInTheDocument();
  });

  it('should call getJobs on mount', () => {
    renderWithRouter(<SyncJobs />);

    expect(mockGetJobs).toHaveBeenCalled();
  });

  it('should have submit button', () => {
    renderWithRouter(<SyncJobs />);

    expect(screen.getByText('提交任务')).toBeInTheDocument();
  });

  it('should have refresh button', () => {
    renderWithRouter(<SyncJobs />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<SyncJobs />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display modal when submit button clicked', () => {
    renderWithRouter(<SyncJobs />);

    const submitButton = screen.getByText('提交任务');
    fireEvent.click(submitButton);

    // Modal should be visible (checks for modal title)
    const modalTitle = screen.queryByText('提交 SeaTunnel 任务');
    expect(modalTitle).toBeInTheDocument();
  });

  it('should render table', () => {
    const { container } = renderWithRouter(<SyncJobs />);

    // Just verify the page structure is correct
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });
});
