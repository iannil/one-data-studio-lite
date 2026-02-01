/**
 * Core type definitions for Playwright E2E tests
 * Aligned with backend test configuration
 */

/**
 * User roles defined in the system
 */
export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  ADMIN = 'admin',
  DATA_SCIENTIST = 'data_scientist',
  ANALYST = 'analyst',
  VIEWER = 'viewer',
  SERVICE_ACCOUNT = 'service_account',
  ENGINEER = 'engineer',
  STEWARD = 'steward',
  // Legacy/alias codes
  SUP = 'super_admin',
  ADM = 'admin',
  SCI = 'data_scientist',
  ANA = 'analyst',
  VW = 'viewer',
  SVC = 'service_account',
}

/**
 * Display names for user roles
 */
export const ROLE_DISPLAY_NAMES: Record<UserRole, string> = {
  [UserRole.SUPER_ADMIN]: '超级管理员',
  [UserRole.ADMIN]: '管理员',
  [UserRole.DATA_SCIENTIST]: '数据科学家',
  [UserRole.ANALYST]: '数据分析师',
  [UserRole.VIEWER]: '查看者',
  [UserRole.SERVICE_ACCOUNT]: '服务账户',
  [UserRole.ENGINEER]: '数据工程师',
  [UserRole.STEWARD]: '数据治理员',
};

/**
 * Role codes used in test naming (TC-ROLE-XX-XX-XX format)
 */
export const ROLE_CODES: Record<UserRole, string> = {
  [UserRole.SUPER_ADMIN]: 'SUP',
  [UserRole.ADMIN]: 'ADM',
  [UserRole.DATA_SCIENTIST]: 'SCI',
  [UserRole.ANALYST]: 'ANA',
  [UserRole.VIEWER]: 'VW',
  [UserRole.SERVICE_ACCOUNT]: 'SVC',
  [UserRole.ENGINEER]: 'ENG',
  [UserRole.STEWARD]: 'STW',
};

/**
 * Lifecycle stages for user account management
 */
export enum LifecycleStage {
  ACCOUNT_CREATION = 'account_creation',
  PERMISSION_CONFIG = 'permission_config',
  DATA_ACCESS = 'data_access',
  FEATURE_USAGE = 'feature_usage',
  MONITORING_AUDIT = 'monitoring_audit',
  MAINTENANCE = 'maintenance',
  ACCOUNT_DISABLE = 'account_disable',
  ACCOUNT_DELETION = 'account_deletion',
  EMERGENCY = 'emergency',
}

/**
 * Stage numbers for test naming (TC-ROLE-NN-XX-XX format)
 */
export const STAGE_NUMBERS: Record<LifecycleStage, string> = {
  [LifecycleStage.ACCOUNT_CREATION]: '01',
  [LifecycleStage.PERMISSION_CONFIG]: '02',
  [LifecycleStage.DATA_ACCESS]: '03',
  [LifecycleStage.FEATURE_USAGE]: '04',
  [LifecycleStage.MONITORING_AUDIT]: '05',
  [LifecycleStage.MAINTENANCE]: '06',
  [LifecycleStage.ACCOUNT_DISABLE]: '07',
  [LifecycleStage.ACCOUNT_DELETION]: '08',
  [LifecycleStage.EMERGENCY]: '09',
};

/**
 * Test priority levels
 */
export enum Priority {
  P0 = 'p0',   // Critical - smoke tests, core functionality
  P1 = 'p1',   // High - important features
  P2 = 'p2',   // Medium - edge cases
  P3 = 'p3',   // Low - nice to have
}

/**
 * Test user credentials
 * Matches backend conftest.py test users
 */
export interface TestUser {
  username: string;
  password: string;
  role: UserRole;
  displayName: string;
  roleCode?: string;
}

/**
 * Default test users
 */
