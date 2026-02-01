/**
 * Cube-Studio AI 平台 API 测试
 * TDD: 验证Cube-Studio相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getPipelinesV1,
  getPipelineV1,
  runPipelineV1,
  deletePipelineV1,
  listModelsV1,
  modelInferenceV1,
  chatCompletionV1,
  quickChat,
  listDataSourcesV1,
  createDataSourceV1,
  listDatasetsV1,
  listNotebooksV1,
  createNotebookV1,
  getMetricsV1,
  listAlertsV1,
  getServicesStatusV1,
} from './cubestudio';
import { ErrorCode } from './types';

// Mock axios client
vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import client from './client';
const mockClient = vi.mocked(client);

describe('Cube-Studio API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // Pipeline API 测试
  // ============================================
  describe('Pipeline API', () => {
    describe('getPipelinesV1', () => {
      it('should return pipelines list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: [
            { id: 1, name: 'ETL Pipeline', status: 'running' },
            { id: 2, name: 'ML Training', status: 'completed' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getPipelinesV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/pipelines', {
          params: undefined,
        });
        expect(result.data).toHaveLength(2);
      });

      it('should support pagination', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
        });

        // Act
        await getPipelinesV1({ page: 2, page_size: 20 });

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/pipelines', {
          params: { page: 2, page_size: 20 },
        });
      });
    });

    describe('getPipelineV1', () => {
      it('should return pipeline detail', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: 1,
            name: 'ETL Pipeline',
            description: 'Data ETL process',
            status: 'running',
            created_at: '2024-02-01T10:00:00Z',
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getPipelineV1(1);

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/pipelines/1');
        expect(result.data.name).toBe('ETL Pipeline');
      });
    });

    describe('runPipelineV1', () => {
      it('should run pipeline', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            success: true,
            run_id: 'run-123',
            message: 'Pipeline started',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await runPipelineV1(1);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/pipelines/1/run', {});
        expect(result.data.success).toBe(true);
      });

      it('should run pipeline with parameters', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { success: true, run_id: 'run-456' },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await runPipelineV1(1, {
          parameters: { batch_size: 100 },
          variables: { env: 'prod' },
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/pipelines/1/run', {
          parameters: { batch_size: 100 },
          variables: { env: 'prod' },
        });
      });
    });

    describe('deletePipelineV1', () => {
      it('should delete pipeline', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: { message: 'Pipeline deleted' },
        };
        mockClient.delete.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await deletePipelineV1(1);

        // Assert
        expect(mockClient.delete).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/pipelines/1');
        expect(result.data.message).toBe('Pipeline deleted');
      });
    });
  });

  // ============================================
  // 模型推理 API 测试
  // ============================================
  describe('Model Inference API', () => {
    describe('listModelsV1', () => {
      it('should return available models', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            models: ['qwen2.5:7b', 'llama3:8b', 'mistral:7b'],
            details: [
              { name: 'qwen2.5:7b', modified_at: '2024-02-01', size: 4700000000 },
              { name: 'llama3:8b', modified_at: '2024-01-15', size: 4700000000 },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listModelsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/models');
        expect(result.data.models).toHaveLength(3);
        expect(result.data.models).toContain('qwen2.5:7b');
      });
    });

    describe('modelInferenceV1', () => {
      it('should return inference result', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            model: 'qwen2.5:7b',
            response: 'This is a generated response',
            done: true,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await modelInferenceV1({
          model_name: 'qwen2.5:7b',
          prompt: 'Hello',
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/models/inference', {
          model_name: 'qwen2.5:7b',
          prompt: 'Hello',
        });
        expect(result.data.response).toBe('This is a generated response');
      });

      it('should support inference parameters', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            model: 'llama3:8b',
            response: 'Response',
            done: true,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await modelInferenceV1({
          model_name: 'llama3:8b',
          prompt: 'Test',
          max_tokens: 1000,
          temperature: 0.5,
          top_p: 0.9,
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/models/inference', {
          model_name: 'llama3:8b',
          prompt: 'Test',
          max_tokens: 1000,
          temperature: 0.5,
          top_p: 0.9,
        });
      });
    });

    describe('chatCompletionV1', () => {
      it('should return chat completion', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            model: 'qwen2.5:7b',
            response: 'Chat response',
            done: true,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await chatCompletionV1({
          model_name: 'qwen2.5:7b',
          messages: [
            { role: 'user', content: 'Hello' },
            { role: 'assistant', content: 'Hi there!' },
          ],
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/models/chat', {
          model_name: 'qwen2.5:7b',
          messages: [
            { role: 'user', content: 'Hello' },
            { role: 'assistant', content: 'Hi there!' },
          ],
        });
      });
    });

    describe('quickChat', () => {
      it('should return quick chat response', async () => {
        // Arrange
        const mockResponse = {
          code: 20000,
          message: 'success',
          data: {
            model: 'qwen2.5:7b',
            response: 'Quick response',
            done: true,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await quickChat('Hello');

        // Assert
        expect(result).toBe('Quick response');
      });

      it('should use default model and tokens', async () => {
        // Arrange
        const mockResponse = {
          code: 20000,
          message: 'success',
          data: {
            model: 'qwen2.5:7b',
            response: 'Response',
            done: true,
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        await quickChat('Test');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/models/chat', {
          model_name: 'qwen2.5:7b',
          prompt: 'Test',
          max_tokens: 2048,
          temperature: 0.1,
        });
      });

      it('should throw error on failure', async () => {
        // Arrange
        const mockResponse = {
          code: 50000,
          message: 'Model not available',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act & Assert
        await expect(quickChat('Test')).rejects.toThrow('Model not available');
      });
    });
  });

  // ============================================
  // 数据管理 API 测试
  // ============================================
  describe('Data Management API', () => {
    describe('listDataSourcesV1', () => {
      it('should return data sources list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            data_sources: [
              { id: '1', name: 'MySQL Source', type: 'mysql', status: 'active' },
              { id: '2', name: 'PostgreSQL Source', type: 'postgresql', status: 'active' },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listDataSourcesV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/data-sources');
        expect(result.data.data_sources).toHaveLength(2);
      });
    });

    describe('createDataSourceV1', () => {
      it('should create data source', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            id: '3',
            name: 'New Source',
            type: 'mysql',
            status: 'active',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createDataSourceV1({
          name: 'New Source',
          type: 'mysql',
          connection_params: { host: 'localhost', port: 3306 },
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/data-sources', {
          name: 'New Source',
          type: 'mysql',
          connection_params: { host: 'localhost', port: 3306 },
        });
        expect(result.data.id).toBe('3');
      });
    });

    describe('listDatasetsV1', () => {
      it('should return datasets list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            datasets: [
              { id: '1', name: 'users', type: 'table', rows: 1000 },
              { id: '2', name: 'orders', type: 'table', rows: 5000 },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listDatasetsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/datasets', {
          params: undefined,
        });
        expect(result.data.datasets).toHaveLength(2);
      });
    });
  });

  // ============================================
  // Notebook API 测试
  // ============================================
  describe('Notebook API', () => {
    describe('listNotebooksV1', () => {
      it('should return notebooks list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            items: [
              { name: 'analysis.ipynb', path: '/home/analysis.ipynb', type: 'notebook' },
              { name: 'etl-pipeline.ipynb', path: '/home/etl-pipeline.ipynb', type: 'notebook' },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listNotebooksV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/notebooks?path=%2F');
        expect(result.data.items).toHaveLength(2);
      });

      it('should list notebooks in specific path', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { code: ErrorCode.SUCCESS, message: 'success', data: { items: [] } },
        });

        // Act
        await listNotebooksV1('/projects/ml');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/notebooks?path=%2Fprojects%2Fml');
      });
    });

    describe('createNotebookV1', () => {
      it('should create notebook', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            name: 'new-analysis.ipynb',
            path: '/home/new-analysis.ipynb',
            type: 'notebook',
          },
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await createNotebookV1({
          name: 'new-analysis.ipynb',
          description: 'My analysis',
          kernel_type: 'python3',
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/notebooks', {
          name: 'new-analysis.ipynb',
          description: 'My analysis',
          kernel_type: 'python3',
        });
      });
    });
  });

  // ============================================
  // 监控告警 API 测试
  // ============================================
  describe('Monitoring API', () => {
    describe('getMetricsV1', () => {
      it('should return system metrics', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            metrics: [
              { name: 'cpu_usage', value: 45.2 },
              { name: 'memory_usage', value: 62.8 },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getMetricsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/metrics');
        expect(result.data.metrics).toBeDefined();
      });
    });

    describe('listAlertsV1', () => {
      it('should return alerts list', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            alerts: [
              { id: '1', level: 'warning', message: 'High CPU usage' },
              { id: '2', level: 'error', message: 'Pipeline failed' },
            ],
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listAlertsV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/alerts');
        expect(result.data.alerts).toHaveLength(2);
      });
    });

    describe('getServicesStatusV1', () => {
      it('should return services status', async () => {
        // Arrange
        const mockResponse = {
          code: ErrorCode.SUCCESS,
          message: 'success',
          data: {
            services: {
              cube_studio: { url: 'http://localhost:8000', status: 'online' },
              ollama: { url: 'http://localhost:11434', status: 'online' },
              prometheus: { url: 'http://localhost:9090', status: 'online' },
              grafana: { url: 'http://localhost:3000', status: 'offline' },
            },
          },
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getServicesStatusV1();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/cubestudio/v1/services/status');
        expect(result.data.services.cube_studio.status).toBe('online');
        expect(result.data.services.grafana.status).toBe('offline');
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty pipelines list', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: [] },
      });

      // Act
      const result = await getPipelinesV1();

      // Assert
      expect(result.data).toEqual([]);
    });

    it('should handle special characters in notebook path', async () => {
      // Arrange
      const pathWithSpaces = '/projects/My Project/analysis';
      mockClient.get.mockResolvedValue({
        data: { code: ErrorCode.SUCCESS, message: 'success', data: { items: [] } },
      });

      // Act
      await listNotebooksV1(pathWithSpaces);

      // Assert - path should be encoded
      expect(mockClient.get).toHaveBeenCalled();
    });
  });
});
