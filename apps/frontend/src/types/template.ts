/**
 * Template Types
 *
 * Types for workflow template marketplace functionality.
 */

// ============================================================================
// Enums
// ============================================================================

export enum TemplateCategory {
  ETL = 'etl',
  ML_TRAINING = 'ml_training',
  DATA_QUALITY = 'data_quality',
  MONITORING = 'monitoring',
  BATCH_INFERENCE = 'batch_inference',
  DATA_SYNC = 'data_sync',
  REPORTING = 'reporting',
  NOTIFICATION = 'notification',
  BACKUP = 'backup',
  DATA_PIPELINE = 'data_pipeline',
}

export enum TemplateComplexity {
  BEGINNER = 'beginner',
  INTERMEDIATE = 'intermediate',
  ADVANCED = 'advanced',
}

export enum VariableType {
  STRING = 'string',
  NUMBER = 'number',
  BOOLEAN = 'boolean',
  SELECT = 'select',
  MULTILINE = 'multiline',
  CODE = 'code',
  JSON = 'json',
}

export enum TaskType {
  SQL = 'sql',
  PYTHON = 'python',
  SHELL = 'shell',
  NOTEBOOK = 'notebook',
  ETl = 'etl',
  TRAINING = 'training',
  INFERENCE = 'inference',
  EVALUATION = 'evaluation',
  MODEL_REGISTER = 'model_register',
  EMAIL = 'email',
  SENSOR = 'sensor',
  HTTP = 'http',
  CUSTOM = 'custom',
}

// ============================================================================
// Template Types
// ============================================================================

export interface TemplateVariable {
  name: string;
  type: VariableType;
  label: string;
  default?: any;
  required?: boolean;
  options?: string[];
  description?: string;
  placeholder?: string;
  min?: number;
  max?: number;
}

export interface TemplateTask {
  task_id: string;
  task_type: TaskType;
  name: string;
  description?: string;
  depends_on?: string[];
  parameters?: Record<string, unknown>;
  position?: { x: number; y: number };
}

export interface TemplateStats {
  usage_count: number;
  view_count: number;
  download_count: number;
  fork_count: number;
  avg_rating: number;
  rating_count: number;
}

export interface TemplateReview {
  review_id: string;
  template_id: string;
  user_id: number;
  user_name: string;
  rating: number;
  comment?: string;
  created_at: string;
}

export interface TemplateVersion {
  version: string;
  changelog: string;
  created_at: string;
  author: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: TemplateCategory;
  icon?: string;
  tags?: string[];
  tasks?: TemplateTask[];
  variables?: TemplateVariable[];
  thumbnail?: string;
  author?: string;
  created_at?: string;
  updated_at?: string;

  // Market-specific fields
  complexity?: TemplateComplexity;
  featured?: boolean;
  verified?: boolean;
  official?: boolean;
  stats?: TemplateStats;
  versions?: TemplateVersion[];
  current_version?: string;
  reviews?: TemplateReview[];
  screenshots?: string[];
  documentation_url?: string;
  repository_url?: string;
  license?: string;
  requirements?: string[];

  // UI state
  is_builtin?: boolean;
  task_count?: number;
  variable_count?: number;
}

export interface TemplateListItem {
  id: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
  tags?: string[];
  complexity?: string;
  author?: string;
  created_at?: string;
  thumbnail?: string;
  official?: boolean;
  verified?: boolean;
  featured?: boolean;
  task_count?: number;
  variable_count?: number;
  current_version?: string;
  stats?: TemplateStats;
  is_builtin?: boolean;
}

// ============================================================================
// Request/Response Types
// ============================================================================

export interface CreateTemplateRequest {
  id?: string;
  name: string;
  description: string;
  category: TemplateCategory;
  icon?: string;
  tags?: string[];
  tasks?: TemplateTask[];
  variables?: TemplateVariable[];
  thumbnail?: string;
}

export interface UpdateTemplateRequest {
  name?: string;
  description?: string;
  category?: TemplateCategory;
  icon?: string;
  tags?: string[];
  tasks?: TemplateTask[];
  variables?: TemplateVariable[];
  thumbnail?: string;
}

export interface InstantiateTemplateRequest {
  template_id: string;
  variables: Record<string, unknown>;
  dag_name?: string;
}

export interface AddReviewRequest {
  rating: number;
  comment?: string;
}

export interface TemplateFilters {
  category?: TemplateCategory;
  complexity?: TemplateComplexity;
  search?: string;
  tags?: string[];
  sort_by?: 'popular' | 'newest' | 'rating' | 'verified';
  featured_only?: boolean;
  verified_only?: boolean;
}

// ============================================================================
// Category Info
// ============================================================================

export interface CategoryInfo {
  value: TemplateCategory;
  label: string;
  count: number;
  icon: string;
}

// ============================================================================
// Constants
// ============================================================================

