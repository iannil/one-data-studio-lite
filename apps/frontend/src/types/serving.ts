/**
 * Model Serving Types
 *
 * Types for model inference service management, A/B testing, and canary deployments.
 */

// ============================================================================
// Enums
// ============================================================================

export enum ServingPlatform {
  KSERVE = 'kserve',
  SELDON = 'seldon',
  TRITON = 'triton',
  CUSTOM = 'custom',
}

export enum ServingStatus {
  PENDING = 'pending',
  DEPLOYING = 'deploying',
  RUNNING = 'running',
  UPDATING = 'updating',
  FAILED = 'failed',
  STOPPED = 'stopped',
  UNKNOWN = 'unknown',
}

export enum PredictorType {
  SKLEARN = 'sklearn',
  XGBOOST = 'xgboost',
  LIGHTGBM = 'lightgbm',
  PYTORCH = 'pytorch',
  TENSORFLOW = 'tensorflow',
  ONNX = 'onnx',
  HUGGINGFACE = 'huggingface',
  CUSTOM = 'custom',
}

export enum DeploymentMode {
  RAW = 'raw',
  AB_TESTING = 'ab_testing',
  CANARY = 'canary',
  SHADOW = 'shadow',
  MIRRORED = 'mirrored',
}

export enum TrafficSplitMethod {
  FIXED = 'fixed',
  EPSILON_GREEDY = 'epsilon_greedy',
  THOMPSON_SAMPLING = 'thompson_sampling',
  UCB1 = 'ucb1',
}

export enum SuccessMetricType {
  ACCURACY = 'accuracy',
  PRECISION = 'precision',
  RECALL = 'recall',
  F1_SCORE = 'f1_score',
  LATENCY = 'latency',
  THROUGHPUT = 'throughput',
  CONVERSION_RATE = 'conversion_rate',
  REVENUE = 'revenue',
  CUSTOM = 'custom',
}

export enum CanaryPhase {
  INITIALIZING = 'initializing',
  TRAFFIC_SHIFT = 'traffic_shift',
  MONITORING = 'monitoring',
  PROMOTED = 'promoted',
  ROLLED_BACK = 'rolled_back',
  FAILED = 'failed',
}

export enum CanaryStrategy {
  LINEAR = 'linear',
  EXPONENTIAL = 'exponential',
  CUSTOM = 'custom',
}

// ============================================================================
// Model Serving Types
// ============================================================================

export interface ResourceRequirements {
  limits?: Record<string, string>;
  requests?: Record<string, string>;
}

export interface PredictorConfig {
  predictor_type: PredictorType;
  model_uri: string;
  runtime_version?: string;
  protocol?: string; // v1 or v2
  storage_uri?: string;
  framework?: string;
  device?: string; // cpu or gpu
  replicas?: number;
  resource_requirements?: ResourceRequirements;
  batch_size?: number;
  max_batch_size?: number;
  timeout?: number;
  custom_predictor_image?: string;
  custom_predictor_args?: string[];
  env?: Record<string, string>;
}

export interface ABTestConfig {
  experiment_id: string;
  model_variants: ModelVariant[];
  duration?: string;
  sample_size?: number;
  success_metric: string;
  success_mode: string;
  min_sample_size: number;
  traffic_split_method: string;
}

export interface ModelVariant {
  name: string;
  model_uri: string;
  model_version?: string;
  traffic_percentage: number;
  predictor_config?: PredictorConfig;
}

export interface CanaryConfig {
  canary_model_uri: string;
  canary_predictor_config: PredictorConfig;
  baseline_model_uri: string;
  baseline_predictor_config: PredictorConfig;
  canary_traffic_percentage: number;
  auto_promote: boolean;
  promotion_threshold: number;
  monitoring_window: string;
  min_requests: number;
  auto_rollback: boolean;
  rollback_threshold: number;
}

export interface InferenceService {
  name: string;
  namespace: string;
  description?: string;
  tags: string[];
  platform: ServingPlatform;
  mode: DeploymentMode;
  predictor_config?: PredictorConfig;
  ab_test_config?: ABTestConfig;
  canary_config?: CanaryConfig;
  endpoint?: string;
  url?: string;
  autoscaling_enabled: boolean;
  min_replicas: number;
  max_replicas: number;
  target_requests_per_second: number;
  enable_logging: boolean;
  log_url?: string;
  status: ServingStatus;
  status_message?: string;
  metadata: Record<string, unknown>;
  traffic_distribution?: Record<string, number>;
  project_id?: number;
  owner_id?: number;
  created_at: string;
  updated_at: string;
}

export interface ServiceMetrics {
  request_count: number;
  request_success_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  throughput_per_second: number;
}

// ============================================================================
// A/B Testing Types
// ============================================================================

