/**
 * Argo Workflow Types
 *
 * Types for Argo Workflow integration.
 */

// ============================================================================
// Enums
// ============================================================================

export enum WorkflowPhase {
  PENDING = 'Pending',
  RUNNING = 'Running',
  SUCCEEDED = 'Succeeded',
  FAILED = 'Failed',
  ERROR = 'Error',
  SKIPPED = 'Skipped',
}

export enum NodePhase {
  PENDING = 'Pending',
  RUNNING = 'Running',
  SUCCEEDED = 'Succeeded',
  FAILED = 'Failed',
  ERROR = 'Error',
  SKIPPED = 'Skipped',
  OMITTED = 'Omitted',
}

export enum ArtifactLocation {
  S3 = 's3',
  GCS = 'gcs',
  GIT = 'git',
  HTTP = 'http',
  RAW = 'raw',
  MEMORY = 'memory',
}

export enum TaskType {
  SQL = 'sql',
  PYTHON = 'python',
  SHELL = 'shell',
  NOTEBOOK = 'notebook',
  ETL = 'etl',
  TRAINING = 'training',
  INFERENCE = 'inference',
  EVALUATION = 'evaluation',
  MODEL_REGISTER = 'model_register',
  EMAIL = 'email',
  SENSOR = 'sensor',
  HTTP = 'http',
  NOTIFICATION = 'notification',
  CUSTOM = 'custom',
}

// ============================================================================
// Workflow Types
// ============================================================================

export interface Artifact {
  name: string;
  path: string;
  location_type: ArtifactLocation;
  location?: string;
  from?: string;
  archive?: Record<string, unknown>;
  mode?: number;
}

export interface ResourceRequirements {
  requests_cpu?: string;
  requests_memory?: string;
  limits_cpu?: string;
  limits_memory?: string;
  gpu_count?: number;
  gpu_type?: string;
  ephemeral_storage?: string;
}

export interface DAGNode {
  node_id: string;
  name: string;
  task_type: TaskType;
  description?: string;
  image?: string;
  command?: string[];
  args?: string[];
  script?: string;
  source_code?: string;
  depends_on?: string[];
  cpu_request?: string;
  cpu_limit?: string;
  memory_request?: string;
  memory_limit?: string;
  gpu_count?: number;
  env_vars?: Record<string, string>;
  retry_count?: number;
  retry_backoff?: number;
  retry_duration?: string;
  timeout_seconds?: number;
  position_x?: number;
  position_y?: number;
}

export interface DAGEdge {
  from_node: string;
  to_node: string;
  condition?: string;
}

export interface DAGDefinition {
  dag_id: string;
  name: string;
  description?: string;
  schedule?: string;
  tags?: string[];
  nodes: DAGNode[];
  edges: DAGEdge[];
  namespace?: string;
  service_account?: string;
  ttl_seconds_after_finished?: number;
  parallelism?: number;
  s3_bucket?: string;
  s3_endpoint?: string;
  s3_access_key?: string;
  s3_secret_key?: string;
}

export interface Workflow {
  name: string;
  namespace: string;
  entrypoint?: string;
  templates?: WorkflowNode[];
  arguments?: Record<string, unknown>;
  tasks?: Record<string, unknown>[];
  service_account_name?: string;
  automount_service_account_token?: boolean;
  executors?: Record<string, unknown>;
  pod_spec_patch?: string;
  pod_metadata?: Record<string, unknown>;
  node_selector?: Record<string, string>;
  tolerations?: Record<string, unknown>[];
  affinity?: Record<string, unknown>;
  parallelism?: number;
  ttl_seconds_after_finished?: number;
  artifact_repository?: Record<string, unknown>;
  labels?: Record<string, string>;
  annotations?: Record<string, string>;
  priority?: number;
  created_at?: string;
  started_at?: string;
  finished_at?: string;
  phase?: WorkflowPhase;
}

export interface WorkflowNode {
  name: string;
  template_type: string;
  image?: string;
  command?: string[];
  args?: string[];
  script?: string;
  source?: string;
  dependencies?: string[];
  resources?: ResourceRequirements;
  active_deadline_seconds?: number;
  retry_strategy?: Record<string, unknown>;
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  input_artifacts?: Artifact[];
  output_artifacts?: Artifact[];
  working_dir?: string;
  env?: Record<string, string>;
  volume_mounts?: Record<string, unknown>[];
  labels?: Record<string, string>;
  annotations?: Record<string, string>;
}

export interface WorkflowStatus {
  name: string;
  namespace: string;
  phase: WorkflowPhase;
  started_at?: string;
  finished_at?: string;
  message?: string;
  nodes: Record<string, WorkflowNodeInfo>;
  started_at_iso?: string;
  finished_at_iso?: string;
  conditions?: Record<string, unknown>[];
  resources_duration?: string;
  progress?: string;
}

export interface WorkflowNodeInfo {
  id: string;
  name: string;
  phase: NodePhase;
  started_at?: string;
  finished_at?: string;
  message?: string;
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  children?: string[];
}

export interface WorkflowListItem {
  metadata: {
    name: string;
    namespace: string;
    uid: string;
    creationTimestamp: string;
    labels?: Record<string, string>;
    annotations?: Record<string, string>;
  };
  spec: Record<string, unknown>;
  status: {
    phase: WorkflowPhase;
    startedAt?: string;
    finishedAt?: string;
    message?: string;
    progress?: string;
  };
}

