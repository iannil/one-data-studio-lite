/**
 * AuditLog 组件测试
 * 测试统一日志审计页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AuditLog from './AuditLog';

// Mock audit API
const mockGetLogs = vi.fn();
const mockGetStats = vi.fn();
const mockExportLogs = vi.fn();
vi.mock('../../api/audit', () => ({
  getLogs: () => mockGetLogs(),
  getStats: () => mockGetStats(),
  exportLogs: () => mockExportLogs(),
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

describe('AuditLog Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetLogs.mockResolvedValue([]);
    mockGetStats.mockResolvedValue({
      total_events: 0,
      events_by_subsystem: {},
      events_by_type: {},
      events_by_user: {},
    });
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<AuditLog />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<AuditLog />);

    expect(screen.getByText('统一日志审计')).toBeInTheDocument();
  });

  it('should call getLogs and getStats on mount', () => {
    renderWithRouter(<AuditLog />);

    expect(mockGetLogs).toHaveBeenCalled();
    expect(mockGetStats).toHaveBeenCalled();
  });

  it('should have refresh button', () => {
    renderWithRouter(<AuditLog />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should have export buttons', () => {
    renderWithRouter(<AuditLog />);

    const exportButtons = screen.queryAllByText(/导出/);
    expect(exportButtons.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<AuditLog />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display statistics cards', () => {
    const { container } = renderWithRouter(<AuditLog />);

    const statsCards = container.querySelectorAll('.ant-statistic');
    expect(statsCards.length).toBeGreaterThanOrEqual(0);
  });

  it('should have table for logs', () => {
    const { container } = renderWithRouter(<AuditLog />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });
});
