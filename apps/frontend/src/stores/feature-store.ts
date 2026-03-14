/**
 * Feature Store Store - Zustand state management for feature store
 */

import { create } from 'zustand';
import { featureStoreApi } from '@/services/api/feature-store';
import {
  Entity,
  FeatureGroup,
  Feature,
  FeatureView,
  FeatureService,
  FeatureStoreType,
  DataType,
  FeatureType,
  RetrievalMode,
  FeatureRetrievalRequest,
  FeatureRetrievalResponse,
} from '@/types/feature_store';

interface FeatureStoreState {
  // Entities
  entities: Entity[];
  entitiesLoading: boolean;
  entitiesError: string | null;

  // Feature Groups
  featureGroups: FeatureGroup[];
  groupsLoading: boolean;
  groupsError: string | null;

  // Features
  features: Feature[];
  featuresLoading: boolean;
  featuresError: string | null;

  // Feature Views
  featureViews: FeatureView[];
  viewsLoading: boolean;
  viewsError: string | null;

  // Feature Services
  featureServices: FeatureService[];
  servicesLoading: boolean;
  servicesError: string | null;

  // Health
  healthStatus: any | null;

  // Actions
  fetchEntities: () => Promise<void>;
  createEntity: (data: {
    name: string;
    display_name?: string;
    description?: string;
    entity_type?: string;
    join_keys?: string[];
    tags?: string[];
  }) => Promise<Entity>;

  fetchFeatureGroups: (entityId?: string, storeType?: FeatureStoreType) => Promise<void>;
  createFeatureGroup: (data: {
    name: string;
    display_name?: string;
    description?: string;
    entity_id?: string;
    primary_keys?: string[];
    store_type?: FeatureStoreType;
    source_type?: string;
    tags?: string[];
  }) => Promise<FeatureGroup>;
  updateFeatureGroup: (groupId: string, data: any) => Promise<void>;
  deleteFeatureGroup: (groupId: string) => Promise<void>;

  fetchFeatures: (featureGroupId?: string, entityId?: string, dataType?: DataType) => Promise<void>;
  createFeature: (featureGroupId: string, data: {
    name: string;
    data_type: DataType;
    display_name?: string;
    description?: string;
    feature_type?: FeatureType;
    dimension?: number;
    tags?: string[];
  }) => Promise<Feature>;

  fetchFeatureViews: (featureGroupId?: string) => Promise<void>;
  createFeatureView: (data: {
    name: string;
    feature_group_id: string;
    feature_ids: string[];
    display_name?: string;
    description?: string;
    serving_mode?: string;
    tags?: string[];
  }) => Promise<FeatureView>;

  fetchFeatureServices: (deploymentStatus?: string) => Promise<void>;
  createFeatureService: (data: {
    name: string;
    feature_view_ids: string[];
    display_name?: string;
    description?: string;
    serving_type?: string;
    enable_cache?: boolean;
    tags?: string[];
  }) => Promise<FeatureService>;
  deployFeatureService: (serviceId: string) => Promise<void>;

  retrieveFeatures: (request: FeatureRetrievalRequest) => Promise<FeatureRetrievalResponse>;

  fetchHealthStatus: () => Promise<void>;
}

