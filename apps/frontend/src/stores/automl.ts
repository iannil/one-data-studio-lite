/**
 * AutoML Store - Zustand state management for AutoML
 */

import { create } from "zustand";
import { api } from "@/services/api";
import type {
  AutoMLExperiment,
  AutoMLTrial,
  AutoMLModel,
  ExperimentCreateRequest,
  TrainingRequest,
  ExperimentFilters,
  ModelFilters,
  SearchSpaceDefinition,
  HealthStatus,
  ProblemType,
  ExperimentStatus,
  DeploymentStatus,
} from "@/types/automl";

interface AutoMLState {
  // Experiments
  experiments: AutoMLExperiment[];
  currentExperiment: AutoMLExperiment | null;
  experimentsLoading: boolean;
  experimentsError: string | null;
  experimentsFilters: ExperimentFilters;

  // Trials
  trials: AutoMLTrial[];
  trialsLoading: boolean;
  trialsError: string | null;

  // Models
  models: AutoMLModel[];
  currentModel: AutoMLModel | null;
  modelsLoading: boolean;
  modelsError: string | null;
  modelsFilters: ModelFilters;

  // Search Spaces
  searchSpaces: SearchSpaceDefinition | null;
  searchSpacesLoading: boolean;

  // Health
  healthStatus: HealthStatus | null;
  healthStatusLoading: boolean;

  // Actions
  fetchExperiments: (filters?: ExperimentFilters) => Promise<void>;
  fetchExperiment: (id: string) => Promise<void>;
  createExperiment: (data: ExperimentCreateRequest) => Promise<AutoMLExperiment>;
  updateExperiment: (id: string, data: Partial<ExperimentCreateRequest>) => Promise<void>;
  deleteExperiment: (id: string) => Promise<void>;
  startExperiment: (data: TrainingRequest) => Promise<void>;
  stopExperiment: (id: string) => Promise<void>;

  fetchTrials: (experimentId: string) => Promise<void>;

  fetchModels: (filters?: ModelFilters) => Promise<void>;
  fetchModel: (id: string) => Promise<void>;
  deployModel: (id: string, deploymentStatus: DeploymentStatus) => Promise<void>;

  fetchSearchSpaces: (modelType?: string) => Promise<void>;
  fetchHealthStatus: () => Promise<void>;

  setCurrentExperiment: (experiment: AutoMLExperiment | null) => void;
  setCurrentModel: (model: AutoMLModel | null) => void;
  setExperimentsFilters: (filters: Partial<ExperimentFilters>) => void;
  setModelsFilters: (filters: Partial<ModelFilters>) => void;
  reset: () => void;
}

const initialState = {
  experiments: [],
  currentExperiment: null,
  experimentsLoading: false,
  experimentsError: null,
  experimentsFilters: { limit: 100, offset: 0 },

  trials: [],
  trialsLoading: false,
  trialsError: null,

  models: [],
  currentModel: null,
  modelsLoading: false,
  modelsError: null,
  modelsFilters: { limit: 100, offset: 0 },

  searchSpaces: null,
  searchSpacesLoading: false,

  healthStatus: null,
  healthStatusLoading: false,
};

