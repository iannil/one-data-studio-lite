/**
 * Notebook Type Definitions
 */

export interface Notebook {
  id: string;
  name: string;
  user: string;
  state: 'running' | 'stopped' | 'pending' | 'error';
  image: string;
  cpu_limit: number;
  mem_limit: string;
  gpu_limit: number;
  url?: string;
  pod_name?: string;
  created_at?: string;
  last_activity?: string;
}

export interface NotebookImage {
  id: string;
  name: string;
  description: string;
  image: string;
  icon: string;
  packages: string[];
  default: boolean;
  gpu_required: boolean;
  gpu_recommended: boolean;
}

export interface ResourceProfile {
  id: string;
  name: string;
  description: string;
  cpu_limit: number;
  cpu_guarantee: number;
  mem_limit: string;
  mem_guarantee: string;
  gpu_limit: number;
  default: boolean;
}

export interface NotebookCreateRequest {
  image_id?: string;
  profile_id?: string;
  server_name?: string;
}

export interface NotebookResponse {
  id: string;
  name: string;
  user: string;
  state: string;
  image: string;
  cpu_limit: number;
  mem_limit: string;
  gpu_limit: number;
  url?: string;
  created_at?: string;
  last_activity?: string;
}

export interface ProgressResponse {
  progress: number;
  message: string;
  ready: boolean;
}
