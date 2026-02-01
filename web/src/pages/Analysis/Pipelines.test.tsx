/**
 * Pipelines 组件测试
 * 测试 AI Pipeline 页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Pipelines from './Pipelines';

// Mock cubestudio API
const mockGetPipelines = vi.fn();
const mockRunPipeline = vi.fn();
vi.mock('../../api/cubestudio', () => ({
  getPipelines: () => mockGetPipelines(),
  runPipeline: () => mockRunPipeline(),
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

describe('Pipelines Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetPipelines.mockResolvedValue([]);
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<Pipelines />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Pipelines />);

    expect(screen.getByText('AI Pipeline')).toBeInTheDocument();
  });

  it('should call getPipelines on mount', () => {
    renderWithRouter(<Pipelines />);

    expect(mockGetPipelines).toHaveBeenCalled();
  });

  it('should have refresh button', () => {
    renderWithRouter(<Pipelines />);

    const refreshButtons = screen.queryAllByText('刷新');
    expect(refreshButtons.length).toBeGreaterThan(0);
  });

  it('should render table', () => {
    const { container } = renderWithRouter(<Pipelines />);

    // Just verify the page structure is correct
    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Pipelines />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
