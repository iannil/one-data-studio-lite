/**
 * EtlLink 组件测试
 * 测试 ETL 数据联动页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import EtlLink from './EtlLink';

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

describe('EtlLink Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<EtlLink />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<EtlLink />);

    expect(screen.getByText('ETL 数据联动')).toBeInTheDocument();
  });

  it('should have tabs', () => {
    renderWithRouter(<EtlLink />);

    const tabElements = screen.queryAllByText(/联动规则|联动历史/);
    expect(tabElements.length).toBeGreaterThan(0);
  });

  it('should have add rule button', () => {
    renderWithRouter(<EtlLink />);

    const addButtons = screen.queryAllByText('新建规则');
    expect(addButtons.length).toBeGreaterThan(0);
  });

  it('should have action buttons', () => {
    const { container } = renderWithRouter(<EtlLink />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should display info alert', () => {
    renderWithRouter(<EtlLink />);

    expect(screen.getByText('数据联动说明')).toBeInTheDocument();
  });
});
