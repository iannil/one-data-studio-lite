/**
 * Test constants and configuration
 */

import { PAGE_ROUTES } from '@types/index';

/**
 * Timeouts in milliseconds
 */
export const TIMEOUTS = {
  DEFAULT: 10000,
  NAVIGATION: 30000,
  LONG: 60000,
  SHORT: 3000,
  PAGE_LOAD: 15000,
  NETWORK_IDLE: 5000,
  ANIMATION: 500,
} as const;

/**
 * Test selectors (data-testid attributes)
 * These should match the frontend implementation
 */
export const SELECTORS = {
  // Common
  ROOT: '#root',
  MAIN: 'main',
  HEADER: 'header',
  SIDEBAR: '.ant-layout-sider',
  CONTENT: '.ant-layout-content',

  // Auth
  LOGIN_PAGE: '[data-testid="login-page"]',
  LOGIN_FORM: '[data-testid="login-form"]',
  USERNAME_INPUT: '#username',
  PASSWORD_INPUT: '#password',
  LOGIN_BUTTON: '[type="submit"]',
  LOGOUT_BUTTON: '[data-testid="logout-button"]',

  // Navigation
  MENU_ITEM: '.ant-menu-item',
  SUBMENU: '.ant-menu-submenu',

  // Dashboard
  DASHBOARD: '[data-testid="dashboard"]',
  STATS_CARD: '.ant-card',

  // Tables
  TABLE: '.ant-table',
  TABLE_BODY: '.ant-table-tbody',
  TABLE_ROW: '.ant-table-row',
  TABLE_CELL: '.ant-table-cell',
  PAGINATION: '.ant-pagination',

  // Forms
  FORM: '.ant-form',
  FORM_ITEM: '.ant-form-item',
  INPUT: '.ant-input',
  SELECT: '.ant-select',
  BUTTON: '.ant-btn',
  SUBMIT_BUTTON: 'button[type="submit"]',

  // Modals
  MODAL: '.ant-modal',
  MODAL_TITLE: '.ant-modal-title',
  MODAL_CLOSE: '.ant-modal-close',

  // Messages
  MESSAGE: '.ant-message',
  SUCCESS_MESSAGE: '.ant-message-success',
  ERROR_MESSAGE: '.ant-message-error',
  WARNING_MESSAGE: '.ant-message-warning',

  // Loading
  SPIN: '.ant-spin',
  LOADING: '.ant-loading',

  // NL2SQL
  NL2SQL_INPUT: '[data-testid="nl2sql-input"]',
  NL2SQL_SUBMIT: '[data-testid="nl2sql-submit"]',
  NL2SQL_RESULT: '[data-testid="nl2sql-result"]',
  NL2SQL_SQL_OUTPUT: '[data-testid="nl2sql-sql"]',

  // Audit Log
  AUDIT_LOG_TABLE: '[data-testid="audit-log-table"]',
  AUDIT_LOG_FILTER: '[data-testid="audit-log-filter"]',

  // User Management
  USERS_TABLE: '[data-testid="users-table"]',
  USER_CREATE_BUTTON: '[data-testid="user-create-button"]',
  USER_EDIT_BUTTON: '[data-testid="user-edit-button"]',
  USER_DELETE_BUTTON: '[data-testid="user-delete-button"]',

  // Data API
  API_CATALOG: '[data-testid="api-catalog"]',
  API_ENDPOINT: '[data-testid="api-endpoint"]',

  // Sensitive Data
  SENSITIVE_SCAN: '[data-testid="sensitive-scan"]',
  SENSITIVE_RESULT: '[data-testid="sensitive-result"]',
} as const;

/**
 * Error messages
 */
export const ERROR_MESSAGES = {
  LOGIN_FAILED: '用户名或密码错误',
  TOKEN_EXPIRED: 'Token已过期',
  PERMISSION_DENIED: '权限不足',
  NETWORK_ERROR: '网络连接失败',
  VALIDATION_ERROR: '输入验证失败',
  USER_NOT_FOUND: '用户不存在',
  DUPLICATE_USER: '用户已存在',
} as const;

/**
 * Success messages
 */
export const SUCCESS_MESSAGES = {
  LOGIN_SUCCESS: '登录成功',
  LOGOUT_SUCCESS: '登出成功',
  CREATE_SUCCESS: '创建成功',
  UPDATE_SUCCESS: '更新成功',
  DELETE_SUCCESS: '删除成功',
  OPERATION_SUCCESS: '操作成功',
} as const;

/**
 * API endpoints
 */
export const API_ENDPOINTS = {
  // Auth
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  REFRESH: '/auth/refresh',
  VALIDATE: '/auth/validate',
  USER_INFO: '/auth/userinfo',

  // Subsystem status
  SUBSYSTEMS: '/auth/subsystems',

  // NL2SQL
  NL2SQL_QUERY: '/nl2sql/query',
  NL2SQL_EXPLAIN: '/nl2sql/explain',

  // Audit log
  AUDIT_LOGS: '/audit/logs',
  AUDIT_STATS: '/audit/stats',

  // Data API
  DATA_QUERY: '/data/query',
  DATA_SCHEMA: '/data/schema',

  // Sensitive detection
  SENSITIVE_SCAN: '/sensitive/scan',
  SENSITIVE_REPORT: '/sensitive/report',
} as const;

/**
 * Browser viewport sizes
 */
export const VIEWPORTS = {
  DESKTOP: { width: 1920, height: 1080 },
  LAPTOP: { width: 1366, height: 768 },
  TABLET: { width: 768, height: 1024 },
  MOBILE: { width: 375, height: 667 },
} as const;

/**
 * Test data
 */
export const TEST_DATA = {
  VALID_USERNAMES: ['admin', 'superadmin', 'analyst', 'viewer', 'scientist'],
  INVALID_USERNAME: 'nonexistentuser',
  INVALID_PASSWORD: 'wrongpassword',

  NL2SQL_QUERIES: [
    '显示所有用户',
    '查询销售额最高的产品',
    '统计每个部门的人数',
  ],

  SEARCH_KEYWORDS: ['用户', '日志', '配置'],
} as const;

/**
 * Feature flags for enabling/disabling tests
 */
export const FEATURE_FLAGS = {
  NL2SQL: true,
  AUDIT_LOG: true,
  SENSITIVE_DATA: true,
  DATA_API: true,
  USER_MANAGEMENT: true,
  PIPELINE: true,
} as const;

/**
 * Test tags
 */
export const TEST_TAGS = {
  PRIORITY: {
    P0: '@p0',
    P1: '@p1',
    P2: '@p2',
    P3: '@p3',
  },
  ROLE: {
    SUP: '@sup',
    ADM: '@adm',
    SCI: '@sci',
    ANA: '@ana',
    VW: '@vw',
    SVC: '@svc',
    COM: '@com',
  },
  TYPE: {
    SMOKE: '@smoke',
    REGRESSION: '@regression',
    INTEGRATION: '@integration',
    AUTH: '@auth',
    API: '@api',
    UI: '@ui',
  },
  FEATURE: {
    NL2SQL: '@nl2sql',
    AUDIT: '@audit',
    SECURITY: '@security',
    DATA: '@data',
  },
} as const;
