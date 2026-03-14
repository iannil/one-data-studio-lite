/**
 * Training Type Definitions
 *
 * Types for distributed training jobs and configuration.
 */

// Training backends
export type TrainingBackend = 'pytorch' | 'tensorflow' | 'jax' | 'huggingface';

// Distributed strategies
export type DistributedStrategy =
  | 'ddp'  // PyTorch DistributedDataParallel
  | 'fsdp'  // PyTorch FullyShardedDataParallel
  | 'deepspeed'  // DeepSpeed
  | 'mirrored'  // TensorFlow MirroredStrategy
  | 'multi_worker_mirrored'  // TensorFlow MultiWorkerMirroredStrategy
  | 'tpu'  // TensorFlow TPUStrategy
  | 'parameter_server'  // ParameterServerStrategy
  | 'single_node'
  | 'multi_node';

// Training job status
export type TrainingStatus =
  | 'pending'
  | 'starting'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

// Resource configuration
export interface ResourceConfig {
  cpu_limit?: number;
  cpu_request?: number;
  memory_limit?: string;  // e.g., "16Gi"
  memory_request?: string;
  gpu_count: number;
  gpu_type?: string;  // e.g., "nvidia.com/gpu", "nvidia.com/a100-gh"
  gpu_memory?: string;
  tpu_count?: number;
  tpu_type?: string;  // e.g., "v3-8", "v4-16"
  node_selector?: Record<string, string>;
  tolerations?: Array<Record<string, any>>;
  shared_memory?: string;
}

// Training job configuration
export interface TrainingConfig {
  // Basic info
  name: string;
  experiment_id?: string;
  description?: string;
  tags: string[];

  // Training framework
  backend: TrainingBackend;
  strategy: DistributedStrategy;

  // Entry point
  entry_point: string;
  entry_point_args: string[];
  working_dir?: string;

  // Hyperparameters
  hyperparameters: Record<string, any>;

  // Data configuration
  data_config: Record<string, any>;

  // Model configuration
  model_config: Record<string, any>;

  // Distributed settings
  num_nodes: number;
  num_processes_per_node: number;
  master_addr: string;
  master_port?: number;

  // Checkpointing
  checkpoint_path?: string;
  resume_from_checkpoint?: string;
  save_frequency: number;
  save_total_limit: number;

  // Logging
  log_level: string;
  log_frequency: number;

  // Training duration
  max_steps?: number;
  max_epochs?: number;
  max_duration?: string;

  // Early stopping
  early_stopping: boolean;
  early_stopping_patience: number;
  early_stopping_metric: string;

  // Resources
  resources: ResourceConfig;

  // Environment
  environment: Record<string, string>;
  pip_packages: string[];

  // Docker
  image?: string;
  image_pull_policy: string;
  namespace: string;

  // Service account
  service_account?: string;

  // Priority
  priority_class_name?: string;

  // TTL
  ttl_seconds_after_finished?: number;
}

// Training job instance
export interface TrainingJob {
  id: number;
  job_id: string;
  name: string;
  description?: string;
  backend: TrainingBackend;
  strategy: DistributedStrategy;
  status: TrainingStatus;
  num_nodes: number;
  num_processes_per_node: number;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  duration?: number;
  exit_code?: number;
  error_message?: string;
  metrics: Record<string, any>;
  pod_names: string[];
  service_name?: string;
  latest_checkpoint?: string;
  owner_id?: number;
  tags: string[];
}

// Training node status
export interface TrainingNode {
  id: number;
  training_job_id: number;
  node_rank: number;
  node_name?: string;
  pod_name?: string;
  status: string;
  hostname?: string;
  ip_address?: string;
  gpu_ids?: number[];
  started_at?: string;
  finished_at?: string;
  log_url?: string;
  metrics?: Record<string, any>;
}

// Training checkpoint
export interface TrainingCheckpoint {
  id: number;
  training_job_id: number;
  checkpoint_path: string;
  step: number;
  epoch?: number;
  metrics?: Record<string, any>;
  file_size?: number;
  is_best: boolean;
  is_latest: boolean;
  created_at: string;
}

// Training metrics
export interface TrainingMetrics {
  loss?: number;
  accuracy?: number;
  learning_rate?: number;
  epoch?: number;
  step?: number;
  gpu_memory?: number;
  gpu_utilization?: number;
  throughput?: number;  // samples/second
  // Custom metrics
  [key: string]: any;
}

