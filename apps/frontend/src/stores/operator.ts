/**
 * Operator Store
 *
 * Zustand store for managing Kubernetes operator resources.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';
import {
  ResourceState,
  OperatorType,
  NotebookResource,
  TrainingJobResource,
  InferenceServiceResource,
  ClusterStatus,
  CreateNotebookRequest,
  CreateTrainingJobRequest,
  CreateInferenceServiceRequest,
} from '../types/operator';

interface OperatorState {
  // Resources
  notebooks: NotebookResource[];
  trainingJobs: TrainingJobResource[];
  inferenceServices: InferenceServiceResource[];
  clusterStatus: ClusterStatus | null;

  // UI State
  loading: boolean;
  error: string | null;

  // Actions
  fetchNotebooks: () => Promise<NotebookResource[]>;
  fetchTrainingJobs: () => Promise<TrainingJobResource[]>;
  fetchInferenceServices: () => Promise<InferenceServiceResource[]>;
  fetchClusterStatus: () => Promise<ClusterStatus>;

  // Notebook Actions
  createNotebook: (request: CreateNotebookRequest & { namespace?: string }) => Promise<NotebookResource>;
  getNotebook: (name: string, namespace?: string) => Promise<NotebookResource>;
  startNotebook: (name: string, namespace?: string) => Promise<void>;
  stopNotebook: (name: string, namespace?: string) => Promise<void>;
  deleteNotebook: (name: string, namespace?: string) => Promise<void>;

  // Training Job Actions
  createTrainingJob: (request: CreateTrainingJobRequest & { namespace?: string }) => Promise<TrainingJobResource>;
  getTrainingJob: (name: string, namespace?: string) => Promise<TrainingJobResource>;
  deleteTrainingJob: (name: string, namespace?: string) => Promise<void>;

  // Inference Service Actions
  createInferenceService: (request: CreateInferenceServiceRequest & { namespace?: string }) => Promise<InferenceServiceResource>;
  getInferenceService: (name: string, namespace?: string) => Promise<InferenceServiceResource>;
  scaleInferenceService: (name: string, replicas: number, namespace?: string) => Promise<void>;
  deleteInferenceService: (name: string, namespace?: string) => Promise<void>;

  // Cluster Actions
  installCrds: () => Promise<void>;

  // Utility
  clearError: () => void;
}

export const useOperatorStore = create<OperatorState>()(
  persist(
    (set, get) => ({
      // Initial state
      notebooks: [],
      trainingJobs: [],
      inferenceServices: [],
      clusterStatus: null,
      loading: false,
      error: null,

      // Fetch all notebooks
      fetchNotebooks: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/operator/notebooks');
          const notebooks: NotebookResource[] = response.data.map((nb: any) => ({
            apiVersion: nb.apiVersion || 'studio.one-data.io/v1alpha1',
            kind: 'Notebook',
            metadata: {
              name: nb.name,
              namespace: nb.namespace || 'default',
              uid: nb.uid || `${nb.name}-${Date.now()}`,
              creationTimestamp: nb.createdAt,
            },
            spec: {
              image: nb.spec?.image || nb.image || 'jupyter/base-notebook:latest',
              cpu: nb.spec?.cpu || nb.cpu || '500m',
              memory: nb.spec?.memory || nb.memory || '1Gi',
              gpu: nb.spec?.gpu || nb.gpu,
              storage: nb.spec?.storage || nb.storage || '1Gi',
              ports: nb.spec?.ports || nb.ports || [8888],
              env: nb.spec?.env || nb.env || {},
              workspace: nb.spec?.workspace || nb.workspace,
              timeout: nb.spec?.timeout || nb.timeout,
              autoStop: nb.spec?.autoStop ?? nb.autoStop ?? true,
            },
            status: {
              phase: nb.phase || nb.status?.phase || ResourceState.UNKNOWN,
              conditions: nb.status?.conditions || [],
              observedGeneration: nb.status?.observedGeneration || 1,
              replicas: nb.replicas || nb.status?.replicas || 0,
              readyReplicas: nb.readyReplicas || nb.status?.readyReplicas || 0,
              availableReplicas: nb.status?.availableReplicas || 0,
              updatedReplicas: nb.status?.updatedReplicas || 0,
              jupyterURL: nb.jupyterURL || nb.status?.jupyterURL,
              tensorboardURL: nb.status?.tensorboardURL,
              createdAt: nb.createdAt,
            },
          }));
          set({ notebooks, loading: false });
          return notebooks;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Fetch all training jobs
      fetchTrainingJobs: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/operator/training-jobs');
          const jobs: TrainingJobResource[] = response.data.map((job: any) => ({
            apiVersion: job.apiVersion || 'studio.one-data.io/v1alpha1',
            kind: 'TrainingJob',
            metadata: {
              name: job.name,
              namespace: job.namespace || 'default',
              uid: job.uid || `${job.name}-${Date.now()}`,
              creationTimestamp: job.createdAt,
            },
            spec: {
              backend: job.spec?.backend || job.backend || 'pytorch',
              strategy: job.spec?.strategy || job.strategy || 'ddp',
              entryPoint: job.spec?.entryPoint || job.entry_point || 'train.py',
              entryPointArgs: job.spec?.entryPointArgs || job.entry_point_args || [],
              numNodes: job.spec?.numNodes || job.num_nodes || 1,
              numProcessesPerNode: job.spec?.numProcessesPerNode || job.num_processes_per_node || 1,
              modelUri: job.spec?.modelUri || job.model_uri || '',
              outputUri: job.spec?.outputUri || job.output_uri,
              tensorboard: job.spec?.tensorboard ?? job.tensorboard ?? false,
              dockerImage: job.spec?.dockerImage || job.docker_image,
              resources: job.spec?.resources || job.resources || {},
            },
            status: {
              phase: job.phase || job.status?.phase || ResourceState.UNKNOWN,
              conditions: job.status?.conditions || [],
              observedGeneration: job.status?.observedGeneration || 1,
              replicas: job.status?.replicas || 0,
              readyReplicas: job.status?.readyReplicas || 0,
              availableReplicas: job.status?.availableReplicas || 0,
              updatedReplicas: job.status?.updatedReplicas || 0,
              startedAt: job.startedAt || job.status?.startedAt,
              completedAt: job.status?.completedAt,
            },
          }));
          set({ trainingJobs: jobs, loading: false });
          return jobs;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Fetch all inference services
      fetchInferenceServices: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/operator/inference-services');
          const services: InferenceServiceResource[] = response.data.map((svc: any) => ({
            apiVersion: svc.apiVersion || 'studio.one-data.io/v1alpha1',
            kind: 'InferenceService',
            metadata: {
              name: svc.name,
              namespace: svc.namespace || 'default',
              uid: svc.uid || `${svc.name}-${Date.now()}`,
              creationTimestamp: svc.createdAt,
            },
            spec: {
              modelUri: svc.spec?.modelUri || svc.model_uri || '',
              predictorType: svc.spec?.predictorType || svc.predictor_type || 'custom',
              framework: svc.spec?.framework || svc.framework,
              replicas: svc.spec?.replicas || svc.replicas || 1,
              autoscalingEnabled: svc.spec?.autoscalingEnabled ?? svc.autoscaling_enabled ?? false,
              minReplicas: svc.spec?.minReplicas || svc.min_replicas || 1,
              maxReplicas: svc.spec?.maxReplicas || svc.max_replicas || 3,
              resources: svc.spec?.resources || svc.resources || {},
            },
            status: {
              phase: svc.phase || svc.status?.phase || ResourceState.UNKNOWN,
              conditions: svc.status?.conditions || [],
              observedGeneration: svc.status?.observedGeneration || 1,
              replicas: svc.replicas || svc.status?.replicas || 0,
              readyReplicas: svc.readyReplicas || svc.status?.readyReplicas || 0,
              availableReplicas: svc.status?.availableReplicas || 0,
              updatedReplicas: svc.status?.updatedReplicas || 0,
              serviceURL: svc.serviceURL || svc.status?.serviceURL,
            },
          }));
          set({ inferenceServices: services, loading: false });
          return services;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Fetch cluster status
      fetchClusterStatus: async () => {
        try {
          const response = await api.get('/operator/cluster/status');
          const status: ClusterStatus = response.data;
          set({ clusterStatus: status });
          return status;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Create notebook
      createNotebook: async (request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/operator/notebooks', {
            name: request.name,
            image: request.image,
            cpu: request.cpu,
            memory: request.memory,
            gpu: request.gpu,
            storage: request.storage,
            ports: request.ports,
            env: request.env,
            workspace: request.workspace,
            timeout: request.timeout,
            autoStop: request.autoStop,
          }, {
            params: { namespace: request.namespace || 'default' },
          });
          set({ loading: false });
          await get().fetchNotebooks();
          return response.data;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Get single notebook
      getNotebook: async (name, namespace = 'default') => {
        try {
          const response = await api.get(`/operator/notebooks/${name}`, {
            params: { namespace },
          });
          return response.data;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Start notebook
      startNotebook: async (name, namespace = 'default') => {
        try {
          await api.post(`/operator/notebooks/${name}/start`, null, {
            params: { namespace },
          });
          await get().fetchNotebooks();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Stop notebook
      stopNotebook: async (name, namespace = 'default') => {
        try {
          await api.post(`/operator/notebooks/${name}/stop`, null, {
            params: { namespace },
          });
          await get().fetchNotebooks();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Delete notebook
      deleteNotebook: async (name, namespace = 'default') => {
        try {
          await api.delete(`/operator/notebooks/${name}`, {
            params: { namespace },
          });
          await get().fetchNotebooks();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Create training job
      createTrainingJob: async (request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/operator/training-jobs', {
            name: request.name,
            backend: request.backend,
            strategy: request.strategy,
            entry_point: request.entryPoint,
            entry_point_args: request.entryPointArgs,
            num_nodes: request.numNodes,
            num_processes_per_node: request.numProcessesPerNode,
            model_uri: request.modelUri,
            output_uri: request.outputUri,
            tensorboard: request.tensorboard,
            docker_image: request.dockerImage,
            resources: request.resources,
          }, {
            params: { namespace: request.namespace || 'default' },
          });
          set({ loading: false });
          await get().fetchTrainingJobs();
          return response.data;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Get single training job
      getTrainingJob: async (name, namespace = 'default') => {
        try {
          const response = await api.get(`/operator/training-jobs/${name}`, {
            params: { namespace },
          });
          return response.data;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Delete training job
      deleteTrainingJob: async (name, namespace = 'default') => {
        try {
          await api.delete(`/operator/training-jobs/${name}`, {
            params: { namespace },
          });
          await get().fetchTrainingJobs();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Create inference service
      createInferenceService: async (request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/operator/inference-services', {
            name: request.name,
            model_uri: request.modelUri,
            predictor_type: request.predictorType,
            framework: request.framework,
            replicas: request.replicas,
            autoscaling_enabled: request.autoscalingEnabled,
            min_replicas: request.minReplicas,
            max_replicas: request.maxReplicas,
            resources: request.resources,
          }, {
            params: { namespace: request.namespace || 'default' },
          });
          set({ loading: false });
          await get().fetchInferenceServices();
          return response.data;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Get single inference service
      getInferenceService: async (name, namespace = 'default') => {
        try {
          const response = await api.get(`/operator/inference-services/${name}`, {
            params: { namespace },
          });
          return response.data;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Scale inference service
      scaleInferenceService: async (name, replicas, namespace = 'default') => {
        try {
          await api.put(`/operator/inference-services/${name}/scale`, {
            replicas,
          }, {
            params: { namespace },
          });
          await get().fetchInferenceServices();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Delete inference service
      deleteInferenceService: async (name, namespace = 'default') => {
        try {
          await api.delete(`/operator/inference-services/${name}`, {
            params: { namespace },
          });
          await get().fetchInferenceServices();
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Install CRDs
      installCrds: async () => {
        set({ loading: true, error: null });
        try {
          await api.post('/operator/cluster/install-crds');
          set({ loading: false });
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Clear error
      clearError: () => set({ error: null }),
    }),
    {
      name: 'operator-storage',
      partialize: (state) => ({
        clusterStatus: state.clusterStatus,
      }),
    }
  )
);

// Selectors
export const selectRunningNotebooks = (state: OperatorState) =>
  state.notebooks.filter((n) => n.status.phase === ResourceState.RUNNING);

export const selectRunningTrainingJobs = (state: OperatorState) =>
  state.trainingJobs.filter((j) => j.status.phase === ResourceState.RUNNING);

export const selectRunningInferenceServices = (state: OperatorState) =>
  state.inferenceServices.filter((s) => s.status.phase === ResourceState.RUNNING);

export const selectFailedResources = (state: OperatorState) => ({
  notebooks: state.notebooks.filter((n) => n.status.phase === ResourceState.FAILED),
  trainingJobs: state.trainingJobs.filter((j) => j.status.phase === ResourceState.FAILED),
  inferenceServices: state.inferenceServices.filter((s) => s.status.phase === ResourceState.FAILED),
});
