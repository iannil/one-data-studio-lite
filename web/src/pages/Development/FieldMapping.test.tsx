/**
 * FieldMapping 组件测试
 * 测试字段映射管理页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FieldMapping from './FieldMapping';

// Mock metadata-sync API
const mockGetMappingsV1 = vi.fn();
const mockCreateMappingV1 = vi.fn();
const mockUpdateMappingV1 = vi.fn();
const mockDeleteMappingV1 = vi.fn();
const mockTriggerSyncV1 = vi.fn();
vi.mock('../../api/metadata-sync', () => ({
  getMappingsV1: () => mockGetMappingsV1(),
  createMappingV1: () => mockCreateMappingV1(),
  updateMappingV1: () => mockUpdateMappingV1(),
  deleteMappingV1: () => mockDeleteMappingV1(),
  triggerSyncV1: () => mockTriggerSyncV1(),
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

describe('FieldMapping Component', () => {
  it('should render without errors', () => {
    const { container } = renderWithRouter(<FieldMapping />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<FieldMapping />);

    expect(screen.getByText('字段映射管理')).toBeInTheDocument();
  });

  it('should have info alert', () => {
    renderWithRouter(<FieldMapping />);

    expect(screen.getByText('元数据联动说明')).toBeInTheDocument();
  });

  it('should have add mapping button', () => {
    renderWithRouter(<FieldMapping />);

    const addButtons = screen.queryAllByText('新建映射');
    expect(addButtons.length).toBeGreaterThan(0);
  });

  it('should have sync button', () => {
    renderWithRouter(<FieldMapping />);

    const syncButtons = screen.queryAllByText('手动同步');
    expect(syncButtons.length).toBeGreaterThan(0);
  });

  it('should call getMappingsV1 on mount', () => {
    renderWithRouter(<FieldMapping />);

    expect(mockGetMappingsV1).toHaveBeenCalled();
  });
});
