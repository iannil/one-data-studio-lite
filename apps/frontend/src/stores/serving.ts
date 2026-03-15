/**
 * Model Serving Store
 *
 * Zustand store for model serving state management.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  InferenceService,
  ServiceMetrics,
  ServiceFilters,
  ABTestExperiment,
  CreateABTestRequest,
  StatisticalTestResult,
  CanaryDeployment,
  CreateCanaryRequest,
  CreateServiceRequest,
  ServingStatus,
  CanaryPhase,
} from '@/types/serving';
import { api } from '@/services/api';

// ============================================================================
// Service State
// ============================================================================

interface ServingState {
  // Inference Services
  services: InferenceService[];
  selectedServiceIds: string[];
  currentService: InferenceService | null;
  serviceMetrics: Record<string, ServiceMetrics>;
  serviceFilters: ServiceFilters;
  servicesLoading: boolean;
  servicesError: string | null;

  // A/B Tests
  abTests: ABTestExperiment[];
  currentABTest: ABTestExperiment | null;
  abTestResults: Record<string, StatisticalTestResult>;
  abTestsLoading: boolean;
  abTestsError: string | null;

  // Canary Deployments
  canaryDeployments: CanaryDeployment[];
  currentCanary: CanaryDeployment | null;
  canariesLoading: boolean;
  canariesError: string | null;

  // Actions
  // Services
  fetchServices: () => Promise<void>;
  createService: (data: CreateServiceRequest) => Promise<InferenceService>;
  updateService: (name: string, data: Partial<InferenceService>) => Promise<void>;
  deleteService: (name: string) => Promise<void>;
  scaleService: (name: string, replicas: number) => Promise<void>;
  getServiceMetrics: (name: string, duration?: string) => Promise<ServiceMetrics>;
  getTrafficDistribution: (name: string) => Promise<Record<string, number>>;
  updateTrafficDistribution: (name: string, distribution: Record<string, number>) => Promise<void>;
  selectService: (name: string) => void;
  selectMultipleServices: (ids: string[]) => void;
  clearServiceSelection: () => void;
  setServiceFilters: (filters: ServiceFilters) => void;
  setServicesError: (error: string | null) => void;
  clearServicesError: () => void;

  // A/B Tests
  fetchABTests: (project_id?: number) => Promise<void>;
  createABTest: (data: CreateABTestRequest) => Promise<ABTestExperiment>;
  getABTest: (experiment_id: string) => Promise<void>;
  updateABTestTraffic: (experiment_id: string, distribution: Record<string, number>) => Promise<void>;
  runSignificanceTest: (experiment_id: string, treatment_variant_id: string) => Promise<StatisticalTestResult>;
  selectWinner: (experiment_id: string, winner_id?: string) => Promise<void>;
  pauseABTest: (experiment_id: string) => Promise<void>;
  resumeABTest: (experiment_id: string) => Promise<void>;
  deleteABTest: (experiment_id: string) => Promise<void>;

  // Canary Deployments
  fetchCanaryDeployments: (service_name?: string) => Promise<void>;
  createCanaryDeployment: (data: CreateCanaryRequest) => Promise<CanaryDeployment>;
  getCanaryDeployment: (deployment_id: string) => Promise<void>;
  startCanaryDeployment: (deployment_id: string) => Promise<void>;
  promoteCanary: (deployment_id: string) => Promise<void>;
  rollbackCanary: (deployment_id: string, reason?: string) => Promise<void>;
  pauseCanaryDeployment: (deployment_id: string) => Promise<void>;
  resumeCanaryDeployment: (deployment_id: string) => Promise<void>;
  setCanaryTraffic: (deployment_id: string, traffic_percentage: number) => Promise<void>;
  deleteCanaryDeployment: (deployment_id: string) => Promise<void>;

  // Deploy from Training
  deployTrainedModel: (jobId: string, config: {
    name: string;
    description?: string;
    platform?: ServingPlatform;
    predictor_type: PredictorType;
    runtime_version?: string;
    device?: string;
    replicas?: number;
    autoscaling_enabled?: boolean;
    min_replicas?: number;
    max_replicas?: number;
  }) => Promise<InferenceService>;
}

export const useServingStore = create<ServingState>()(
  persist(
    (set, get) => ({
      // Initial state
      services: [],
      selectedServiceIds: [],
      currentService: null,
      serviceMetrics: {},
      serviceFilters: {},
      servicesLoading: false,
      servicesError: null,

      abTests: [],
      currentABTest: null,
      abTestResults: {},
      abTestsLoading: false,
      abTestsError: null,

      canaryDeployments: [],
      currentCanary: null,
      canariesLoading: false,
      canariesError: null,

      // ======================================================================
      // Service Actions
      // ======================================================================

      fetchServices: async () => {
        set({ servicesLoading: true, servicesError: null });
        try {
          const params = new URLSearchParams();
          const filters = get().serviceFilters;

          if (filters.status) params.append('status_filter', filters.status);
          if (filters.platform) params.append('platform_filter', filters.platform);
          if (filters.mode) params.append('mode', filters.mode);
          if (filters.project_id) params.append('project_id', filters.project_id.toString());

          const response = await api.get(`/serving/services?${params.toString()}`);
          set({ services: response.data || [], servicesLoading: false });
        } catch (error: any) {
          set({
            servicesError: error.response?.data?.detail || 'Failed to fetch services',
            servicesLoading: false,
          });
        }
      },

      createService: async (data) => {
        set({ servicesLoading: true, servicesError: null });
        try {
          const response = await api.post('/serving/services', data);
          const newService = response.data as InferenceService;

          set((state) => ({
            services: [...state.services, newService],
            servicesLoading: false,
          }));

          return newService;
        } catch (error: any) {
          set({
            servicesError: error.response?.data?.detail || 'Failed to create service',
            servicesLoading: false,
          });
          throw error;
        }
      },

      updateService: async (name, data) => {
        set({ servicesLoading: true, servicesError: null });
        try {
          await api.put(`/serving/services/${name}`, data);
          set((state) => ({
            services: state.services.map((s) =>
              s.name === name ? { ...s, ...data } : s
            ),
            servicesLoading: false,
          }));
        } catch (error: any) {
          set({
            servicesError: error.response?.data?.detail || 'Failed to update service',
            servicesLoading: false,
          });
          throw error;
        }
      },

      deleteService: async (name) => {
        set({ servicesLoading: true, servicesError: null });
        try {
          await api.delete(`/serving/services/${name}`);
          set((state) => ({
            services: state.services.filter((s) => s.name !== name),
            selectedServiceIds: state.selectedServiceIds.filter((id) => id !== name),
            servicesLoading: false,
          }));
        } catch (error: any) {
          set({
            servicesError: error.response?.data?.detail || 'Failed to delete service',
            servicesLoading: false,
          });
          throw error;
        }
      },

      scaleService: async (name, replicas) => {
        set({ servicesLoading: true, servicesError: null });
        try {
          await api.post(`/serving/services/${name}/scale`, { replicas });
          set((state) => ({
            services: state.services.map((s) =>
              s.name === name
                ? { ...s, predictor_config: s.predictor_config ? { ...s.predictor_config, replicas } : undefined }
                : s
            ),
            servicesLoading: false,
          }));
        } catch (error: any) {
          set({
            servicesError: error.response?.data?.detail || 'Failed to scale service',
            servicesLoading: false,
          });
          throw error;
        }
      },

      getServiceMetrics: async (name, duration = '1h') => {
        try {
          const response = await api.get(`/serving/services/${name}/metrics?duration=${duration}`);
          const metrics = response.data.metrics as ServiceMetrics;

          set((state) => ({
            serviceMetrics: { ...state.serviceMetrics, [name]: metrics },
          }));

          return metrics;
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to fetch metrics');
        }
      },

      getTrafficDistribution: async (name) => {
        try {
          const response = await api.get(`/serving/services/${name}/traffic`);
          return response.data as Record<string, number>;
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to get traffic distribution');
        }
      },

      updateTrafficDistribution: async (name, distribution) => {
        try {
          await api.put(`/serving/services/${name}/traffic`, { distribution });
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to update traffic distribution');
        }
      },

      selectService: (name) => {
        const service = get().services.find((s) => s.name === name);
        set({ currentService: service || null });
      },

      selectMultipleServices: (ids) => {
        set({ selectedServiceIds: ids });
      },

      clearServiceSelection: () => {
        set({ selectedServiceIds: [], currentService: null });
      },

      setServiceFilters: (filters) => {
        set({ serviceFilters: filters });
      },

      setServicesError: (error) => {
        set({ servicesError: error });
      },

      clearServicesError: () => {
        set({ servicesError: null });
      },

      // ======================================================================
      // A/B Test Actions
      // ======================================================================

      fetchABTests: async (project_id) => {
        set({ abTestsLoading: true, abTestsError: null });
        try {
          const params = new URLSearchParams();
          if (project_id) params.append('project_id', project_id.toString());

          const response = await api.get(`/serving/ab-tests?${params.toString()}`);
          set({ abTests: response.data || [], abTestsLoading: false });
        } catch (error: any) {
          set({
            abTestsError: error.response?.data?.detail || 'Failed to fetch A/B tests',
            abTestsLoading: false,
          });
        }
      },

      createABTest: async (data) => {
        set({ abTestsLoading: true, abTestsError: null });
        try {
          const response = await api.post('/serving/ab-tests', data);
          const newTest = response.data as ABTestExperiment;

          set((state) => ({
            abTests: [...state.abTests, newTest],
            abTestsLoading: false,
          }));

          return newTest;
        } catch (error: any) {
          set({
            abTestsError: error.response?.data?.detail || 'Failed to create A/B test',
            abTestsLoading: false,
          });
          throw error;
        }
      },

      getABTest: async (experiment_id) => {
        try {
          const response = await api.get(`/serving/ab-tests/${experiment_id}`);
          set({ currentABTest: response.data });
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to fetch A/B test');
        }
      },

      updateABTestTraffic: async (experiment_id, distribution) => {
        try {
          await api.post(`/serving/ab-tests/${experiment_id}/traffic`, { distribution });
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to update traffic split');
        }
      },

      runSignificanceTest: async (experiment_id, treatment_variant_id) => {
        try {
          const response = await api.post(`/serving/ab-tests/${experiment_id}/significance`, null, {
            params: { treatment_variant_id },
          });
          const result = response.data as StatisticalTestResult;

          set((state) => ({
            abTestResults: { ...state.abTestResults, [experiment_id]: result },
          }));

          return result;
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to run significance test');
        }
      },

      selectWinner: async (experiment_id, winner_id) => {
        try {
          await api.post(`/serving/ab-tests/${experiment_id}/winner`, null, {
            params: winner_id ? { winner_variant_id: winner_id } : undefined,
          });
          set((state) => ({
            abTests: state.abTests.map((t) =>
              t.experiment_id === experiment_id
                ? { ...t, is_active: false, winner_variant_id: winner_id || t.winner_variant_id }
                : t
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to select winner');
        }
      },

      pauseABTest: async (experiment_id) => {
        try {
          await api.post(`/serving/ab-tests/${experiment_id}/pause`);
          set((state) => ({
            abTests: state.abTests.map((t) =>
              t.experiment_id === experiment_id ? { ...t, is_active: false } : t
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to pause A/B test');
        }
      },

      resumeABTest: async (experiment_id) => {
        try {
          await api.post(`/serving/ab-tests/${experiment_id}/resume`);
          set((state) => ({
            abTests: state.abTests.map((t) =>
              t.experiment_id === experiment_id ? { ...t, is_active: true } : t
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to resume A/B test');
        }
      },

      deleteABTest: async (experiment_id) => {
        try {
          await api.delete(`/serving/ab-tests/${experiment_id}`);
          set((state) => ({
            abTests: state.abTests.filter((t) => t.experiment_id !== experiment_id),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to delete A/B test');
        }
      },

      // ======================================================================
      // Canary Deployment Actions
      // ======================================================================

      fetchCanaryDeployments: async (service_name) => {
        set({ canariesLoading: true, canariesError: null });
        try {
          const params = new URLSearchParams();
          if (service_name) params.append('service_name', service_name);

          const response = await api.get(`/serving/canaries?${params.toString()}`);
          set({ canaryDeployments: response.data || [], canariesLoading: false });
        } catch (error: any) {
          set({
            canariesError: error.response?.data?.detail || 'Failed to fetch canary deployments',
            canariesLoading: false,
          });
        }
      },

      createCanaryDeployment: async (data) => {
        set({ canariesLoading: true, canariesError: null });
        try {
          const response = await api.post('/serving/canaries', data);
          const newCanary = response.data as CanaryDeployment;

          set((state) => ({
            canaryDeployments: [...state.canaryDeployments, newCanary],
            canariesLoading: false,
          }));

          return newCanary;
        } catch (error: any) {
          set({
            canariesError: error.response?.data?.detail || 'Failed to create canary deployment',
            canariesLoading: false,
          });
          throw error;
        }
      },

      getCanaryDeployment: async (deployment_id) => {
        try {
          const response = await api.get(`/serving/canaries/${deployment_id}`);
          set({ currentCanary: response.data });
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to fetch canary deployment');
        }
      },

      startCanaryDeployment: async (deployment_id) => {
        try {
          await api.post(`/serving/canaries/${deployment_id}/start`);
          set((state) => ({
            canaryDeployments: state.canaryDeployments.map((c) =>
              c.deployment_id === deployment_id
                ? { ...c, phase: CanaryPhase.TRAFFIC_SHIFT, is_running: true }
                : c
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to start canary deployment');
        }
      },

      promoteCanary: async (deployment_id) => {
        try {
          await api.post(`/serving/canaries/${deployment_id}/promote`);
          set((state) => ({
            canaryDeployments: state.canaryDeployments.map((c) =>
              c.deployment_id === deployment_id
                ? { ...c, phase: CanaryPhase.PROMOTED, is_complete: true, is_running: false }
                : c
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to promote canary');
        }
      },

      rollbackCanary: async (deployment_id, reason) => {
        try {
          await api.post(`/serving/canaries/${deployment_id}/rollback`, null, {
            params: { reason },
          });
          set((state) => ({
            canaryDeployments: state.canaryDeployments.map((c) =>
              c.deployment_id === deployment_id
                ? { ...c, phase: CanaryPhase.ROLLED_BACK, is_complete: true, is_running: false }
                : c
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to rollback canary');
        }
      },

      pauseCanaryDeployment: async (deployment_id) => {
        try {
          await api.post(`/serving/canaries/${deployment_id}/pause`);
          set((state) => ({
            canaryDeployments: state.canaryDeployments.map((c) =>
              c.deployment_id === deployment_id ? { ...c, phase: CanaryPhase.MONITORING } : c
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to pause canary deployment');
        }
      },

      resumeCanaryDeployment: async (deployment_id) => {
        try {
          await api.post(`/serving/canaries/${deployment_id}/resume`);
          set((state) => ({
            canaryDeployments: state.canaryDeployments.map((c) =>
              c.deployment_id === deployment_id ? { ...c, phase: CanaryPhase.TRAFFIC_SHIFT, is_running: true } : c
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to resume canary deployment');
        }
      },

      setCanaryTraffic: async (deployment_id, traffic_percentage) => {
        try {
          await api.put(`/serving/canaries/${deployment_id}/traffic`, null, {
            params: { traffic_percentage },
          });
          set((state) => ({
            canaryDeployments: state.canaryDeployments.map((c) =>
              c.deployment_id === deployment_id ? { ...c, current_traffic_percentage: traffic_percentage } : c
            ),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to set canary traffic');
        }
      },

      deleteCanaryDeployment: async (deployment_id) => {
        try {
          await api.delete(`/serving/canaries/${deployment_id}`);
          set((state) => ({
            canaryDeployments: state.canaryDeployments.filter((c) => c.deployment_id !== deployment_id),
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to delete canary deployment');
        }
      },

      // Deploy from training job
      deployTrainedModel: async (jobId: string, config: {
        name: string;
        description?: string;
        platform?: ServingPlatform;
        predictor_type: PredictorType;
        runtime_version?: string;
        device?: string;
        replicas?: number;
        autoscaling_enabled?: boolean;
        min_replicas?: number;
        max_replicas?: number;
      }) => {
        try {
          // Get job details to find model path
          const jobResponse = await api.get(`/training/jobs/${jobId}`);
          const job = jobResponse.data;

          // Determine model URI from job checkpoint path
          const modelUri = job.config?.checkpoint_path || `/models/${jobId}`;

          const response = await api.post('/serving/services', {
            name: config.name,
            namespace: 'default',
            description: config.description || `Model from training job ${jobId}`,
            platform: config.platform || ServingPlatform.KSERVE,
            mode: DeploymentMode.RAW,
            predictor_config: {
              predictor_type: config.predictor_type,
              model_uri: modelUri,
              runtime_version: config.runtime_version,
              device: config.device || 'cpu',
              replicas: config.replicas || 1,
            },
            autoscaling_enabled: config.autoscaling_enabled || false,
            min_replicas: config.min_replicas || 1,
            max_replicas: config.max_replicas || 3,
            enable_logging: true,
            metadata: {
              source_job_id: jobId,
              source_job_name: job.name,
            },
          });

          const newService = response.data as InferenceService;

          set((state) => ({
            services: [...state.services, newService],
          }));

          return newService;
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to deploy model');
        }
      },
    }),
    {
      name: 'serving-storage',
      partialize: (state) => ({
        serviceFilters: state.serviceFilters,
        selectedServiceIds: state.selectedServiceIds,
      }),
    }
  )
);

// ============================================================================
// Selectors
// ============================================================================

export const useServices = () => useServingStore((state) => state.services);
export const useServicesLoading = () => useServingStore((state) => state.servicesLoading);
export const useServicesError = () => useServingStore((state) => state.servicesError);

export const useCurrentService = () => useServingStore((state) => state.currentService);
export const useSelectedServices = () => useServingStore((state) => state.selectedServiceIds);

export const useABTests = () => useServingStore((state) => state.abTests);
export const useABTestsLoading = () => useServingStore((state) => state.abTestsLoading);
export const useCurrentABTest = () => useServingStore((state) => state.currentABTest);

export const useCanaryDeployments = () => useServingStore((state) => state.canaryDeployments);
export const useCanariesLoading = () => useServingStore((state) => state.canariesLoading);
export const useCurrentCanary = () => useServingStore((state) => state.currentCanary);

// Stats selectors
export const useServiceStats = () => {
  const services = useServingStore((state) => state.services);

  return {
    total: services.length,
    running: services.filter((s) => s.status === 'running').length,
    failed: services.filter((s) => s.status === 'failed').length,
    pending: services.filter((s) => s.status === 'pending').length,
    deploying: services.filter((s) => s.status === 'deploying').length,
    stopped: services.filter((s) => s.status === 'stopped').length,
  };
};

export const useABTestStats = () => {
  const abTests = useServingStore((state) => state.abTests);

  return {
    total: abTests.length,
    active: abTests.filter((t) => t.is_active).length,
    running: abTests.filter((t) => t.is_running).length,
    completed: abTests.filter((t) => !t.is_active && t.winner_variant_id).length,
  };
};

export const useCanaryStats = () => {
  const deployments = useServingStore((state) => state.canaryDeployments);

  return {
    total: deployments.length,
    running: deployments.filter((d) => d.is_running).length,
    promoted: deployments.filter((d) => d.phase === CanaryPhase.PROMOTED).length,
    rolledBack: deployments.filter((d) => d.phase === CanaryPhase.ROLLED_BACK).length,
    failed: deployments.filter((d) => d.phase === CanaryPhase.FAILED).length,
  };
};

// Deploy from training
export const useDeployTrainedModel = () => useServingStore((state) => state.deployTrainedModel);