export const useAutoMLStore = create<AutoMLState>((set, get) => ({
  ...initialState,

  fetchExperiments: async (filters?: ExperimentFilters) => {
    set({ experimentsLoading: true, experimentsError: null });
    try {
      const params = filters || get().experimentsFilters;
      const response = await api.get("/automl/experiments", { params });
      set({
        experiments: response.data,
        experimentsLoading: false,
        experimentsFilters: { ...get().experimentsFilters, ...params },
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to fetch experiments";
      set({ experimentsLoading: false, experimentsError: message });
    }
  },

  fetchExperiment: async (id: string) => {
    set({ experimentsLoading: true, experimentsError: null });
    try {
      const response = await api.get(`/automl/experiments/${id}`);
      set({
        currentExperiment: response.data,
        experimentsLoading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to fetch experiment";
      set({ experimentsLoading: false, experimentsError: message });
    }
  },

  createExperiment: async (data: ExperimentCreateRequest) => {
    set({ experimentsLoading: true, experimentsError: null });
    try {
      const response = await api.post("/automl/experiments", data);
      set((state) => ({
        experiments: [...state.experiments, response.data],
        experimentsLoading: false,
      }));
      return response.data;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to create experiment";
      set({ experimentsLoading: false, experimentsError: message });
      throw error;
    }
  },

  updateExperiment: async (id: string, data: Partial<ExperimentCreateRequest>) => {
    set({ experimentsLoading: true, experimentsError: null });
    try {
      const response = await api.put(`/automl/experiments/${id}`, data);
      set((state) => ({
        experiments: state.experiments.map((exp) =>
          exp.id === id ? response.data : exp
        ),
        currentExperiment: state.currentExperiment?.id === id ? response.data : state.currentExperiment,
        experimentsLoading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to update experiment";
      set({ experimentsLoading: false, experimentsError: message });
      throw error;
    }
  },

  deleteExperiment: async (id: string) => {
    set({ experimentsLoading: true, experimentsError: null });
    try {
      await api.delete(`/automl/experiments/${id}`);
      set((state) => ({
        experiments: state.experiments.filter((exp) => exp.id !== id),
        currentExperiment: state.currentExperiment?.id === id ? null : state.currentExperiment,
        experimentsLoading: false,
      }));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to delete experiment";
      set({ experimentsLoading: false, experimentsError: message });
      throw error;
    }
  },

  startExperiment: async (data: TrainingRequest) => {
    set({ experimentsLoading: true, experimentsError: null });
    try {
      await api.post(`/automl/experiments/${data.experiment_id}/start`, data);
      // Update the experiment status
      if (get().currentExperiment?.id === data.experiment_id) {
        await get().fetchExperiment(data.experiment_id);
      }
      set({ experimentsLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to start experiment";
      set({ experimentsLoading: false, experimentsError: message });
      throw error;
    }
  },

  stopExperiment: async (id: string) => {
    set({ experimentsLoading: true, experimentsError: null });
    try {
      await api.post(`/automl/experiments/${id}/stop`);
      // Update the experiment status
      if (get().currentExperiment?.id === id) {
        await get().fetchExperiment(id);
      }
      set({ experimentsLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to stop experiment";
      set({ experimentsLoading: false, experimentsError: message });
      throw error;
    }
  },

  fetchTrials: async (experimentId: string) => {
    set({ trialsLoading: true, trialsError: null });
    try {
      const response = await api.get(`/automl/experiments/${experimentId}/trials`);
      set({
        trials: response.data,
        trialsLoading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to fetch trials";
      set({ trialsLoading: false, trialsError: message });
    }
  },

  fetchModels: async (filters?: ModelFilters) => {
    set({ modelsLoading: true, modelsError: null });
    try {
      const params = filters || get().modelsFilters;
      const response = await api.get("/automl/models", { params });
      set({
        models: response.data,
        modelsLoading: false,
        modelsFilters: { ...get().modelsFilters, ...params },
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to fetch models";
      set({ modelsLoading: false, modelsError: message });
    }
  },

  fetchModel: async (id: string) => {
    set({ modelsLoading: true, modelsError: null });
    try {
      const response = await api.get(`/automl/models/${id}`);
      set({
        currentModel: response.data,
        modelsLoading: false,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to fetch model";
      set({ modelsLoading: false, modelsError: message });
    }
  },

  deployModel: async (id: string, deploymentStatus: DeploymentStatus) => {
    set({ modelsLoading: true, modelsError: null });
    try {
      await api.post(`/automl/models/${id}/deploy`, { deployment_status: deploymentStatus });
      // Refresh the model
      await get().fetchModel(id);
      set({ modelsLoading: false });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to deploy model";
      set({ modelsLoading: false, modelsError: message });
      throw error;
    }
  },

  fetchSearchSpaces: async (modelType?: string) => {
    set({ searchSpacesLoading: true });
    try {
      const params = modelType ? { model_type: modelType } : {};
      const response = await api.get("/automl/search-spaces", { params });
      set({
        searchSpaces: response.data.search_spaces,
        searchSpacesLoading: false,
      });
    } catch (error: unknown) {
      set({ searchSpacesLoading: false });
    }
  },

  fetchHealthStatus: async () => {
    set({ healthStatusLoading: true });
    try {
      const response = await api.get("/automl/health");
      set({
        healthStatus: response.data,
        healthStatusLoading: false,
      });
    } catch (error: unknown) {
      set({ healthStatusLoading: false });
    }
  },

  setCurrentExperiment: (experiment: AutoMLExperiment | null) => {
    set({ currentExperiment: experiment });
  },

  setCurrentModel: (model: AutoMLModel | null) => {
    set({ currentModel: model });
  },

  setExperimentsFilters: (filters: Partial<ExperimentFilters>) => {
    set({ experimentsFilters: { ...get().experimentsFilters, ...filters } });
  },

  setModelsFilters: (filters: Partial<ModelFilters>) => {
    set({ modelsFilters: { ...get().modelsFilters, ...filters } });
  },

  reset: () => {
    set(initialState);
  },
}));
