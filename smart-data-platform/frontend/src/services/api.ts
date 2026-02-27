import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3101/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
};

// Data Sources
export const sourcesApi = {
  list: (skip = 0, limit = 100) =>
    api.get('/sources', { params: { skip, limit } }),
  get: (id: string) => api.get(`/sources/${id}`),
  create: (data: any) => api.post('/sources', data),
  update: (id: string, data: any) => api.patch(`/sources/${id}`, data),
  delete: (id: string) => api.delete(`/sources/${id}`),
  test: (id: string) => api.post(`/sources/${id}/test`),
  scan: (id: string, data?: any) => api.post(`/sources/${id}/scan`, data || {}),
  getTables: (id: string) => api.get(`/sources/${id}/tables`),
};

// Metadata
export const metadataApi = {
  listTables: (sourceId?: string, skip = 0, limit = 1000) =>
    api.get('/metadata/tables', { params: { source_id: sourceId, skip, limit } }),
  getTable: (id: string) => api.get(`/metadata/tables/${id}`),
  aiAnalyze: (sourceId: string, tableName: string) =>
    api.post('/metadata/ai-analyze', null, { params: { source_id: sourceId, table_name: tableName } }),
  batchUpdateTags: (data: {
    table_ids?: string[];
    column_ids?: string[];
    tags_to_add?: string[];
    tags_to_remove?: string[];
  }) => api.post('/metadata/batch-tags', data),
  listAllTags: () => api.get('/metadata/tags'),
};

// ETL
export const etlApi = {
  listPipelines: (status?: string, skip = 0, limit = 100) =>
    api.get('/etl/pipelines', { params: { status, skip, limit } }),
  getPipeline: (id: string) => api.get(`/etl/pipelines/${id}`),
  createPipeline: (data: any) => api.post('/etl/pipelines', data),
  updatePipeline: (id: string, data: any) => api.patch(`/etl/pipelines/${id}`, data),
  deletePipeline: (id: string) => api.delete(`/etl/pipelines/${id}`),
  runPipeline: (id: string, previewMode = false) =>
    api.post(`/etl/pipelines/${id}/run`, { preview_mode: previewMode }),
  previewPipeline: (id: string, rows = 100) =>
    api.post(`/etl/pipelines/${id}/preview`, null, { params: { rows } }),
  listExecutions: (pipelineId: string, skip = 0, limit = 20) =>
    api.get(`/etl/pipelines/${pipelineId}/executions`, { params: { skip, limit } }),
  suggestRules: (sourceId: string, tableName: string, sampleSize = 1000) =>
    api.post('/etl/ai/suggest-rules', { source_id: sourceId, table_name: tableName, sample_size: sampleSize }),
};

// Collection
export const collectApi = {
  listTasks: (sourceId?: string, status?: string, skip = 0, limit = 100) =>
    api.get('/collect/tasks', { params: { source_id: sourceId, status, skip, limit } }),
  getTask: (id: string) => api.get(`/collect/tasks/${id}`),
  createTask: (data: any) => api.post('/collect/tasks', data),
  updateTask: (id: string, data: any) => api.patch(`/collect/tasks/${id}`, data),
  deleteTask: (id: string) => api.delete(`/collect/tasks/${id}`),
  runTask: (id: string, forceFullSync = false) =>
    api.post(`/collect/tasks/${id}/run`, { force_full_sync: forceFullSync }),
  listExecutions: (taskId: string, skip = 0, limit = 20) =>
    api.get(`/collect/tasks/${taskId}/executions`, { params: { skip, limit } }),
  addSchedule: (id: string, cronExpression: string) =>
    api.post(`/collect/tasks/${id}/schedule`, null, { params: { cron_expression: cronExpression } }),
  removeSchedule: (id: string) => api.delete(`/collect/tasks/${id}/schedule`),
  getSchedule: (id: string) => api.get(`/collect/tasks/${id}/schedule`),
  pauseSchedule: (id: string) => api.post(`/collect/tasks/${id}/schedule/pause`),
  resumeSchedule: (id: string) => api.post(`/collect/tasks/${id}/schedule/resume`),
  listJobs: () => api.get('/collect/jobs'),
  previewSchedule: (cronExpression: string, count = 5) =>
    api.get('/collect/schedule/preview', { params: { cron_expression: cronExpression, count } }),
};

