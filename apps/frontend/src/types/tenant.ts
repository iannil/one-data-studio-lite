/**
 * Multi-Tenant Types
 *
 * Types for multi-tenant isolation, quota management, and tenant administration.
 */

// ============================================================================
// Enums
// ============================================================================

export enum TenantStatus {
  ACTIVE = 'active',
  SUSPENDED = 'suspended',
  TERMINATED = 'terminated',
  PENDING = 'pending',
}

export enum TenantTier {
  BASIC = 'basic',
  STANDARD = 'standard',
  PREMIUM = 'premium',
  ENTERPRISE = 'enterprise',
}

export enum TenantUserRole {
  OWNER = 'owner',
  ADMIN = 'admin',
  MEMBER = 'member',
  VIEWER = 'viewer',
}

// ============================================================================
// Tenant Models
// ============================================================================

export interface Tenant {
  id: number;
  name: string;
  slug: string;
  description?: string;
  status: TenantStatus;
  tier: TenantTier;
  contact_email: string;
  contact_name?: string;
  contact_phone?: string;
  billing_email?: string;
  billing_address?: string;
  enable_sso: boolean;
  sso_provider?: string;
  network_isolated: boolean;
  vpc_id?: string;
  subnet_id?: string;
  is_trial: boolean;
  trial_ends_at?: string;
  created_at: string;
  updated_at: string;
  suspended_at?: string;
  terminated_at?: string;
  settings?: Record<string, any>;
}

export interface ResourceQuota {
  id: number;
  tenant_id: number;

  // Compute
  max_cpu_cores: number;
  max_memory_gb: number;
  max_gpu_count: number;

  // Storage
  max_storage_gb: number;
  max_object_storage_gb: number;

  // Services
  max_notebooks: number;
  max_training_jobs: number;
  max_inference_services: number;
  max_workflows: number;

  // Data
  max_data_sources: number;
  max_etl_pipelines: number;
  max_data_assets: number;

  // Users
  max_users: number;

  // API
  max_api_requests_per_minute: number;
  max_api_requests_per_day: number;

  // Concurrency
  max_concurrent_jobs: number;
  max_concurrent_notebooks: number;

  // Custom
  custom_limits?: Record<string, number>;

  created_at: string;
  updated_at: string;
}

export interface QuotaUsage {
  id: number;
  tenant_id: number;

  // Compute usage
  cpu_cores_used: number;
  memory_gb_used: number;
  gpu_count_used: number;

  // Storage usage
  storage_gb_used: number;
  object_storage_gb_used: number;

  // Service usage
  notebooks_used: number;
  training_jobs_used: number;
  inference_services_used: number;
  workflows_used: number;

  // Data usage
  data_sources_used: number;
  etl_pipelines_used: number;
  data_assets_used: number;

  // User count
  users_count: number;

  // API usage
  api_requests_today: number;
  api_requests_this_minute: number;
  last_api_request_at?: string;

  recorded_at: string;
  updated_at: string;
}

export interface QuotaValue {
  limit: number;      // -1 means unlimited
  current: number;
  remaining: number;
  percent: number;    // 0-100
}

export interface QuotaSummary {
  tenant_id: number;
  tenant_name: string;
  tier: string;
  status: string;

  cpu_cores: QuotaValue;
  memory_gb: QuotaValue;
  gpu_count: QuotaValue;
  storage_gb: QuotaValue;
  object_storage_gb: QuotaValue;

  notebooks: QuotaValue;
  training_jobs: QuotaValue;
  inference_services: QuotaValue;
  workflows: QuotaValue;

  data_sources: QuotaValue;
  etl_pipelines: QuotaValue;
  data_assets: QuotaValue;

  users: QuotaValue;

  api_requests_per_minute: QuotaValue;
  api_requests_per_day: QuotaValue;

  overall_usage_percent: number;
}

export interface TenantUser {
  user_id: number;
  email: string;
  full_name?: string;
  role: TenantUserRole;
  is_primary: boolean;
  joined_at?: string;
  invited_by?: number;
}

export interface TenantApiKey {
  id: number;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at?: string;
  last_used_at?: string;
  usage_count: number;
  created_at: string;
}

export interface AuditLog {
  id: number;
  action: string;
  resource_type: string;
  resource_id?: string;
  user_id?: number;
  user_email?: string;
  user_name?: string;
  ip_address?: string;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  status: string;
  error_message?: string;
  created_at: string;
}

// ============================================================================
// Request/Response Types
// ============================================================================

export interface CreateTenantRequest {
  name: string;
  slug: string;
  contact_email: string;
  contact_name?: string;
  description?: string;
  tier?: TenantTier;
  trial_days?: number;
  settings?: Record<string, any>;
}

