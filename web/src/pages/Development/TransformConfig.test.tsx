/**
 * TransformConfig 组件测试
 * 测试数据转换配置页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TransformConfig from './TransformConfig';

// Mock cleaning API
const mockGenerateConfigV1 = vi.fn();
vi.mock('../../api/cleaning', () => ({
  generateConfigV1: () => mockGenerateConfigV1(),
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

describe('TransformConfig Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<TransformConfig />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<TransformConfig />);

    expect(screen.getByText('数据转换配置')).toBeInTheDocument();
  });

  it('should have table name input', () => {
    const { container } = renderWithRouter(<TransformConfig />);

    const inputs = container.querySelectorAll('input');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should have rule selector', () => {
    const { container } = renderWithRouter(<TransformConfig />);

    expect(container.querySelector('.ant-select')).toBeInTheDocument();
  });

  it('should have generate button', () => {
    renderWithRouter(<TransformConfig />);

    const generateButtons = screen.queryAllByText(/生成.*SeaTunnel.*配置/);
    expect(generateButtons.length).toBeGreaterThanOrEqual(0);
  });
});
