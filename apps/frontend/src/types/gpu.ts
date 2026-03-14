/**
 * GPU Resource Management Types
 *
 * Types for GPU pool management, VGPU allocation, and scheduling.
 */

// ============================================================================
// Enums
// ============================================================================

export enum GPUType {
  NVIDIA_H100 = 'H100',
  NVIDIA_A100 = 'A100',
  NVIDIA_A30 = 'A30',
  NVIDIA_A10G = 'A10G',
  NVIDIA_V100 = 'V100',
  NVIDIA_T4 = 'T4',
  GENERIC = 'generic',
}

export enum GPUAllocationStrategy {
  INTERLEAVED = 'interleaved',
  EXCLUSIVE = 'exclusive',
  MIG = 'mig',
  MPS = 'mps',
}

export enum SchedulingPolicy {
  BEST_FIT = 'best_fit',
  WORST_FIT = 'worst_fit',
  FIRST_FIT = 'first_fit',
  SPREAD = 'spread',
  PACK = 'pack',
  BIN_PACKING = 'bin_packing',
}

export enum TaskPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export enum UtilizationStatus {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
}

// ============================================================================
// Physical GPU
// ============================================================================

export interface PhysicalGPU {
  gpu_id: string;
  name: string;
  type: GPUType;
  total_memory_mb: number;
  used_memory_mb: number;
  available_memory_mb: number;
  cuda_cores: number;
  utilization_percent: number;
  temperature_celsius: number;
  power_draw_watts: number;
  healthy: boolean;
  utilization_status: UtilizationStatus;
  max_vgpu_instances: number;
  vgpu_instances: number;
  active_vgpus: number;
  available_vgpu_slots: number;
  mig_enabled: boolean;
  driver_version: string;
  cuda_version: string;
}

// ============================================================================
// Virtual GPU
// ============================================================================

export interface VirtualGPU {
  vgpu_id: string;
  parent_gpu_id: string;
  memory_mb: number;
  cpu_cores: number;
  vgpu_index: number;
  allocated_to: string | null;
  allocated_at: string | null;
  allocation_type: GPUAllocationStrategy | null;
  is_available: boolean;
  utilization_percent: number;
  memory_used_mb: number;
  memory_utilization: number;
}

// ============================================================================
// GPU Allocation
// ============================================================================

export interface GPUAllocation {
  allocation_id: string;
  request_id: string;
  resource_name: string;
  gpu_id: string;
  vgpu_ids: string[];
  vgpu_count: number;
  allocated_at: string;
  expires_at: string | null;
  strategy: GPUAllocationStrategy;
  memory_mb: number;
}

// ============================================================================
// GPU Task
// ============================================================================

export interface GPUTask {
  task_id: string;
  resource_name: string;
  vgpu_count: number;
  gpu_type?: GPUType;
  memory_mb?: number;
  strategy: GPUAllocationStrategy;
  priority: TaskPriority;
  estimated_duration_minutes?: number;
  status: 'pending' | 'running' | 'completed';
  submit_time: string;
  scheduled_time: string | null;
  started_time: string | null;
  completed_time: string | null;
  wait_time_seconds: number;
  run_time_seconds: number;
  retry_count: number;
}

export interface GPURequestResult {
  task_id: string;
  scheduled: boolean;
  allocation_id?: string;
  gpu_ids?: string[];
  reason?: string;
  estimated_start_time?: string;
  queue_position?: number;
}

// ============================================================================
// GPU Pool Status
// ============================================================================

export interface GPUPoolStatus {
  cluster_stats: {
    total_gpus: number;
    healthy_gpus: number;
    unhealthy_gpus: number;
    total_memory_mb: number;
    used_memory_mb: number;
    available_memory_mb: number;
    memory_utilization_percent: number;
    total_vgpu_instances: number;
    active_allocations: number;
    gpu_type_counts: Record<string, number>;
  };
  queue_stats: {
    pending_tasks: number;
    running_tasks: number;
    completed_tasks: number;
    avg_wait_time_seconds: number;
    avg_run_time_seconds: number;
    pending_by_priority: Record<string, number>;
    queue_depth: number;
  };
  gpus: PhysicalGPU[];
  allocations: GPUAllocation[];
}

export interface GPUMonitoringSummary {
  timestamp: string;
  total_gpus: number;
  healthy_gpus: number;
  unhealthy_gpus: number;
  avg_utilization_percent: number;
  utilization_status_counts: Record<string, number>;
  total_memory_mb: number;
  used_memory_mb: number;
  memory_utilization_percent: number;
  total_vgpu_instances: number;
  active_allocations: number;
  pending_tasks: number;
  running_tasks: number;
  avg_wait_time_seconds: number;
}

// ============================================================================
// Request Types
// ============================================================================

export interface GPURequestRequest {
  resource_name: string;
  vgpu_count: number;
  gpu_type?: GPUType;
  memory_mb?: number;
  strategy: GPUAllocationStrategy;
  priority: TaskPriority;
  estimated_duration_minutes?: number;
}

export interface VGPUCreateRequest {
  gpu_id: string;
  count: number;
  memory_per_vgpu: number;
  cpu_cores_per_vgpu: number;
}

export interface GPUMetricsUpdate {
  gpu_id: string;
  utilization_percent: number;
  memory_used_mb: number;
  temperature_celsius: number;
  power_draw_watts: number;
}

export interface TaskSubmitRequest {
  task_id?: string;
  resource_name: string;
  vgpu_count: number;
  gpu_type?: GPUType;
  memory_mb?: number;
  strategy: GPUAllocationStrategy;
  priority: TaskPriority;
  estimated_duration_minutes?: number;
  allowed_gpu_ids?: string[];
  forbidden_gpu_ids?: string[];
}

