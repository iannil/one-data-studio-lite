/**
 * FillMissing 组件测试
 * 测试缺失值填充页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FillMissing from './FillMissing';

// Mock cleaning API
const mockAnalyzeQualityV1 = vi.fn();
vi.mock('../../api/cleaning', () => ({
  analyzeQualityV1: () => mockAnalyzeQualityV1(),
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

describe('FillMissing Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<FillMissing />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<FillMissing />);

    expect(screen.getByText('缺失值填充')).toBeInTheDocument();
  });

  it('should have table name input', () => {
    const { container } = renderWithRouter(<FillMissing />);

    const inputs = container.querySelectorAll('input');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should have analyze button', () => {
    renderWithRouter(<FillMissing />);

    const analyzeButtons = screen.queryAllByText('分析缺失值');
    expect(analyzeButtons.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<FillMissing />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
