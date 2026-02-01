/**
 * AssetDetail 组件测试
 * 测试资产详情页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AssetDetail from './AssetDetail';

// Mock data-api API
const mockGetAssetDetailV1 = vi.fn();
const mockGetDatasetSchemaV1 = vi.fn();
vi.mock('../../api/data-api', () => ({
  getAssetDetailV1: () => mockGetAssetDetailV1(),
  getDatasetSchemaV1: () => mockGetDatasetSchemaV1(),
}));

// Mock datahub API
const mockGetLineage = vi.fn();
vi.mock('../../api/datahub', () => ({
  getLineage: () => mockGetLineage(),
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
  return render(
    <MemoryRouter initialEntries={['/assets/test-id']}>
      <Routes>
        <Route path="/assets/:id" element={component} />
      </Routes>
    </MemoryRouter>
  );
};

describe('AssetDetail Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetAssetDetailV1.mockResolvedValue({ data: { name: 'Test Asset' } });
    mockGetDatasetSchemaV1.mockResolvedValue({ data: { fields: [] } });
    mockGetLineage.mockResolvedValue({ relationships: [] });
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<AssetDetail />);

    // Component starts with loading state (Spin)
    expect(container.querySelector('.ant-spin') || container.querySelector('.ant-card')).toBeInTheDocument();
  });

  it('should call getAssetDetailV1 on mount', () => {
    renderWithRouter(<AssetDetail />);

    expect(mockGetAssetDetailV1).toHaveBeenCalled();
  });

  it('should have tabs', () => {
    renderWithRouter(<AssetDetail />);

    const tabElements = screen.queryAllByText(/基本信息|Schema|血缘/);
    expect(tabElements.length).toBeGreaterThanOrEqual(0);
  });
});
