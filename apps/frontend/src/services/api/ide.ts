/**
 * IDE API Service
 */

import { apiClient } from './client';

export interface VSCodeServerConfig {
  version?: string;
  port?: number;
  host?: string;
  without_connection_token?: boolean;
  memory_limit?: string;
  cpu_limit?: string;
  extensions?: string[];
  settings?: Record<string, unknown>;
  enable_password?: boolean;
  password?: string;
  data_dir?: string;
  work_dir?: string;
}

export interface VSCodeInstance {
  id: string;
  notebook_id: number;
  user_id: number;
  status: string;
  url: string;
  port: number;
  workspace_path?: string;
  created_at: string;
  started_at?: string;
  extensions?: string[];
}

export interface TerminalSessionCreate {
  notebook_id: number;
  shell?: string;
  rows?: number;
  cols?: number;
  cwd?: string;
  env_vars?: Record<string, string>;
}

export interface TerminalSession {
  id: string;
  notebook_id: number;
  user_id: number;
  status: string;
  shell: string;
  rows: number;
  cols: number;
  cwd: string;
  created_at: string;
  last_activity: string;
}

export interface TerminalMessage {
  id: string;
  type: string;
  data: string;
  timestamp: string;
}

export const ideApi = {
  // VS Code endpoints
  createVSCodeInstance: (notebookId: number, config?: VSCodeServerConfig) =>
    apiClient.post<VSCodeInstance>('/ide/vscode', {
      notebook_id: notebookId,
      ...config,
    }),

  startVSCodeInstance: (instanceId: string) =>
    apiClient.post<{ success: boolean; message: string }>(`/ide/vscode/${instanceId}/start`),

  stopVSCodeInstance: (instanceId: string) =>
    apiClient.post<{ success: boolean; message: string }>(`/ide/vscode/${instanceId}/stop`),

  restartVSCodeInstance: (instanceId: string) =>
    apiClient.post<{ success: boolean; message: string }>(`/ide/vscode/${instanceId}/restart`),

  deleteVSCodeInstance: (instanceId: string, removeData = false) =>
    apiClient.delete<{ success: boolean; message: string }>(`/ide/vscode/${instanceId}`, {
      params: { remove_data: removeData },
    }),

  listVSCodeInstances: (statusFilter?: string) =>
    apiClient.get<VSCodeInstance[]>('/ide/vscode', {
      params: { status_filter: statusFilter },
    }),

  getVSCodeInstance: (instanceId: string) =>
    apiClient.get<Record<string, unknown>>(`/ide/vscode/${instanceId}`),

  getVSCodeLogs: (instanceId: string, lines = 100) =>
    apiClient.get<{ logs: string[] }>(`/ide/vscode/${instanceId}/logs`, {
      params: { lines },
    }),

  installExtension: (instanceId: string, extensionId: string) =>
    apiClient.post<{ success: boolean; message: string }>(
      `/ide/vscode/${instanceId}/extensions/${extensionId}`,
    ),

  // Terminal endpoints
  createTerminalSession: (data: TerminalSessionCreate) =>
    apiClient.post<TerminalSession>('/ide/terminal', data),

  sendTerminalInput: (sessionId: string, data: { input: string }) =>
    apiClient.post<{ success: boolean; message: string }>(`/ide/terminal/${sessionId}/input`, data),

  resizeTerminal: (sessionId: string, data: { rows: number; cols: number }) =>
    apiClient.post<{ success: boolean; message: string }>(`/ide/terminal/${sessionId}/resize`, data),

  getTerminalOutput: (sessionId: string, since?: string) =>
    apiClient.get<TerminalMessage[]>(`/ide/terminal/${sessionId}/output`, {
      params: { since },
    }),

  terminateTerminalSession: (sessionId: string) =>
    apiClient.post<{ success: boolean; message: string }>(`/ide/terminal/${sessionId}/terminate`),

  deleteTerminalSession: (sessionId: string) =>
    apiClient.delete<{ success: boolean; message: string }>(`/ide/terminal/${sessionId}`),

  listTerminalSessions: (notebookId?: number, statusFilter?: string) =>
    apiClient.get<TerminalSession[]>('/ide/terminal', {
      params: {
        notebook_id: notebookId,
        status_filter: statusFilter,
      },
    }),

  getTerminalSession: (sessionId: string) =>
    apiClient.get<Record<string, unknown>>(`/ide/terminal/${sessionId}`),

  // Health check
  healthCheck: () =>
    apiClient.get<{
      vscode: {
        total_instances: number;
        healthy_instances: number;
        unhealthy_instances: number;
        stale_instances: string[];
      };
      terminal: {
        total_sessions: number;
        active_sessions: number;
        idle_sessions: number;
        output_buffers: number;
      };
    }>('/ide/health'),
};
