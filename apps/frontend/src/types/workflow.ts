/**
 * Workflow Type Definitions
 */

// Node position
export interface Position {
  x: number;
  y: number;
}

// DAG Node configuration
export interface NodeConfig {
  description?: string;
  retry_count?: number;
  retry_delay_seconds?: number;
  timeout_seconds?: number;
  parameters?: Record<string, any>;
  depends_on?: string[];
  // Task-type specific configs
  sql?: string;
  conn_id?: string;
  pipeline_id?: string;
  experiment_id?: string;
  command?: string;
  code?: string;
  image?: string;
  resources?: NodeResources;
}

// Node resource requirements
export interface NodeResources {
  cpu?: string;
  memory?: string;
  gpu?: number;
  gpu_type?: string;
}

// DAG Node
export interface DAGNode {
  id: string;
  task_type: TaskTypeName;
  name: string;
  description?: string;
  config?: NodeConfig;
  position: Position;
  status?: 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'upstream_failed';
}

// Task type names
export type TaskTypeName =
  | 'sql'
  | 'python'
  | 'shell'
  | 'etl'
  | 'training'
  | 'inference'
  | 'evaluation'
  | 'model_register'
  | 'wait'
  | 'sensor'
  | 'email'
  | 'webhook'
  | 'slack'
  | 'export'
  | 'import'
  | 'notebook';

// DAG Edge
export interface DAGEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

// DAG
export interface DAG {
  id: number;
  dag_id: string;
  name: string;
  description?: string;
  schedule_interval?: string;
  is_active: boolean;
  is_paused: boolean;
  tags: string[];
  owner_id?: number;
  created_at: string;
  updated_at: string;
}

// DAG Run
export interface DAGRun {
  id: number;
  dag_id: number;
  run_id: string;
  execution_date: string;
  state: 'queued' | 'running' | 'success' | 'failed' | 'cancelled' | 'paused';
  start_date?: string;
  end_date?: string;
  run_type: string;
  duration?: number;
}

// Task Instance
export interface TaskInstance {
  id: number;
  task_id: string;
  node_id: number;
  state: 'pending' | 'queued' | 'running' | 'success' | 'failed' | 'skipped' | 'upstream_failed' | 'retried';
  start_date?: string;
  end_date?: string;
  duration?: number;
  try_number: number;
  max_tries: number;
  error?: string;
  log_url?: string;
}

// Task Type
export interface TaskType {
  type: TaskTypeName;
  name: string;
  category: TaskCategory;
  description?: string;
  icon?: string;
  color?: string;
}

// Task Categories
export type TaskCategory =
  | 'Data'
  | 'Code'
  | 'Machine Learning'
  | 'Control Flow'
  | 'Notification'
  | 'Data Transfer'
  | 'Notebook'
  | 'Integration';

// Task Type Category mapping
export const TASK_TYPE_CATEGORIES: Record<TaskCategory, TaskTypeName[]> = {
  Data: ['sql', 'etl'],
  Code: ['python', 'shell'],
  'Machine Learning': ['training', 'inference', 'evaluation', 'model_register'],
  'Control Flow': ['wait', 'sensor'],
  Notification: ['email', 'webhook', 'slack'],
  'Data Transfer': ['export', 'import'],
  Notebook: ['notebook'],
  Integration: [],
};

// Workflow Template
export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
  tags?: string[];
  tasks: TemplateTask[];
  variables?: TemplateVariable[];
  thumbnail?: string;
}

// Template Task
export interface TemplateTask {
  task_id: string;
  task_type: TaskTypeName;
  name: string;
  description?: string;
  depends_on?: string[];
  parameters?: Record<string, any>;
  position?: Position;
}

// Template Variable
export interface TemplateVariable {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'multiline';
  label: string;
  default?: any;
  required?: boolean;
  options?: string[];
  description?: string;
}

// Workflow Export Format
export interface WorkflowExport {
  version: string;
  exported_at: string;
  dag: {
    dag_id: string;
    name: string;
    description?: string;
    schedule_interval?: string;
    tags: string[];
    tasks: TemplateTask[];
    edges?: DAGEdge[];
  };
}

// Canvas State
export interface CanvasState {
  scale: number;
  position: Position;
  minScale: number;
  maxScale: number;
}

// Selection State
export interface SelectionState {
  nodes: string[];
  edges: string[];
}

// Validation Error
export interface ValidationError {
  type: 'node' | 'edge' | 'dag';
  id?: string;
  message: string;
  severity: 'error' | 'warning';
}

// ETL Pipeline Reference
export interface ETLPipelineRef {
  id: string;
  name: string;
  description?: string;
  source_type: string;
  target_type: string;
  step_count: number;
}

// Experiment Reference
export interface ExperimentRef {
  id: string;
  name: string;
  description?: string;
  project_id?: string;
}

// Model Reference
export interface ModelRef {
  id: string;
  name: string;
  version: string;
  stage?: 'development' | 'staging' | 'production' | 'archived';
}

// Scheduling Options
export interface ScheduleOptions {
  cron_expression?: string;
  start_date?: string;
  end_date?: string;
  catchup?: boolean;
  max_active_runs?: number;
  concurrency?: number;
}

// Notification Config
export interface NotificationConfig {
  on_success?: boolean;
  on_failure?: boolean;
  on_retry?: boolean;
  channels: {
    email?: {
      to: string[];
      subject?: string;
    };
    slack?: {
      webhook: string;
      channel?: string;
    };
    webhook?: {
      url: string;
      method?: 'POST' | 'PUT' | 'PATCH';
      headers?: Record<string, string>;
    };
  };
}

// Workflow Execution History
export interface ExecutionHistory {
  run_id: string;
  execution_date: string;
  state: string;
  duration?: number;
  triggered_by?: string;
  tasks: {
    total: number;
    success: number;
    failed: number;
    running: number;
    pending: number;
  };
}

// Node execution result
export interface NodeExecutionResult {
  node_id: string;
  state: string;
  start_time: string;
  end_time?: string;
  duration?: number;
  output?: any;
  error?: string;
  logs?: string[];
}

// Drag and Drop Types
export interface DragItem {
  type: string;
  taskType: TaskType;
  position?: Position;
}

// View Mode
export type ViewMode = 'edit' | 'view' | 'monitor';