// Analysis
export const analysisApi = {
  nlQuery: (query: string, contextTables?: string[], limit = 100) =>
    api.post('/analysis/nl-query', { query, context_tables: contextTables, limit }),
  dataQuality: (sourceId: string, tableName: string, sampleSize = 10000) =>
    api.post('/analysis/data-quality', { source_id: sourceId, table_name: tableName, sample_size: sampleSize }),
  predict: (data: any) => api.post('/analysis/predict', data),
  // Time series prediction
  predictTimeSeries: (data: {
    source_table: string;
    target_column: string;
    config?: Record<string, unknown>;
  }) => api.post('/analysis/predict', {
    model_type: 'timeseries',
    source_table: data.source_table,
    target_column: data.target_column,
    config: data.config || {},
  }),
  // Clustering analysis
  clusterAnalysis: (data: {
    source_table: string;
    features?: string[];
    n_clusters?: number;
  }) => api.post('/analysis/predict', {
    model_type: 'clustering',
    source_table: data.source_table,
    target_column: data.features?.[0] || '',
    config: {
      n_clusters: data.n_clusters || 3,
      features: data.features || [],
    },
  }),
  // Anomaly detection
  detectAnomalies: (data: {
    data: Record<string, unknown>[];
    features: string[];
    method?: string;
  }) => api.post('/analysis/anomalies', data),
  // Forecasting
  forecast: (data: {
    data: Array<{ date: string; value: number }>;
    date_column: string;
    value_column: string;
    periods?: number;
    method?: string;
  }) => api.post('/analysis/forecast', data),
  // Enhanced clustering
  clusterEnhanced: (data: {
    data: Record<string, unknown>[];
    features: string[];
    algorithm?: string;
    n_clusters?: number;
  }) => api.post('/analysis/cluster-enhanced', data),
};

// Data Quality
export const qualityApi = {
  getAssessment: (assetId: string) =>
    api.get(`/quality/assessment/${assetId}`),
  getIssues: (params?: { asset_id?: string; source_id?: string; table_name?: string; severity?: string; skip?: number; limit?: number }) =>
    api.get('/quality/issues', { params }),
  getTrend: (assetId: string, days = 30) =>
    api.get(`/quality/trend/${assetId}`, { params: { days } }),
  getReport: (assetId: string) =>
    api.get(`/quality/report/${assetId}`),
  runAssessment: (sourceId: string, tableName: string) =>
    api.post('/quality/assessment', { source_id: sourceId, table_name: tableName }),
};