export const TEST_USERS: Record<string, TestUser> = {
  superAdmin: {
    username: 'superadmin',
    password: 'admin123',
    role: UserRole.SUPER_ADMIN,
    displayName: '超级管理员',
    roleCode: 'SUP',
  },
  admin: {
    username: 'admin',
    password: 'admin123',
    role: UserRole.ADMIN,
    displayName: '管理员',
    roleCode: 'ADM',
  },
  dataScientist: {
    username: 'scientist',
    password: 'sci123',
    role: UserRole.DATA_SCIENTIST,
    displayName: '数据科学家',
    roleCode: 'SCI',
  },
  analyst: {
    username: 'analyst',
    password: 'ana123',
    role: UserRole.ANALYST,
    displayName: '数据分析师',
    roleCode: 'ANA',
  },
  viewer: {
    username: 'viewer',
    password: 'view123',
    role: UserRole.VIEWER,
    displayName: '查看者',
    roleCode: 'VW',
  },
  engineer: {
    username: 'engineer',
    password: 'eng123',
    role: UserRole.ENGINEER,
    displayName: '数据工程师',
    roleCode: 'ENG',
  },
  steward: {
    username: 'steward',
    password: 'stw123',
    role: UserRole.STEWARD,
    displayName: '数据治理员',
    roleCode: 'STW',
  },
};

/**
 * Test case metadata
 */
export interface TestCase {
  id: string;           // e.g., TC-SUP-01-01-01
  title: string;
  description: string;
  role: UserRole;
  stage: LifecycleStage;
  priority: Priority;
  tags: string[];
  steps: TestStep[];
}

/**
 * Test step definition
 */
export interface TestStep {
  description: string;
  action: () => Promise<void> | void;
  expected: string;
}

/**
 * API response format
 */
export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T;
  timestamp: number;
}

/**
 * Login response
 */
export interface LoginResponse {
  token: string;
  refreshToken?: string;
  expiresIn: number;
  user: {
    id: string;
    username: string;
    role: string;
    displayName: string;
  };
}

/**
 * Page routes
 */
export const PAGE_ROUTES = {
  LOGIN: '/login',
  DASHBOARD_COCKPIT: '/dashboard/cockpit',
  DASHBOARD_WORKSPACE: '/dashboard/workspace',
  DASHBOARD_NOTIFICATIONS: '/dashboard/notifications',
  DASHBOARD_PROFILE: '/dashboard/profile',

  // Planning
  PLANNING_DATASOURCES: '/planning/datasources',
  PLANNING_METADATA: '/planning/metadata',
  PLANNING_TAGS: '/planning/tags',
  PLANNING_LINEAGE: '/planning/lineage',
  PLANNING_STANDARDS: '/planning/standards',

  // Collection
  COLLECTION_SYNC_JOBS: '/collection/sync-jobs',
  COLLECTION_SCHEDULES: '/collection/schedules',
  COLLECTION_TASK_MONITOR: '/collection/task-monitor',
  COLLECTION_ETL_FLOWS: '/collection/etl-flows',

  // Development
  DEVELOPMENT_CLEANING: '/development/cleaning',
  DEVELOPMENT_FIELD_MAPPING: '/development/field-mapping',
  DEVELOPMENT_OCR: '/development/ocr',
  DEVELOPMENT_FUSION: '/development/fusion',
  DEVELOPMENT_QUALITY_CHECK: '/development/quality-check',
  DEVELOPMENT_TRANSFORM: '/development/transform',

  // Analysis
  ANALYSIS_BI: '/analysis/bi',
  ANALYSIS_CHARTS: '/analysis/charts',
  ANALYSIS_NL2SQL: '/analysis/nl2sql',
  ANALYSIS_PIPELINES: '/analysis/pipelines',
  ANALYSIS_ALERTS: '/analysis/alerts',
  ANALYSIS_ETL_LINK: '/analysis/etl-link',

  // Assets
  ASSETS_CATALOG: '/assets/catalog',
  ASSETS_SEARCH: '/assets/search',
  ASSETS_API_MANAGEMENT: '/assets/api-management',
  ASSETS_METADATA_SYNC: '/assets/metadata-sync',

  // Security
  SECURITY_PERMISSIONS: '/security/permissions',
  SECURITY_SSO: '/security/sso',
  SECURITY_SENSITIVE: '/security/sensitive',
  SECURITY_MASKING: '/security/masking',

  // Operations
  OPERATIONS_AUDIT: '/operations/audit',
  OPERATIONS_USERS: '/operations/users',
  OPERATIONS_API_GATEWAY: '/operations/api-gateway',
  OPERATIONS_MONITORING: '/operations/monitoring',
  OPERATIONS_TENANTS: '/operations/tenants',
} as const;

/**
 * Subsystem status
 */
export interface SubsystemStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  port: number;
  url: string;
}

/**
 * Audit log entry
 */
export interface AuditLog {
  id: string;
  timestamp: number;
  userId: string;
  username: string;
  action: string;
  resource: string;
  result: 'success' | 'failure';
  details: Record<string, unknown>;
}
