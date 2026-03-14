/**
 * Training Store
 *
 * Zustand store for managing training job state and API calls.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';
import type {
  TrainingJob,
  TrainingConfig,
  TrainingBackend,
  TrainingStatus,
  TrainingTemplate,
  ResourceConfig,
  DistributedStrategy,
  TrainingJobFilters,
  TrainingSortOptions,
  TrainingStats,
  TrainingNode,
  ValidationResult,
} from '@/types/training';

interface TrainingState {
  // State
  jobs: TrainingJob[];
  currentJob: TrainingJob | null;
  selectedJobIds: string[];
  templates: TrainingTemplate[];
  backends: any[];
  strategies: any[];
  loading: boolean;
  error: string | null;
  filters: TrainingJobFilters;
  sort: TrainingSortOptions;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };

  // Actions - Jobs
  fetchJobs: () => Promise<void>;
  fetchJob: (jobId: string) => Promise<TrainingJob | null>;
  createJob: (config: TrainingConfig) => Promise<TrainingJob>;
  cancelJob: (jobId: string) => Promise<void>;
  deleteJob: (jobId: string) => Promise<void>;
  getJobLogs: (jobId: string, follow?: boolean, tailLines?: number) => Promise<string>;
  getJobMetrics: (jobId: string) => Promise<Record<string, any> | null>;
  getJobNodes: (jobId: string) => Promise<TrainingNode[]>;

  // Actions - Templates
  fetchTemplates: (framework?: TrainingBackend) => Promise<void>;
  fetchBackends: () => Promise<void>;
  fetchStrategies: () => Promise<void>;

  // Actions - Validation
  validateConfig: (config: TrainingConfig) => Promise<ValidationResult>;

  // Actions - Selection
  selectJob: (jobId: string) => void;
  selectMultipleJobs: (jobIds: string[]) => void;
  clearSelection: () => void;

  // Actions - Filters
  setFilters: (filters: Partial<TrainingJobFilters>) => void;
  setSort: (sort: TrainingSortOptions) => void;
  setPage: (page: number) => void;

  // Actions - Stats
  getStats: () => TrainingStats;

  // Error handling
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useTrainingStore = create<TrainingState>()(
  persist(
    (set, get) => ({
      // Initial state
      jobs: [],
      currentJob: null,
      selectedJobIds: [],
      templates: [],
      backends: [],
      strategies: [],
      loading: false,
      error: null,
      filters: {},
      sort: { field: 'created_at', order: 'desc' },
      pagination: {
        page: 1,
        pageSize: 20,
        total: 0,
      },

      // Fetch all jobs
      fetchJobs: async () => {
        set({ loading: true, error: null });
        try {
          const { filters, sort } = get();

          // Build query params
          const params = new URLSearchParams();
          if (filters.status) params.append('status', filters.status);
          if (filters.backend) params.append('backend', filters.backend);
          if (filters.experiment_id) params.append('experiment_id', filters.experiment_id);
          params.append('limit', '1000');

          const response = await api.get(`/training/jobs?${params}`);

          // Apply sorting and filtering
          let jobs = response.data || [];

          // Client-side search
          if (filters.search) {
            const search = filters.search.toLowerCase();
            jobs = jobs.filter((j: TrainingJob) =>
              j.name.toLowerCase().includes(search) ||
              j.job_id.toLowerCase().includes(search)
            );
          }

          // Client-side tag filtering
          if (filters.tags && filters.tags.length > 0) {
            jobs = jobs.filter((j: TrainingJob) =>
              filters.tags?.some((tag) => j.tags.includes(tag))
            );
          }

          // Apply sorting
          jobs.sort((a: TrainingJob, b: TrainingJob) => {
            const aVal = a[sort.field as keyof TrainingJob];
            const bVal = b[sort.field as keyof TrainingJob];

            if (sort.field === 'created_at' || sort.field === 'started_at') {
              const aTime = new Date(aVal as string).getTime();
              const bTime = new Date(bVal as string).getTime();
              return sort.order === 'asc' ? aTime - bTime : bTime - aTime;
            }

            if (typeof aVal === 'string' && typeof bVal === 'string') {
              return sort.order === 'asc'
                ? aVal.localeCompare(bVal)
                : bVal.localeCompare(aVal);
            }

            return 0;
          });

          set({
            jobs,
            loading: false,
            pagination: { ...get().pagination, total: jobs.length },
          });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch training jobs',
            loading: false,
          });
          throw error;
        }
      },

      // Fetch single job
      fetchJob: async (jobId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/training/jobs/${jobId}`);
          const job = response.data;
          set({ currentJob: job, loading: false });
          return job;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch training job',
            loading: false,
          });
          throw error;
        }
      },

      // Create job
      createJob: async (config: TrainingConfig) => {
        set({ loading: true, error: null });
        try {
          // Convert to request format
          const request = {
            name: config.name,
            description: config.description,
            experiment_id: config.experiment_id,
            tags: config.tags,
            backend: config.backend,
            strategy: config.strategy,
            entry_point: config.entry_point,
            entry_point_args: config.entry_point_args,
            working_dir: config.working_dir,
            hyperparameters: config.hyperparameters,
            data_config: config.data_config,
            model_config: config.model_config,
            num_nodes: config.num_nodes,
            num_processes_per_node: config.num_processes_per_node,
            master_addr: config.master_addr,
            master_port: config.master_port,
            checkpoint_path: config.checkpoint_path,
            resume_from_checkpoint: config.resume_from_checkpoint,
            save_frequency: config.save_frequency,
            save_total_limit: config.save_total_limit,
            max_steps: config.max_steps,
            max_epochs: config.max_epochs,
            max_duration: config.max_duration,
            resources: config.resources,
            environment: config.environment,
            pip_packages: config.pip_packages,
            image: config.image,
            namespace: config.namespace,
          };

          const response = await api.post('/training/jobs', request);
          const job = response.data;

          set((state) => ({
            jobs: [...state.jobs, job],
            loading: false,
          }));

          return job;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create training job',
            loading: false,
          });
          throw error;
        }
      },

      // Cancel job
      cancelJob: async (jobId: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/training/jobs/${jobId}`);

          set((state) => ({
            jobs: state.jobs.map((j) =>
              j.job_id === jobId ? { ...j, status: 'cancelled' as TrainingStatus } : j
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to cancel training job',
            loading: false,
          });
          throw error;
        }
      },

      // Delete job
      deleteJob: async (jobId: string) => {
        set({ loading: true, error: null });
        try {
          // Cancel first if running
          const job = get().jobs.find((j) => j.job_id === jobId);
          if (job && ['pending', 'starting', 'running'].includes(job.status)) {
            await api.delete(`/training/jobs/${jobId}`);
          }

          set((state) => ({
            jobs: state.jobs.filter((j) => j.job_id !== jobId),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete training job',
            loading: false,
          });
          throw error;
        }
      },

      // Get job logs
      getJobLogs: async (jobId: string, follow = false, tailLines?: number) => {
        try {
          const params = new URLSearchParams();
          if (follow) params.append('follow', 'true');
          if (tailLines) params.append('tail_lines', String(tailLines));

          const response = await api.get(`/training/jobs/${jobId}/logs?${params}`);
          return response.data?.logs || '';
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch job logs',
          });
          throw error;
        }
      },

      // Get job metrics
      getJobMetrics: async (jobId: string) => {
        try {
          const response = await api.get(`/training/jobs/${jobId}/metrics`);
          return response.data?.metrics || {};
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch job metrics',
          });
          throw error;
        }
      },

      // Get job nodes
      getJobNodes: async (jobId: string) => {
        try {
          const response = await api.get(`/training/jobs/${jobId}/nodes`);
          return response.data || [];
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch job nodes',
          });
          return [];
        }
      },

      // Fetch templates
      fetchTemplates: async (framework?: TrainingBackend) => {
        try {
          const params = framework ? `?framework=${framework}` : '';
          const response = await api.get(`/training/templates${params}`);
          set({ templates: response.data || [] });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch templates',
          });
        }
      },

      // Fetch backends
      fetchBackends: async () => {
        try {
          const response = await api.get('/training/backends');
          set({ backends: response.data || [] });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch backends',
          });
        }
      },

      // Fetch strategies
      fetchStrategies: async () => {
        try {
          const response = await api.get('/training/strategies');
          set({ strategies: response.data || [] });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch strategies',
          });
        }
      },

      // Validate config
      validateConfig: async (config: TrainingConfig) => {
        try {
          const response = await api.post('/training/validate', config);
          return response.data;
        } catch (error: any) {
          return {
            valid: false,
            errors: [error.response?.data?.detail || 'Validation failed'],
          };
        }
      },

      // Selection
      selectJob: (jobId: string) => {
        set({ selectedJobIds: [jobId] });
      },

      selectMultipleJobs: (jobIds: string[]) => {
        set({ selectedJobIds: jobIds });
      },

      clearSelection: () => {
        set({ selectedJobIds: [] });
      },

      // Filters
      setFilters: (filters: Partial<TrainingJobFilters>) => {
        set((state) => ({
          filters: { ...state.filters, ...filters },
          pagination: { ...state.pagination, page: 1 },
        }));
      },

      setSort: (sort: TrainingSortOptions) => {
        set({ sort });
      },

      setPage: (page: number) => {
        set((state) => ({
          pagination: { ...state.pagination, page },
        }));
      },

      // Get stats
      getStats: () => {
        const { jobs } = get();
        return {
          total: jobs.length,
          pending: jobs.filter((j) => j.status === 'pending').length,
          running: jobs.filter((j) => j.status === 'running').length,
          completed: jobs.filter((j) => j.status === 'completed').length,
          failed: jobs.filter((j) => j.status === 'failed').length,
          cancelled: jobs.filter((j) => j.status === 'cancelled').length,
        };
      },

      // Error handling
      setError: (error: string | null) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'training-store',
      partialize: (state) => ({
        jobs: state.jobs,
        templates: state.templates,
        backends: state.backends,
        strategies: state.strategies,
      }),
    }
  )
);

// Selectors
export const useCurrentJob = () => useTrainingStore((state) => state.currentJob);
export const useSelectedJobs = () => useTrainingStore((state) =>
  state.jobs.filter((j) => state.selectedJobIds.includes(j.job_id))
);
export const useTrainingLoading = () => useTrainingStore((state) => state.loading);
export const useTrainingError = () => useTrainingStore((state) => state.error);
export const useTrainingStats = () => useTrainingStore((state) => state.getStats());