// Assets
export const assetsApi = {
  list: (params?: any) => api.get('/assets', { params }),
  get: (id: string) => api.get(`/assets/${id}`),
  create: (data: any) => api.post('/assets', data),
  update: (id: string, data: any) => api.patch(`/assets/${id}`, data),
  delete: (id: string) => api.delete(`/assets/${id}`),
  search: (data: any) => api.post('/assets/search', data),
  getLineage: (id: string, depth = 1) =>
    api.get(`/assets/${id}/lineage`, { params: { depth } }),
  export: (id: string, data: any) => api.post(`/assets/${id}/export`, data),
  certify: (id: string) => api.post(`/assets/${id}/certify`),
  getValue: (id: string) => api.get(`/assets/${id}/value`),
  refreshValue: (id: string) => api.post(`/assets/${id}/value/refresh`),
  getUsageStats: (id: string, days = 30) =>
    api.get(`/assets/${id}/usage-stats`, { params: { days } }),
  getValueDistribution: () => api.get('/assets/value/distribution'),
  batchRefreshValues: () => api.post('/assets/value/batch-refresh'),
  aiSearch: (query: string, limit = 20) =>
    api.post('/assets/ai-search', null, { params: { query, limit } }),
  // API Configuration
  getApiConfig: (id: string) => api.get(`/assets/${id}/api-config`),
  updateApiConfig: (id: string, data: {
    is_enabled?: boolean;
    endpoint_slug?: string;
    rate_limit_requests?: number;
    rate_limit_window_seconds?: number;
    allow_query?: boolean;
    allow_export?: boolean;
    allowed_export_formats?: string[];
    exposed_columns?: string[];
    hidden_columns?: string[];
    default_limit?: number;
    max_limit?: number;
    require_auth?: boolean;
    allowed_roles?: string[];
    enable_desensitization?: boolean;
    desensitization_rules?: Record<string, unknown>;
  }) => api.put(`/assets/${id}/api-config`, data),
  deleteApiConfig: (id: string) => api.delete(`/assets/${id}/api-config`),
  getApiDocs: (id: string) => api.get(`/assets/${id}/api-docs`),
  // Subscriptions
  subscribe: (id: string, data?: {
    event_types?: string[];
    notify_email?: boolean;
    notify_in_app?: boolean;
    notes?: string;
  }) => api.post(`/assets/${id}/subscribe`, data || {}),
  unsubscribe: (id: string) => api.delete(`/assets/${id}/subscribe`),
  getSubscription: (id: string) => api.get(`/assets/${id}/subscription`),
  updateSubscription: (id: string, data: {
    event_types?: string[];
    is_active?: boolean;
    notify_email?: boolean;
    notify_in_app?: boolean;
    notes?: string;
  }) => api.patch(`/assets/${id}/subscription`, data),
  getSubscribers: (id: string) => api.get(`/assets/${id}/subscribers`),
};

// User Subscriptions
export const subscriptionsApi = {
  list: (isActive?: boolean) =>
    api.get('/subscriptions', { params: { is_active: isActive } }),
  delete: (subscriptionId: string) =>
    api.delete(`/subscriptions/${subscriptionId}`),
  batchUnsubscribe: (assetIds: string[]) =>
    api.post('/subscriptions/batch-unsubscribe', assetIds),
};

// Alerts
export const alertsApi = {
  listRules: (skip = 0, limit = 100) =>
    api.get('/alerts/rules', { params: { skip, limit } }),
  createRule: (data: any) => api.post('/alerts/rules', data),
  updateRule: (id: string, data: any) => api.patch(`/alerts/rules/${id}`, data),
  deleteRule: (id: string) => api.delete(`/alerts/rules/${id}`),
  listAlerts: (status?: string, skip = 0, limit = 100) =>
    api.get('/alerts', { params: { status, skip, limit } }),
  acknowledgeAlert: (id: string) => api.post(`/alerts/${id}/acknowledge`),
  resolveAlert: (id: string, note?: string) =>
    api.post(`/alerts/${id}/resolve`, { resolution_note: note }),
  detectAnomalies: (sourceId: string, tableName: string, columnName: string, method = 'zscore', threshold = 3.0) =>
    api.post('/alerts/detect-anomalies', {
      source_id: sourceId,
      table_name: tableName,
      column_name: columnName,
      method,
      threshold,
    }),
};

// Security
export const securityApi = {
  detectSensitive: (sourceId: string, tableName: string) =>
    api.post('/security/detect-sensitive', null, { params: { source_id: sourceId, table_name: tableName } }),
  listAuditLogs: (params?: any) => api.get('/audit/logs', { params }),
};

// BI Integration
export const biApi = {
  getStatus: () => api.get('/bi/status'),
  listDatasets: () => api.get('/bi/datasets'),
  syncTable: (tableName: string, schemaName = 'public') =>
    api.post(`/bi/sync/${tableName}`, { schema_name: schemaName }),
  getSyncStatus: (tableName: string, schemaName = 'public') =>
    api.get(`/bi/sync/${tableName}`, { params: { schema_name: schemaName } }),
  unsyncTable: (tableName: string, schemaName = 'public') =>
    api.delete(`/bi/sync/${tableName}`, { params: { schema_name: schemaName } }),
  batchSync: (tables: string[], schemaName = 'public') =>
    api.post('/bi/sync-batch', { tables, schema_name: schemaName }),
  syncAsset: (assetId: string) =>
    api.post(`/bi/sync-asset/${assetId}`),
};

