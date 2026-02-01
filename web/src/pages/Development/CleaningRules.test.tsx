/**
 * CleaningRules 组件测试
 * 测试清洗规则配置页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CleaningRules from './CleaningRules';

// Mock cleaning API
const mockRecommendRulesV1 = vi.fn();
const mockGetCleaningRulesV1 = vi.fn();
vi.mock('../../api/cleaning', () => ({
  recommendRulesV1: () => mockRecommendRulesV1(),
  getCleaningRulesV1: () => mockGetCleaningRulesV1(),
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

describe('CleaningRules Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<CleaningRules />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<CleaningRules />);

    expect(screen.getByText('清洗规则配置')).toBeInTheDocument();
  });

  it('should have tabs', () => {
    renderWithRouter(<CleaningRules />);

    const tabElements = screen.queryAllByText(/AI 推荐|规则模板/);
    expect(tabElements.length).toBeGreaterThan(0);
  });

  it('should have table name input', () => {
    const { container } = renderWithRouter(<CleaningRules />);

    const inputs = container.querySelectorAll('input');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should have AI recommend button', () => {
    renderWithRouter(<CleaningRules />);

    const recommendButtons = screen.queryAllByText('AI 推荐');
    expect(recommendButtons.length).toBeGreaterThan(0);
  });

  it('should call getCleaningRulesV1 on mount', () => {
    renderWithRouter(<CleaningRules />);

    expect(mockGetCleaningRulesV1).toHaveBeenCalled();
  });
});
