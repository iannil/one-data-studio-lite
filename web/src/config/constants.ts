/**
 * Application Constants
 *
 * Centralized configuration constants for the ONE-DATA-STUDIO-LITE frontend.
 * Environment variables should be defined in .env files.
 */

/**
 * API Configuration
 */
export const API_CONFIG = {
  /** Base URL for the portal API */
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010',

  /** Request timeout in milliseconds */
  TIMEOUT: 30000,

  /** API endpoints for microservices */
  ENDPOINTS: {
    PORTAL: import.meta.env.VITE_PORTAL_URL || 'http://localhost:8010',
    NL2SQL: import.meta.env.VITE_NL2SQL_URL || 'http://localhost:8011',
    AI_CLEANING: import.meta.env.VITE_AI_CLEANING_URL || 'http://localhost:8012',
    METADATA_SYNC: import.meta.env.VITE_METADATA_SYNC_URL || 'http://localhost:8013',
    DATA_API: import.meta.env.VITE_DATA_API_URL || 'http://localhost:8014',
    SENSITIVE_DETECT: import.meta.env.VITE_SENSITIVE_DETECT_URL || 'http://localhost:8015',
    AUDIT_LOG: import.meta.env.VITE_AUDIT_LOG_URL || 'http://localhost:8016',
  },
} as const;

/**
 * SSO Configuration
 */
export const SSO_CONFIG = {
  /** Enterprise WeChat (WeCom) Client ID */
  WEWORK_CLIENT_ID: import.meta.env.VITE_SSO_WEWORK_CLIENT_ID || '',

  /** DingTalk Client ID */
  DINGTALK_CLIENT_ID: import.meta.env.VITE_SSO_DINGTALK_CLIENT_ID || '',

  /** Default OAuth issuer URLs */
  ISSUERS: {
    WEWORK: 'https://work.weixin.qq.com',
    DINGTALK: 'https://api.dingtalk.com',
  },
} as const;

/**
 * Dashboard/Workspace Configuration
 */
export const WORKSPACE_CONFIG = {
  /** Default statistics values (used when API data is unavailable) */
  DEFAULT_STATS: {
    TODAY_VISITS: 12,
    WEEK_COMPLETED: 28,
  },

  /** Demo data for development */
  DEMO_QUICK_ACTIONS: [
    { id: '1', name: '数据源配置', path: '/planning/datasources', color: '#1890ff' },
    { id: '2', name: '数据质量检测', path: '/development/quality', color: '#52c41a' },
    { id: '3', name: 'NL2SQL 查询', path: '/analysis/nl2sql', color: '#722ed1' },
    { id: '4', name: '清洗规则配置', path: '/development/cleaning', color: '#fa8c16' },
  ],

  /** Demo todo items for development */
  DEMO_TODOS: [
    { id: '1', title: '完成用户表数据质量检测', priority: 'high' as const, dueDate: '2026-02-02' },
    { id: '2', title: '审核待发布的数据API', priority: 'medium' as const },
    { id: '3', title: '配置 SeaTunnel 同步任务', priority: 'high' as const },
    { id: '4', title: '查看系统告警信息', priority: 'low' as const },
  ],

  /** Demo recent items for development */
  DEMO_RECENTS: [
    { id: '1', name: 'user_info', type: 'table' as const, visitedAt: '10:30' },
    { id: '2', name: 'sales_dashboard', type: 'dashboard' as const, visitedAt: '10:15' },
    { id: '3', name: 'user_profile_api', type: 'api' as const, visitedAt: '09:45' },
    { id: '4', name: 'daily_sync_pipeline', type: 'pipeline' as const, visitedAt: '09:30' },
  ],

  /** Demo favorite items for development */
  DEMO_FAVORITES: [
    { id: '1', name: 'user_info', type: 'table' as const, visitedAt: '' },
    { id: '2', name: 'orders', type: 'table' as const, visitedAt: '' },
    { id: '3', name: 'sales_dashboard', type: 'dashboard' as const, visitedAt: '' },
    { id: '4', name: 'user_profile_api', type: 'api' as const, visitedAt: '' },
  ],

  /** Data asset overview defaults */
  DATA_ASSET_DEFAULTS: {
    TABLES: 156,
    APIS: 23,
    DASHBOARDS: 8,
    PIPELINES: 12,
  },
} as const;

/**
 * Pagination Configuration
 */
export const PAGINATION_CONFIG = {
  /** Default page size for tables */
  DEFAULT_PAGE_SIZE: 10,

  /** Page size options */
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],

  /** Maximum page size */
  MAX_PAGE_SIZE: 100,
} as const;

/**
 * Authentication Configuration
 */
export const AUTH_CONFIG = {
  /** Enable Cookie-based authentication (httpOnly) */
  USE_COOKIE_AUTH: import.meta.env.VITE_USE_COOKIE_AUTH !== 'false',

  /** Token expiration check threshold (seconds) */
  TOKEN_EXPIRY_THRESHOLD: 30,

  /** Local storage keys */
  STORAGE_KEYS: {
    TOKEN: 'auth_token',
    USER: 'auth_user',
    REFRESH_TOKEN: 'auth_refresh_token',
  },
} as const;

/**
 * Feature Flags
 */
export const FEATURE_FLAGS = {
  /** Enable NL2SQL feature */
  NL2SQL: import.meta.env.VITE_FEATURE_NL2SQL !== 'false',

  /** Enable data API feature */
  DATA_API: import.meta.env.VITE_FEATURE_DATA_API !== 'false',

  /** Enable sensitive data detection */
  SENSITIVE_DATA: import.meta.env.VITE_FEATURE_SENSITIVE_DATA !== 'false',

  /** Enable audit log */
  AUDIT_LOG: import.meta.env.VITE_FEATURE_AUDIT_LOG !== 'false',

  /** Enable pipeline feature */
  PIPELINE: import.meta.env.VITE_FEATURE_PIPELINE !== 'false',
} as const;

/**
 * Environment helpers
 */
export const isDev = import.meta.env.DEV;
export const isProd = import.meta.env.PROD;
export const isTest = import.meta.env.TEST;
