/**
 * Workflow Store
 *
 * Zustand store for managing workflow DAG state and API calls.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';

// Types
export interface DAGNode {
  id: string;
  task_type: string;
  name: string;
  description?: string;
  config?: {
    description?: string;
    retry_count?: number;
    retry_delay_seconds?: number;
    timeout_seconds?: number;
    parameters?: Record<string, any>;
    depends_on?: string[];
  };
  position: {
    x: number;
    y: number;
  };
}

export interface DAGEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

export interface DAG {
  id: number;
  dag_id: string;
  name: string;
  description?: string;
  schedule_interval?: string;
  is_active: boolean;
  is_paused: boolean;
  tags: string[];
  owner_id?: number;
  created_at: string;
  updated_at: string;
}

export interface DAGRun {
  id: number;
  dag_id: number;
  run_id: string;
  execution_date: string;
  state: 'queued' | 'running' | 'success' | 'failed' | 'cancelled' | 'paused';
  start_date?: string;
  end_date?: string;
  run_type: string;
}

export interface TaskType {
  type: string;
  name: string;
  category: string;
}

interface WorkflowState {
  // State
  dags: DAG[];
  currentDag: DAG | null;
  currentDagNodes: DAGNode[];
  currentDagEdges: DAGEdge[];
  taskTypes: TaskType[];
  etlPipelines: any[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchDags: () => Promise<void>;
  fetchDag: (dagId: string) => Promise<void>;
  createDag: (data: any) => Promise<DAG>;
  updateDag: (dagId: string, data: any) => Promise<void>;
  deleteDag: (dagId: string) => Promise<void>;
  triggerDagRun: (dagId: string, conf?: any) => Promise<void>;
  pauseDag: (dagId: string) => Promise<void>;
  unpauseDag: (dagId: string) => Promise<void>;
  getDagRuns: (dagId: string) => Promise<DAGRun[]>;
  getTaskInstances: (runId: string) => Promise<any>;
  fetchTaskTypes: () => Promise<void>;
  fetchEtlPipelines: () => Promise<void>;

  // Export/Import actions
  exportDag: (dagId: string) => Promise<any>;
  importDag: (data: any) => Promise<any>;
  cloneDag: (dagId: string, newName?: string) => Promise<any>;
  exportCurrentDag: () => string;
  importDagFromFile: (file: File) => Promise<any>;

  // DAG Builder actions
  setCurrentDag: (dag: DAG | null) => void;
  addNode: (node: DAGNode) => void;
  updateNode: (node: DAGNode) => void;
  deleteNode: (nodeId: string) => void;
  addEdge: (edge: DAGEdge) => void;
  deleteEdge: (edgeId: string) => void;
  clearCurrentDag: () => void;

  // Error handling
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useWorkflowStore = create<WorkflowState>()(
  persist(
    (set, get) => ({
      // Initial state
      dags: [],
      currentDag: null,
      currentDagNodes: [],
      currentDagEdges: [],
      taskTypes: [],
      etlPipelines: [],
      loading: false,
      error: null,

      // Fetch all DAGs
      fetchDags: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/workflows/dags');
          set({ dags: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch DAGs',
            loading: false,
          });
          throw error;
        }
      },

      // Fetch single DAG
      fetchDag: async (dagId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/workflows/dags/${dagId}`);
          set({ currentDag: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Create DAG
      createDag: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/workflows/dags', data);
          set((state) => ({
            dags: [...state.dags, response.data],
            loading: false,
          }));
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Update DAG
      updateDag: async (dagId: string, data) => {
        set({ loading: true, error: null });
        try {
          await api.put(`/workflows/dags/${dagId}`, data);
          await set((state) => {
            const updated = state.dags.map((dag) =>
              dag.dag_id === dagId ? { ...dag, ...data } : dag
            );
            return { dags: updated, loading: false };
          });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to update DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Delete DAG
      deleteDag: async (dagId: string) => {
        set({ loading: true, error: null });
        try:
          await api.delete(`/workflows/dags/${dagId}`);
          set((state) => ({
            dags: state.dags.filter((dag) => dag.dag_id !== dagId),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Trigger DAG run
      triggerDagRun: async (dagId: string, conf?: any) => {
        set({ loading: true, error: null });
        try:
          await api.post(`/workflows/dags/${dagId}/run`, { conf });
          set({ loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to trigger DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Pause DAG
      pauseDag: async (dagId: string) => {
        set({ loading: true, error: null });
        try:
          await api.post(`/workflows/dags/${dagId}/pause`);
          set((state) => ({
            dags: state.dags.map((dag) =>
              dag.dag_id === dagId ? { ...dag, is_paused: true } : dag
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to pause DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Unpause DAG
      unpauseDag: async (dagId: string) => {
        set({ loading: true, error: null });
        try:
          await api.post(`/workflows/dags/${dagId}/unpause`);
          set((state) => ({
            dags: state.dags.map((dag) =>
              dag.dag_id === dagId ? { ...dag, is_paused: false } : dag
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to unpause DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Get DAG runs
      getDagRuns: async (dagId: string) => {
        try:
          const response = await api.get(`/workflows/dags/${dagId}/runs`);
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to get DAG runs',
          });
          throw error;
        }
      },

      // Get task instances
      getTaskInstances: async (runId: string) => {
        try:
          const response = await api.get(`/workflows/runs/${runId}/tasks`);
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to get task instances',
          });
          throw error;
        }
      },

      // Fetch task types
      fetchTaskTypes: async () => {
        try {
          const response = await api.get('/workflows/task-types');
          set({ taskTypes: response.data });
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Failed to fetch task types' });
          throw error;
        }
      },

      // Fetch ETL pipelines for workflow integration
      fetchEtlPipelines: async () => {
        try {
          const response = await api.get('/workflows/etl-pipelines');
          set({ etlPipelines: response.data });
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Failed to fetch ETL pipelines' });
          throw error;
        }
      },

      // Export DAG from server
      exportDag: async (dagId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/workflows/dags/${dagId}/export`);
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to export DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Import DAG to server
      importDag: async (data: any) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/workflows/dags/import', data);
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to import DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Clone DAG
      cloneDag: async (dagId: string, newName?: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post(`/workflows/dags/${dagId}/clone`, { new_name: newName });
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to clone DAG',
            loading: false,
          });
          throw error;
        }
      },

      // Export current DAG (editor state) to JSON
      exportCurrentDag: () => {
        const state = get();
        const exportData = {
          version: '1.0',
          exported_at: new Date().toISOString(),
          dag: {
            dag_id: state.currentDag?.dag_id || 'untitled',
            name: state.currentDag?.name || 'Untitled Workflow',
            description: state.currentDag?.description,
            schedule_interval: state.currentDag?.schedule_interval,
            tags: state.currentDag?.tags || [],
            tasks: state.currentDagNodes.map((node) => ({
              task_id: node.id,
              task_type: node.task_type,
              name: node.name,
              description: node.config?.description,
              depends_on: node.config?.depends_on || [],
              retry_count: node.config?.retry_count || 0,
              retry_delay_seconds: node.config?.retry_delay_seconds || 300,
              timeout_seconds: node.config?.timeout_seconds,
              parameters: node.config?.parameters || {},
              position: node.position,
            })),
            edges: state.currentDagEdges,
          },
        };
        return JSON.stringify(exportData, null, 2);
      },

      // Import DAG from file
      importDagFromFile: async (file: File) => {
        set({ loading: true, error: null });
        try {
          const text = await file.text();
          const data = JSON.parse(text);

          // Validate import data
          if (!data.dag) {
            throw new Error('Invalid import file: missing dag data');
          }

          // Import via API
          const response = await api.post('/workflows/dags/import', data);
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({
            error: error.message || 'Failed to import DAG file',
            loading: false,
          });
          throw error;
        }
      },

      // Current DAG management
      setCurrentDag: (dag: DAG | null) => {
        set({ currentDag: dag });
      },

      addNode: (node: DAGNode) => {
        set((state) => ({
          currentDagNodes: [...state.currentDagNodes, node],
        }));
      },

      updateNode: (node: DAGNode) => {
        set((state) => ({
          currentDagNodes: state.currentDagNodes.map((n) =>
            n.id === node.id ? node : n
          ),
        }));
      },

      deleteNode: (nodeId: string) => {
        set((state) => ({
          currentDagNodes: state.currentDagNodes.filter((n) => n.id !== nodeId),
          currentDagEdges: state.currentDagEdges.filter(
            (e) => e.source !== nodeId && e.target !== nodeId
          ),
        }));
      },

      addEdge: (edge: DAGEdge) => {
        set((state) => ({
          currentDagEdges: [...state.currentDagEdges, edge],
        }));
      },

      deleteEdge: (edgeId: string) => {
        set((state) => ({
          currentDagEdges: state.currentDagEdges.filter((e) => e.id !== edgeId),
        }));
      },

      clearCurrentDag: () => {
        set({
          currentDag: null,
          currentDagNodes: [],
          currentDagEdges: [],
        });
      },

      // Error handling
      setError: (error: string | null) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'workflow-store',
      partialize: (state) => ({
        dags: state.dags,
        taskTypes: state.taskTypes,
        etlPipelines: state.etlPipelines,
      }),
    }
  )
);

// Selectors
export const useCurrentDag = () => useWorkflowStore((state) => state.currentDag);
export const useCurrentDagNodes = () => useWorkflowStore((state) => state.currentDagNodes);
export const useCurrentDagEdges = () => useWorkflowStore((state) => state.currentDagEdges);
export const useWorkflowLoading = () => useWorkflowStore((state) => state.loading);
export const useWorkflowError = () => useWorkflowStore((state) => state.error);
export const useEtlPipelines = () => useWorkflowStore((state) => state.etlPipelines);