export const TEMPLATE_CATEGORIES: CategoryInfo[] = [
  { value: TemplateCategory.ETL, label: 'ETL', count: 0, icon: '🔄' },
  { value: TemplateCategory.ML_TRAINING, label: 'ML Training', count: 0, icon: '🧠' },
  { value: TemplateCategory.DATA_QUALITY, label: 'Data Quality', count: 0, icon: '📊' },
  { value: TemplateCategory.MONITORING, label: 'Monitoring', count: 0, icon: '📈' },
  { value: TemplateCategory.BATCH_INFERENCE, label: 'Batch Inference', count: 0, icon: '🔮' },
  { value: TemplateCategory.DATA_SYNC, label: 'Data Sync', count: 0, icon: '🔄' },
  { value: TemplateCategory.REPORTING, label: 'Reporting', count: 0, icon: '📄' },
  { value: TemplateCategory.NOTIFICATION, label: 'Notification', count: 0, icon: '🔔' },
  { value: TemplateCategory.BACKUP, label: 'Backup', count: 0, icon: '💾' },
  { value: TemplateCategory.DATA_PIPELINE, label: 'Data Pipeline', count: 0, icon: '⚙️' },
];

export const COMPLEXITY_OPTIONS = [
  { label: 'Beginner', value: TemplateComplexity.BEGINNER, color: 'green', icon: '🌱' },
  { label: 'Intermediate', value: TemplateComplexity.INTERMEDIATE, color: 'blue', icon: '📊' },
  { label: 'Advanced', value: TemplateComplexity.ADVANCED, color: 'purple', icon: '🚀' },
];

export const SORT_OPTIONS = [
  { label: 'Most Popular', value: 'popular' },
  { label: 'Newest', value: 'newest' },
  { label: 'Highest Rated', value: 'rating' },
  { label: 'Verified', value: 'verified' },
];

export const TASK_TYPE_ICONS: Record<string, string> = {
  sql: '🗃️',
  python: '🐍',
  shell: '💻',
  notebook: '📓',
  etl: '🔄',
  training: '🧠',
  inference: '🔮',
  evaluation: '📊',
  model_register: '📦',
  email: '📧',
  sensor: '📡',
  http: '🌐',
  custom: '⚙️',
};

export const FEATURED_TEMPLATES = [
  {
    id: 'daily_etl',
    name: 'Daily ETL Pipeline',
    description: 'Extract, transform, and load data between systems with automated quality checks.',
    category: TemplateCategory.ETL,
    icon: '🔄',
    tags: ['etl', 'daily', 'data', 'popular'],
    complexity: TemplateComplexity.BEGINNER,
    usage_count: 1250,
    avg_rating: 4.8,
  },
  {
    id: 'ml_training',
    name: 'ML Training Pipeline',
    description: 'End-to-end machine learning workflow with data prep, training, and model registration.',
    category: TemplateCategory.ML_TRAINING,
    icon: '🧠',
    tags: ['ml', 'training', 'model', 'featured'],
    complexity: TemplateComplexity.INTERMEDIATE,
    usage_count: 980,
    avg_rating: 4.7,
  },
  {
    id: 'data_quality',
    name: 'Data Quality Monitor',
    description: 'Monitor data quality with automated alerts for anomalies and schema drift.',
    category: TemplateCategory.DATA_QUALITY,
    icon: '📊',
    tags: ['quality', 'monitoring', 'alerting'],
    complexity: TemplateComplexity.INTERMEDIATE,
    usage_count: 756,
    avg_rating: 4.6,
  },
  {
    id: 'batch_inference',
    name: 'Batch Inference Pipeline',
    description: 'Run batch predictions on large datasets using registered ML models.',
    category: TemplateCategory.BATCH_INFERENCE,
    icon: '🔮',
    tags: ['inference', 'batch', 'prediction'],
    complexity: TemplateComplexity.BEGINNER,
    usage_count: 634,
    avg_rating: 4.5,
  },
  {
    id: 'data_sync',
    name: 'Multi-Cloud Data Sync',
    description: 'Synchronize data across multiple cloud storage systems with conflict resolution.',
    category: TemplateCategory.DATA_SYNC,
    icon: '🔄',
    tags: ['sync', 'cloud', 'storage'],
    complexity: TemplateComplexity.ADVANCED,
    usage_count: 445,
    avg_rating: 4.4,
  },
  {
    id: 'monitoring',
    name: 'System Monitoring Pipeline',
    description: 'Collect, aggregate, and alert on system metrics and logs.',
    category: TemplateCategory.MONITORING,
    icon: '📈',
    tags: ['monitoring', 'metrics', 'logs'],
    complexity: TemplateComplexity.INTERMEDIATE,
    usage_count: 567,
    avg_rating: 4.5,
  },
];

export const POPULAR_TAGS = [
  'etl',
  'ml',
  'training',
  'data',
  'monitoring',
  'quality',
  'inference',
  'batch',
  'cloud',
  'automation',
  'scheduled',
  'real-time',
  'pipeline',
];
