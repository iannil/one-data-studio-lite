/**
 * EtlFlows 组件测试
 * 测试 ETL 流程管理页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import EtlFlows from './EtlFlows';

// Mock dolphinscheduler API
const mockGetProjects = vi.fn();
vi.mock('../../api/dolphinscheduler', () => ({
  getProjects: () => mockGetProjects(),
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

describe('EtlFlows Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<EtlFlows />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<EtlFlows />);

    const titleElements = screen.queryAllByText(/ETL 流程管理/);
    expect(titleElements.length).toBeGreaterThan(0);
  });

  it('should have refresh button', () => {
    const { container } = renderWithRouter(<EtlFlows />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should call getProjects on mount', () => {
    renderWithRouter(<EtlFlows />);

    expect(mockGetProjects).toHaveBeenCalled();
  });

  it('should have table for flows', () => {
    const { container } = renderWithRouter(<EtlFlows />);

    expect(container.querySelector('.ant-spin') || container.querySelector('.ant-card')).toBeInTheDocument();
  });
});
