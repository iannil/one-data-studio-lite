/**
 * Kubernetes Operator Types
 *
 * Types for Kubernetes Operator integration.
 */

// ============================================================================
// Enums
// ============================================================================

export enum ResourceState {
  PENDING = 'Pending',
  CREATING = 'Creating',
  RUNNING = 'Running',
  UPDATING = 'Updating',
  DELETING = 'Deleting',
  COMPLETED = 'Completed',
  FAILED = 'Failed',
  UNKNOWN = 'Unknown',
}

export enum ConditionType {
  READY = 'Ready',
  RESOURCES_AVAILABLE = 'ResourcesAvailable',
  PROVISIONED = 'Provisioned',
  RUNNING = 'Running',
  FAILED = 'Failed',
  TERMINATING = 'Terminating',
}

export enum OperatorType {
  NOTEBOOK = 'notebook',
  TRAINING_JOB = 'trainingjob',
  INFERENCE_SERVICE = 'inferenceservice',
}

// ============================================================================
// Operator Types
// ============================================================================

export interface Condition {
  type: ConditionType;
  status: string; // 'True', 'False', 'Unknown'
  reason?: string;
  message?: string;
  lastTransitionTime?: string;
  lastUpdateTime?: string;
}

export interface ResourceStatus {
  phase: ResourceState;
  conditions: Condition[];
  observedGeneration: number;
  replicas: number;
  readyReplicas: number;
  availableReplicas: number;
  updatedReplicas: number;
  serviceURL?: string;
  jupyterURL?: string;
  tensorboardURL?: string;
  createdAt?: string;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
  errorReason?: string;
}

export interface NotebookSpec {
  image: string;
  cpu: string;
  memory: string;
  gpu?: number;
  storage?: string;
  ports?: number[];
  env?: Record<string, string>;
  workspace?: string;
  timeout?: number;
  autoStop?: boolean;
}

export interface NotebookResource {
  apiVersion: string;
  kind: 'Notebook';
  metadata: {
    name: string;
    namespace: string;
    uid: string;
    creationTimestamp?: string;
    labels?: Record<string, string>;
    annotations?: Record<string, string>;
  };
  spec: NotebookSpec;
  status: ResourceStatus;
}

export interface TrainingJobSpec {
  backend: string; // pytorch, tensorflow
  strategy: string; // ddp, mirrored, etc.
  entryPoint: string;
  entryPointArgs: string[];
  numNodes: number;
  numProcessesPerNode: number;
  modelUri: string;
  outputUri?: string;
  tensorboard?: boolean;
  dockerImage?: string;
  resources?: {
    cpu?: string;
    memory?: string;
    gpu?: number;
    gpuType?: string;
  };
}

export interface TrainingJobResource {
  apiVersion: string;
  kind: 'TrainingJob';
  metadata: {
    name: string;
    namespace: string;
    uid: string;
    creationTimestamp?: string;
  };
  spec: TrainingJobSpec;
  status: ResourceStatus;
}

export interface InferenceServiceSpec {
  modelUri: string;
  predictorType: string;
  framework?: string;
  replicas: number;
  autoscalingEnabled: boolean;
  minReplicas: number;
  maxReplicas: number;
  resources?: {
    cpu?: string;
    memory?: string;
    gpu?: number;
  };
}

export interface InferenceServiceResource {
  apiVersion: string;
  kind: 'InferenceService';
  metadata: {
    name: string;
    namespace: string;
    uid: string;
    creationTimestamp?: string;
  };
  spec: InferenceServiceSpec;
  status: ResourceStatus;
}

// ============================================================================
// Request/Response Types
// ============================================================================

export interface CreateNotebookRequest {
  name: string;
  image: string;
  cpu?: string;
  memory?: string;
  gpu?: number;
  storage?: string;
  ports?: number[];
  env?: Record<string, string>;
  workspace?: string;
  timeout?: number;
  autoStop?: boolean;
}

