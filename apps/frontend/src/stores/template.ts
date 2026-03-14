/**
 * Template Store
 *
 * Zustand store for template marketplace state management.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  WorkflowTemplate,
  TemplateListItem,
  TemplateReview,
  CategoryInfo,
  TemplateFilters,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  InstantiateTemplateRequest,
  AddReviewRequest,
  TemplateCategory,
  TemplateComplexity,
} from '@/types/template';
import { api } from '@/services/api';

// ============================================================================
// Template State
// ============================================================================

interface TemplateState {
  // Templates
  templates: TemplateListItem[];
  currentTemplate: WorkflowTemplate | null;
  selectedTemplateIds: string[];

  // Featured & Trending
  featuredTemplates: TemplateListItem[];
  trendingTemplates: TemplateListItem[];
  recommendedTemplates: TemplateListItem[];

  // Categories
  categories: CategoryInfo[];

  // Reviews
  templateReviews: Record<string, TemplateReview[]>;

  // Filters
  filters: TemplateFilters;

  // UI State
  loading: boolean;
  error: string | null;
  searchQuery: string;

  // Actions
  fetchTemplates: () => Promise<void>;
  fetchTemplate: (id: string) => Promise<void>;
  createTemplate: (data: CreateTemplateRequest) => Promise<WorkflowTemplate>;
  updateTemplate: (id: string, data: UpdateTemplateRequest) => Promise<void>;
  deleteTemplate: (id: string) => Promise<void>;
  instantiateTemplate: (request: InstantiateTemplateRequest) => Promise<void>;
  exportTemplate: (id: string) => Promise<Blob>;
  importTemplate: (file: File) => Promise<WorkflowTemplate>;

  // Market actions
  fetchFeaturedTemplates: (limit?: number) => Promise<void>;
  fetchTrendingTemplates: (limit?: number) => Promise<void>;
  fetchRecommendedTemplates: (limit?: number) => Promise<void>;
  fetchCategories: () => Promise<void>;

  // Reviews
  fetchReviews: (templateId: string) => Promise<void>;
  addReview: (templateId: string, data: AddReviewRequest) => Promise<void>;

  // Filters
  setFilters: (filters: Partial<TemplateFilters>) => void;
  setSearchQuery: (query: string) => void;
  resetFilters: () => void;

  // Selection
  selectTemplate: (id: string) => void;
  selectMultipleTemplates: (ids: string[]) => void;
  clearSelection: () => void;

  // Error handling
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useTemplateStore = create<TemplateState>()(
  persist(
    (set, get) => ({
      // Initial state
      templates: [],
      currentTemplate: null,
      selectedTemplateIds: [],
      featuredTemplates: [],
      trendingTemplates: [],
      recommendedTemplates: [],
      categories: [],
      templateReviews: {},
      filters: {
        sort_by: 'popular',
      },
      loading: false,
      error: null,
      searchQuery: '',

      // ======================================================================
      // Template Actions
      // ======================================================================

      fetchTemplates: async () => {
        set({ loading: true, error: null });
        try {
          const filters = get().filters;
          const searchQuery = get().searchQuery;

          const params = new URLSearchParams();
          if (filters.category) params.append('category', filters.category);
          if (filters.complexity) params.append('complexity', filters.complexity);
          if (filters.tags?.length) params.append('tags', filters.tags.join(','));
          if (filters.sort_by) params.append('sort_by', filters.sort_by);
          if (filters.featured_only) params.append('featured_only', 'true');
          if (filters.verified_only) params.append('verified_only', 'true');
          if (searchQuery) params.append('search', searchQuery);

          const response = await api.get(`/templates/market?${params.toString()}`);
          set({ templates: response.data || [], loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch templates',
            loading: false,
          });
        }
      },

      fetchTemplate: async (id) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/templates/market/${id}`);
          set({ currentTemplate: response.data, loading: false });
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to fetch template',
            loading: false,
          });
        }
      },

      createTemplate: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/templates', data);
          const newTemplate = response.data as WorkflowTemplate;

          set((state) => ({
            templates: [...state.templates, { ...newTemplate, task_count: newTemplate.tasks?.length || 0 }],
            loading: false,
          }));

          return newTemplate;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to create template',
            loading: false,
          });
          throw error;
        }
      },

      updateTemplate: async (id, data) => {
        set({ loading: true, error: null });
        try {
          await api.put(`/templates/${id}`, data);
          set((state) => ({
            templates: state.templates.map((t) =>
              t.id === id ? { ...t, ...data } : t
            ),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to update template',
            loading: false,
          });
          throw error;
        }
      },

      deleteTemplate: async (id) => {
        set({ loading: true, error: null });
        try {
          await api.delete(`/templates/${id}`);
          set((state) => ({
            templates: state.templates.filter((t) => t.id !== id),
            selectedTemplateIds: state.selectedTemplateIds.filter((tid) => tid !== id),
            loading: false,
          }));
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to delete template',
            loading: false,
          });
          throw error;
        }
      },

      instantiateTemplate: async (request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post(`/templates/${request.template_id}/instantiate`, {
            variables: request.variables,
            dag_name: request.dag_name,
          });
          set({ loading: false });
          return response.data;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to instantiate template',
            loading: false,
          });
          throw error;
        }
      },

      exportTemplate: async (id) => {
        try {
          const response = await api.get(`/templates/${id}/export`, {
            responseType: 'blob',
          });
          return response.data as Blob;
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to export template');
        }
      },

      importTemplate: async (file) => {
        set({ loading: true, error: null });
        try {
          const formData = new FormData();
          formData.append('file', file);

          const response = await api.post('/templates/import', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });

          set((state) => ({
            templates: [...state.templates, response.data],
            loading: false,
          }));

          return response.data as WorkflowTemplate;
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || 'Failed to import template',
            loading: false,
          });
          throw error;
        }
      },

      // ======================================================================
      // Market Actions
      // ======================================================================

      fetchFeaturedTemplates: async (limit = 6) => {
        try {
          const response = await api.get(`/templates/market/featured?limit=${limit}`);
          set({ featuredTemplates: response.data || [] });
        } catch (error: any) {
          console.error('Failed to fetch featured templates:', error);
        }
      },

      fetchTrendingTemplates: async (limit = 10) => {
        try {
          const response = await api.get(`/templates/market/trending?limit=${limit}`);
          set({ trendingTemplates: response.data || [] });
        } catch (error: any) {
          console.error('Failed to fetch trending templates:', error);
        }
      },

      fetchRecommendedTemplates: async (limit = 5) => {
        try {
          const response = await api.get(`/templates/market/recommended?limit=${limit}`);
          set({ recommendedTemplates: response.data || [] });
        } catch (error: any) {
          console.error('Failed to fetch recommended templates:', error);
        }
      },

      fetchCategories: async () => {
        try {
          const response = await api.get('/templates/categories');
          set({ categories: response.data || [] });
        } catch (error: any) {
          console.error('Failed to fetch categories:', error);
        }
      },

      // ======================================================================
      // Review Actions
      // ======================================================================

      fetchReviews: async (templateId) => {
        try {
          const response = await api.get(`/templates/${templateId}/reviews`);
          set((state) => ({
            templateReviews: {
              ...state.templateReviews,
              [templateId]: response.data || [],
            },
          }));
        } catch (error: any) {
          console.error('Failed to fetch reviews:', error);
        }
      },

      addReview: async (templateId, data) => {
        try {
          const response = await api.post(`/templates/${templateId}/reviews`, data);
          const newReview = response.data as TemplateReview;

          set((state) => ({
            templateReviews: {
              ...state.templateReviews,
              [templateId]: [
                ...(state.templateReviews[templateId] || []),
                newReview,
              ],
            },
          }));
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Failed to add review');
        }
      },

      // ======================================================================
      // Filters
      // ======================================================================

      setFilters: (partialFilters) => {
        set((state) => ({
          filters: { ...state.filters, ...partialFilters },
        }));
      },

      setSearchQuery: (query) => {
        set({ searchQuery: query });
      },

      resetFilters: () => {
        set({
          filters: { sort_by: 'popular' },
          searchQuery: '',
        });
      },

      // ======================================================================
      // Selection
      // ======================================================================

      selectTemplate: (id) => {
        const template = get().templates.find((t) => t.id === id);
        if (template) {
          set({ currentTemplate: template as unknown as WorkflowTemplate });
        }
      },

      selectMultipleTemplates: (ids) => {
        set({ selectedTemplateIds: ids });
      },

      clearSelection: () => {
        set({ selectedTemplateIds: [], currentTemplate: null });
      },

      // ======================================================================
      // Error Handling
      // ======================================================================

      setError: (error) => {
        set({ error });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'template-storage',
      partialize: (state) => ({
        filters: state.filters,
        selectedTemplateIds: state.selectedTemplateIds,
      }),
    }
  )
);

// ============================================================================
// Selectors
// ============================================================================

export const useTemplates = () => useTemplateStore((state) => state.templates);
export const useCurrentTemplate = () => useTemplateStore((state) => state.currentTemplate);
export const useSelectedTemplates = () => useTemplateStore((state) => state.selectedTemplateIds);
export const useFeaturedTemplates = () => useTemplateStore((state) => state.featuredTemplates);
export const useTrendingTemplates = () => useTemplateStore((state) => state.trendingTemplates);
export const useCategories = () => useTemplateStore((state) => state.categories);
export const useTemplateLoading = () => useTemplateStore((state) => state.loading);
export const useTemplateError = () => useTemplateStore((state) => state.error);

// Computed selectors
export const useCategoryStats = () => {
  const templates = useTemplates();

  const stats = new Map<TemplateCategory, number>();
  templates.forEach((t) => {
    const count = stats.get(t.category as TemplateCategory) || 0;
    stats.set(t.category as TemplateCategory, count + 1);
  });

  return Object.fromEntries(stats);
};

export const useFilteredTemplates = () => {
  const templates = useTemplates();
  const filters = useTemplateStore((state) => state.filters);
  const searchQuery = useTemplateStore((state) => state.searchQuery);

  return templates.filter((t) => {
    if (filters.category && t.category !== filters.category) return false;
    if (filters.complexity && t.complexity !== filters.complexity) return false;
    if (filters.tags?.length && !filters.tags.some((tag) => t.tags?.includes(tag))) return false;
    if (filters.featured_only && !t.featured) return false;
    if (filters.verified_only && !t.verified) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (
        !t.name.toLowerCase().includes(query) &&
        !t.description.toLowerCase().includes(query) &&
        !t.tags?.some((tag) => tag.toLowerCase().includes(query))
      ) {
        return false;
      }
    }
    return true;
  });
};
