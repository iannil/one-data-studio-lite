/**
 * Model Store
 *
 * Zustand store for managing ML model registry and deployments.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';

// Types
export interface RegisteredModel {
  name: string;
  description?: string;
  latest_version?: string;
  production_version?: string;
  staging_version?: string;
  tags?: Record<string, string>;
  creation_time: number;
  last_updated?: number;
}

export interface ModelVersion {
  name: string;
  version: string;
  run_id?: string;
  run_name?: string;
  current_stage: 'None' | 'Staging' | 'Production' | 'Archived';
  status?: string;
  description?: string;
  creation_time: number;
  last_updated?: number;
  source?: string;
  artifacts?: Artifact[];
  run_params?: Record<string, string>;
  run_metrics?: Record<string, number>;
}

export interface Artifact {
  path: string;
  is_dir: boolean;
  size?: number;
}

export interface ModelDeployment {
  id: string;
  name: string;
  model_name: string;
  model_version: string;
  model_uri: string;
  framework: string;
  status: 'deploying' | 'running' | 'failed' | 'stopped';
  replicas: number;
  gpu_enabled: boolean;
  gpu_type?: string;
  gpu_count: number;
  resources: {
    cpu: string;
    memory: string;
    gpu: number;
  };
  endpoint: string;
  url?: string;
  traffic_percentage: number;
  autoscaling: {
    enabled: boolean;
    min_replicas: number;
    max_replicas: number;
  };
  description?: string;
  tags?: Record<string, string>;
  created_at: string;
  updated_at: string;
  model_details?: ModelVersion;
}

export interface CanaryDeployment {
  name: string;
  type: 'canary';
  primary_deployment: ModelDeployment;
  canary_deployment: ModelDeployment;
  canary_traffic_percentage: number;
  endpoint: string;
}

interface ModelState {
  // State
  models: RegisteredModel[];
  currentModel: RegisteredModel | null;
  modelVersions: ModelVersion[];
  currentVersion: ModelVersion | null;
  deployments: ModelDeployment[];
  currentDeployment: ModelDeployment | null;
  loading: boolean;
  error: string | null;

  // Model Registry actions
  fetchModels: (search?: string) => Promise<void>;
  fetchModel: (name: string) => Promise<void>;
  createRegisteredModel: (name: string, description?: string, tags?: Record<string, string>) => Promise<void>;
  deleteModel: (name: string) => Promise<void>;
  renameModel: (name: string, newName: string) => Promise<void>;
  searchModels: (filterString?: string, maxResults?: number) => Promise<void>;

  // Model Version actions
  fetchModelVersions: (name: string) => Promise<void>;
  fetchModelVersion: (name: string, version: string) => Promise<void>;
  registerModelVersion: (data: {
    name: string;
    run_id: string;
    artifact_path: string;
    model_type?: string;
    description?: string;
    tags?: Record<string, string>;
  }) => Promise<void>;
  updateModelVersion: (name: string, version: string, description?: string) => Promise<void>;
  deleteModelVersion: (name: string, version: string) => Promise<void>;
  transitionModelStage: (name: string, version: string, stage: string) => Promise<void>;
  getModelHistory: (name: string, version: string) => Promise<void>;

  // Deployment actions
  fetchDeployments: (modelName?: string, status?: string) => Promise<void>;
  fetchDeployment: (deploymentId: string) => Promise<void>;
  createDeployment: (data: {
    name: string;
    model_name: string;
    model_version: string;
    replicas?: number;
    gpu_enabled?: boolean;
    gpu_type?: string;
    gpu_count?: number;
    cpu?: string;
    memory?: string;
    endpoint?: string;
    traffic_percentage?: number;
    framework?: string;
    autoscaling_enabled?: boolean;
    autoscaling_min?: number;
    autoscaling_max?: number;
    description?: string;
    tags?: Record<string, string>;
  }) => Promise<void>;
  updateDeployment: (deploymentId: string, data: {
    replicas?: number;
    traffic_percentage?: number;
    description?: string;
  }) => Promise<void>;
  deleteDeployment: (deploymentId: string) => Promise<void>;
  scaleDeployment: (deploymentId: string, replicas: number) => Promise<void>;
  rollbackDeployment: (deploymentId: string, targetVersion?: string) => Promise<void>;
  getDeploymentMetrics: (deploymentId: string) => Promise<void>;

  // Canary deployment actions
  createCanaryDeployment: (data: {
    name: string;
    model_name: string;
    current_version: string;
    new_version: string;
    canary_traffic_percentage?: number;
  }) => Promise<void>;
  promoteCanary: (deploymentId: string) => Promise<void>;

  // State management
  setCurrentModel: (model: RegisteredModel | null) => void;
  setCurrentVersion: (version: ModelVersion | null) => void;
  setCurrentDeployment: (deployment: ModelDeployment | null) => void;
  clearError: () => void;
}

export const useModelStore = create<ModelState>()(
  persist(
    (set, get) => ({
      // Initial state
      models: [],
      currentModel: null,
      modelVersions: [],
      currentVersion: null,
      deployments: [],
      currentDeployment: null,
      loading: false,
      error: null,

      // Model Registry actions
      fetchModels: async (search?: string) => {
        set({ loading: true, error: null });
        try {
          const params = search ? { search } : {};
          const response = await api.get('/models/registered', { params });
          set({ models: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch models',
            loading: false,
          });
          throw error;
        }
      },

      fetchModel: async (name: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/models/registered/${name}`);
          set({ currentModel: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch model',
            loading: false,
          });
          throw error;
        }
      },

      createRegisteredModel: async (name, description, tags) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, any> = {};
          if (description) params.description = description;
          if (tags) params.tags = tags;

          await api.post('/models/registered', null, { params });
          await get().fetchModels();
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create model',
            loading: false,
          });
          throw error;
        }
      },

      deleteModel: async (name: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/models/registered/${name}`);
          set((state) => ({
            models: state.models.filter((m) => m.name !== name),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete model',
            loading: false,
          });
          throw error;
        }
      },

      renameModel: async (name: string, newName: string) => {
        set({ loading: true, error: null });
        try {
          await api.put(`/models/registered/${name}/rename`, null, {
            params: { new_name: newName },
          });
          await get().fetchModels();
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to rename model',
            loading: false,
          });
          throw error;
        }
      },

      searchModels: async (filterString, maxResults = 100) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, any> = { max_results: maxResults };
          if (filterString) params.filter_string = filterString;

          const response = await api.get('/models/search', { params });
          set({ models: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to search models',
            loading: false,
          });
          throw error;
        }
      },

      // Model Version actions
      fetchModelVersions: async (name: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/models/registered/${name}`);
          set({ currentModel: response.data, modelVersions: response.data.versions || [], loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch model versions',
            loading: false,
          });
          throw error;
        }
      },

      fetchModelVersion: async (name: string, version: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/models/versions/${name}/${version}`);
          set({ currentVersion: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch model version',
            loading: false,
          });
          throw error;
        }
      },

      registerModelVersion: async (data) => {
        set({ loading: true, error: null });
        try {
          await api.post('/models/versions', data);
          await get().fetchModels();
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to register model',
            loading: false,
          });
          throw error;
        }
      },

      updateModelVersion: async (name: string, version: string, description) => {
        set({ loading: true, error: null });
        try {
          await api.put(`/models/versions/${name}/${version}`, { description });
          await get().fetchModelVersions(name);
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to update model version',
            loading: false,
          });
          throw error;
        }
      },

      deleteModelVersion: async (name: string, version: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/models/versions/${name}/${version}`);
          set((state) => ({
            modelVersions: state.modelVersions.filter((v) => !(v.name === name && v.version === version)),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete model version',
            loading: false,
          });
          throw error;
        }
      },

      transitionModelStage: async (name: string, version: string, stage: string) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/models/versions/${name}/${version}/stage`, { stage });
          await get().fetchModelVersions(name);
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to transition model stage',
            loading: false,
          });
          throw error;
        }
      },

      getModelHistory: async (name: string, version: string) => {
        try {
          const response = await api.get(`/models/versions/${name}/${version}/history`);
          return response.data.history;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to get model history',
          });
          throw error;
        }
      },

      // Deployment actions
      fetchDeployments: async (modelName?: string, status?: string) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, string> = {};
          if (modelName) params.model_name = modelName;
          if (status) params.status = status;

          const response = await api.get('/models/deployments', { params });
          set({ deployments: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch deployments',
            loading: false,
          });
          throw error;
        }
      },

      fetchDeployment: async (deploymentId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/models/deployments/${deploymentId}`);
          set({ currentDeployment: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch deployment',
            loading: false,
          });
          throw error;
        }
      },

      createDeployment: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/models/deployments', data);
          set((state) => ({
            deployments: [...state.deployments, response.data],
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create deployment',
            loading: false,
          });
          throw error;
        }
      },

      updateDeployment: async (deploymentId: string, data) => {
        set({ loading: true, error: null });
        try {
          await api.put(`/models/deployments/${deploymentId}`, data);
          set((state) => ({
            deployments: state.deployments.map((d) =>
              d.id === deploymentId ? { ...d, ...data } : d
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to update deployment',
            loading: false,
          });
          throw error;
        }
      },

      deleteDeployment: async (deploymentId: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/models/deployments/${deploymentId}`);
          set((state) => ({
            deployments: state.deployments.filter((d) => d.id !== deploymentId),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete deployment',
            loading: false,
          });
          throw error;
        }
      },

      scaleDeployment: async (deploymentId: string, replicas: number) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/models/deployments/${deploymentId}/scale`, null, {
            params: { replicas },
          });
          await get().fetchDeployments();
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to scale deployment',
            loading: false,
          });
          throw error;
        }
      },

      rollbackDeployment: async (deploymentId: string, targetVersion) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/models/deployments/${deploymentId}/rollback`, null, {
            params: { target_version: targetVersion },
          });
          await get().fetchDeployments();
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to rollback deployment',
            loading: false,
          });
          throw error;
        }
      },

      getDeploymentMetrics: async (deploymentId: string) => {
        try {
          const response = await api.get(`/models/deployments/${deploymentId}/metrics`);
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to get deployment metrics',
          });
          throw error;
        }
      },

      // Canary deployment actions
      createCanaryDeployment: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/models/deployments/canary', data);
          set((state) => ({
            deployments: [...state.deployments, response.data.primary_deployment, response.data.canary_deployment],
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create canary deployment',
            loading: false,
          });
          throw error;
        }
      },

      promoteCanary: async (deploymentId: string) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/models/deployments/canary/${deploymentId}/promote`);
          await get().fetchDeployments();
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to promote canary',
            loading: false,
          });
          throw error;
        }
      },

      // State management
      setCurrentModel: (model) => set({ currentModel: model }),
      setCurrentVersion: (version) => set({ currentVersion: version }),
      setCurrentDeployment: (deployment) => set({ currentDeployment: deployment }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'model-store',
      partialize: (state) => ({
        models: state.models,
        deployments: state.deployments,
      }),
    }
  )
);

// Selectors
export const useModels = () => useModelStore((state) => state.models);
export const useCurrentModel = () => useModelStore((state) => state.currentModel);
export const useModelVersions = () => useModelStore((state) => state.modelVersions);
export const useCurrentVersion = () => useModelStore((state) => state.currentVersion);
export const useDeployments = () => useModelStore((state) => state.deployments);
export const useCurrentDeployment = () => useModelStore((state) => state.currentDeployment);
export const useModelLoading = () => useModelStore((state) => state.loading);
export const useModelError = () => useModelStore((state) => state.error);
