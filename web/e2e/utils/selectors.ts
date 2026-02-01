/**
 * Selector definitions for Playwright tests
 *
 * This file centralizes all selectors to make tests more maintainable.
 * When frontend changes, update selectors here rather than in individual tests.
 */

/**
 * Page selectors
 */
export const pageSelectors = {
  // Login page
  loginPage: {
    container: '.login-page, [data-testid="login-page"]',
    title: 'h1, .login-title',
    form: 'form.ant-form, [data-testid="login-form"]',
    usernameInput: '#username, [name="username"]',
    passwordInput: '#password, [name="password"]',
    submitButton: 'button[type="submit"], .login-button',
    errorMessage: '.ant-message-error, .error-message',
  },

  // Dashboard
  dashboard: {
    container: '.dashboard, [data-testid="dashboard"]',
    cockpit: '.dashboard-cockpit, [data-testid="cockpit"]',
    workspace: '.dashboard-workspace, [data-testid="workspace"]',
    statsCard: '.ant-card, .stats-card',
  },

  // Navigation
  nav: {
    sidebar: '.ant-layout-sider',
    menu: '.ant-menu',
    menuItem: '.ant-menu-item',
    submenu: '.ant-menu-submenu',
    submenuTitle: '.ant-menu-submenu-title',
    collapsedButton: '.ant-layout-sider-trigger',
  },

  // Common components
  common: {
    button: '.ant-btn, button',
    primaryButton: '.ant-btn-primary',
    dangerButton: '.ant-btn-dangerous',
    input: '.ant-input, input',
    select: '.ant-select',
    selectDropdown: '.ant-select-dropdown',
    table: '.ant-table',
    tableRow: '.ant-table-row',
    tableCell: '.ant-table-cell',
    pagination: '.ant-pagination',
    modal: '.ant-modal',
    modalTitle: '.ant-modal-title',
    modalContent: '.ant-modal-body',
    modalClose: '.ant-modal-close',
    drawer: '.ant-drawer',
    spin: '.ant-spin',
    message: '.ant-message',
    notification: '.ant-notification',
  },
} as const;

/**
 * Function to get role-based menu item selector
 */
export function getMenuItemSelector(label: string): string {
  return `.ant-menu-item:has-text("${label}")`;
}

/**
 * Function to get submenu selector
 */
export function getSubmenuSelector(label: string): string {
  return `.ant-menu-submenu:has-text("${label}")`;
}

/**
 * Function to get button by text
 */
export function getButtonByText(text: string): string {
  return `.ant-btn:has-text("${text}")`;
}

/**
 * Function to get table cell by row and column index
 */
export function getTableCell(row: number, col: number): string {
  return `.ant-table-tbody .ant-table-row:nth-child(${row}) .ant-table-cell:nth-child(${col})`;
}

/**
 * Attribute selectors for data-testid
 */
export const testId = {
  /**
   * Get selector by data-testid attribute
   */
  get: (id: string): string => `[data-testid="${id}"]`,

  /**
   * Login page
   */
  loginPage: '[data-testid="login-page"]',
  loginForm: '[data-testid="login-form"]',
  usernameInput: '[data-testid="username-input"]',
  passwordInput: '[data-testid="password-input"]',
  loginButton: '[data-testid="login-button"]',
  logoutButton: '[data-testid="logout-button"]',

  /**
   * Dashboard
   */
  dashboard: '[data-testid="dashboard"]',
  cockpit: '[data-testid="cockpit"]',
  workspace: '[data-testid="workspace"]',

  /**
   * User management
   */
  usersPage: '[data-testid="users-page"]',
  usersTable: '[data-testid="users-table"]',
  createUserButton: '[data-testid="create-user-button"]',
  editUserButton: '[data-testid="edit-user-button"]',
  deleteUserButton: '[data-testid="delete-user-button"]',

  /**
   * Audit log
   */
  auditLogPage: '[data-testid="audit-log-page"]',
  auditLogTable: '[data-testid="audit-log-table"]',
  auditLogFilter: '[data-testid="audit-log-filter"]',
  auditLogSearch: '[data-testid="audit-log-search"]',

  /**
   * NL2SQL
   */
  nl2sqlPage: '[data-testid="nl2sql-page"]',
  nl2sqlInput: '[data-testid="nl2sql-input"]',
  nl2sqlSubmit: '[data-testid="nl2sql-submit"]',
  nl2sqlResult: '[data-testid="nl2sql-result"]',
  nl2sqlSqlOutput: '[data-testid="nl2sql-sql"]',

  /**
   * Data API
   */
  dataApiPage: '[data-testid="data-api-page"]',
  apiCatalog: '[data-testid="api-catalog"]',
  apiEndpoint: '[data-testid="api-endpoint"]',

  /**
   * Sensitive data
   */
  sensitiveDataPage: '[data-testid="sensitive-data-page"]',
  sensitiveScan: '[data-testid="sensitive-scan"]',
  sensitiveResult: '[data-testid="sensitive-result"]',
} as const;

/**
 * ARIA selectors for accessibility
 */
export const aria = {
  /**
   * Get selector by ARIA role
   */
  role: (role: string): string => `[role="${role}"]`,

  /**
   * Get selector by ARIA label
   */
  label: (label: string): string => `[aria-label="${label}"]`,

  /**
   * Common ARIA roles
   */
  button: '[role="button"]',
  link: '[role="link"]',
  dialog: '[role="dialog"]',
  menu: '[role="menu"]',
  menuitem: '[role="menuitem"]',
  textbox: '[role="textbox"]',
} as const;

/**
 * Text-based selectors
 */
export const text = {
  /**
   * Get element by exact text
   */
  exact: (str: string): string => `text="${str}"`,

  /**
   * Get element containing text
   */
  contains: (str: string): string => `text="${str}"`,

  /**
   * Get element by regex
   */
  regex: (pattern: string): string => `text=${pattern}`,
} as const;
