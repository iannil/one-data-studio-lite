/**
 * AutoML Type Definitions
 */

export enum ProblemType {
  CLASSIFICATION = "classification",
  REGRESSION = "regression",
  CLUSTERING = "clustering",
  TIMESERIES = "timeseries",
}

export enum SearchAlgorithm {
  RANDOM = "random",
  BAYESIAN = "bayesian",
  GENETIC = "genetic",
  GRID = "grid",
}

export enum ModelType {
  XGBOOST = "xgboost",
  LIGHTGBM = "lightgbm",
  RANDOM_FOREST = "random_forest",
  LINEAR = "linear",
  CATBOOST = "catboost",
  NGBOOST = "ngboost",
}

export enum ExperimentStatus {
  DRAFT = "draft",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export enum TrialStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
}

export enum DeploymentStatus {
  NONE = "none",
  STAGING = "staging",
  PRODUCTION = "production",
}

export interface AutoMLExperiment {
  id: string;
  name: string;
  display_name: string | null;
  description: string | null;
  problem_type: ProblemType;
  target_column: string;
  feature_columns: string[];
  source_type: string;
  source_config: Record<string, unknown>;
  eval_metric: string;
  cv_folds: number;
  test_split: number;
  random_seed: number;
  search_algorithm: SearchAlgorithm;
  max_trials: number;
  max_time_minutes: number;
  model_types: ModelType[];
  enable_auto_feature_engineering: boolean;
  feature_engineering_config: Record<string, unknown> | null;
  enable_early_stopping: boolean;
  early_stopping_patience: number;
  early_stopping_min_delta: number;
  status: ExperimentStatus;
  progress: number;
  best_model_id: string | null;
  best_score: number | null;
  best_trial_number: number | null;
  tags: string[];
  properties: Record<string, unknown>;
  owner_id: string | null;
  project_id: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface AutoMLTrial {
  id: string;
  experiment_id: string;
  trial_number: number;
  model_type: string;
  model_config: Record<string, unknown>;
  hyperparameters: Record<string, unknown>;
  feature_pipeline: Record<string, unknown> | null;
  selected_features: string[];
  status: TrialStatus;
  start_time: string | null;
  end_time: string | null;
  duration_seconds: number | null;
  train_score: number | null;
  val_score: number | null;
  test_score: number | null;
  metrics: Record<string, number>;
  model_path: string | null;
  feature_importance: Record<string, number> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutoMLModel {
  id: string;
  name: string;
  version: number;
  experiment_id: string | null;
  trial_id: string | null;
  model_type: string;
  problem_type: string;
  target_column: string;
  model_path: string;
  model_format: string;
  feature_names: string[];
  feature_importance: Record<string, number> | null;
  metrics: Record<string, number>;
  deployment_status: DeploymentStatus;
  deployment_endpoint: string | null;
  status: string;
  tags: string[];
  properties: Record<string, unknown>;
  owner_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface HyperparameterSpace {
  name: string;
  type: "float" | "int" | "categorical";
  low: number | null;
  high: number | null;
  choices: string[] | null;
  log: boolean;
}

export interface SearchSpaceDefinition {
  [modelType: string]: HyperparameterSpace[];
}

export interface TrialResult {
  trial_number: number;
  model_type: ModelType;
  hyperparameters: Record<string, unknown>;
  train_score: number;
  val_score: number;
  test_score: number | null;
  metrics: Record<string, number>;
  duration_seconds: number;
}

export interface AutoMLResult {
  best_model: {
    model_type: ModelType;
    hyperparameters: Record<string, unknown>;
    score: number;
    metrics: Record<string, number>;
  };
  all_trials: TrialResult[];
  total_duration_seconds: number;
}

export interface ExperimentCreateRequest {
  name: string;
  display_name?: string;
  description?: string;
  problem_type: ProblemType;
  target_column: string;
  feature_columns: string[];
  source_type?: string;
  source_config?: Record<string, unknown>;
  eval_metric?: string;
  search_algorithm?: SearchAlgorithm;
  max_trials?: number;
  max_time_minutes?: number;
  model_types?: ModelType[];
  enable_auto_feature_engineering?: boolean;
  enable_early_stopping?: boolean;
  feature_config?: Record<string, unknown>;
  tags?: string[];
}

export interface TrainingRequest {
  experiment_id: string;
  data_path?: string;
  train_split?: number;
  val_split?: number;
  cv_folds?: number;
}

export interface ExperimentFilters {
  status?: ExperimentStatus;
  problem_type?: ProblemType;
  limit?: number;
  offset?: number;
}

export interface ModelFilters {
  deployment_status?: DeploymentStatus;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface HealthStatus {
  status: string;
  experiments: {
    total: number;
    running: number;
    completed: number;
  };
  trials: {
    total: number;
  };
  models: {
    total: number;
  };
  problem_distribution: Record<string, number>;
}
