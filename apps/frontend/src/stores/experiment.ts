/**
 * Experiment Store
 *
 * Zustand store for managing MLflow experiment state and API calls.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';

// Types
export interface Experiment {
  id: string;
  name: string;
  description?: string;
  artifact_location?: string;
  lifecycle_stage: string;
  tags?: Record<string, string>;
  created_at: string;
  updated_at?: string;
  run_count?: number;
  best_run?: Run;
}

export interface Run {
  run_id: string;
  run_uuid: string;
  run_name?: string;
  experiment_id: string;
  status: 'running' | 'completed' | 'failed' | 'killed' | 'scheduled';
  lifecycle_stage: string;
  start_time?: number;
  end_time?: number;
  artifact_uri?: string;
  params?: Record<string, string>;
  metrics?: Record<string, number>;
  tags?: Record<string, string>;
  artifacts?: Artifact[];
}

export interface Artifact {
  path: string;
  is_dir: boolean;
  size?: number;
}

export interface MetricHistory {
  key: string;
  value: number;
  timestamp: number;
  step: number;
}

export interface MetricComparison {
  runs: Run[];
  param_keys: string[];
  metric_keys: string[];
  metric_stats?: Record<string, {
    values: Array<{
      run_id: string;
      run_name: string;
      value: number;
    }>;
    min: number;
    max: number;
    mean: number;
    median: number;
    stdev: number;
  }>;
}

interface ExperimentState {
  // State
  experiments: Experiment[];
  currentExperiment: Experiment | null;
  runs: Run[];
  currentRun: Run | null;
  loading: boolean;
  error: string | null;

  // Experiment actions
  fetchExperiments: (projectId?: string, search?: string) => Promise<void>;
  fetchExperiment: (experimentId: string) => Promise<void>;
  createExperiment: (data: {
    name: string;
    description?: string;
    tags?: Record<string, string>;
    projectId?: number;
  }) => Promise<Experiment>;
  updateExperiment: (
    experimentId: string,
    data: { name?: string; description?: string; tags?: Record<string, string> }
  ) => Promise<void>;
  deleteExperiment: (experimentId: string) => Promise<void>;
  restoreExperiment: (experimentId: string) => Promise<void>;

  // Run actions
  fetchRuns: (experimentId: string, maxResults?: number, status?: string) => Promise<void>;
  fetchRun: (runId: string) => Promise<void>;
  createRun: (data: {
    experimentId: string;
    runName?: string;
    tags?: Record<string, string>;
  }) => Promise<Run>;
  deleteRun: (runId: string) => Promise<void>;

  // Logging actions
  logParams: (runId: string, params: Record<string, any>) => Promise<void>;
  logMetrics: (runId: string, metrics: Record<string, number>, step?: number) => Promise<void>;
  logBatch: (
    runId: string,
    data: {
      params?: Record<string, any>;
      metrics?: Record<string, number>;
      tags?: Record<string, string>;
    }
  ) => Promise<void>;
  setRunStatus: (runId: string, status: 'FINISHED' | 'FAILED' | 'KILLED') => Promise<void>;

  // Metric actions
  getMetricHistory: (runId: string, metricKey: string) => Promise<MetricHistory[]>;
  compareMetrics: (runIds: string[], metricKeys?: string[]) => Promise<MetricComparison>;
  getMetricSummary: (experimentId: string, metricKey?: string) => Promise<any>;
  getMetricCorrelation: (experimentId: string, metricKey: string) => Promise<any>;

  // Comparison actions
  compareRuns: (runIds: string[]) => Promise<MetricComparison>;

  // Artifact actions
  listArtifacts: (runId: string, path?: string) => Promise<Artifact[]>;

  // State management
  setCurrentExperiment: (experiment: Experiment | null) => void;
  setCurrentRun: (run: Run | null) => void;
  clearError: () => void;
}

export const useExperimentStore = create<ExperimentState>()(
  persist(
    (set, get) => ({
      // Initial state
      experiments: [],
      currentExperiment: null,
      runs: [],
      currentRun: null,
      loading: false,
      error: null,

      // Experiment actions
      fetchExperiments: async (projectId?: string, search?: string) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, string> = {};
          if (projectId) params.project_id = String(projectId);
          if (search) params.search = search;

          const response = await api.get('/experiments', { params });
          set({ experiments: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch experiments',
            loading: false,
          });
          throw error;
        }
      },

      fetchExperiment: async (experimentId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/experiments/${experimentId}`);
          set({ currentExperiment: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch experiment',
            loading: false,
          });
          throw error;
        }
      },

      createExperiment: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/experiments', data);
          set((state) => ({
            experiments: [...state.experiments, response.data],
            loading: false,
          }));
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create experiment',
            loading: false,
          });
          throw error;
        }
      },

      updateExperiment: async (experimentId, data) => {
        set({ loading: true, error: null });
        try {
          await api.put(`/experiments/${experimentId}`, data);
          set((state) => ({
            experiments: state.experiments.map((exp) =>
              exp.id === experimentId ? { ...exp, ...data } : exp
            ),
            currentExperiment: state.currentExperiment?.id === experimentId
              ? { ...state.currentExperiment, ...data }
              : state.currentExperiment,
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to update experiment',
            loading: false,
          });
          throw error;
        }
      },

      deleteExperiment: async (experimentId: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/experiments/${experimentId}`);
          set((state) => ({
            experiments: state.experiments.filter((exp) => exp.id !== experimentId),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete experiment',
            loading: false,
          });
          throw error;
        }
      },

      restoreExperiment: async (experimentId: string) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/experiments/${experimentId}/restore`);
          await get().fetchExperiments();
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to restore experiment',
            loading: false,
          });
          throw error;
        }
      },

      // Run actions
      fetchRuns: async (experimentId: string, maxResults = 100, status?: string) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, string | number> = { max_results: maxResults };
          if (status) params.status = status;

          const response = await api.get(`/experiments/${experimentId}/runs`, { params });
          set({ runs: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch runs',
            loading: false,
          });
          throw error;
        }
      },

      fetchRun: async (runId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/experiments/runs/${runId}`);
          set({ currentRun: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch run',
            loading: false,
          });
          throw error;
        }
      },

      createRun: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/experiments/runs', data);
          set((state) => ({
            runs: [response.data, ...state.runs],
            loading: false,
          }));
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create run',
            loading: false,
          });
          throw error;
        }
      },

      deleteRun: async (runId: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/experiments/runs/${runId}`);
          set((state) => ({
            runs: state.runs.filter((run) => run.run_id !== runId),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete run',
            loading: false,
          });
          throw error;
        }
      },

      // Logging actions
      logParams: async (runId: string, params: Record<string, any>) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/experiments/runs/${runId}/params`, { params });
          set({ loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to log params',
            loading: false,
          });
          throw error;
        }
      },

      logMetrics: async (runId: string, metrics: Record<string, number>, step = 0) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/experiments/runs/${runId}/metrics`, { metrics, step });
          set({ loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to log metrics',
            loading: false,
          });
          throw error;
        }
      },

      logBatch: async (runId, data) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/experiments/runs/${runId}/batch`, data);
          set({ loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to log batch',
            loading: false,
          });
          throw error;
        }
      },

      setRunStatus: async (runId, status) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/experiments/runs/${runId}/status`, null, {
            params: { run_status: status },
          });
          set((state) => ({
            runs: state.runs.map((run) =>
              run.run_id === runId ? { ...run, status: status.toLowerCase() as any } : run
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to set run status',
            loading: false,
          });
          throw error;
        }
      },

      // Metric actions
      getMetricHistory: async (runId: string, metricKey: string) => {
        try {
          const response = await api.get(`/experiments/runs/${runId}/metrics/history`, {
            params: { metric_key: metricKey },
          });
          return response.data.history;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to get metric history',
          });
          throw error;
        }
      },

      compareMetrics: async (runIds: string[], metricKeys?: string[]) => {
        try {
          const response = await api.post('/experiments/metrics/compare', {
            run_ids: runIds,
            metric_keys: metricKeys,
          });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to compare metrics',
          });
          throw error;
        }
      },

      getMetricSummary: async (experimentId: string, metricKey?: string) => {
        try {
          const params: Record<string, string> = {};
          if (metricKey) params.metric_key = metricKey;

          const response = await api.get(`/experiments/${experimentId}/metrics/summary`, {
            params,
          });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to get metric summary',
          });
          throw error;
        }
      },

      getMetricCorrelation: async (experimentId: string, metricKey: string) => {
        try {
          const response = await api.get(`/experiments/${experimentId}/metrics/correlation`, {
            params: { metric_key: metricKey },
          });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to get metric correlation',
          });
          throw error;
        }
      },

      // Comparison actions
      compareRuns: async (runIds: string[]) => {
        try {
          const response = await api.post('/experiments/runs/compare', runIds);
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to compare runs',
          });
          throw error;
        }
      },

      // Artifact actions
      listArtifacts: async (runId: string, path?: string) => {
        try {
          const params: Record<string, string> = {};
          if (path) params.path = path;

          const response = await api.get(`/experiments/runs/${runId}/artifacts`, { params });
          return response.data.artifacts;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to list artifacts',
          });
          throw error;
        }
      },

      // State management
      setCurrentExperiment: (experiment) => set({ currentExperiment: experiment }),
      setCurrentRun: (run) => set({ currentRun: run }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'experiment-store',
      partialize: (state) => ({
        experiments: state.experiments,
      }),
    }
  )
);

// Selectors
export const useExperiments = () => useExperimentStore((state) => state.experiments);
export const useCurrentExperiment = () => useExperimentStore((state) => state.currentExperiment);
export const useRuns = () => useExperimentStore((state) => state.runs);
export const useCurrentRun = () => useExperimentStore((state) => state.currentRun);
export const useExperimentLoading = () => useExperimentStore((state) => state.loading);
export const useExperimentError = () => useExperimentStore((state) => state.error);