export interface UpdateTenantRequest {
  name?: string;
  description?: string;
  contact_email?: string;
  contact_name?: string;
  contact_phone?: string;
  billing_email?: string;
  billing_address?: string;
  settings?: Record<string, any>;
}

export interface InviteUserRequest {
  email: string;
  role: TenantUserRole;
}

export interface AddUserRequest {
  user_id: number;
  role: TenantUserRole;
  is_primary?: boolean;
}

export interface CreateAPIKeyRequest {
  name: string;
  scopes?: string[];
  expires_in_days?: number;
}

export interface QuotaCheckRequest {
  resource_type: string;
  count: number;
}

export interface QuotaCheckResult {
  allowed: boolean;
  resource_type: string;
  requested: number;
  limit: number;
  current: number;
  remaining: number;
  reason?: string;
}

// ============================================================================
// Constants
// ============================================================================

export const TIER_COLORS: Record<TenantTier, string> = {
  [TenantTier.BASIC]: 'default',
  [TenantTier.STANDARD]: 'blue',
  [TenantTier.PREMIUM]: 'gold',
  [TenantTier.ENTERPRISE]: 'purple',
};

export const TIER_ICONS: Record<TenantTier, string> = {
  [TenantTier.BASIC]: '🥉',
  [TenantTier.STANDARD]: '🥈',
  [TenantTier.PREMIUM]: '🥇',
  [TenantTier.ENTERPRISE]: '💎',
};

export const TIER_LABELS: Record<TenantTier, string> = {
  [TenantTier.BASIC]: 'Basic',
  [TenantTier.STANDARD]: 'Standard',
  [TenantTier.PREMIUM]: 'Premium',
  [TenantTier.ENTERPRISE]: 'Enterprise',
};

export const STATUS_COLORS: Record<TenantStatus, string> = {
  [TenantStatus.ACTIVE]: 'success',
  [TenantStatus.SUSPENDED]: 'warning',
  [TenantStatus.TERMINATED]: 'error',
  [TenantStatus.PENDING]: 'processing',
};

export const STATUS_LABELS: Record<TenantStatus, string> = {
  [TenantStatus.ACTIVE]: 'Active',
  [TenantStatus.SUSPENDED]: 'Suspended',
  [TenantStatus.TERMINATED]: 'Terminated',
  [TenantStatus.PENDING]: 'Pending',
};

export const ROLE_COLORS: Record<TenantUserRole, string> = {
  [TenantUserRole.OWNER]: 'gold',
  [TenantUserRole.ADMIN]: 'blue',
  [TenantUserRole.MEMBER]: 'default',
  [TenantUserRole.VIEWER]: 'default',
};

export const ROLE_LABELS: Record<TenantUserRole, string> = {
  [TenantUserRole.OWNER]: 'Owner',
  [TenantUserRole.ADMIN]: 'Admin',
  [TenantUserRole.MEMBER]: 'Member',
  [TenantUserRole.VIEWER]: 'Viewer',
};

export const TIER_FEATURES: Record<TenantTier, string[]> = {
  [TenantTier.BASIC]: [
    '5 Users',
    '2 Notebooks',
    '5 Training Jobs',
    '1 GPU',
    '32GB Memory',
    '500GB Storage',
  ],
  [TenantTier.STANDARD]: [
    '25 Users',
    '10 Notebooks',
    '20 Training Jobs',
    '4 GPUs',
    '128GB Memory',
    '2TB Storage',
    'Priority Support',
  ],
  [TenantTier.PREMIUM]: [
    '100 Users',
    '50 Notebooks',
    '100 Training Jobs',
    '16 GPUs',
    '512GB Memory',
    '10TB Storage',
    '24/7 Support',
    'SSO Integration',
    'Network Isolation',
  ],
  [TenantTier.ENTERPRISE]: [
    'Unlimited Users',
    'Unlimited Resources',
    'Unlimited GPUs',
    'Dedicated Support',
    'Custom SLA',
    'On-premise Deployment',
    'Advanced Security',
    'Compliance Reports',
    'Account Manager',
  ],
};

export const RESOURCE_TYPE_LABELS: Record<string, string> = {
  cpu_cores: 'CPU Cores',
  memory_gb: 'Memory (GB)',
  gpu_count: 'GPUs',
  storage_gb: 'Storage (GB)',
  object_storage_gb: 'Object Storage (GB)',
  notebooks: 'Notebooks',
  training_jobs: 'Training Jobs',
  inference_services: 'Inference Services',
  workflows: 'Workflows',
  data_sources: 'Data Sources',
  etl_pipelines: 'ETL Pipelines',
  data_assets: 'Data Assets',
  users: 'Users',
};

export const QUOTA_WARNING_THRESHOLD = 80; // percent
export const QUOTA_CRITICAL_THRESHOLD = 95; // percent
