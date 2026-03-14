/**
 * Notebook Store
 *
 * Zustand store for managing notebook state and API calls.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';

// Types
export interface Notebook {
  id: string;
  name: string;
  user: string;
  state: 'running' | 'stopped' | 'pending' | 'error';
  image: string;
  cpu_limit: number;
  mem_limit: string;
  gpu_limit: number;
  url?: string;
  pod_name?: string;
  created_at?: string;
  last_activity?: string;
}

export interface NotebookImage {
  id: string;
  name: string;
  description: string;
  image: string;
  icon: string;
  packages: string[];
  default: boolean;
  gpu_required: boolean;
  gpu_recommended: boolean;
}

export interface ResourceProfile {
  id: string;
  name: string;
  description: string;
  cpu_limit: number;
  cpu_guarantee: number;
  mem_limit: string;
  mem_guarantee: string;
  gpu_limit: number;
  default: boolean;
}

interface NotebookState {
  // State
  notebooks: Notebook[];
  images: NotebookImage[];
  profiles: ResourceProfile[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchNotebooks: () => Promise<void>;
  fetchImages: () => Promise<void>;
  fetchProfiles: () => Promise<void>;
  createNotebook: (data: {
    image_id?: string;
    profile_id?: string;
    server_name?: string;
  }) => Promise<Notebook>;
  startNotebook: (userId: string, serverName?: string) => Promise<void>;
  stopNotebook: (userId: string, serverName?: string) => Promise<void>;
  deleteNotebook: (userId: string, serverName?: string) => Promise<void>;
  getNotebook: (userId: string, serverName?: string) => Notebook | undefined;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useNotebookStore = create<NotebookState>()(
  persist(
    (set, get) => ({
      // Initial state
      notebooks: [],
      images: [],
      profiles: [],
      loading: false,
      error: null,

      // Fetch notebooks
      fetchNotebooks: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/notebooks');
          set({ notebooks: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch notebooks',
            loading: false,
          });
          throw error;
        }
      },

      // Fetch images
      fetchImages: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/notebooks/images');
          set({ images: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch images',
            loading: false,
          });
          throw error;
        }
      },

      // Fetch profiles
      fetchProfiles: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/notebooks/profiles');
          set({ profiles: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch profiles',
            loading: false,
          });
          throw error;
        }
      },

      // Create notebook
      createNotebook: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/notebooks', data);
          const newNotebook = response.data;
          set((state) => ({
            notebooks: [...state.notebooks, newNotebook],
            loading: false,
          }));
          return newNotebook;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create notebook',
            loading: false,
          });
          throw error;
        }
      },

      // Start notebook
      startNotebook: async (userId, serverName = '') => {
        set({ loading: true, error: null });
        try {
          // Optimistically update state
          set((state) => ({
            notebooks: state.notebooks.map((nb) =>
              nb.user === userId && nb.name === serverName
                ? { ...nb, state: 'pending' as const }
                : nb
            ),
          }));

          await api.post(`/notebooks/${userId}/start`, { server_name });

          // Poll for notebook to be ready
          const pollInterval = setInterval(async () => {
            try {
              const response = await api.get(`/notebooks/${userId}`);
              const notebook = response.data;

              if (notebook.state === 'running') {
                clearInterval(pollInterval);
                set((state) => ({
                  notebooks: state.notebooks.map((nb) =>
                    nb.user === userId && nb.name === serverName ? notebook : nb
                  ),
                  loading: false,
                }));
              }
            } catch {
              clearInterval(pollInterval);
              set({ loading: false });
            }
          }, 2000);

          // Timeout after 2 minutes
          setTimeout(() => clearInterval(pollInterval), 120000);
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to start notebook',
            loading: false,
          });
          throw error;
        }
      },

      // Stop notebook
      stopNotebook: async (userId, serverName = '') => {
        set({ loading: true, error: null });
        try {
          await api.post(`/notebooks/${userId}/stop`, { server_name });
          set((state) => ({
            notebooks: state.notebooks.map((nb) =>
              nb.user === userId && nb.name === serverName
                ? { ...nb, state: 'stopped' as const }
                : nb
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to stop notebook',
            loading: false,
          });
          throw error;
        }
      },

      // Delete notebook
      deleteNotebook: async (userId, serverName = '') => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/notebooks/${userId}`, { data: { server_name } });
          set((state) => ({
            notebooks: state.notebooks.filter(
              (nb) => !(nb.user === userId && nb.name === serverName)
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete notebook',
            loading: false,
          });
          throw error;
        }
      },

      // Get specific notebook
      getNotebook: (userId, serverName = '') => {
        return get().notebooks.find(
          (nb) => nb.user === userId && nb.name === serverName
        );
      },

      // Set error
      setError: (error) => set({ error }),

      // Clear error
      clearError: () => set({ error: null }),
    }),
    {
      name: 'notebook-store',
      partialize: (state) => ({
        notebooks: state.notebooks,
        images: state.images,
        profiles: state.profiles,
      }),
    }
  )
);

// Selectors for common use cases
export const useUserNotebooks = () => {
  const { user } = useAuthStore();
  const notebooks = useNotebookStore((state) => state.notebooks);

  return notebooks.filter((nb) => nb.user === user?.username);
};

export const useRunningNotebooks = () => {
  const notebooks = useNotebookStore((state) => state.notebooks);
  return notebooks.filter((nb) => nb.state === 'running');
};

// Import useAuthStore (avoiding circular dependency)
// This should be imported from the auth store
import { useAuthStore } from './auth';
