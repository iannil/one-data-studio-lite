/**
 * Apache Hop ETL API 测试
 * TDD: 验证ETL工作流与管道相关API的正确性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  listWorkflows,
  getWorkflow,
  runWorkflow,
  getWorkflowStatus,
  stopWorkflow,
  listPipelines,
  getPipeline,
  runPipeline,
  getPipelineStatus,
  stopPipeline,
  getServerStatus,
  getServerInfo,
  listRunConfigurations,
  runWorkflowAndWait,
  runPipelineAndWait,
} from './hop';

// Mock axios client
vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import client from './client';
const mockClient = vi.mocked(client);

describe('Hop API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // 工作流 API 测试
  // ============================================
  describe('Workflow API', () => {
    describe('listWorkflows', () => {
      it('should return workflows list', async () => {
        // Arrange
        const mockResponse = {
          workflows: [
            { name: 'etl-workflow', description: 'Main ETL workflow', status: 'active' },
            { name: 'ml-pipeline', description: 'ML training workflow', status: 'active' },
          ],
          total: 2,
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listWorkflows();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/hop/workflows');
        expect(result.workflows).toHaveLength(2);
        expect(result.total).toBe(2);
      });

      it('should handle empty workflows list', async () => {
        // Arrange
        mockClient.get.mockResolvedValue({
          data: { workflows: [], total: 0 },
        });

        // Act
        const result = await listWorkflows();

        // Assert
        expect(result.workflows).toEqual([]);
      });
    });

    describe('getWorkflow', () => {
      it('should return workflow detail', async () => {
        // Arrange
        const mockResponse = {
          name: 'etl-workflow',
          description: 'Main ETL workflow',
          filename: 'etl-workflow.hwf',
          status: 'active',
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getWorkflow('etl-workflow');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/hop/workflows/etl-workflow');
        expect(result.name).toBe('etl-workflow');
      });

      it('should handle special characters in workflow name', async () => {
        // Arrange
        const workflowName = 'my-workflow (2024)';
        mockClient.get.mockResolvedValue({
          data: { name: workflowName, status: 'active' },
        });

        // Act
        const result = await getWorkflow(workflowName);

        // Assert - name should be encoded
        expect(result.name).toBe(workflowName);
      });
    });

    describe('runWorkflow', () => {
      it('should run workflow with default configuration', async () => {
        // Arrange
        const mockResponse = {
          success: true,
          message: 'Workflow started',
          execution_id: 'exec-123',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await runWorkflow('etl-workflow');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/hop/workflows/etl-workflow/run',
          { run_configuration: 'local' }
        );
        expect(result.success).toBe(true);
        expect(result.execution_id).toBe('exec-123');
      });

      it('should run workflow with custom configuration', async () => {
        // Arrange
        const mockResponse = {
          success: true,
          message: 'Workflow started',
          execution_id: 'exec-456',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await runWorkflow('etl-workflow', {
          run_configuration: 'production',
          parameters: { batch_size: '1000' },
          variables: { env: 'prod' },
        });

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/hop/workflows/etl-workflow/run',
          {
            run_configuration: 'production',
            parameters: { batch_size: '1000' },
            variables: { env: 'prod' },
          }
        );
      });
    });

    describe('getWorkflowStatus', () => {
      it('should return workflow status', async () => {
        // Arrange
        const mockResponse = {
          id: 'exec-123',
          status: 'Running',
          start_time: '2024-02-01T10:00:00Z',
          errors: 0,
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getWorkflowStatus('etl-workflow', 'exec-123');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith(
          '/api/proxy/hop/workflows/etl-workflow/status/exec-123'
        );
        expect(result.status).toBe('Running');
      });

      it('should return finished status', async () => {
        // Arrange
        const mockResponse = {
          id: 'exec-123',
          status: 'Finished',
          start_time: '2024-02-01T10:00:00Z',
          end_time: '2024-02-01T10:15:00Z',
          errors: 0,
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getWorkflowStatus('etl-workflow', 'exec-123');

        // Assert
        expect(result.status).toBe('Finished');
        expect(result.end_time).toBeDefined();
      });
    });

    describe('stopWorkflow', () => {
      it('should stop running workflow', async () => {
        // Arrange
        const mockResponse = {
          success: true,
          message: 'Workflow stopped',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await stopWorkflow('etl-workflow', 'exec-123');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/hop/workflows/etl-workflow/stop/exec-123'
        );
        expect(result.success).toBe(true);
      });
    });
  });

  // ============================================
  // 管道 API 测试
  // ============================================
  describe('Pipeline API', () => {
    describe('listPipelines', () => {
      it('should return pipelines list', async () => {
        // Arrange
        const mockResponse = {
          pipelines: [
            { name: 'data-pipeline', description: 'Data processing pipeline', status: 'active' },
            { name: 'transform-pipeline', description: 'Data transform pipeline', status: 'active' },
          ],
          total: 2,
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listPipelines();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/hop/pipelines');
        expect(result.pipelines).toHaveLength(2);
      });
    });

    describe('getPipeline', () => {
      it('should return pipeline detail', async () => {
        // Arrange
        const mockResponse = {
          name: 'data-pipeline',
          description: 'Data processing pipeline',
          filename: 'data-pipeline.hpl',
          status: 'active',
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getPipeline('data-pipeline');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/hop/pipelines/data-pipeline');
        expect(result.name).toBe('data-pipeline');
      });
    });

    describe('runPipeline', () => {
      it('should run pipeline', async () => {
        // Arrange
        const mockResponse = {
          success: true,
          message: 'Pipeline started',
          execution_id: 'pipe-exec-123',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await runPipeline('data-pipeline');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/hop/pipelines/data-pipeline/run',
          { run_configuration: 'local' }
        );
        expect(result.success).toBe(true);
      });
    });

    describe('getPipelineStatus', () => {
      it('should return pipeline status', async () => {
        // Arrange
        const mockResponse = {
          id: 'pipe-exec-123',
          status: 'Running',
          start_time: '2024-02-01T10:00:00Z',
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getPipelineStatus('data-pipeline', 'pipe-exec-123');

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith(
          '/api/proxy/hop/pipelines/data-pipeline/status/pipe-exec-123'
        );
        expect(result.status).toBe('Running');
      });
    });

    describe('stopPipeline', () => {
      it('should stop running pipeline', async () => {
        // Arrange
        const mockResponse = {
          success: true,
          message: 'Pipeline stopped',
        };
        mockClient.post.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await stopPipeline('data-pipeline', 'pipe-exec-123');

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/hop/pipelines/data-pipeline/stop/pipe-exec-123'
        );
        expect(result.success).toBe(true);
      });
    });
  });

  // ============================================
  // 服务器 API 测试
  // ============================================
  describe('Server API', () => {
    describe('getServerStatus', () => {
      it('should return server status', async () => {
        // Arrange
        const mockResponse = {
          status: 'running',
          version: '2.0.0',
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getServerStatus();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/hop/server/status');
        expect(result.status).toBe('running');
      });
    });

    describe('getServerInfo', () => {
      it('should return server info', async () => {
        // Arrange
        const mockResponse = {
          version: '2.0.0',
          status: 'running',
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await getServerInfo();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/hop/server/info');
        expect(result.version).toBe('2.0.0');
      });
    });

    describe('listRunConfigurations', () => {
      it('should return run configurations', async () => {
        // Arrange
        const mockResponse = {
          configurations: [
            { name: 'local', description: 'Local execution' },
            { name: 'production', description: 'Production server' },
          ],
        };
        mockClient.get.mockResolvedValue({ data: mockResponse });

        // Act
        const result = await listRunConfigurations();

        // Assert
        expect(mockClient.get).toHaveBeenCalledWith('/api/proxy/hop/run-configurations');
        expect(result.configurations).toHaveLength(2);
      });
    });
  });

  // ============================================
  // 边界条件测试
  // ============================================
  describe('boundary conditions', () => {
    it('should handle empty workflows list', async () => {
      // Arrange
      mockClient.get.mockResolvedValue({
        data: { workflows: [], total: 0 },
      });

      // Act
      const result = await listWorkflows();

      // Assert
      expect(result.workflows).toEqual([]);
    });

    it('should handle workflow run failure', async () => {
      // Arrange
      const mockResponse = {
        success: false,
        message: 'Workflow not found',
      };
      mockClient.post.mockResolvedValue({ data: mockResponse });

      // Act
      const result = await runWorkflow('non-existent');

      // Assert
      expect(result.success).toBe(false);
    });

    it('should handle special characters in name', async () => {
      // Arrange
      const nameWithSpaces = 'My Workflow (2024)';
      mockClient.get.mockResolvedValue({
        data: { name: nameWithSpaces, status: 'active' },
      });

      // Act
      const result = await getWorkflow(nameWithSpaces);

      // Assert - name should be URL encoded
      expect(result.name).toBe(nameWithSpaces);
    });
  });

  // ============================================
  // 集成场景测试
  // ============================================
  describe('integration: ETL workflow', () => {
    it('should list, run, and monitor workflow', async () => {
      // Step 1: List workflows
      mockClient.get.mockResolvedValue({
        data: {
          workflows: [{ name: 'etl-workflow', description: 'ETL', status: 'active' }],
          total: 1,
        },
      });

      const workflows = await listWorkflows();
      expect(workflows.workflows).toHaveLength(1);

      // Step 2: Run workflow
      mockClient.post.mockResolvedValue({
        data: {
          success: true,
          message: 'Started',
          execution_id: 'exec-123',
        },
      });

      const runResult = await runWorkflow('etl-workflow');
      expect(runResult.success).toBe(true);
      expect(runResult.execution_id).toBe('exec-123');

      // Step 3: Check status - running
      mockClient.get.mockResolvedValue({
        data: {
          id: 'exec-123',
          status: 'Running',
          start_time: '2024-02-01T10:00:00Z',
        },
      });

      const statusRunning = await getWorkflowStatus('etl-workflow', 'exec-123');
      expect(statusRunning.status).toBe('Running');

      // Step 4: Check status - finished
      mockClient.get.mockResolvedValue({
        data: {
          id: 'exec-123',
          status: 'Finished',
          start_time: '2024-02-01T10:00:00Z',
          end_time: '2024-02-01T10:15:00Z',
          errors: 0,
        },
      });

      const statusFinished = await getWorkflowStatus('etl-workflow', 'exec-123');
      expect(statusFinished.status).toBe('Finished');
    });
  });

  // ============================================
  // 便捷函数测试
  // ============================================
  describe('convenience functions', () => {
    describe('runWorkflowAndWait', () => {
      it('should run workflow and wait for completion', async () => {
        // Arrange - First call starts workflow, subsequent calls check status
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Started',
            execution_id: 'exec-123',
          },
        });

        // Mock status responses - first running, then finished
        mockClient.get
          .mockResolvedValueOnce({
            data: {
              id: 'exec-123',
              status: 'Running',
              start_time: '2024-02-01T10:00:00Z',
            },
          })
          .mockResolvedValueOnce({
            data: {
              id: 'exec-123',
              status: 'Finished',
              start_time: '2024-02-01T10:00:00Z',
              end_time: '2024-02-01T10:05:00Z',
              errors: 0,
            },
          });

        // Act
        const result = await runWorkflowAndWait('etl-workflow', undefined, 10);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/hop/workflows/etl-workflow/run',
          { run_configuration: 'local' }
        );
        expect(result.status).toBe('Finished');
      });

      it('should throw error when workflow start fails', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: false,
            message: 'Workflow not found',
          },
        });

        // Act & Assert
        await expect(runWorkflowAndWait('non-existent')).rejects.toThrow('Workflow not found');
      });

      it('should throw error when no execution ID returned', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Started but no ID',
          },
        });

        // Act & Assert - Uses the message from the response
        await expect(runWorkflowAndWait('etl-workflow')).rejects.toThrow('Started but no ID');
      });

      it('should throw error on timeout', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Started',
            execution_id: 'exec-123',
          },
        });

        // Always return running status
        mockClient.get.mockResolvedValue({
          data: {
            id: 'exec-123',
            status: 'Running',
            start_time: '2024-02-01T10:00:00Z',
          },
        });

        // Act & Assert - timeout after 100ms
        await expect(runWorkflowAndWait('etl-workflow', undefined, 10, 100)).rejects.toThrow('执行超时');
      });

      it('should return error status when workflow fails', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Started',
            execution_id: 'exec-123',
          },
        });

        mockClient.get.mockResolvedValue({
          data: {
            id: 'exec-123',
            status: 'Error',
            start_time: '2024-02-01T10:00:00Z',
            end_time: '2024-02-01T10:02:00Z',
            errors: 5,
            log: 'Error processing step 3',
          },
        });

        // Act
        const result = await runWorkflowAndWait('etl-workflow', undefined, 10);

        // Assert
        expect(result.status).toBe('Error');
        expect(result.errors).toBe(5);
      });

      it('should respect custom poll interval and timeout', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Started',
            execution_id: 'exec-123',
          },
        });

        mockClient.get.mockResolvedValue({
          data: {
            id: 'exec-123',
            status: 'Stopped',
            start_time: '2024-02-01T10:00:00Z',
            end_time: '2024-02-01T10:03:00Z',
          },
        });

        // Act - custom interval and timeout
        const result = await runWorkflowAndWait('etl-workflow', undefined, 50, 5000);

        // Assert
        expect(result.status).toBe('Stopped');
      });
    });

    describe('runPipelineAndWait', () => {
      it('should run pipeline and wait for completion', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Pipeline started',
            execution_id: 'pipe-exec-456',
          },
        });

        mockClient.get
          .mockResolvedValueOnce({
            data: {
              id: 'pipe-exec-456',
              status: 'Running',
              start_time: '2024-02-01T11:00:00Z',
            },
          })
          .mockResolvedValueOnce({
            data: {
              id: 'pipe-exec-456',
              status: 'Finished',
              start_time: '2024-02-01T11:00:00Z',
              end_time: '2024-02-01T11:10:00Z',
              errors: 0,
            },
          });

        // Act
        const result = await runPipelineAndWait('data-pipeline', undefined, 10);

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/hop/pipelines/data-pipeline/run',
          { run_configuration: 'local' }
        );
        expect(result.status).toBe('Finished');
      });

      it('should throw error when pipeline start fails', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: false,
            message: 'Pipeline configuration invalid',
          },
        });

        // Act & Assert
        await expect(runPipelineAndWait('data-pipeline')).rejects.toThrow('Pipeline configuration invalid');
      });

      it('should throw error on timeout', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Started',
            execution_id: 'pipe-exec-456',
          },
        });

        // Always return running status
        mockClient.get.mockResolvedValue({
          data: {
            id: 'pipe-exec-456',
            status: 'Running',
            start_time: '2024-02-01T11:00:00Z',
          },
        });

        // Act & Assert
        await expect(runPipelineAndWait('data-pipeline', undefined, 10, 100)).rejects.toThrow('执行超时');
      });

      it('should accept custom run configuration', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Started',
            execution_id: 'pipe-exec-456',
          },
        });

        mockClient.get.mockResolvedValue({
          data: {
            id: 'pipe-exec-456',
            status: 'Finished',
            start_time: '2024-02-01T11:00:00Z',
          },
        });

        // Act
        const result = await runPipelineAndWait(
          'data-pipeline',
          { run_configuration: 'production', variables: { env: 'prod' } },
          10
        );

        // Assert
        expect(mockClient.post).toHaveBeenCalledWith(
          '/api/proxy/hop/pipelines/data-pipeline/run',
          { run_configuration: 'production', variables: { env: 'prod' } }
        );
        expect(result.status).toBe('Finished');
      });

      it('should return stopped status when pipeline is stopped', async () => {
        // Arrange
        mockClient.post.mockResolvedValue({
          data: {
            success: true,
            message: 'Started',
            execution_id: 'pipe-exec-456',
          },
        });

        mockClient.get.mockResolvedValue({
          data: {
            id: 'pipe-exec-456',
            status: 'Stopped',
            start_time: '2024-02-01T11:00:00Z',
            end_time: '2024-02-01T11:05:00Z',
          },
        });

        // Act
        const result = await runPipelineAndWait('data-pipeline', undefined, 10);

        // Assert
        expect(result.status).toBe('Stopped');
      });
    });
  });
});