// ============================================================================
// GPU Type Info
// ============================================================================

export interface GPUTypeInfo {
  type: string;
  name: string;
  memory_gb: number;
  cuda_cores: number;
  supports_mig: boolean;
  max_mig_instances: number;
}

// ============================================================================
// GPU Details
// ============================================================================

export interface GPUDetails {
  gpu_id: string;
  name: string;
  type: string;
  total_memory_mb: number;
  used_memory_mb: number;
  available_memory_mb: number;
  cuda_cores: number;
  utilization_percent: number;
  temperature_celsius: number;
  power_draw_watts: number;
  healthy: boolean;
  utilization_status: string;
  driver_version: string;
  cuda_version: string;
  max_vgpu_instances: number;
  mig_enabled: boolean;
  vgpu_instances: VirtualGPU[];
}

// ============================================================================
// Constants
// ============================================================================

export const GPU_TYPE_COLORS: Record<GPUType, string> = {
  [GPUType.NVIDIA_H100]: '#FF6B6B',
  [GPUType.NVIDIA_A100]: '#4ECDC4',
  [GPUType.NVIDIA_A30]: '#45B7D1',
  [GPUType.NVIDIA_A10G]: '#96CEB4',
  [GPUType.NVIDIA_V100]: '#FFEEAD',
  [GPUType.NVIDIA_T4]: '#D4A5A5',
  [GPUType.GENERIC]: '#9B9B9B',
};

export const GPU_TYPE_ICONS: Record<GPUType, string> = {
  [GPUType.NVIDIA_H100]: '🚀',
  [GPUType.NVIDIA_A100]: '⚡',
  [GPUType.NVIDIA_A30]: '💾',
  [GPUType.NVIDIA_A10G]: '🎮',
  [GPUType.NVIDIA_V100]: '🔥',
  [GPUType.NVIDIA_T4]: '📊',
  [GPUType.GENERIC]: '🖥️',
};

export const ALLOCATION_STRATEGY_LABELS: Record<GPUAllocationStrategy, string> = {
  [GPUAllocationStrategy.EXCLUSIVE]: 'Exclusive',
  [GPUAllocationStrategy.INTERLEAVED]: 'Shared (Interleaved)',
  [GPUAllocationStrategy.MIG]: 'MIG (Multi-Instance)',
  [GPUAllocationStrategy.MPS]: 'MPS (Multi-Process)',
};

export const PRIORITY_COLORS: Record<TaskPriority, string> = {
  [TaskPriority.LOW]: 'default',
  [TaskPriority.NORMAL]: 'processing',
  [TaskPriority.HIGH]: 'warning',
  [TaskPriority.URGENT]: 'error',
};

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  [TaskPriority.LOW]: 'Low',
  [TaskPriority.NORMAL]: 'Normal',
  [TaskPriority.HIGH]: 'High',
  [TaskPriority.URGENT]: 'Urgent',
};

export const UTILIZATION_STATUS_COLORS: Record<UtilizationStatus, string> = {
  [UtilizationStatus.LOW]: 'success',
  [UtilizationStatus.MEDIUM]: 'processing',
  [UtilizationStatus.HIGH]: 'error',
};

export const VGPU_MEMORY_PRESETS = [
  { label: '1 GB', value: 1024 },
  { label: '2 GB', value: 2048 },
  { label: '4 GB', value: 4096 },
  { label: '8 GB', value: 8192 },
  { label: '10 GB', value: 10240 },
  { label: '16 GB', value: 16384 },
  { label: '20 GB', value: 20480 },
  { label: '32 GB', value: 32768 },
  { label: '40 GB', value: 40960 },
  { label: '80 GB', value: 81920 },
];

export const VGPU_COUNT_PRESETS = [
  { label: '1 GPU', value: 1 },
  { label: '2 GPUs', value: 2 },
  { label: '4 GPUs', value: 4 },
  { label: '8 GPUs', value: 8 },
  { label: '16 GPUs', value: 16 },
  { label: '32 GPUs', value: 32 },
  { label: '64 GPUs', value: 64 },
];

export const GPU_TYPES_FOR_REQUEST = [
  { value: GPUType.NVIDIA_H100, label: 'H100 (80GB)', memory: 80 * 1024 },
  { value: GPUType.NVIDIA_A100, label: 'A100 (40GB)', memory: 40 * 1024 },
  { value: GPUType.NVIDIA_A30, label: 'A30 (24GB)', memory: 24 * 1024 },
  { value: GPUType.NVIDIA_A10G, label: 'A10G (24GB)', memory: 24 * 1024 },
  { value: GPUType.NVIDIA_V100, label: 'V100 (32GB)', memory: 32 * 1024 },
  { value: GPUType.NVIDIA_T4, label: 'T4 (16GB)', memory: 16 * 1024 },
];

export const MIG_PROFILES = [
  { label: '1g.5gb', value: '1g.5gb', gpus: 1, memory: 5 * 1024 },
  { label: '1g.10gb', value: '1g.10gb', gpus: 1, memory: 10 * 1024 },
  { label: '2g.10gb', value: '2g.10gb', gpus: 2, memory: 10 * 1024 },
  { label: '3g.20gb', value: '3g.20gb', gpus: 3, memory: 20 * 1024 },
  { label: '4g.20gb', value: '4g.20gb', gpus: 4, memory: 20 * 1024 },
  { label: '7g.40gb', value: '7g.40gb', gpus: 7, memory: 40 * 1024 },
];

export const TEMPERATURE_THRESHOLDS = {
  WARNING: 75, // Celsius
  CRITICAL: 85, // Celsius
};

export const UTILIZATION_THRESHOLDS = {
  LOW: 50, // percent
  MEDIUM: 80, // percent
};
