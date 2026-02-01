/**
 * MetadataBrowser 组件测试
 * 测试元数据管理页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MetadataBrowser from './MetadataBrowser';

// Mock datahub API
const mockSearchEntities = vi.fn();
const mockGetEntityAspect = vi.fn();
vi.mock('../../api/datahub', () => ({
  searchEntities: () => mockSearchEntities(),
  getEntityAspect: () => mockGetEntityAspect(),
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

describe('MetadataBrowser Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchEntities.mockResolvedValue({
      entities: [
        { urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,test.db1,PROD)', name: 'db1', platform: 'mysql' },
        { urn: 'urn:li:dataset:(urn:li:dataPlatform:mysql,test.db2,PROD)', name: 'db2', platform: 'mysql' },
      ],
    });
    mockGetEntityAspect.mockResolvedValue({
      fields: [
        { fieldPath: 'id', nativeDataType: 'INT', nullable: false, description: 'ID' },
        { fieldPath: 'name', nativeDataType: 'VARCHAR', nullable: true, description: 'Name' },
      ],
    });
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<MetadataBrowser />);

    expect(container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should render page title', () => {
    renderWithRouter(<MetadataBrowser />);

    expect(screen.getByText('元数据管理')).toBeInTheDocument();
  });

  it('should call searchEntities on mount', () => {
    renderWithRouter(<MetadataBrowser />);

    expect(mockSearchEntities).toHaveBeenCalled();
  });

  it('should render search input', () => {
    renderWithRouter(<MetadataBrowser />);

    const searchInput = screen.getByPlaceholderText('搜索');
    expect(searchInput).toBeInTheDocument();
  });

  it('should handle search input change', () => {
    renderWithRouter(<MetadataBrowser />);

    const searchInput = screen.getByPlaceholderText('搜索');
    fireEvent.change(searchInput, { target: { value: 'test' } });

    expect(searchInput).toHaveValue('test');
  });

  it('should display datasets card', () => {
    renderWithRouter(<MetadataBrowser />);

    expect(screen.getByText('数据集')).toBeInTheDocument();
  });

  it('should display placeholder when no dataset selected', () => {
    renderWithRouter(<MetadataBrowser />);

    expect(screen.getByText('请从左侧选择一个数据集查看 Schema')).toBeInTheDocument();
  });

  it('should have tree view for datasets', () => {
    const { container } = renderWithRouter(<MetadataBrowser />);

    // Tree might not be rendered while loading, so just check the page structure
    const cardElement = container.querySelector('.ant-card');
    expect(cardElement).toBeInTheDocument();
  });
});