// Training logs response
export interface TrainingLogs {
  job_id: string;
  logs: string;
  follow_url?: string;
}

// Backend info
export interface TrainingBackendInfo {
  backend: string;
  name: string;
  strategies: StrategyInfo[];
  features: string[];
  available: boolean;
}

export interface StrategyInfo {
  strategy: string;
  name: string;
  description: string;
  multi_node: boolean;
  requires_master: boolean;
  scaling: string;
}

// Template info
export interface TrainingTemplate {
  id: string;
  name: string;
  framework: TrainingBackend;
  strategy: DistributedStrategy;
  description: string;
  entry_point: string;
  hyperparameters: Record<string, any>;
  requirements: string[];
  tags?: string[];
}

// Validation result
export interface ValidationResult {
  valid: boolean;
  errors?: string[];
  warnings?: string[];
  estimated_cost?: CostEstimate;
}

export interface CostEstimate {
  currency: string;
  estimated_cost: number;
  gpu_hours: number;
}

// Hyperparameter tuning
export interface TuningStrategy {
  type: 'bayesian' | 'random' | 'grid' | 'hyperband';
  name: string;
  description: string;
}

export interface HyperparameterTune {
  id: number;
  tune_id: string;
  name: string;
  description?: string;
  tuning_strategy: TuningStrategy['type'];
  optimization_metric: string;
  optimization_mode: 'min' | 'max';
  search_space: Record<string, any>;
  max_trials: number;
  parallel_trials: number;
  max_duration?: string;
  status: TrainingStatus;
  best_trial_id?: number;
  best_value?: number;
  created_at: string;
  started_at?: string;
  finished_at?: string;
}

export interface HyperparameterTrial {
  id: number;
  tune_id: number;
  trial_number: number;
  hyperparameters: Record<string, any>;
  metrics?: Record<string, any>;
  training_job_id?: number;
  status: TrainingStatus;
  created_at: string;
  started_at?: string;
  finished_at?: string;
}

// Training statistics
export interface TrainingStats {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
}

// Filter options
export interface TrainingJobFilters {
  status?: TrainingStatus;
  backend?: TrainingBackend;
  experiment_id?: string;
  owner_id?: number;
  search?: string;
  tags?: string[];
  date_from?: string;
  date_to?: string;
}

// Sort options
export type TrainingSortField = 'name' | 'created_at' | 'started_at' | 'duration' | 'status';
export type SortOrder = 'asc' | 'desc';

export interface TrainingSortOptions {
  field: TrainingSortField;
  order: SortOrder;
}

// Common presets
export const GPU_PRESETS: Record<string, Partial<ResourceConfig>> = {
  'single-gpu': {
    gpu_count: 1,
    gpu_type: 'nvidia.com/gpu',
  },
  'single-a100': {
    gpu_count: 1,
    gpu_type: 'nvidia.com/a100-80gb',
    gpu_memory: '80Gi',
  },
  'quad-gpu': {
    gpu_count: 4,
    gpu_type: 'nvidia.com/gpu',
  },
  'eight-gpu': {
    gpu_count: 8,
    gpu_type: 'nvidia.com/gpu',
  },
  'ddp-4nodes': {
    gpu_count: 8,
    gpu_type: 'nvidia.com/gpu',
  },
  'tpu-v3-8': {
    tpu_count: 8,
    tpu_type: 'v3-8',
  },
};

export const STRATEGY_PRESETS: Record<string, Pick<TrainingConfig, 'backend' | 'strategy'>> = {
  'pytorch-ddp': {
    backend: 'pytorch',
    strategy: 'ddp',
  },
  'pytorch-fsdp': {
    backend: 'pytorch',
    strategy: 'fsdp',
  },
  'pytorch-deepspeed': {
    backend: 'pytorch',
    strategy: 'deepspeed',
  },
  'tf-mirrored': {
    backend: 'tensorflow',
    strategy: 'mirrored',
  },
  'tf-tpu': {
    backend: 'tensorflow',
    strategy: 'tpu',
  },
};

// Status colors for UI
export const STATUS_COLORS: Record<TrainingStatus, string> = {
  pending: 'default',
  starting: 'processing',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
  paused: 'warning',
};

// Backend icons
export const BACKEND_ICONS: Record<TrainingBackend, string> = {
  pytorch: '🔥',
  tensorflow: '🧠',
  jax: '⚡',
  huggingface: '🤗',
};
