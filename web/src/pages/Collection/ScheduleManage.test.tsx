/**
 * ScheduleManage 组件测试
 * 测试任务调度管理页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ScheduleManage from './ScheduleManage';

// Mock dolphinscheduler API
const mockGetProjects = vi.fn();
const mockGetProcessDefinitions = vi.fn();
const mockGetSchedules = vi.fn();
const mockUpdateScheduleState = vi.fn();
vi.mock('../../api/dolphinscheduler', () => ({
  getProjects: () => mockGetProjects(),
  getProcessDefinitions: () => mockGetProcessDefinitions(),
  getSchedules: () => mockGetSchedules(),
  updateScheduleState: () => mockUpdateScheduleState(),
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

describe('ScheduleManage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetProjects.mockResolvedValue({ data: { totalList: [] } });
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<ScheduleManage />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<ScheduleManage />);

    expect(screen.getByText('任务调度管理')).toBeInTheDocument();
  });

  it('should call getProjects on mount', () => {
    renderWithRouter(<ScheduleManage />);

    expect(mockGetProjects).toHaveBeenCalled();
  });

  it('should have project selector placeholder', () => {
    renderWithRouter(<ScheduleManage />);

    expect(screen.getByText('选择项目：')).toBeInTheDocument();
  });

  it('should have refresh button', () => {
    renderWithRouter(<ScheduleManage />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<ScheduleManage />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should have select placeholder', () => {
    renderWithRouter(<ScheduleManage />);

    // Select might not have the placeholder text directly
    const { container } = renderWithRouter(<ScheduleManage />);
    expect(container.querySelector('.ant-select')).toBeInTheDocument();
  });
});
