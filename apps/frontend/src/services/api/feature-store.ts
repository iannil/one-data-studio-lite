/**
 * Feature Store API Service
 */

import { apiClient } from './client';

export interface Entity {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  entity_type?: string;
  join_keys: string[];
  tags: string[];
  created_at: string;
}

export interface FeatureGroup {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  entity_id?: string;
  primary_keys: string[];
  store_type: string;
  source_type?: string;
  status: string;
  feature_count: number;
  row_count: number;
  created_at: string;
  updated_at: string;
}

export interface Feature {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  feature_group_id: string;
  data_type: string;
  feature_type?: string;
  dimension?: number;
  null_percentage: number;
  mean_value?: number;
  created_at: string;
}

export interface FeatureView {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  feature_group_id: string;
  feature_ids: string[];
  view_type: string;
  serving_mode: string;
  ttl_seconds: number;
  status: string;
  created_at: string;
}

export interface FeatureService {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  feature_view_ids: string[];
  serving_type: string;
  endpoint_path?: string;
  deployment_status: string;
  status: string;
  total_requests: number;
  avg_latency_ms: number;
  created_at: string;
  deployed_at?: string;
}

export const featureStoreApi = {
  // Entities
  createEntity: (data: {
    name: string;
    display_name?: string;
    description?: string;
    entity_type?: string;
    join_keys?: string[];
    tags?: string[];
  }) => apiClient.post<Entity>('/feature-store/entities', data),

  listEntities: (params?: { entity_type?: string; limit?: number; offset?: number }) =>
    apiClient.get<Entity[]>('/feature-store/entities', { params }),

  getEntity: (entityId: string) =>
    apiClient.get<Entity>(`/feature-store/entities/${entityId}`),

  // Feature Groups
  createFeatureGroup: (data: {
    name: string;
    display_name?: string;
    description?: string;
    entity_id?: string;
    primary_keys?: string[];
    store_type?: string;
    source_type?: string;
    tags?: string[];
  }) => apiClient.post<FeatureGroup>('/feature-store/feature-groups', data),

  listFeatureGroups: (entityId?: string, storeType?: string, status?: string) =>
    apiClient.get<FeatureGroup[]>('/feature-store/feature-groups', {
      params: { entity_id: entityId, store_type: storeType, status },
    }),

  getFeatureGroup: (groupId: string) =>
    apiClient.get<FeatureGroup>(`/feature-store/feature-groups/${groupId}`),

  updateFeatureGroup: (groupId: string, data: {
    display_name?: string;
    description?: string;
    tags?: string[];
  }) => apiClient.put(`/feature-store/feature-groups/${groupId}`, data),

  deleteFeatureGroup: (groupId: string) =>
    apiClient.delete(`/feature-store/feature-groups/${groupId}`),

  // Features
  createFeature: (featureGroupId: string, data: {
    name: string;
    data_type: string;
    display_name?: string;
    description?: string;
    feature_type?: string;
    dimension?: number;
    tags?: string[];
  }) => apiClient.post<Feature>(`/feature-store/features?feature_group_id=${featureGroupId}`, data),

  listFeatures: (featureGroupId?: string, entityId?: string, dataType?: string) =>
    apiClient.get<Feature[]>('/feature-store/features', {
      params: { feature_group_id: featureGroupId, entity_id: entityId, data_type: dataType },
    }),

  // Feature Views
  createFeatureView: (data: {
    name: string;
    feature_group_id: string;
    feature_ids: string[];
    display_name?: string;
    description?: string;
    serving_mode?: string;
    tags?: string[];
  }) => apiClient.post<FeatureView>('/feature-store/feature-views', data),

  listFeatureViews: (featureGroupId?: string, servingMode?: string) =>
    apiClient.get<FeatureView[]>('/feature-store/feature-views', {
      params: { feature_group_id: featureGroupId, serving_mode: servingMode },
    }),

  // Feature Services
  createFeatureService: (data: {
    name: string;
    feature_view_ids: string[];
    display_name?: string;
    description?: string;
    serving_type?: string;
    enable_cache?: boolean;
    tags?: string[];
  }) => apiClient.post<FeatureService>('/feature-store/feature-services', data),

  listFeatureServices: (deploymentStatus?: string, status?: string) =>
    apiClient.get<FeatureService[]>('/feature-store/feature-services', {
      params: { deployment_status: deploymentStatus, status },
    }),

  deployFeatureService: (serviceId: string) =>
    apiClient.post<{ success: boolean; message: string }>(`/feature-store/feature-services/${serviceId}/deploy`),

  // Feature Retrieval
  retrieveFeatures: (request: {
    entity_keys: Record<string, any>[];
    feature_view_names: string[];
    point_in_time?: string;
    mode: string;
  }) => apiClient.post<{
    request_id: string;
    features: Record<string, any[]>;
    metadata: Record<string, any>;
    latency_ms: number;
    cached: boolean;
  }>('/feature-store/features/retrieve', request),

  // Health
  getHealthStatus: () =>
    apiClient.get<{
      status: string;
      entities: { total: number };
      feature_groups: { total: number; by_store_type: Record<string, number> };
      features: { total: number };
      feature_views: { total: number };
      feature_services: { total: number; deployed: number };
    }>('/feature-store/feature-store/health'),
};