export const useFeatureStoreStore = create<FeatureStoreState>((set, get) => ({
  // Initial state
  entities: [],
  entitiesLoading: false,
  entitiesError: null,
  featureGroups: [],
  groupsLoading: false,
  groupsError: null,
  features: [],
  featuresLoading: false,
  featuresError: null,
  featureViews: [],
  viewsLoading: false,
  viewsError: null,
  featureServices: [],
  servicesLoading: false,
  servicesError: null,
  healthStatus: null,

  // Entity actions
  fetchEntities: async () => {
    set({ entitiesLoading: true, entitiesError: null });
    try {
      const response = await featureStoreApi.listEntities();
      set({ entities: response.data || [], entitiesLoading: false });
    } catch (error: any) {
      set({
        entitiesError: error.message || 'Failed to fetch entities',
        entitiesLoading: false,
      });
    }
  },

  createEntity: async (data) => {
    try {
      const response = await featureStoreApi.createEntity(data);
      const entity = response.data;
      set((state) => ({ entities: [...state.entities, entity] }));
      return entity;
    } catch (error: any) {
      throw new Error(error.message || 'Failed to create entity');
    }
  },

  // Feature Group actions
  fetchFeatureGroups: async (entityId, storeType) => {
    set({ groupsLoading: true, groupsError: null });
    try {
      const response = await featureStoreApi.listFeatureGroups(entityId, storeType);
      set({ featureGroups: response.data || [], groupsLoading: false });
    } catch (error: any) {
      set({
        groupsError: error.message || 'Failed to fetch feature groups',
        groupsLoading: false,
      });
    }
  },

  createFeatureGroup: async (data) => {
    try {
      const response = await featureStoreApi.createFeatureGroup(data);
      const group = response.data;
      set((state) => ({ featureGroups: [...state.featureGroups, group] }));
      return group;
    } catch (error: any) {
      throw new Error(error.message || 'Failed to create feature group');
    }
  },

  updateFeatureGroup: async (groupId, data) => {
    try {
      await featureStoreApi.updateFeatureGroup(groupId, data);
      await get().fetchFeatureGroups();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to update feature group');
    }
  },

  deleteFeatureGroup: async (groupId) => {
    try {
      await featureStoreApi.deleteFeatureGroup(groupId);
      set((state) => ({
        featureGroups: state.featureGroups.filter((g) => g.id !== groupId),
      }));
    } catch (error: any) {
      throw new Error(error.message || 'Failed to delete feature group');
    }
  },

  // Feature actions
  fetchFeatures: async (featureGroupId, entityId, dataType) => {
    set({ featuresLoading: true, featuresError: null });
    try {
      const response = await featureStoreApi.listFeatures(featureGroupId, entityId, dataType);
      set({ features: response.data || [], featuresLoading: false });
    } catch (error: any) {
      set({
        featuresError: error.message || 'Failed to fetch features',
        featuresLoading: false,
      });
    }
  },

  createFeature: async (featureGroupId, data) => {
    try {
      const response = await featureStoreApi.createFeature(featureGroupId, data);
      const feature = response.data;
      set((state) => ({ features: [...state.features, feature] }));
      return feature;
    } catch (error: any) {
      throw new Error(error.message || 'Failed to create feature');
    }
  },

  // Feature View actions
  fetchFeatureViews: async (featureGroupId) => {
    set({ viewsLoading: true, viewsError: null });
    try {
      const response = await featureStoreApi.listFeatureViews(featureGroupId);
      set({ featureViews: response.data || [], viewsLoading: false });
    } catch (error: any) {
      set({
        viewsError: error.message || 'Failed to fetch feature views',
        viewsLoading: false,
      });
    }
  },

  createFeatureView: async (data) => {
    try {
      const response = await featureStoreApi.createFeatureView(data);
      const view = response.data;
      set((state) => ({ featureViews: [...state.featureViews, view] }));
      return view;
    } catch (error: any) {
      throw new Error(error.message || 'Failed to create feature view');
    }
  },

  // Feature Service actions
  fetchFeatureServices: async (deploymentStatus) => {
    set({ servicesLoading: true, servicesError: null });
    try {
      const response = await featureStoreApi.listFeatureServices(deploymentStatus);
      set({ featureServices: response.data || [], servicesLoading: false });
    } catch (error: any) {
      set({
        servicesError: error.message || 'Failed to fetch feature services',
        servicesLoading: false,
      });
    }
  },

  createFeatureService: async (data) => {
    try {
      const response = await featureStoreApi.createFeatureService(data);
      const service = response.data;
      set((state) => ({ featureServices: [...state.featureServices, service] }));
      return service;
    } catch (error: any) {
      throw new Error(error.message || 'Failed to create feature service');
    }
  },

  deployFeatureService: async (serviceId) => {
    try {
      await featureStoreApi.deployFeatureService(serviceId);
      await get().fetchFeatureServices();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to deploy feature service');
    }
  },

  retrieveFeatures: async (request) => {
    try {
      const response = await featureStoreApi.retrieveFeatures(request);
      return response.data;
    } catch (error: any) {
      throw new Error(error.message || 'Failed to retrieve features');
    }
  },

  fetchHealthStatus: async () => {
    try {
      const response = await featureStoreApi.getHealthStatus();
      set({ healthStatus: response.data });
    } catch (error) {
      console.error('Failed to fetch health status:', error);
    }
  },
}));
