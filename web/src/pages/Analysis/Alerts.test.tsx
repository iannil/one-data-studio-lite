/**
 * Alerts 组件测试
 * 测试智能预警配置页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Alerts from './Alerts';

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

describe('Alerts Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<Alerts />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<Alerts />);

    expect(screen.getByText('智能预警配置')).toBeInTheDocument();
  });

  it('should have tabs', () => {
    renderWithRouter(<Alerts />);

    const tabElements = screen.queryAllByText(/预警规则|告警历史/);
    expect(tabElements.length).toBeGreaterThan(0);
  });

  it('should have add rule button', () => {
    renderWithRouter(<Alerts />);

    const addButtons = screen.queryAllByText('新建规则');
    expect(addButtons.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<Alerts />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display info alert', () => {
    renderWithRouter(<Alerts />);

    expect(screen.getByText('预警配置说明')).toBeInTheDocument();
  });
});
