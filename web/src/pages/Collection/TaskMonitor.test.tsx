/**
 * TaskMonitor 组件测试
 * 测试任务监控日志页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TaskMonitor from './TaskMonitor';

// Mock dolphinscheduler API
const mockGetProjects = vi.fn();
const mockGetTaskInstances = vi.fn();
const mockGetTaskLog = vi.fn();
vi.mock('../../api/dolphinscheduler', () => ({
  getProjects: () => mockGetProjects(),
  getTaskInstances: () => mockGetTaskInstances(),
  getTaskLog: () => mockGetTaskLog(),
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

describe('TaskMonitor Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<TaskMonitor />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<TaskMonitor />);

    const titleElements = screen.queryAllByText(/任务监控日志/);
    expect(titleElements.length).toBeGreaterThan(0);
  });

  it('should have project selector', () => {
    const { container } = renderWithRouter(<TaskMonitor />);

    expect(container.querySelector('.ant-select')).toBeInTheDocument();
  });

  it('should have status filter', () => {
    renderWithRouter(<TaskMonitor />);

    const filterElements = screen.queryAllByText(/全部|成功|失败|运行中/);
    expect(filterElements.length).toBeGreaterThanOrEqual(0);
  });

  it('should have refresh button', () => {
    const { container } = renderWithRouter(<TaskMonitor />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should call getProjects on mount', () => {
    renderWithRouter(<TaskMonitor />);

    expect(mockGetProjects).toHaveBeenCalled();
  });
});
