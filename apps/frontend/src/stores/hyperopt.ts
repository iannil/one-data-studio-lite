/**
 * Hyperparameter Optimization Store
 *
 * Zustand store for managing hyperparameter optimization state and API calls.
 */

import { create } from 'zustand';
import api from '@/services/api';

// Types
export type StudyStatus = 'created' | 'running' | 'completed' | 'failed' | 'cancelled';
export type OptimizationDirection = 'maximize' | 'minimize';
export type SamplerType = 'random' | 'tpe' | 'cmaes' | 'grid' | 'quasi_monte_carlo' | 'particle_swarm';
export type PrunerType = 'none' | 'median' | 'successive_halving' | 'hyperband' | 'sha';
export type TrialStatus = 'running' | 'completed' | 'pruned' | 'failed';
export type HyperparamType =
  | 'categorical'
  | 'float_uniform'
  | 'float_log_uniform'
  | 'float_discrete_uniform'
  | 'int_uniform'
  | 'int_log_uniform';

export interface OptimizationStudy {
  study_id: string;
  name: string;
  experiment_id?: string;
  project_id?: number;
  metric: string;
  direction: OptimizationDirection;
  sampler: SamplerType;
  pruner: PrunerType;
  n_trials: number;
  status: StudyStatus;
  progress: number;
  best_value: number | null;
  best_params?: Record<string, any>;
  completed_trials: number;
  created_at: string;
  start_time?: string;
  end_time?: string;
  n_warmup_steps?: number;
  early_stopping_rounds?: number;
  early_stopping_threshold?: number;
  timeout_hours?: number;
  n_jobs?: number;
  search_space?: SearchSpaceConfig;
}

export interface SearchSpaceConfig {
  categorical?: Record<string, string[]>;
  float_uniform?: Record<string, [number, number]>;
  float_log_uniform?: Record<string, [number, number]>;
  float_discrete_uniform?: Record<string, [number, number, number]>;
  int_uniform?: Record<string, [number, number]>;
  int_log_uniform?: Record<string, [number, number]>;
}

export interface Trial {
  trial_number: number;
  trial_id: string;
  params: Record<string, any>;
  value: number;
  status: TrialStatus;
  start_time: string;
  end_time?: string;
}

export interface StudyHistory {
  study_id: string;
  name: string;
  metric: string;
  direction: string;
  best_value: number | null;
  best_params: Record<string, any> | null;
  trials: Trial[];
  status: string;
  progress: number;
  created_at: string;
  start_time?: string;
  end_time?: string;
}

export interface OptimizationTemplate {
  id: string;
  name: string;
  framework: string;
  description: string;
  metric: string;
  direction: string;
  sampler?: SamplerType;
  n_trials?: number;
  search_space?: SearchSpaceConfig;
}

interface HyperoptState {
  // State
  studies: OptimizationStudy[];
  currentStudy: OptimizationStudy | null;
  trials: Trial[];
  history: StudyHistory | null;
  templates: OptimizationTemplate[];
  samplers: any[];
  pruners: any[];
  loading: boolean;
  error: string | null;

  // Actions - Studies
  fetchStudies: (projectId?: number, status?: string) => Promise<void>;
  fetchStudy: (studyId: string) => Promise<void>;
  createStudy: (config: StudyCreateConfig) => Promise<OptimizationStudy>;
  deleteStudy: (studyId: string) => Promise<void>;

  // Actions - Trials
  fetchTrials: (studyId: string, status?: TrialStatus) => Promise<void>;
  fetchHistory: (studyId: string) => Promise<void>;

  // Actions - Templates
  fetchTemplates: (framework?: string) => Promise<void>;
  fetchSamplers: () => Promise<void>;
  fetchPruners: () => Promise<void>;

  // Error handling
  setError: (error: string | null) => void;
  clearError: () => void;
}

export interface StudyCreateConfig {
  name: string;
  experiment_id?: string;
  project_id?: number;
  metric: string;
  direction: OptimizationDirection;
  sampler: SamplerType;
  pruner: PrunerType;
  n_trials: number;
  timeout_hours?: number;
  n_jobs?: number;
  n_warmup_steps?: number;
  early_stopping_rounds?: number;
  early_stopping_threshold?: number;
  search_space?: SearchSpaceConfig;
}

