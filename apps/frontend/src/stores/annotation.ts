/**
 * Annotation Store
 *
 * Zustand store for managing Label Studio annotation projects and tasks.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';

// Types
export interface AnnotationProject {
  id: string;
  name: string;
  description: string;
  task_type: string;
  labeling_config: string;
  status: 'active' | 'archived' | 'completed';
  auto_annotation: boolean;
  mlflow_run_id?: string;
  created_at: string;
  updated_at?: string;
  stats: {
    total_tasks: number;
    completed_tasks: number;
    in_progress_tasks: number;
    skipped_tasks: number;
    total_annotations: number;
    completion_rate: number;
  };
}

export interface AnnotationTask {
  id: string;
  project_id: string;
  data: {
    image?: string;
    text?: string;
    audio?: string;
    video?: string;
    [key: string]: any;
  };
  annotations: any[];
  predictions?: any[];
  status: 'pending' | 'in_progress' | 'completed' | 'skipped';
  created_at: string;
  updated_at?: string;
}

export interface PreAnnotationRequest {
  task_type: string;
  data: {
    image?: string;
    text?: string;
    [key: string]: any;
  };
  model?: string;
  labels?: string[];
}

export interface PreAnnotationResponse {
  result: any[];
  score: number;
  model: string;
}

export interface TaskImportRequest {
  project_id: string;
  tasks: any[];
  preannotate?: boolean;
  model?: string;
}

export interface AnnotationMetrics {
  project_id: string;
  total_tasks: number;
  completed_tasks: number;
  average_time_per_task: number;
  agreement_score: number;
  quality_score: number;
  annotators: AnnotatorMetric[];
}

export interface AnnotatorMetric {
  user_id: number;
  username: string;
  completed_tasks: number;
  average_time: number;
  agreement_score: number;
}

export interface LabelDistribution {
  [label: string]: number;
}

interface AnnotationState {
  // State
  projects: AnnotationProject[];
  currentProject: AnnotationProject | null;
  tasks: AnnotationTask[];
  currentTask: AnnotationTask | null;
  metrics: AnnotationMetrics | null;
  labelDistribution: LabelDistribution | null;
  loading: boolean;
  error: string | null;

  // Auth
  authToken: string | null;
  labelStudioUrl: string | null;

  // Project actions
  fetchProjects: () => Promise<void>;
  fetchProject: (projectId: string) => Promise<void>;
  createProject: (data: {
    name: string;
    description?: string;
    task_type?: string;
    labeling_config?: string;
    use_default_config?: boolean;
    auto_annotation?: boolean;
    mlflow_run_id?: string;
  }) => Promise<void>;
  deleteProject: (projectId: string) => Promise<void>;
  updateProject: (projectId: string, data: Partial<AnnotationProject>) => Promise<void>;

  // Task actions
  fetchTasks: (projectId: string) => Promise<void>;
  importTasks: (data: TaskImportRequest) => Promise<void>;
  exportAnnotations: (projectId: string, format?: string, onlyFinished?: boolean) => Promise<any>;

  // Pre-annotation
  preAnnotate: (request: PreAnnotationRequest) => Promise<PreAnnotationResponse>;

  // Metrics
  fetchProjectStats: (projectId: string) => Promise<void>;
  fetchAnnotatorPerformance: (projectId: string, startDate?: string, endDate?: string) => Promise<void>;
  fetchLabelDistribution: (projectId: string) => Promise<void>;

  // Auth
  fetchAuthToken: () => Promise<void>;

  // State management
  setCurrentProject: (project: AnnotationProject | null) => void;
  setCurrentTask: (task: AnnotationTask | null) => void;
  clearError: () => void;
}

export const useAnnotationStore = create<AnnotationState>()(
  persist(
    (set, get) => ({
      // Initial state
      projects: [],
      currentProject: null,
      tasks: [],
      currentTask: null,
      metrics: null,
      labelDistribution: null,
      loading: false,
      error: null,
      authToken: null,
      labelStudioUrl: null,

      // Project actions
      fetchProjects: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/annotation/projects');
          set({ projects: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch projects',
            loading: false,
          });
          throw error;
        }
      },

      fetchProject: async (projectId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/annotation/projects/${projectId}`);
          set({ currentProject: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch project',
            loading: false,
          });
          throw error;
        }
      },

      createProject: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/annotation/projects', data);
          set((state) => ({
            projects: [...state.projects, response.data],
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create project',
            loading: false,
          });
          throw error;
        }
      },

      deleteProject: async (projectId: string) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/annotation/projects/${projectId}`);
          set((state) => ({
            projects: state.projects.filter((p) => p.id !== projectId),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete project',
            loading: false,
          });
          throw error;
        }
      },

      updateProject: async (projectId: string, data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.put(`/annotation/projects/${projectId}`, data);
          set((state) => ({
            projects: state.projects.map((p) =>
              p.id === projectId ? { ...p, ...response.data } : p
            ),
            currentProject:
              state.currentProject?.id === projectId
                ? { ...state.currentProject, ...response.data }
                : state.currentProject,
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to update project',
            loading: false,
          });
          throw error;
        }
      },

      // Task actions
      fetchTasks: async (projectId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/annotation/projects/${projectId}/tasks`);
          set({ tasks: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch tasks',
            loading: false,
          });
          throw error;
        }
      },

      importTasks: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/annotation/projects/tasks/import', data);
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to import tasks',
            loading: false,
          });
          throw error;
        }
      },

      exportAnnotations: async (projectId: string, format = 'JSON', onlyFinished = true) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/annotation/projects/tasks/export', {
            project_id: projectId,
            format,
            only_finished: onlyFinished,
          });
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to export annotations',
            loading: false,
          });
          throw error;
        }
      },

      // Pre-annotation
      preAnnotate: async (request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/annotation/pre-annotate', request);
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to pre-annotate',
            loading: false,
          });
          throw error;
        }
      },

      // Metrics
      fetchProjectStats: async (projectId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/annotation/projects/${projectId}/stats`);
          set((state) => ({
            currentProject: state.currentProject
              ? { ...state.currentProject, stats: response.data }
              : null,
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch stats',
            loading: false,
          });
          throw error;
        }
      },

      fetchAnnotatorPerformance: async (projectId: string, startDate?: string, endDate?: string) => {
        set({ loading: true, error: null });
        try {
          const params: Record<string, string> = {};
          if (startDate) params.start_date = startDate;
          if (endDate) params.end_date = endDate;

          const response = await api.get(`/annotation/projects/${projectId}/metrics/performance`, {
            params,
          });
          set({ metrics: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch metrics',
            loading: false,
          });
          throw error;
        }
      },

      fetchLabelDistribution: async (projectId: string) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/annotation/projects/${projectId}/metrics/labels`);
          set({ labelDistribution: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch label distribution',
            loading: false,
          });
          throw error;
        }
      },

      // Auth
      fetchAuthToken: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/annotation/auth/token');
          set({
            authToken: response.data.token,
            labelStudioUrl: response.data.label_studio_url,
            loading: false,
          });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to get auth token',
            loading: false,
          });
          throw error;
        }
      },

      // State management
      setCurrentProject: (project) => set({ currentProject: project }),
      setCurrentTask: (task) => set({ currentTask: task }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'annotation-store',
      partialize: (state) => ({
        projects: state.projects,
        authToken: state.authToken,
        labelStudioUrl: state.labelStudioUrl,
      }),
    }
  )
);

// Selectors
export const useAnnotationProjects = () => useAnnotationStore((state) => state.projects);
export const useCurrentAnnotationProject = () => useAnnotationStore((state) => state.currentProject);
export const useAnnotationTasks = () => useAnnotationStore((state) => state.tasks);
export const useAnnotationMetrics = () => useAnnotationStore((state) => state.metrics);
export const useAnnotationLoading = () => useAnnotationStore((state) => state.loading);
export const useAnnotationError = () => useAnnotationStore((state) => state.error);
export const useLabelStudioAuth = () => useAnnotationStore((state) => ({
  token: state.authToken,
  url: state.labelStudioUrl,
  fetchToken: state.fetchAuthToken,
}));