export interface VariantMetrics {
  variant_id: string;
  name: string;
  traffic_percentage: number;
  request_count: number;
  success_rate: number;
  avg_latency_ms: number;
  is_enabled: boolean;
  is_winner: boolean;
  custom_metrics: Record<string, number>;
}

export interface ABTestExperiment {
  experiment_id: string;
  name: string;
  description?: string;
  is_active: boolean;
  is_running: boolean;
  has_minimum_samples: boolean;
  success_metric: string;
  split_method: string;
  variants: VariantMetrics[];
  winner_variant_id?: string;
  project_id?: number;
  created_at: string;
  updated_at: string;
}

export interface StatisticalTestResult {
  is_significant: boolean;
  p_value: number;
  confidence_interval: [number, number];
  effect_size: number;
  control_metric: number;
  treatment_metric: number;
  relative_improvement: number;
  should_promote: boolean;
  recommendation: string;
}

export interface CreateABTestRequest {
  name: string;
  description?: string;
  variants: Omit<ModelVariant, 'predictor_config'>[];
  success_metric?: SuccessMetricType;
  split_method?: TrafficSplitMethod;
  duration_hours?: number;
  min_sample_size?: number;
  confidence_level?: number;
  project_id?: number;
  tags?: string[];
}

// ============================================================================
// Canary Deployment Types
// ============================================================================

export interface CanaryStep {
  step_number: number;
  traffic_percentage: number;
  duration_minutes: number;
  min_requests: number;
  max_error_rate?: number;
  max_latency_p95_ms?: number;
  status: 'pending' | 'in_progress' | 'passed' | 'failed';
  started_at?: string;
  completed_at?: string;
  actual_error_rate: number;
  actual_latency_p95_ms: number;
  total_requests: number;
}