export const useHyperoptStore = create<HyperoptState>()((set, get) => ({
  // Initial state
  studies: [],
  currentStudy: null,
  trials: [],
  history: null,
  templates: [],
  samplers: [],
  pruners: [],
  loading: false,
  error: null,

  // Fetch all studies
  fetchStudies: async (projectId?: number, status?: string) => {
    set({ loading: true, error: null });
    try {
      const params: any = {};
      if (projectId) params.project_id = projectId;
      if (status) params.status = status;

      const response = await api.get('/experiments/hyperopt/studies', { params });
      set({ studies: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to fetch studies', loading: false });
    }
  },

  // Fetch single study
  fetchStudy: async (studyId: string) => {
    set({ loading: true, error: null });
    try {
      const response = await api.get(`/experiments/hyperopt/studies/${studyId}`);
      set({ currentStudy: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to fetch study', loading: false });
    }
  },

  // Create study
  createStudy: async (config: StudyCreateConfig) => {
    set({ loading: true, error: null });
    try {
      // Convert search_space from param format to format expected by API
      const searchSpaceParams = config.search_space as any;
      const search_space: any = {};
      const search_space_params: any[] = [];

      if (searchSpaceParams) {
        if (searchSpaceParams.categorical) search_space.categorical = searchSpaceParams.categorical;
        if (searchSpaceParams.float_uniform) search_space.float_uniform = searchSpaceParams.float_uniform;
        if (searchSpaceParams.float_log_uniform) search_space.float_log_uniform = searchSpaceParams.float_log_uniform;
        if (searchSpaceParams.float_discrete_uniform) search_space.float_discrete_uniform = searchSpaceParams.float_discrete_uniform;
        if (searchSpaceParams.int_uniform) search_space.int_uniform = searchSpaceParams.int_uniform;
        if (searchSpaceParams.int_log_uniform) search_space.int_log_uniform = searchSpaceParams.int_log_uniform;
      }

      const response = await api.post('/experiments/hyperopt/studies', {
        ...config,
        search_space,
      });

      set({ loading: false });
      return response.data;
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to create study', loading: false });
      throw err;
    }
  },

  // Delete study
  deleteStudy: async (studyId: string) => {
    set({ loading: true, error: null });
    try {
      await api.delete(`/experiments/hyperopt/studies/${studyId}`);
      set((state) => ({
        studies: state.studies.filter((s) => s.study_id !== studyId),
        loading: false,
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to delete study', loading: false });
      throw err;
    }
  },

  // Fetch trials for a study
  fetchTrials: async (studyId: string, status?: TrialStatus) => {
    set({ loading: true, error: null });
    try {
      const params: any = {};
      if (status) params.status = status;

      const response = await api.get(`/experiments/hyperopt/studies/${studyId}/trials`, { params });
      set({ trials: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to fetch trials', loading: false });
    }
  },

  // Fetch study history
  fetchHistory: async (studyId: string) => {
    set({ loading: true, error: null });
    try {
      const response = await api.get(`/experiments/hyperopt/studies/${studyId}/history`);
      set({ history: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to fetch history', loading: false });
    }
  },

  // Fetch templates
  fetchTemplates: async (framework?: string) => {
    set({ loading: true, error: null });
    try {
      const params: any = {};
      if (framework) params.framework = framework;

      const response = await api.get('/experiments/hyperopt/templates', { params });
      set({ templates: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to fetch templates', loading: false });
    }
  },

  // Fetch samplers
  fetchSamplers: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.get('/experiments/hyperopt/samplers');
      set({ samplers: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to fetch samplers', loading: false });
    }
  },

  // Fetch pruners
  fetchPruners: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.get('/experiments/hyperopt/pruners');
      set({ pruners: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to fetch pruners', loading: false });
    }
  },

  // Set error
  setError: (error: string | null) => set({ error }),
  clearError: () => set({ error: null }),
}));
