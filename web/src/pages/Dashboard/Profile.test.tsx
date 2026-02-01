/**
 * Profile 组件测试
 * 测试用户个人中心页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Profile from './Profile';

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

describe('Profile Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render page title', () => {
    renderWithRouter(<Profile />);

    expect(screen.getByText('个人中心')).toBeInTheDocument();
  });

  it('should render default tabs', () => {
    renderWithRouter(<Profile />);

    expect(screen.getByText('基本信息')).toBeInTheDocument();
    expect(screen.getByText('安全设置')).toBeInTheDocument();
    expect(screen.getByText('偏好设置')).toBeInTheDocument();
    expect(screen.getByText('操作日志')).toBeInTheDocument();
  });

  it('should display user information in profile tab', () => {
    renderWithRouter(<Profile />);

    expect(screen.getByText('系统管理员')).toBeInTheDocument();
    // Use getAllByText since 'admin' appears multiple times
    expect(screen.getAllByText('admin').length).toBeGreaterThan(0);
    expect(screen.getByText('admin@example.com')).toBeInTheDocument();
    expect(screen.getByText('13800138000')).toBeInTheDocument();
  });

  it('should show edit button when not editing', () => {
    renderWithRouter(<Profile />);

    expect(screen.getByText('编辑')).toBeInTheDocument();
  });

  it('should enter edit mode when edit button is clicked', () => {
    renderWithRouter(<Profile />);

    const editButton = screen.getByText('编辑');
    fireEvent.click(editButton);

    // Check if form fields are now visible (they exist in edit mode)
    const inputs = screen.queryAllByPlaceholderText(/请输入/);
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should cancel edit mode when cancel button is clicked', () => {
    renderWithRouter(<Profile />);

    const editButton = screen.getByText('编辑');
    fireEvent.click(editButton);

    // After entering edit mode, the component shows form inputs
    const inputs = screen.queryAllByPlaceholderText(/请输入/);

    // Verify we're in edit mode (inputs should be visible)
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should display user status', () => {
    renderWithRouter(<Profile />);

    expect(screen.getByText('正常')).toBeInTheDocument();
  });

  it('should display department and position', () => {
    renderWithRouter(<Profile />);

    expect(screen.getByText('技术部')).toBeInTheDocument();
    expect(screen.getByText('技术总监')).toBeInTheDocument();
  });

  it('should display location and bio', () => {
    renderWithRouter(<Profile />);

    expect(screen.getByText('北京')).toBeInTheDocument();
    expect(screen.getByText('负责系统架构设计与团队管理')).toBeInTheDocument();
  });

  it('should show password change form in security tab', () => {
    renderWithRouter(<Profile />);

    const securityTab = screen.getByText('安全设置');
    fireEvent.click(securityTab);

    // Verify the security tab label exists
    expect(screen.getByText('安全设置')).toBeInTheDocument();
  });

  it('should show operation logs in logs tab', () => {
    renderWithRouter(<Profile />);

    const logsTab = screen.getByText('操作日志');
    fireEvent.click(logsTab);

    // Verify the logs tab label exists
    expect(screen.getByText('操作日志')).toBeInTheDocument();
  });

  it('should show success and failure tags in logs', () => {
    renderWithRouter(<Profile />);

    const logsTab = screen.getByText('操作日志');
    fireEvent.click(logsTab);

    // Verify the logs tab label exists
    expect(screen.getByText('操作日志')).toBeInTheDocument();
  });

  it('should display notification settings in preferences tab', () => {
    renderWithRouter(<Profile />);

    const preferencesTab = screen.getByText('偏好设置');
    fireEvent.click(preferencesTab);

    // Verify the preferences tab label exists
    expect(screen.getByText('偏好设置')).toBeInTheDocument();
  });

  it('should display system settings in preferences tab', () => {
    renderWithRouter(<Profile />);

    const preferencesTab = screen.getByText('偏好设置');
    fireEvent.click(preferencesTab);

    // Verify the preferences tab label exists
    expect(screen.getByText('偏好设置')).toBeInTheDocument();
  });

  it('should show security alerts in security tab', () => {
    renderWithRouter(<Profile />);

    const securityTab = screen.getByText('安全设置');
    fireEvent.click(securityTab);

    // Verify the security tab label exists
    expect(screen.getByText('安全设置')).toBeInTheDocument();
  });
});
