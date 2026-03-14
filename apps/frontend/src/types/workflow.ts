/**
 * Workflow Type Definitions
 */

export interface DAGNode {
  id: string;
  task_type: string;
  name: string;
  description?: string;
  config?: {
    description?: string;
    retry_count?: number;
    retry_delay_seconds?: number;
    timeout_seconds?: number;
    parameters?: Record<string, any>;
  };
  position: {
    x: number;
    y: number;
  };
}

export interface DAGEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

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

export interface DAGRun {
  id: number;
  dag_id: number;
  run_id: string;
  execution_date: string;
  state: 'queued' | 'running' | 'success' | 'failed' | 'cancelled' | 'paused';
  start_date?: string;
  end_date?: string;
  run_type: string;
}

export interface TaskType {
  type: string;
  name: string;
  category: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tasks: any[];
}