// Data Standards
export const standardsApi = {
  list: (params?: { standard_type?: string; status?: string }) =>
    api.get('/standards', { params }),
  get: (id: string) => api.get(`/standards/${id}`),
  create: (data: {
    name: string;
    code: string;
    description?: string;
    standard_type: string;
    rules: Record<string, unknown>;
    applicable_domains?: string[];
    applicable_data_types?: string[];
    tags?: string[];
    department?: string;
  }) => api.post('/standards', data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/standards/${id}`, data),
  delete: (id: string) => api.delete(`/standards/${id}`),
  suggest: (data: { source_id: string; table_name: string }) =>
    api.post('/standards/suggest', data),
  createFromSuggestion: (suggestion: Record<string, unknown>) =>
    api.post('/standards/suggest/create', suggestion),
  approve: (id: string) => api.post(`/standards/${id}/approve`),
  createVersion: (id: string, data: { updated_rules: Record<string, unknown> }) =>
    api.post(`/standards/${id}/version`, data),
  apply: (data: {
    standard_id: string;
    target_type: string;
    table_name?: string;
    column_name?: string;
    source_id?: string;
    asset_id?: string;
    is_mandatory?: boolean;
  }) => api.post('/standards/apply', data),
  checkCompliance: (data: {
    standard_id: string;
    source_id?: string;
    table_name?: string;
    column_name?: string;
  }) => api.post('/standards/compliance/check', data),
  getComplianceHistory: (params?: {
    standard_id?: string;
    table_name?: string;
    column_name?: string;
    limit?: number;
  }) => api.get('/standards/compliance/history', { params }),
};

// Data Service
export const dataServiceApi = {
  query: (data: {
    asset_id: string;
    query_params?: {
      filters?: Array<{ column: string; operator: string; value: unknown }>;
      sort_by?: string;
      sort_order?: string;
      columns?: string[];
    };
    limit?: number;
    offset?: number;
  }) => api.post('/data-service/query', data),
  querySimple: (assetId: string, params?: {
    limit?: number;
    offset?: number;
    sort_by?: string;
    sort_order?: string;
  }) => api.get(`/data-service/query/${assetId}`, { params }),
  export: (data: {
    asset_id: string;
    format?: 'csv' | 'json' | 'parquet' | 'excel';
    query_params?: {
      filters?: Array<{ column: string; operator: string; value: unknown }>;
      sort_by?: string;
      sort_order?: string;
      columns?: string[];
    };
    limit?: number;
  }) => api.post('/data-service/export', data, { responseType: 'blob' }),
  exportSimple: (assetId: string, params?: {
    format?: string;
    limit?: number;
  }) => api.get(`/data-service/export/${assetId}`, { params, responseType: 'blob' }),
  getStatistics: (params?: { asset_id?: string; user_id?: string; days?: number }) =>
    api.get('/data-service/statistics', { params }),
  getTopAssets: (params?: { limit?: number; days?: number }) =>
    api.get('/data-service/top-assets', { params }),
};

// Permissions
export const permissionsApi = {
  suggestForAsset: (assetId: string) =>
    api.get(`/permissions/suggest/asset/${assetId}`),
  suggestForUser: (userId: string) =>
    api.get(`/permissions/suggest/user/${userId}`),
  autoConfigure: (data: { user_id: string; department?: string }) =>
    api.post('/permissions/auto-configure', data),
  check: (data: { user_id: string; asset_id: string; operation?: string }) =>
    api.post('/permissions/check', data),
  recordChange: (data: {
    target_user_id: string;
    action: 'grant' | 'revoke' | 'modify';
    details: Record<string, unknown>;
  }) => api.post('/permissions/audit', data),
  getAuditHistory: (params?: { user_id?: string; limit?: number }) =>
    api.get('/permissions/audit', { params }),
};

// OCR Document Processing
export const ocrApi = {
  process: (file: File, extractStructured = true) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/ocr/process', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { extract_structured: extractStructured },
    });
  },
  batchProcess: (files: File[], extractStructured = true) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return api.post('/ocr/batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { extract_structured: extractStructured },
    });
  },
  getSupportedTypes: () => api.get('/ocr/supported-types'),
};

// Lineage
export const lineageApi = {
  getAssetLineage: (assetId: string, direction = 'both', depth = 3) =>
    api.get(`/lineage/asset/${assetId}`, { params: { direction, depth } }),
  getGlobalGraph: (nodeTypes?: string, limit = 100) =>
    api.get('/lineage/graph', { params: { node_types: nodeTypes, limit } }),
  impactAnalysis: (assetId: string, includeDownstream = true) =>
    api.post(`/lineage/impact/${assetId}`, null, {
      params: { include_downstream: includeDownstream },
    }),
  buildLineage: (data?: { rebuild_all?: boolean; source_ids?: string[]; asset_ids?: string[] }) =>
    api.post('/lineage/build', data),
  getUpstream: (nodeId: string, depth = 3) =>
    api.get(`/lineage/upstream/${nodeId}`, { params: { depth } }),
  getDownstream: (nodeId: string, depth = 3) =>
    api.get(`/lineage/downstream/${nodeId}`, { params: { depth } }),
  discoverRelations: (data?: { source_ids?: string[]; confidence_threshold?: number }) =>
    api.post('/lineage/discover-relations', data),
};

// Reports
export const reportsApi = {
  list: (params?: { status?: string; is_public?: boolean; skip?: number; limit?: number }) =>
    api.get('/reports', { params }),
  get: (id: string) => api.get(`/reports/${id}`),
  create: (data: {
    name: string;
    description?: string;
    department?: string;
    is_public?: boolean;
    layout_config?: Record<string, unknown>;
    tags?: string[];
    auto_refresh?: boolean;
    refresh_interval_seconds?: number;
    charts?: Array<{
      title: string;
      description?: string;
      chart_type: string;
      query_type?: string;
      nl_query?: string;
      sql_query?: string;
      asset_id?: string;
      chart_options?: Record<string, unknown>;
      x_field?: string;
      y_field?: string;
      group_by?: string;
      position?: number;
      grid_x?: number;
      grid_y?: number;
      grid_width?: number;
      grid_height?: number;
    }>;
  }) => api.post('/reports', data),
  update: (id: string, data: Record<string, unknown>) => api.patch(`/reports/${id}`, data),
  delete: (id: string) => api.delete(`/reports/${id}`),
  addChart: (reportId: string, data: {
    title: string;
    description?: string;
    chart_type: string;
    query_type?: string;
    nl_query?: string;
    sql_query?: string;
    asset_id?: string;
    chart_options?: Record<string, unknown>;
    x_field?: string;
    y_field?: string;
    group_by?: string;
    position?: number;
    grid_x?: number;
    grid_y?: number;
    grid_width?: number;
    grid_height?: number;
  }) => api.post(`/reports/${reportId}/charts`, data),
  updateChart: (reportId: string, chartId: string, data: Record<string, unknown>) =>
    api.patch(`/reports/${reportId}/charts/${chartId}`, data),
  deleteChart: (reportId: string, chartId: string) =>
    api.delete(`/reports/${reportId}/charts/${chartId}`),
  refresh: (id: string) => api.post(`/reports/${id}/refresh`),
  publish: (id: string) => api.post(`/reports/${id}/publish`),
};

// Celery Task Management
export const celeryApi = {
  getStatus: () => api.get('/celery/status'),
  getWorkers: () => api.get('/celery/workers'),
  getTaskStatus: (taskId: string) => api.get(`/celery/task/${taskId}`),
  cancelTask: (taskId: string) => api.post(`/celery/task/${taskId}/cancel`),
  getQueues: () => api.get('/celery/queues'),
  getFlowerUrl: () => api.get('/celery/flower/url'),
  // Admin only
  shutdownWorkers: () => api.post('/celery/worker/shutdown'),
  restartPools: () => api.post('/celery/worker/pool/restart'),
};

export default api;