// ============================================================================
// Request/Response Types
// ============================================================================

export interface SubmitWorkflowRequest {
  dag_id: string;
  name: string;
  description?: string;
  namespace?: string;
  nodes?: Partial<DAGNode>[];
  edges?: Partial<DAGEdge>[];
  tags?: string[];
  variables?: Record<string, unknown>;
  service_account?: string;
  ttl_seconds_after_finished?: number;
  parallelism?: number;
  s3_bucket?: string;
  s3_endpoint?: string;
}

export interface RetryWorkflowRequest {
  restart_successful: boolean;
  node_field_selector?: string;
}

export interface StopWorkflowRequest {
  message?: string;
}

export interface LogOptions {
  node_id?: string;
  tail?: number;
  grep?: string;
  container?: string;
  since_time?: string;
}

export interface WorkflowFilters {
  namespace?: string;
  phases?: WorkflowPhase[];
  labels?: string[];
  limit?: number;
  offset?: number;
}

// ============================================================================
// Cluster Info
// ============================================================================

export interface ClusterInfo {
  version: string;
  namespace: string;
  capabilities: {
    workflows: boolean;
    workflow_templates: boolean;
    cron_workflows: boolean;
    cluster_workflow_templates: boolean;
  };
  config: {
    container_runtime_executor: string;
    artifact_repository?: {
      s3?: {
        bucket: string;
        endpoint: string;
      };
    };
  };
}

// ============================================================================
// Constants
// ============================================================================

export const WORKFLOW_PHASE_COLORS: Record<WorkflowPhase, string> = {
  [WorkflowPhase.PENDING]: 'default',
  [WorkflowPhase.RUNNING]: 'processing',
  [WorkflowPhase.SUCCEEDED]: 'success',
  [WorkflowPhase.FAILED]: 'error',
  [WorkflowPhase.ERROR]: 'error',
  [WorkflowPhase.SKIPPED]: 'default',
};

export const WORKFLOW_PHASE_ICONS: Record<WorkflowPhase, string> = {
  [WorkflowPhase.PENDING]: '⏳',
  [WorkflowPhase.RUNNING]: '🔄',
  [WorkflowPhase.SUCCEEDED]: '✅',
  [WorkflowPhase.FAILED]: '❌',
  [WorkflowPhase.ERROR]: '⚠️',
  [WorkflowPhase.SKIPPED]: '⏭️',
};

export const TASK_TYPE_ICONS: Record<TaskType, string> = {
  [TaskType.SQL]: '🗃️',
  [TaskType.PYTHON]: '🐍',
  [TaskType.SHELL]: '💻',
  [TaskType.NOTEBOOK]: '📓',
  [TaskType.ETL]: '🔄',
  [TaskType.TRAINING]: '🧠',
  [TaskType.INFERENCE]: '🔮',
  [TaskType.EVALUATION]: '📊',
  [TaskType.MODEL_REGISTER]: '📦',
  [TaskType.EMAIL]: '📧',
  [TaskType.SENSOR]: '📡',
  [TaskType.HTTP]: '🌐',
  [TaskType.NOTIFICATION]: '🔔',
  [TaskType.CUSTOM]: '⚙️',
};

export const DEFAULT_TASK_IMAGES: Record<TaskType, string> = {
  [TaskType.SQL]: 'postgres:15',
  [TaskType.PYTHON]: 'python:3.11-slim',
  [TaskType.SHELL]: 'bash:5',
  [TaskType.NOTEBOOK]: 'jupyter/scipy-notebook:latest',
  [TaskType.ETL]: 'python:3.11-slim',
  [TaskType.TRAINING]: 'pytorch/pytorch:2.0-cuda11.7-cudnn8-runtime',
  [TaskType.INFERENCE]: 'pytorch/pytorch:2.0-cuda11.7-cudnn8-runtime',
  [TaskType.EVALUATION]: 'python:3.11-slim',
  [TaskType.MODEL_REGISTER]: 'python:3.11-slim',
  [TaskType.EMAIL]: 'curlimages/curl:latest',
  [TaskType.SENSOR]: 'argoproj/argoexec:latest',
  [TaskType.HTTP]: 'curlimages/curl:latest',
  [TaskType.NOTIFICATION]: 'curlimages/curl:latest',
  [TaskType.CUSTOM]: 'alpine:latest',
};

export const RESOURCE_PRESETS = {
  'cpu-small': {
    cpu_request: '100m',
    cpu_limit: '500m',
    memory_request: '128Mi',
    memory_limit: '512Mi',
  },
  'cpu-medium': {
    cpu_request: '500m',
    cpu_limit: '2000m',
    memory_request: '512Mi',
    memory_limit: '2Gi',
  },
  'cpu-large': {
    cpu_request: '2000m',
    cpu_limit: '4000m',
    memory_request: '2Gi',
    memory_limit: '8Gi',
  },
  'gpu-single': {
    cpu_request: '1000m',
    cpu_limit: '4000m',
    memory_request: '4Gi',
    memory_limit: '16Gi',
    gpu_count: 1,
  },
  'gpu-quad': {
    cpu_request: '4000m',
    cpu_limit: '16000m',
    memory_request: '16Gi',
    memory_limit: '64Gi',
    gpu_count: 4,
  },
};
