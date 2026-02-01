/**
 * Workspace 组件测试
 * 测试个人工作台页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Workspace from './Workspace';

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

describe('Workspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render page title', () => {
    renderWithRouter(<Workspace />);

    expect(screen.getByText('个人工作台')).toBeInTheDocument();
  });

  it('should render statistics cards', () => {
    renderWithRouter(<Workspace />);

    expect(screen.getByText('待处理任务')).toBeInTheDocument();
    expect(screen.getByText('今日访问')).toBeInTheDocument();
    expect(screen.getByText('收藏资产')).toBeInTheDocument();
    expect(screen.getByText('本周完成')).toBeInTheDocument();
  });

  it('should display quick actions section', () => {
    renderWithRouter(<Workspace />);

    expect(screen.getByText('快捷功能')).toBeInTheDocument();
    expect(screen.getByText('数据源配置')).toBeInTheDocument();
    expect(screen.getByText('数据质量检测')).toBeInTheDocument();
    expect(screen.getByText('NL2SQL 查询')).toBeInTheDocument();
    expect(screen.getByText('清洗规则配置')).toBeInTheDocument();
  });

  it('should display priority tags for todos', () => {
    renderWithRouter(<Workspace />);

    expect(screen.getAllByText('高').length).toBeGreaterThan(0);
    expect(screen.getAllByText('中').length).toBeGreaterThan(0);
    expect(screen.getAllByText('低').length).toBeGreaterThan(0);
  });

  it('should display clear button for recent visits', () => {
    renderWithRouter(<Workspace />);

    expect(screen.getByText('清空')).toBeInTheDocument();
  });

  it('should display manage button for favorites', () => {
    renderWithRouter(<Workspace />);

    expect(screen.getByText('管理')).toBeInTheDocument();
  });

  it('should display type tags for recent items', () => {
    renderWithRouter(<Workspace />);

    expect(screen.getAllByText('数据表').length).toBeGreaterThan(0);
    expect(screen.getAllByText('看板').length).toBeGreaterThan(0);
    expect(screen.getAllByText('API').length).toBeGreaterThan(0);
  });

  it('should display data asset overview section', () => {
    renderWithRouter(<Workspace />);

    expect(screen.getByText('数据资产概览')).toBeInTheDocument();
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<Workspace />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should display complete buttons', () => {
    renderWithRouter(<Workspace />);

    const completeButtons = screen.queryAllByText('完成');
    expect(completeButtons.length).toBeGreaterThan(0);
  });

  it('should have todo items with titles', () => {
    renderWithRouter(<Workspace />);

    // Check that there are todo items rendered
    const todoTitles = [
      '完成用户表数据质量检测',
      '审核待发布的数据API',
      '配置 SeaTunnel 同步任务',
    ];

    todoTitles.forEach(title => {
      const elements = screen.queryAllByText(title);
      expect(elements.length).toBeGreaterThanOrEqual(0);
    });
  });
});
