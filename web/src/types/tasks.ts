/**
 * Async Task System Types
 *
 * For tracking long-running operations like report generation, bulk imports, etc.
 */

/** 任务状态 */
export type TaskStatus =
  | 'pending'      // 等待执行
  | 'running'      // 执行中
  | 'completed'    // 已完成
  | 'failed'       // 失败
  | 'cancelled'    // 已取消
  | 'timeout';     // 超时

/** 任务类型 */
export type TaskType =
  | 'report_export'      // 报表导出
  | 'bulk_import'        // 批量导入
  | 'bulk_delete'        // 批量删除
  | 'data_sync'          // 数据同步
  | 'metadata_scan'      // 元数据扫描
  | 'quality_check'      // 质量检查
  | 'pipeline_run'       // 流程运行
  | 'custom';            // 自定义任务

/** 任务优先级 */
export type TaskPriority =
  | 'low'
  | 'normal'
  | 'high'
  | 'urgent';

/** 异步任务 */
export interface AsyncTask {
  id: string;
  type: TaskType;
  status: TaskStatus;
  priority: TaskPriority;
  title: string;
  description?: string;
  progress: number;           // 0-100
  current_step?: string;
  total_steps?: number;
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  result?: TaskResult;
  error?: TaskError;
}

/** 任务结果 */
export interface TaskResult {
  success: boolean;
  data?: unknown;
  file_url?: string;          // 结果文件下载地址 (如导出的报表)
  record_count?: number;      // 处理的记录数
  summary?: string;
}

/** 任务错误 */
export interface TaskError {
  code: string;
  message: string;
  details?: string;
}

/** 创建任务请求 */
export interface CreateTaskRequest {
  type: TaskType;
  title: string;
  description?: string;
  priority?: TaskPriority;
  params?: Record<string, unknown>;
}

/** 任务查询参数 */
export interface TaskQueryParams {
  status?: TaskStatus;
  type?: TaskType;
  created_by?: string;
  page?: number;
  page_size?: number;
}

/** 任务列表响应 */
export interface TaskListResponse {
  tasks: AsyncTask[];
  total: number;
  page: number;
  page_size: number;
}

/** 任务进度更新 */
export interface TaskProgressUpdate {
  task_id: string;
  progress: number;
  current_step?: string;
  total_steps?: number;
}

/** WebSocket 消息类型 */
export type TaskMessageType =
  | 'task.created'
  | 'task.started'
  | 'task.progress'
  | 'task.completed'
  | 'task.failed'
  | 'task.cancelled';

/** WebSocket 任务消息 */
export interface TaskWebSocketMessage {
  type: TaskMessageType;
  task: AsyncTask;
}
