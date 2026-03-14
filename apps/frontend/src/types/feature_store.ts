/**
 * Feature Store Type Definitions
 */

export enum FeatureStoreType {
  OFFLINE = 'offline',
  ONLINE = 'online',
  HYBRID = 'hybrid',
}

export enum DataType {
  INT = 'int',
  FLOAT = 'float',
  STRING = 'string',
  BOOL = 'bool',
  ARRAY = 'array',
  VECTOR = 'vector',
  TIMESTAMP = 'timestamp',
}

export enum FeatureType {
  CONTINUOUS = 'continuous',
  CATEGORICAL = 'categorical',
  ORDINAL = 'ordinal',
  TEXT = 'text',
  EMBEDDING = 'embedding',
}

export enum RetrievalMode {
  ONLINE = 'online',
  OFFLINE = 'offline',
  HYBRID = 'hybrid',
}

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
  store_type: FeatureStoreType;
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
  data_type: DataType;
  feature_type?: FeatureType;
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

export interface FeatureValue {
  value: any;
  timestamp: string;
  is_null: boolean;
}

export interface FeatureRow {
  entity_key: Record<string, any>;
  features: Record<string, FeatureValue>;
  event_timestamp?: string;
}

export interface FeatureRetrievalRequest {
  entity_keys: Record<string, any>[];
  feature_view_names: string[];
  point_in_time?: string;
  mode: RetrievalMode;
}

export interface FeatureRetrievalResponse {
  request_id: string;
  features: Record<string, FeatureRow[]>;
  metadata: {
    mode: string;
    entity_count: number;
    feature_view_count: number;
  };
  latency_ms: number;
  cached: boolean;
}

// Type labels and colors
export const DATA_TYPE_LABELS: Record<DataType, string> = {
  [DataType.INT]: 'Integer',
  [DataType.FLOAT]: 'Float',
  [DataType.STRING]: 'String',
  [DataType.BOOL]: 'Boolean',
  [DataType.ARRAY]: 'Array',
  [DataType.VECTOR]: 'Vector',
  [DataType.TIMESTAMP]: 'Timestamp',
};

export const DATA_TYPE_COLORS: Record<DataType, string> = {
  [DataType.INT]: '#1890ff',
  [DataType.FLOAT]: '#52c41a',
  [DataType.STRING]: '#faad14',
  [DataType.BOOL]: '#eb2f96',
  [DataType.ARRAY]: '#722ed1',
  [DataType.VECTOR]: '#13c2c2',
  [DataType.TIMESTAMP]: '#fa8c16',
};

export const FEATURE_STORE_TYPE_LABELS: Record<FeatureStoreType, string> = {
  [FeatureStoreType.OFFLINE]: 'Offline',
  [FeatureStoreType.ONLINE]: 'Online',
  [FeatureStoreType.HYBRID]: 'Hybrid',
};

export const FEATURE_STORE_TYPE_COLORS: Record<FeatureStoreType, string> = {
  [FeatureStoreType.OFFLINE]: '#1890ff',
  [FeatureStoreType.ONLINE]: '#52c41a',
  [FeatureStoreType.HYBRID]: '#722ed1',
};

export const FEATURE_TYPE_LABELS: Record<FeatureType, string> = {
  [FeatureType.CONTINUOUS]: 'Continuous',
  [FeatureType.CATEGORICAL]: 'Categorical',
  [FeatureType.ORDINAL]: 'Ordinal',
  [FeatureType.TEXT]: 'Text',
  [FeatureType.EMBEDDING]: 'Embedding',
};
