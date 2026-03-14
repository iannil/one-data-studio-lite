/**
 * GPU Store
 *
 * Zustand store for managing GPU pool resources.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';
import {
  PhysicalGPU,
  VirtualGPU,
  GPUAllocation,
  GPUTask,
  GPUPoolStatus,
  GPUMonitoringSummary,
  GPUDetails,
  GPUType,
  GPUTypeInfo,
  GPURequestRequest,
  VGPUCreateRequest,
  GPURequestResult,
  TaskSubmitRequest,
  GPUAllocationStrategy,
  TaskPriority,
  SchedulingPolicy,
} from '../types/gpu';

interface GPUState {
  // Data
  gpus: PhysicalGPU[];
  vgpuInstances: VirtualGPU[];
  allocations: GPUAllocation[];
  tasks: GPUTask[];
  poolStatus: GPUPoolStatus | null;
  monitoringSummary: GPUMonitoringSummary | null;
  gpuTypes: GPUTypeInfo[];
  selectedGpuId: string | null;
  selectedGpuDetails: GPUDetails | null;

  // UI State
  loading: boolean;
  error: string | null;
  refreshInterval: number; // seconds

  // Pool Management Actions
  fetchPoolStatus: () => Promise<GPUPoolStatus>;
  fetchGPUs: (gpuType?: GPUType, healthyOnly?: boolean) => Promise<PhysicalGPU[]>;
  fetchGPUDetails: (gpuId: string) => Promise<GPUDetails>;
  fetchVGPUInstances: (
    gpuId?: string,
    allocatedOnly?: boolean,
    availableOnly?: boolean,
  ) => Promise<VirtualGPU[]>;
  fetchAllocations: (resourceName?: string) => Promise<GPUAllocation[]>;
  fetchGPUTypes: () => Promise<GPUTypeInfo[]>;

  // Allocation Actions
  requestGPU: (request: GPURequestRequest) => Promise<GPURequestResult>;
  releaseGPU: (resourceName: string) => Promise<void>;
  createVGPUInstances: (request: VGPUCreateRequest) => Promise<void>;
  deallocateGPU: (allocationId: string) => Promise<void>;

  // Task Actions
  submitTask: (request: TaskSubmitRequest) => Promise<any>;
  listTasks: (status?: string, resourceName?: string) => Promise<GPUTask[]>;
  getTaskStatus: (taskId: string) => Promise<GPUTask | null>;
  cancelTask: (taskId: string) => Promise<void>;
  completeTask: (taskId: string, success?: boolean) => Promise<void>;

  // Scheduling Actions
  getQueueStats: () => Promise<any>;
  setSchedulingPolicy: (policy: SchedulingPolicy) => Promise<void>;

  // Monitoring Actions
  fetchMonitoringSummary: () => Promise<GPUMonitoringSummary>;

  // Utility
  selectGpu: (gpuId: string | null) => void;
  clearError: () => void;
  setError: (error: string) => void;
}

export const useGPUStore = create<GPUState>()(
  persist(
    (set, get) => ({
      // Initial state
      gpus: [],
      vgpuInstances: [],
      allocations: [],
      tasks: [],
      poolStatus: null,
      monitoringSummary: null,
      gpuTypes: [],
      selectedGpuId: null,
      selectedGpuDetails: null,
      loading: false,
      error: null,
      refreshInterval: 10,

      // Fetch pool status
      fetchPoolStatus: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/gpu/pool/status');
          const status: GPUPoolStatus = response.data;
          set({
            poolStatus: status,
            gpus: status.gpus,
            allocations: status.allocations,
            loading: false,
          });
          return status;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Fetch GPUs
      fetchGPUs: async (gpuType, healthyOnly) => {
        set({ loading: true, error: null });
        try {
          const params: any = {};
          if (gpuType) params.gpu_type = gpuType;
          if (healthyOnly) params.healthy_only = true;

          const response = await api.get('/gpu/gpus', { params });
          const gpus: PhysicalGPU[] = response.data;
          set({ gpus, loading: false });
          return gpus;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Fetch GPU details
      fetchGPUDetails: async (gpuId) => {
        try {
          const response = await api.get(`/gpu/gpus/${gpuId}`);
          const details: GPUDetails = response.data;
          set({ selectedGpuDetails: details });
          return details;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Fetch VGPU instances
      fetchVGPUInstances: async (gpuId, allocatedOnly, availableOnly) => {
        try {
          const params: any = {};
          if (gpuId) params.gpu_id = gpuId;
          if (allocatedOnly) params.allocated_only = true;
          if (availableOnly) params.available_only = true;

          const response = await api.get('/gpu/vgpu/instances', { params });
          const instances: VirtualGPU[] = response.data;
          set({ vgpuInstances: instances });
          return instances;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Fetch allocations
      fetchAllocations: async (resourceName) => {
        try {
          const params = resourceName ? { resource_name: resourceName } : {};
          const response = await api.get('/gpu/allocations', { params });
          const allocations: GPUAllocation[] = response.data;
          set({ allocations });
          return allocations;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Fetch GPU types
      fetchGPUTypes: async () => {
        try {
          const response = await api.get('/gpu/gpu-types');
          const types: GPUTypeInfo[] = response.data.gpu_types;
          set({ gpuTypes: types });
          return types;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Request GPU allocation
      requestGPU: async (request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/gpu/allocate', {
            resource_name: request.resourceName,
            vgpu_count: request.vgpuCount,
            gpu_type: request.gpuType,
            memory_mb: request.memoryMb,
            strategy: request.strategy,
            priority: request.priority,
            estimated_duration_minutes: request.estimatedDurationMinutes,
          });
          const result: GPURequestResult = response.data;
          await get().fetchAllocations();
          await get().fetchPoolStatus();
          set({ loading: false });
          return result;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Release GPU allocation
      releaseGPU: async (resourceName) => {
        try {
          await api.post('/gpu/release', { resource_name: resourceName });
          await get().fetchAllocations();
          await get().fetchPoolStatus();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Create VGPU instances
      createVGPUInstances: async (request) => {
        set({ loading: true, error: null });
        try {
          await api.post('/gpu/vgpu/create', {
            gpu_id: request.gpuId,
            count: request.count,
            memory_per_vgpu: request.memoryPerVgpu,
            cpu_cores_per_vgpu: request.cpuCoresPerVgpu,
          });
          await get().fetchVGPUInstances();
          await get().fetchPoolStatus();
          set({ loading: false });
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Deallocate GPU
      deallocateGPU: async (allocationId) => {
        try {
          await api.delete(`/gpu/allocations/${allocationId}`);
          await get().fetchAllocations();
          await get().fetchPoolStatus();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Submit task
      submitTask: async (request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/gpu/tasks/submit', {
            task_id: request.taskId,
            resource_name: request.resourceName,
            vgpu_count: request.vgpuCount,
            gpu_type: request.gpuType,
            memory_mb: request.memoryMb,
            strategy: request.strategy,
            priority: request.priority,
            estimated_duration_minutes: request.estimatedDurationMinutes,
            allowed_gpu_ids: request.allowedGpuIds,
            forbidden_gpu_ids: request.forbiddenGpuIds,
          });
          await get().listTasks();
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // List tasks
      listTasks: async (status, resourceName) => {
        try {
          const params: any = {};
          if (status) params.status = status;
          if (resourceName) params.resource_name = resourceName;

          const response = await api.get('/gpu/tasks', { params });
          const tasks: GPUTask[] = response.data;
          set({ tasks });
          return tasks;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Get task status
      getTaskStatus: async (taskId) => {
        try {
          const response = await api.get(`/gpu/tasks/${taskId}`);
          return response.data;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Cancel task
      cancelTask: async (taskId) => {
        try {
          await api.post(`/gpu/tasks/${taskId}/cancel`);
          await get().listTasks();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Complete task
      completeTask: async (taskId, success = true) => {
        try {
          await api.post(`/gpu/tasks/${taskId}/complete`, null, {
            params: { success },
          });
          await get().listTasks();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Get queue stats
      getQueueStats: async () => {
        try {
          const response = await api.get('/gpu/queue/stats');
          return response.data;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Set scheduling policy
      setSchedulingPolicy: async (policy) => {
        try {
          await api.post('/gpu/scheduler/policy', null, {
            params: { policy },
          });
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Fetch monitoring summary
      fetchMonitoringSummary: async () => {
        try {
          const response = await api.get('/gpu/monitoring/summary');
          const summary: GPUMonitoringSummary = response.data;
          set({ monitoringSummary: summary });
          return summary;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Select GPU
      selectGpu: (gpuId) => {
        set({ selectedGpuId: gpuId });
        if (gpuId) {
          get().fetchGPUDetails(gpuId);
        } else {
          set({ selectedGpuDetails: null });
        }
      },

      // Clear error
      clearError: () => set({ error: null }),

      // Set error
      setError: (error) => set({ error }),
    }),
    {
      name: 'gpu-storage',
      partialize: (state) => ({
        refreshInterval: state.refreshInterval,
        gpuTypes: state.gpuTypes,
      }),
    }
  )
);

// Selectors
export const selectHealthyGPUs = (state: GPUState) =>
  state.gpus.filter((g) => g.healthy);

export const selectAvailableGPUs = (state: GPUState) =>
  state.gpus.filter((g) => g.healthy && g.available_vgpu_slots > 0);

export const selectAllocatedVGPUCount = (state: GPUState) =>
  state.vgpuInstances.filter((v) => !v.is_available).length;

export const selectAvailableVGPUCount = (state: GPUState) =>
  state.vgpuInstances.filter((v) => v.is_available).length;

export const selectPendingTasks = (state: GPUState) =>
  state.tasks.filter((t) => t.status === 'pending');

export const selectRunningTasks = (state: GPUState) =>
  state.tasks.filter((t) => t.status === 'running');

export const selectTasksByResource = (resourceName: string) => (state: GPUState) =>
  state.tasks.filter((t) => t.resource_name === resourceName);

export const selectAllocationsByResource = (resourceName: string) => (state: GPUState) =>
  state.allocations.filter((a) => a.resource_name === resourceName);

export const selectGPUByType = (gpuType: GPUType) => (state: GPUState) =>
  state.gpus.filter((g) => g.type === gpuType);

export const selectHighUtilizationGPUs = (state: GPUState) =>
  state.gpus.filter((g) => g.utilization_status === 'high');

export const selectOverheatingGPUs = (state: GPUState) =>
  state.gpus.filter((g) => g.temperature_celsius > 85);
