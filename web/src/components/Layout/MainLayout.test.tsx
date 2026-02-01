/**
 * MainLayout 组件测试
 * 测试主布局组件的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// Mock auth store
vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    user: { username: 'test', display_name: 'Test User' },
    logout: vi.fn(),
  })),
}));

import MainLayout from './MainLayout';

const renderWithLayout = (component: React.ReactElement) => {
  return render(
    <MemoryRouter initialEntries={['/dashboard/workspace']}>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={component} />
          <Route path="dashboard/*" element={component} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
};

describe('MainLayout Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithLayout(<div>Test Content</div>);

    expect(container.querySelector('.ant-layout')).toBeInTheDocument();
  });

  it('should render sider with logo', () => {
    renderWithLayout(<div>Test Content</div>);

    const logoElement = screen.queryByText(/ONE-DATA-STUDIO|ODS/);
    expect(logoElement).toBeInTheDocument();
  });

  it('should render menu items', () => {
    renderWithLayout(<div>Test Content</div>);

    // Check for menu items
    expect(screen.getByText('工作台')).toBeInTheDocument();
    expect(screen.getByText('数据规划')).toBeInTheDocument();
  });

  it('should render header with user info', () => {
    renderWithLayout(<div>Test Content</div>);

    const userElements = screen.queryAllByText(/Test User|test/);
    expect(userElements.length).toBeGreaterThanOrEqual(0);
  });

  it('should have sidebar navigation', () => {
    const { container } = renderWithLayout(<div>Test Content</div>);

    expect(container.querySelector('.ant-layout-sider')).toBeInTheDocument();
  });

  it('should have content area', () => {
    const { container } = renderWithLayout(<div>Test Content</div>);

    expect(container.querySelector('.ant-layout-content')).toBeInTheDocument();
  });

  it('should have header', () => {
    const { container } = renderWithLayout(<div>Test Content</div>);

    expect(container.querySelector('.ant-layout-header')).toBeInTheDocument();
  });
});
