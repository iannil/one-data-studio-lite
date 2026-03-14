/**
 * AIHub Store
 *
 * Zustand store for AI model marketplace, fine-tuning, and deployment.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';

// Types
export type ModelCategory =
  | 'image_classification'
  | 'object_detection'
  | 'segmentation'
  | 'ocr'
  | 'image_generation'
  | 'text_classification'
  | 'ner'
  | 'translation'
  | 'summarization'
  | 'question_answering'
  | 'llm'
  | 'embedding'
  | 'multimodal'
  | 'vision_language'
  | 'asr'
  | 'tts'
  | 'audio_classification';

export type ModelFramework = 'pytorch' | 'tensorflow' | 'jax' | 'onnx' | 'tflite' | 'opencv';

export interface ModelCapability {
  cuda_supported: boolean;
  cpu_inference: boolean;
  quantization_available: boolean;
  distributed_training?: boolean;
  streaming?: boolean;
  function_calling?: boolean;
  vision?: boolean;
  code?: boolean;
}

export interface AIHubModel {
  id: string;
  name: string;
  category: string;
  framework: string;
  source: string;
  license: string;
  description?: string;
  tags?: string[];
  tasks?: string[];
  languages?: string[];
  parameter_size?: string;
  gpu_memory_mb?: number;
  cpu_cores?: number;
  ram_mb?: number;
  capabilities?: ModelCapability;
  deploy_template?: string;
  default_inference_image?: string;
  provider?: string;
  paper_url?: string;
  demo_url?: string;
}

export interface FinetuneJob {
  job_id: string;
  base_model: string;
  dataset_id: string;
  config: Record<string, any>;
  user_id: number;
  status: 'pending' | 'preparing' | 'training' | 'evaluating' | 'saving' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  metrics: Record<string, number>;
  output_model_uri?: string;
  mlflow_run_id?: string;
}

export interface ModelDeployment {
  deployment_id: string;
  model_id: string;
  name: string;
  config: Record<string, any>;
  user_id: number;
  status: 'pending' | 'building' | 'deploying' | 'running' | 'failed' | 'stopped' | 'deleting';
  created_at: string;
  started_at?: string;
  updated_at: string;
  endpoint?: string;
  error?: string;
  replicas: number;
  ready_replicas: number;
}

export interface FinetuneTemplate {
  name: string;
  description: string;
  config: Record<string, any>;
  estimated_time: string;
  estimated_cost: string;
}

export interface DeploymentTemplate {
  name: string;
  replicas: number;
  gpu_enabled: boolean;
  gpu_count?: number;
  gpu_type?: string;
  autoscaling: {
    enabled: boolean;
    min_replicas: number;
    max_replicas: number;
    target_cpu_utilization?: number;
  };
  resources?: {
    requests: { cpu: string; memory: string };
    limits: { cpu: string; memory: string };
  };
  inference_params?: Record<string, any>;
}

export interface CostEstimate {
  estimated_gpu_hours: number;
  estimated_cost_usd: number;
  estimated_time_hours: number;
  recommended_gpu_type: string;
}

interface AIHubState {
  // State
  models: AIHubModel[];
  currentModel: AIHubModel | null;
  categories: Array<{ value: string; label: string }>;
  frameworks: string[];
  stats: Record<string, any>;
  finetuneJobs: FinetuneJob[];
  currentFinetuneJob: FinetuneJob | null;
  deployments: ModelDeployment[];
  currentDeployment: ModelDeployment | null;
  deploymentTemplates: Record<string, DeploymentTemplate>;
  finetuneTemplates: Record<string, FinetuneTemplate[]>;
  loading: boolean;
  error: string | null;

  // Model actions
  fetchModels: (filters?: {
    category?: string;
    framework?: string;
    task?: string;
    search?: string;
    limit?: number;
  }) => Promise<void>;
  fetchModel: (modelId: string) => Promise<void>;
  fetchCategories: () => Promise<void>;
  fetchFrameworks: () => Promise<void>;
  fetchStats: () => Promise<void>;

  // Fine-tuning actions
  fetchFinetuneTemplates: (modelId: string) => Promise<void>;
  createFinetuneJob: (data: {
    base_model: string;
    dataset_id: string;
    method?: string;
    epochs?: number;
    batch_size?: number;
    learning_rate?: number;
    use_template?: boolean;
    custom_config?: Record<string, any>;
  }) => Promise<void>;
  fetchFinetuneJobs: (baseModel?: string, status?: string) => Promise<void>;
  fetchFinetuneJob: (jobId: string) => Promise<void>;
  startFinetuneJob: (jobId: string) => Promise<void>;
  cancelFinetuneJob: (jobId: string) => Promise<void>;
  deleteFinetuneJob: (jobId: string) => Promise<void>;
  estimateFinetuneCost: (modelId: string, config: {
    method?: string;
    epochs?: number;
    batch_size?: number;
  }) => Promise<CostEstimate>;

  // Deployment actions
  fetchDeploymentTemplate: (modelId: string) => Promise<void>;
  createDeployment: (data: {
    model_id: string;
    name: string;
    replicas?: number;
    gpu_enabled?: boolean;
    gpu_type?: string;
    gpu_count?: number;
    autoscaling_enabled?: boolean;
    autoscaling_min?: number;
    autoscaling_max?: number;
  }) => Promise<void>;
  fetchDeployments: (modelId?: string, status?: string) => Promise<void>;
  fetchDeployment: (deploymentId: string) => Promise<void>;
  stopDeployment: (deploymentId: string) => Promise<void>;
  startDeployment: (deploymentId: string) => Promise<void>;
  deleteDeployment: (deploymentId: string) => Promise<void>;
  scaleDeployment: (deploymentId: string, replicas: number) => Promise<void>;
  predict: (deploymentId: string, inputs: Record<string, any>) => Promise<any>;

  // State management
  setCurrentModel: (model: AIHubModel | null) => void;
  setCurrentFinetuneJob: (job: FinetuneJob | null) => void;
  setCurrentDeployment: (deployment: ModelDeployment | null) => void;
  clearError: () => void;
}

export const useAIHubStore = create<AIHubState>()(
  persist(
    (set, get) => ({
      // Initial state
      models: [],
      currentModel: null,
      categories: [],
      frameworks: [],
      stats: {},
      finetuneJobs: [],
      currentFinetuneJob: null,
      deployments: [],
      currentDeployment: null,
      deploymentTemplates: {},
      finetuneTemplates: {},
      loading: false,
      error: null,

      // Model actions
      fetchModels: async (filters = {}) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, any> = { limit: filters.limit || 100 };
          if (filters.category) params.category = filters.category;
          if (filters.framework) params.framework = filters.framework;
          if (filters.task) params.task = filters.task;
          if (filters.search) params.search = filters.search;

          const response = await api.get('/aihub/models', { params });
          set({ models: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch models',
            loading: false,
          });
          throw error;
        }
      },

      fetchModel: async (modelId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/aihub/models/${modelId}`);
          set({ currentModel: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch model',
            loading: false,
          });
          throw error;
        }
      },

      fetchCategories: async () => {
        try {
          const response = await api.get('/aihub/categories');
          set({ categories: response.data });
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Failed to fetch categories' });
        }
      },

      fetchFrameworks: async () => {
        try {
          const response = await api.get('/aihub/frameworks');
          set({ frameworks: response.data });
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Failed to fetch frameworks' });
        }
      },

      fetchStats: async () => {
        try {
          const response = await api.get('/aihub/stats');
          set({ stats: response.data });
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Failed to fetch stats' });
        }
      },

      // Fine-tuning actions
      fetchFinetuneTemplates: async (modelId: string) => {
        try {
          const response = await api.get(`/aihub/models/${modelId}/finetune-templates`);
          set((state) => ({
            finetuneTemplates: { ...state.finetuneTemplates, [modelId]: response.data },
          }));
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Failed to fetch templates' });
        }
      },

      createFinetuneJob: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/aihub/finetune/jobs', data);
          set((state) => ({
            finetuneJobs: [response.data, ...state.finetuneJobs],
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create job',
            loading: false,
          });
          throw error;
        }
      },

      fetchFinetuneJobs: async (baseModel?: string, status?: string) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, string> = {};
          if (baseModel) params.base_model = baseModel;
          if (status) params.status = status;

          const response = await api.get('/aihub/finetune/jobs', { params });
          set({ finetuneJobs: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch jobs',
            loading: false,
          });
          throw error;
        }
      },

      fetchFinetuneJob: async (jobId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/aihub/finetune/jobs/${jobId}`);
          set({ currentFinetuneJob: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch job',
            loading: false,
          });
          throw error;
        }
      },

      startFinetuneJob: async (jobId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post(`/aihub/finetune/jobs/${jobId}/start`);
          set((state) => ({
            finetuneJobs: state.finetuneJobs.map((j) =>
              j.job_id === jobId ? response.data : j
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to start job',
            loading: false,
          });
          throw error;
        }
      },

      cancelFinetuneJob: async (jobId: string) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/aihub/finetune/jobs/${jobId}/cancel`);
          set((state) => ({
            finetuneJobs: state.finetuneJobs.map((j) =>
              j.job_id === jobId ? { ...j, status: 'cancelled' as const } : j
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to cancel job',
            loading: false,
          });
          throw error;
        }
      },

      deleteFinetuneJob: async (jobId: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/aihub/finetune/jobs/${jobId}`);
          set((state) => ({
            finetuneJobs: state.finetuneJobs.filter((j) => j.job_id !== jobId),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete job',
            loading: false,
          });
          throw error;
        }
      },

      estimateFinetuneCost: async (modelId: string, config) => {
        try {
          const response = await api.post('/aihub/finetune/cost-estimate', {
            model_id: modelId,
            ...config,
          });
          return response.data;
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Failed to estimate cost' });
          throw error;
        }
      },

      // Deployment actions
      fetchDeploymentTemplate: async (modelId: string) => {
        try {
          const response = await api.get(`/aihub/models/${modelId}/template`);
          set((state) => ({
            deploymentTemplates: { ...state.deploymentTemplates, [modelId]: response.data },
          }));
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Failed to fetch template' });
        }
      },

      createDeployment: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/aihub/deployments', data);
          set((state) => ({
            deployments: [response.data, ...state.deployments],
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

      fetchDeployments: async (modelId?: string, status?: string) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, string> = {};
          if (modelId) params.model_id = modelId;
          if (status) params.status = status;

          const response = await api.get('/aihub/deployments', { params });
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
          const response = await api.get(`/aihub/deployments/${deploymentId}`);
          set({ currentDeployment: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch deployment',
            loading: false,
          });
          throw error;
        }
      },

      stopDeployment: async (deploymentId: string) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/aihub/deployments/${deploymentId}/stop`);
          set((state) => ({
            deployments: state.deployments.map((d) =>
              d.deployment_id === deploymentId ? { ...d, status: 'stopped' as const } : d
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to stop deployment',
            loading: false,
          });
          throw error;
        }
      },

      startDeployment: async (deploymentId: string) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/aihub/deployments/${deploymentId}/start`);
          set((state) => ({
            deployments: state.deployments.map((d) =>
              d.deployment_id === deploymentId ? { ...d, status: 'running' as const } : d
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to start deployment',
            loading: false,
          });
          throw error;
        }
      },

      deleteDeployment: async (deploymentId: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/aihub/deployments/${deploymentId}`);
          set((state) => ({
            deployments: state.deployments.filter((d) => d.deployment_id !== deploymentId),
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
          const response = await api.post(`/aihub/deployments/${deploymentId}/scale`, null, {
            params: { replicas },
          });
          set((state) => ({
            deployments: state.deployments.map((d) =>
              d.deployment_id === deploymentId ? response.data : d
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to scale deployment',
            loading: false,
          });
          throw error;
        }
      },

      predict: async (deploymentId: string, inputs: Record<string, any>) => {
        try {
          const response = await api.post(`/aihub/deployments/${deploymentId}/predict`, inputs);
          return response.data;
        } catch (error: any) {
          set({ error: error.response?.data?.detail || 'Prediction failed' });
          throw error;
        }
      },

      // State management
      setCurrentModel: (model) => set({ currentModel: model }),
      setCurrentFinetuneJob: (job) => set({ currentFinetuneJob: job }),
      setCurrentDeployment: (deployment) => set({ currentDeployment: deployment }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'aihub-store',
      partialize: (state) => ({
        models: state.models,
        categories: state.categories,
        frameworks: state.frameworks,
      }),
    }
  )
);

// Selectors
export const useAIHubModels = () => useAIHubStore((state) => state.models);
export const useCurrentAIHubModel = () => useAIHubStore((state) => state.currentModel);
export const useFinetuneJobs = () => useAIHubStore((state) => state.finetuneJobs));
export const useDeployments = () => useAIHubStore((state) => state.deployments);
export const useAIHubLoading = () => useAIHubStore((state) => state.loading);
export const useAIHubError = () => useAIHubStore((state) => state.error);
