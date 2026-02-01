/**
 * Apache Superset BI 分析 API 测试
 * TDD: 验证Superset相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getDashboardsV1,
  getDashboardV1,
  getChartsV1,
  getChartV1,
  getDatasetsV1,
  getDatasetV1,
  getDashboards,
  getDashboard,
  getCharts,
  getChart,
  getDatasets,
} from './superset';
import { ErrorCode } from './types';

// Mock axios client
vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
  },
}));

import client from './client';
const mockClient = vi.mocked(client);

describe('Superset API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // v1 版本 API 测试
  // ============================================
  describe('v1 API', () => {
    describe('getDashboardsV1', () => {
      it('should return dashboards list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 1,
              dashboard_title: 'Sales Overview',
              description: 'Sales performance metrics',
              slug: 'sales-overview',
            },
            {
              id: 2,
              dashboard_title: 'User Analytics',
              description: 'User behavior analysis',
              slug: 'user-analytics',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDashboardsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/dashboards', {
          params: undefined,
        });
        expect(result.data).toHaveLength(2);
        expect(result.data[0].dashboard_title).toBe('Sales Overview');
      });

      it('should support pagination', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await getDashboardsV1({ page: 2, page_size: 20 });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/dashboards', {
          params: { page: 2, page_size: 20 },
        });
      });

      it('should support search query', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await getDashboardsV1({ q: 'sales' });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/dashboards', {
          params: { q: 'sales' },
        });
      });

      it('should return empty array when no dashboards', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        const result = await getDashboardsV1();

        // Assert
        expect(result.data).toEqual([]);
      });
    });

    describe('getDashboardV1', () => {
      it('should return dashboard detail', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 1,
            dashboard_title: 'Sales Overview',
            description: 'Sales performance metrics',
            slug: 'sales-overview',
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDashboardV1(1);

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/dashboards/1');
        expect(result.data.dashboard_title).toBe('Sales Overview');
      });

      it('should handle 404 for non-existent dashboard', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: 404, message: 'Dashboard not found', data: null },
        });

        // Act
        const result = await getDashboardV1(999);

        // Assert - returns error response
        expect(result.code).toBe(404);
        expect(result.message).toBe('Dashboard not found');
      });
    });

    describe('getChartsV1', () => {
      it('should return charts list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 1,
              slice_name: 'Sales by Region',
              description: 'Bar chart showing sales by region',
              viz_type: 'echarts_timeseries_bar',
            },
            {
              id: 2,
              slice_name: 'Revenue Trend',
              description: 'Line chart showing revenue over time',
              viz_type: 'echarts_timeseries_line',
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getChartsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/charts', {
          params: undefined,
        });
        expect(result.data).toHaveLength(2);
        expect(result.data[0].viz_type).toBe('echarts_timeseries_bar');
      });

      it('should support search in charts', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await getChartsV1({ q: 'sales' });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/charts', {
          params: { q: 'sales' },
        });
      });
    });

    describe('getChartV1', () => {
      it('should return chart detail', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 1,
            slice_name: 'Sales by Region',
            description: 'Bar chart',
            viz_type: 'echarts_timeseries_bar',
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getChartV1(1);

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/charts/1');
        expect(result.data.slice_name).toBe('Sales by Region');
      });
    });

    describe('getDatasetsV1', () => {
      it('should return datasets list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 1,
              table_name: 'users',
              schema: 'public',
              database: { id: 1, name: 'production_db' },
            },
            {
              id: 2,
              table_name: 'orders',
              schema: 'public',
              database: { id: 1, name: 'production_db' },
            },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDatasetsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/datasets', {
          params: undefined,
        });
        expect(result.data).toHaveLength(2);
        expect(result.data[0].table_name).toBe('users');
      });

      it('should support pagination for datasets', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await getDatasetsV1({ page: 1, page_size: 50 });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/datasets', {
          params: { page: 1, page_size: 50 },
        });
      });
    });

    describe('getDatasetV1', () => {
      it('should return dataset detail', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 1,
            table_name: 'users',
            schema: 'public',
            database: { id: 1, name: 'production_db' },
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDatasetV1(1);

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/v1/datasets/1');
        expect(result.data.table_name).toBe('users');
      });
    });
  });

  // ============================================
  // 旧版 API 测试（向后兼容）
  // ============================================
  describe('legacy API', () => {
    describe('getDashboards', () => {
      it('should return dashboards list', async () => {
        // Arrange
        const mockResponse = {
          result: [
            { id: 1, dashboard_title: 'Dashboard 1' },
            { id: 2, dashboard_title: 'Dashboard 2' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDashboards();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/api/v1/dashboard/', {
          params: undefined,
        });
        expect(result.result).toHaveLength(2);
      });
    });

    describe('getDashboard', () => {
      it('should return dashboard detail', async () => {
        // Arrange
        const mockResponse = {
          result: { id: 1, dashboard_title: 'Dashboard 1' },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDashboard(1);

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/api/v1/dashboard/1');
        expect(result.result.dashboard_title).toBe('Dashboard 1');
      });
    });

    describe('getCharts', () => {
      it('should return charts list', async () => {
        // Arrange
        const mockResponse = {
          result: [
            { id: 1, slice_name: 'Chart 1' },
            { id: 2, slice_name: 'Chart 2' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getCharts();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/api/v1/chart/', {
          params: undefined,
        });
        expect(result.result).toHaveLength(2);
      });
    });

    describe('getChart', () => {
      it('should return chart detail', async () => {
        // Arrange
        const mockResponse = {
          result: { id: 1, slice_name: 'Chart 1' },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getChart(1);

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/api/v1/chart/1');
        expect(result.result.slice_name).toBe('Chart 1');
      });
    });

    describe('getDatasets', () => {
      it('should return datasets list', async () => {
        // Arrange
        const mockResponse = {
          result: [
            { id: 1, table_name: 'users' },
            { id: 2, table_name: 'orders' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getDatasets();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/superset/api/v1/dataset/', {
          params: undefined,
        });
        expect(result.result).toHaveLength(2);
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty dashboards list', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getDashboardsV1();

      // Assert
      expect(result.data).toEqual([]);
    });

    it('should handle very large page size', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getDashboardsV1({ page: 1, page_size: 10000 });

      // Assert
      expect(result.data).toEqual([]);
    });

    it('should handle zero page number', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getDashboardsV1({ page: 0, page_size: 10 });

      // Assert - API handles invalid input
      expect(result.data).toEqual([]);
    });

    it('should handle special characters in search query', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getDashboardsV1({ q: 'Sales & Analytics' });

      // Assert
      expect(result.data).toEqual([]);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: BI workflow', () => {
    it('should list dashboards and get detail', async () => {
      // Step 1: List dashboards
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 1,
              dashboard_title: 'Sales Overview',
              slug: 'sales-overview',
            },
          ],
        },
      });

      const dashboards = await getDashboardsV1();
      expect(dashboards.data).toHaveLength(1);
      const dashboardId = dashboards.data[0].id;

      // Step 2: Get dashboard detail
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: dashboardId,
            dashboard_title: 'Sales Overview',
            description: 'Sales metrics',
            slug: 'sales-overview',
          },
        },
      });

      const dashboard = await getDashboardV1(dashboardId);
      expect(dashboard.data.description).toBe('Sales metrics');
    });

    it('should get charts and datasets for a dashboard', async () => {
      // Step 1: Get charts
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 1,
              slice_name: 'Sales by Region',
              viz_type: 'bar',
            },
          ],
        },
      });

      const charts = await getChartsV1();
      expect(charts.data).toHaveLength(1);

      // Step 2: Get datasets
      mockClient.get.mockResolvedValue({
        data: {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            {
              id: 1,
              table_name: 'sales',
              schema: 'public',
            },
          ],
        },
      });

      const datasets = await getDatasetsV1();
      expect(datasets.data[0].table_name).toBe('sales');
    });
  });
});