export interface CreateTrainingJobRequest {
  name: string;
  backend: string;
  strategy: string;
  entryPoint: string;
  entryPointArgs?: string[];
  numNodes?: number;
  numProcessesPerNode?: number;
  modelUri: string;
  outputUri?: string;
  tensorboard?: boolean;
  dockerImage?: string;
  resources?: {
    cpu?: string;
    memory?: string;
    gpu?: number;
  };
}

export interface CreateInferenceServiceRequest {
  name: string;
  modelUri: string;
  predictorType?: string;
  framework?: string;
  replicas?: number;
  autoscalingEnabled?: boolean;
  minReplicas?: number;
  maxReplicas?: number;
  resources?: {
    cpu?: string;
    memory?: string;
    gpu?: number;
  };
}

export interface ScaleRequest {
  replicas: number;
}

// ============================================================================
// Cluster Info
// ============================================================================

export interface ClusterStatus {
  operators: {
    notebook: { running: boolean; version: string };
    training: { running: boolean; version: string };
    inference: { running: boolean; version: string };
  };
  crds: {
    notebooks: { installed: boolean };
    trainingjobs: { installed: boolean };
    inferenceservices: { installed: boolean };
  };
}

// ============================================================================
// Constants
// ============================================================================

export const RESOURCE_STATE_COLORS: Record<ResourceState, string> = {
  [ResourceState.PENDING]: 'default',
  [ResourceState.CREATING]: 'processing',
  [ResourceState.RUNNING]: 'success',
  [ResourceState.UPDATING]: 'processing',
  [ResourceState.DELETING]: 'warning',
  [ResourceState.COMPLETED]: 'default',
  [ResourceState.FAILED]: 'error',
  [ResourceState.UNKNOWN]: 'default',
};

export const RESOURCE_STATE_ICONS: Record<ResourceState, string> = {
  [ResourceState.PENDING]: '⏳',
  [ResourceState.CREATING]: '🔄',
  [ResourceState.RUNNING]: '▶️',
  [ResourceState.UPDATING]: '🔄',
  [ResourceState.DELETING]: '🗑️',
  [ResourceState.COMPLETED]: '✅',
  [ResourceState.FAILED]: '❌',
  [ResourceState.UNKNOWN]: '❓',
};

export const DEFAULT_NOTEBOOK_IMAGES = [
  { value: 'jupyter/scipy-notebook:latest', label: 'Jupyter SciPy (Full)' },
  { value: 'jupyter/datascience-notebook:latest', label: 'Jupyter Data Science' },
  { value: 'jupyter/tensorflow-notebook:latest', label: 'Jupyter TensorFlow' },
  { value: 'jupyter/pytorch-notebook:latest', label: 'Jupyter PyTorch' },
  { value: 'jupyter/all-spark-notebook:latest', label: 'Jupyter Spark' },
  { value: 'jupyter/base-notebook:latest', label: 'Jupyter Minimal' },
];

export const GPU_PRESETS = [
  { label: 'No GPU', value: 0 },
  { label: '1 GPU', value: 1 },
  { label: '2 GPUs', value: 2 },
  { label: '4 GPUs', value: 4 },
  { label: '8 GPUs', value: 8 },
];

export const STORAGE_PRESETS = [
  { label: '1 GB', value: '1Gi' },
  { label: '5 GB', value: '5Gi' },
  { label: '10 GB', value: '10Gi' },
  { label: '20 GB', value: '20Gi' },
  { label: '50 GB', value: '50Gi' },
  { label: '100 GB', value: '100Gi' },
];

export const CPU_PRESETS = [
  { label: '0.5 CPU', value: '500m' },
  { label: '1 CPU', value: '1000m' },
  { label: '2 CPUs', value: '2000m' },
  { label: '4 CPUs', value: '4000m' },
  { label: '8 CPUs', value: '8000m' },
];

export const MEMORY_PRESETS = [
  { label: '512 MB', value: '512Mi' },
  { label: '1 GB', value: '1Gi' },
  { label: '2 GB', value: '2Gi' },
  { label: '4 GB', value: '4Gi' },
  { label: '8 GB', value: '8Gi' },
  { label: '16 GB', value: '16Gi' },
  { label: '32 GB', value: '32Gi' },
];