export interface CanaryDeployment {
  deployment_id: string;
  name: string;
  service_name: string;
  phase: CanaryPhase;
  current_step: number;
  total_steps: number;
  current_traffic_percentage: number;
  progress_percentage: number;
  is_running: boolean;
  is_complete: boolean;
  status_message?: string;
  baseline_model: string;
  canary_model: string;
  steps: CanaryStep[];
  latest_metrics?: {
    canary_error_rate: number;
    canary_latency_p95_ms: number;
    canary_request_count: number;
  };
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CreateCanaryRequest {
  service_name: string;
  baseline_model_uri: string;
  baseline_version?: string;
  canary_model_uri: string;
  canary_version?: string;
  strategy?: CanaryStrategy;
  steps?: number;
  duration_minutes?: number;
  auto_promote?: boolean;
  auto_rollback?: boolean;
  rollback_threshold?: number;
  max_error_rate?: number;
  max_latency_p95_ms?: number;
}

// ============================================================================
// Form Types
// ============================================================================

export interface CreateServiceFormData {
  name: string;
  namespace: string;
  description?: string;
  tags: string[];
  platform: ServingPlatform;
  mode: DeploymentMode;
  predictor_config?: PredictorConfig;
  autoscaling_enabled: boolean;
  min_replicas: number;
  max_replicas: number;
  target_requests_per_second: number;
  enable_logging: boolean;
}

export interface ServiceFilters {
  status?: ServingStatus;
  platform?: ServingPlatform;
  mode?: DeploymentMode;
  search?: string;
  project_id?: number;
}

// ============================================================================
// Presets & Constants
// ============================================================================

export const PLATFORM_OPTIONS = [
  { label: 'KServe', value: ServingPlatform.KSERVE, description: 'Kubernetes-native inference' },
  { label: 'Seldon Core', value: ServingPlatform.SELDON, description: 'Advanced deployment strategies' },
  { label: 'Triton', value: ServingPlatform.TRITON, description: 'NVIDIA Triton Inference Server' },
  { label: 'Custom', value: ServingPlatform.CUSTOM, description: 'Custom deployment' },
];

export const DEPLOYMENT_MODE_OPTIONS = [
  { label: 'Single Model', value: DeploymentMode.RAW, icon: '⚡', description: 'Deploy a single model' },
  { label: 'A/B Testing', value: DeploymentMode.AB_TESTING, icon: '🧪', description: 'Test multiple models with traffic split' },
  { label: 'Canary', value: DeploymentMode.CANARY, icon: '🐤', description: 'Gradual traffic shift' },
  { label: 'Shadow', value: DeploymentMode.SHADOW, icon: '👻', description: 'Shadow traffic to new model' },
  { label: 'Mirrored', value: DeploymentMode.MIRRORED, icon: '🪞', description: 'Multiple model mirrors' },
];

export const PREDICTOR_TYPE_OPTIONS = [
  { label: 'Scikit-learn', value: PredictorType.SKLEARN },
  { label: 'XGBoost', value: PredictorType.XGBOOST },
  { label: 'LightGBM', value: PredictorType.LIGHTGBM },
  { label: 'PyTorch', value: PredictorType.PYTORCH },
  { label: 'TensorFlow', value: PredictorType.TENSORFLOW },
  { label: 'ONNX', value: PredictorType.ONNX },
  { label: 'HuggingFace', value: PredictorType.HUGGINGFACE },
  { label: 'Custom', value: PredictorType.CUSTOM },
];

export const SUCCESS_METRIC_OPTIONS = [
  { label: 'Accuracy', value: SuccessMetricType.ACCURACY, mode: 'max' },
  { label: 'Precision', value: SuccessMetricType.PRECISION, mode: 'max' },
  { label: 'Recall', value: SuccessMetricType.RECALL, mode: 'max' },
  { label: 'F1 Score', value: SuccessMetricType.F1_SCORE, mode: 'max' },
  { label: 'Latency', value: SuccessMetricType.LATENCY, mode: 'min' },
  { label: 'Throughput', value: SuccessMetricType.THROUGHPUT, mode: 'max' },
  { label: 'Conversion Rate', value: SuccessMetricType.CONVERSION_RATE, mode: 'max' },
  { label: 'Revenue', value: SuccessMetricType.REVENUE, mode: 'max' },
];

export const TRAFFIC_SPLIT_METHOD_OPTIONS = [
  { label: 'Fixed Split', value: TrafficSplitMethod.FIXED, description: 'Fixed percentage distribution' },
  { label: 'Epsilon-Greedy', value: TrafficSplitMethod.EPSILON_GREEDY, description: 'Explore-exploit balance' },
  { label: 'Thompson Sampling', value: TrafficSplitMethod.THOMPSON_SAMPLING, description: 'Bayesian optimization' },
  { label: 'UCB1', value: TrafficSplitMethod.UCB1, description: 'Upper confidence bound' },
];

export const CANARY_STRATEGY_OPTIONS = [
  { label: 'Linear', value: CanaryStrategy.LINEAR, description: 'Equal step increments' },
  { label: 'Exponential', value: CanaryStrategy.EXPONENTIAL, description: 'Accelerated rollout' },
  { label: 'Custom', value: CanaryStrategy.CUSTOM, description: 'Custom schedule' },
];

// Resource presets
export const RESOURCE_PRESETS: Record<string, Partial<PredictorConfig>> = {
  'cpu-small': {
    replicas: 1,
    resource_requirements: {
      requests: { cpu: '500m', memory: '512Mi' },
      limits: { cpu: '1000m', memory: '1Gi' },
    },
  },
  'cpu-medium': {
    replicas: 2,
    resource_requirements: {
      requests: { cpu: '1000m', memory: '1Gi' },
      limits: { cpu: '2000m', memory: '2Gi' },
    },
  },
  'cpu-large': {
    replicas: 3,
    resource_requirements: {
      requests: { cpu: '2000m', memory: '2Gi' },
      limits: { cpu: '4000m', memory: '4Gi' },
    },
  },
  'gpu-single': {
    replicas: 1,
    device: 'gpu',
    resource_requirements: {
      requests: { cpu: '1000m', memory: '2Gi', 'nvidia.com/gpu': '1' },
      limits: { cpu: '2000m', memory: '4Gi', 'nvidia.com/gpu': '1' },
    },
  },
  'gpu-quad': {
    replicas: 1,
    device: 'gpu',
    resource_requirements: {
      requests: { cpu: '4000m', memory: '8Gi', 'nvidia.com/gpu': '4' },
      limits: { cpu: '8000m', memory: '16Gi', 'nvidia.com/gpu': '4' },
    },
  },
};

export const AUTOSCALING_PRESETS = {
  conservative: {
    min_replicas: 1,
    max_replicas: 3,
    target_requests_per_second: 10,
  },
  moderate: {
    min_replicas: 2,
    max_replicas: 5,
    target_requests_per_second: 20,
  },
  aggressive: {
    min_replicas: 2,
    max_replicas: 10,
    target_requests_per_second: 50,
  },
};

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface CreateServiceRequest {
  name: string;
  namespace?: string;
  description?: string;
  tags?: string[];
  platform?: ServingPlatform;
  mode?: DeploymentMode;
  predictor_config?: PredictorConfig;
  ab_test_config?: ABTestConfig;
  canary_config?: CanaryConfig;
  autoscaling_enabled?: boolean;
  min_replicas?: number;
  max_replicas?: number;
  target_requests_per_second?: number;
  enable_logging?: boolean;
  log_url?: string;
  metadata?: Record<string, unknown>;
  project_id?: number;
}

export interface UpdateTrafficRequest {
  traffic_distribution: Record<string, number>;
}

export interface ScaleServiceRequest {
  replicas: number;
}
