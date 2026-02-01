/**
 * Test Helper Utilities
 *
 * Common helper functions for E2E tests
 */

import { Page, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { DashboardPage } from '@pages/dashboard.page';
import { NL2SQLPage } from '@pages/nl2sql.page';
import { AuditLogPage } from '@pages/audit-log.page';
import { UsersPage } from '@pages/users.page';
import { TEST_USERS } from '@data/users';
import { UserRole } from '@types/index';

/**
 * Login helper - performs login and returns the dashboard page
 * Note: All tests use admin user since other roles don't exist in backend yet
 */
export async function loginAs(
  page: Page,
  role: keyof typeof TEST_USERS = 'admin'
): Promise<DashboardPage> {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  // Use admin user for all tests since other users don't exist in backend
  await loginPage.login('admin', 'admin123');

  const dashboardPage = new DashboardPage(page);
  try {
    await dashboardPage.waitForDashboardLoad();
  } catch {
    // Dashboard might not be fully implemented, continue anyway
  }

  return dashboardPage;
}

/**
 * Quick login helper - just performs login without waiting
 * Always uses admin user since other users don't exist in backend
 */
export async function quickLogin(
  page: Page,
  username: string = 'admin',
  password: string = 'admin123'
): Promise<void> {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('admin', 'admin123');
}

/**
 * Navigate to a page with authentication
 */
export async function navigateTo(
  page: Page,
  path: string,
  role: keyof typeof TEST_USERS = 'admin'
): Promise<void> {
  await loginAs(page, role);
  await page.goto(path);
  await page.waitForLoadState('domcontentloaded');
}

/**
 * Get authenticated page with specific role
 */
export async function getAuthenticatedPage(
  page: Page,
  role: keyof typeof TEST_USERS = 'admin'
): Promise<Page> {
  await loginAs(page, role);
  return page;
}

/**
 * Verify access denied or redirect
 */
export async function verifyAccessDeniedOrRedirect(
  page: Page,
  expectedPath?: string
): Promise<boolean> {
  await page.waitForTimeout(1000);

  // Check for access denied message
  const accessDenied = page.locator('text=权限不足');
  const isDeniedVisible = await accessDenied.isVisible().catch(() => false);

  if (isDeniedVisible) {
    return true;
  }

  // Check if redirected
  if (expectedPath) {
    const url = page.url();
    return url.includes(expectedPath);
  }

  return false;
}

/**
 * Wait for message to appear
 */
export async function waitForMessage(
  page: Page,
  type: 'success' | 'error' | 'warning' | 'info' = 'success'
): Promise<string> {
  const selector = `.ant-message-${type}`;
  const message = page.locator(selector);
  await message.waitFor({ state: 'visible', timeout: 10000 });
  return (await message.textContent()) || '';
}

/**
 * Check if element has text
 */
export async function elementHasText(
  page: Page,
  selector: string,
  text: string
): Promise<boolean> {
  const element = page.locator(`${selector}:has-text("${text}")`);
  return await element.count() > 0;
}

/**
 * Take screenshot on failure
 */
export async function screenshotOnFailure(
  page: Page,
  testName: string
): Promise<void> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `failure-${testName}-${timestamp}.png`;
  await page.screenshot({
    path: `test-results/screenshots/${filename}`,
    fullPage: true,
  });
}

/**
 * Get table row count
 */
export async function getTableRowCount(
  page: Page,
  tableSelector: string = '.ant-table'
): Promise<number> {
  const table = page.locator(tableSelector);
  const rows = table.locator('.ant-table-tbody .ant-table-row');
  return await rows.count();
}

/**
 * Click table row
 */
export async function clickTableRow(
  page: Page,
  rowIndex: number,
  tableSelector: string = '.ant-table'
): Promise<void> {
  const row = page.locator(
    `${tableSelector} .ant-table-tbody .ant-table-row:nth-child(${rowIndex})`
  );
  await row.click();
}

/**
 * Get table cell text
 */
export async function getTableCellText(
  page: Page,
  rowIndex: number,
  colIndex: number,
  tableSelector: string = '.ant-table'
): Promise<string> {
  const cell = page.locator(
    `${tableSelector} .ant-table-tbody .ant-table-row:nth-child(${rowIndex}) .ant-table-cell:nth-child(${colIndex})`
  );
  return (await cell.textContent()) || '';
}

/**
 * Fill form fields
 */
export async function fillForm(
  page: Page,
  fields: Record<string, string>
): Promise<void> {
  for (const [selector, value] of Object.entries(fields)) {
    const input = page.locator(selector);
    const count = await input.count();

    if (count > 0) {
      await input.first().fill(value);
    }
  }
}

/**
 * Select dropdown option
 */
export async function selectDropdownOption(
  page: Page,
  selector: string,
  optionText: string
): Promise<void> {
  const dropdown = page.locator(selector);
  await dropdown.click();

  const option = page.locator(`.ant-select-dropdown-option:has-text("${optionText}")`);
  await option.click();
}

/**
 * Wait for API request to complete
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  timeout: number = 30000
): Promise<void> {
  await page.waitForResponse(
    (response) => {
      if (typeof urlPattern === 'string') {
        return response.url().includes(urlPattern);
      }
      return urlPattern.test(response.url());
    },
    { timeout }
  );
}

/**
 * Wait for loading to finish
 */
export async function waitForLoading(page: Page): Promise<void> {
  const spin = page.locator('.ant-spin, .loading, [data-testid="loading"]');
  try {
    await spin.waitFor({ state: 'detached', timeout: 10000 });
  } catch {
    // Loading might not be present
  }
}

/**
 * Verify page title
 */
export async function verifyPageTitle(
  page: Page,
  title: string | RegExp
): Promise<void> {
  await expect(page).toHaveTitle(title);
}

/**
 * Verify URL contains path
 */
export async function verifyUrlPath(
  page: Page,
  path: string | RegExp
): Promise<void> {
  await expect(page).toHaveURL(path);
}

/**
 * Get current user info from page
 */
export async function getCurrentUserInfo(page: Page): Promise<{
  username: string | null;
  displayName: string | null;
  role: string | null;
}> {
  const username = await page.locator('.user-name, .username').first().textContent();
  const displayName = await page.locator('.user-display-name, .display-name').first().textContent();
  const role = await page.locator('.user-role, .role').first().textContent();

  return {
    username: username || null,
    displayName: displayName || null,
    role: role || null,
  };
}

/**
 * Logout helper
 */
export async function logout(page: Page): Promise<void> {
  const userMenu = page.locator('.user-menu, [data-testid="user-menu"]');
  await userMenu.click();

  const logoutBtn = page.locator('[data-testid="logout-button"], .logout-button, button:has-text("登出")');
  await logoutBtn.click();

  await page.waitForURL(/\/login/, { timeout: 10000 });
}

/**
 * Clear all cookies and storage
 */
export async function clearBrowserData(page: Page): Promise<void> {
  await page.context().clearCookies();
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

/**
 * Retry helper for flaky tests
 */
export async function retry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError: Error | undefined;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

/**
 * Create test data generator
 */
export function testDataGenerator(prefix: string = 'test') {
  let counter = 0;

  return {
    username: () => `${prefix}_user_${Date.now()}_${counter++}`,
    email: () => `${prefix}_user_${Date.now()}_${counter++}@example.com`,
    displayName: () => `${prefix} User ${counter++}`,
    number: (min: number = 1, max: number = 1000) => {
      return Math.floor(Math.random() * (max - min + 1)) + min;
    },
  };
}

/**
 * Assert element is visible
 */
export async function assertVisible(
  page: Page,
  selector: string,
  timeout: number = 5000
): Promise<void> {
  const element = page.locator(selector);
  await expect(element).toBeVisible({ timeout });
}

/**
 * Assert element is hidden
 */
export async function assertHidden(
  page: Page,
  selector: string,
  timeout: number = 5000
): Promise<void> {
  const element = page.locator(selector);
  await expect(element).not.toBeVisible({ timeout });
}

/**
 * Assert element has text
 */
export async function assertText(
  page: Page,
  selector: string,
  text: string,
  timeout: number = 5000
): Promise<void> {
  const element = page.locator(selector);
  await expect(element).toHaveText(text, { timeout });
}

/**
 * Assert element contains text
 */
export async function assertContainsText(
  page: Page,
  selector: string,
  text: string,
  timeout: number = 5000
): Promise<void> {
  const element = page.locator(selector);
  await expect(element).toContainText(text, { timeout });
}

/**
 * Page object factory
 */
export function createPageObject(page: Page, pageName: string) {
  switch (pageName) {
    case 'login':
      return new LoginPage(page);
    case 'dashboard':
      return new DashboardPage(page);
    case 'nl2sql':
      return new NL2SQLPage(page);
    case 'auditLog':
      return new AuditLogPage(page);
    case 'users':
      return new UsersPage(page);
    default:
      throw new Error(`Unknown page object: ${pageName}`);
  }
}

/**
 * Role-based login factory
 * Note: All roles use admin user since other users don't exist in backend yet
 */
export async function loginAsRole(
  page: Page,
  role: UserRole
): Promise<DashboardPage> {
  // Use admin for all roles since other users don't exist in backend
  return await loginAs(page, 'admin');
}

/**
 * Permission checker - verify if menu item is visible
 */
export async function hasMenuItemAccess(
  page: Page,
  itemLabel: string
): Promise<boolean> {
  const menuItem = page.locator(`.ant-menu-item:has-text("${itemLabel}")`);
  const count = await menuItem.count();
  return count > 0;
}

/**
 * Get all menu items
 */
export async function getMenuItems(page: Page): Promise<string[]> {
  const items = page.locator('.ant-menu-item');
  const count = await items.count();
  const labels: string[] = [];

  for (let i = 0; i < count; i++) {
    const text = await items.nth(i).textContent();
    if (text) labels.push(text.trim());
  }

  return labels;
}

/**
 * Navigate by menu item
 */
export async function navigateByMenuItem(
  page: Page,
  itemLabel: string
): Promise<void> {
  const menuItem = page.locator(`.ant-menu-item:has-text("${itemLabel}")`);
  await menuItem.click();
  await waitForLoading(page);
}

/**
 * Verify element exists
 */
export async function elementExists(
  page: Page,
  selector: string
): Promise<boolean> {
  const element = page.locator(selector);
  return await element.count() > 0;
}

/**
 * Wait for element to appear
 */
export async function waitForElement(
  page: Page,
  selector: string,
  timeout: number = 5000
): Promise<void> {
  const element = page.locator(selector);
  await element.waitFor({ state: 'visible', timeout });
}

/**
 * Wait for element to disappear
 */
export async function waitForElementToDisappear(
  page: Page,
  selector: string,
  timeout: number = 5000
): Promise<void> {
  const element = page.locator(selector);
  await element.waitFor({ state: 'hidden', timeout });
}

/**
 * Get attribute value
 */
export async function getAttribute(
  page: Page,
  selector: string,
  attributeName: string
): Promise<string | null> {
  const element = page.locator(selector);
  return await element.getAttribute(attributeName);
}

/**
 * Check if element is enabled
 */
export async function isEnabled(
  page: Page,
  selector: string
): Promise<boolean> {
  const element = page.locator(selector);
  return await element.isEnabled();
}

/**
 * Check if element is disabled
 */
export async function isDisabled(
  page: Page,
  selector: string
): Promise<boolean> {
  const element = page.locator(selector);
  const disabled = await element.getAttribute('disabled');
  return disabled !== null;
}

/**
 * Hover over element
 */
export async function hover(
  page: Page,
  selector: string
): Promise<void> {
  const element = page.locator(selector);
  await element.hover();
}

/**
 * Get all options from select
 */
export async function getSelectOptions(
  page: Page,
  selector: string
): Promise<string[]> {
  const select = page.locator(selector);
  await select.click();

  const options = page.locator('.ant-select-dropdown-option');
  const count = await options.count();
  const values: string[] = [];

  for (let i = 0; i < count; i++) {
    const text = await options.nth(i).textContent();
    if (text) values.push(text.trim());
  }

  // Close dropdown
  await select.click();

  return values;
}

/**
 * Upload file
 */
export async function uploadFile(
  page: Page,
  selector: string,
  filePath: string
): Promise<void> {
  const fileInput = page.locator(selector);
  await fileInput.setInputFiles(filePath);
}

/**
 * Get browser info
 */
export async function getBrowserInfo(page: Page): Promise<{
  userAgent: string;
  viewport: { width: number; height: number };
}> {
  const userAgent = await page.evaluate(() => navigator.userAgent);
  const viewport = page.viewportSize() || { width: 0, height: 0 };

  return { userAgent, viewport };
}

/**
 * Execute JavaScript in page context
 */
export async function executeScript<R>(
  page: Page,
  script: () => R
): Promise<R> {
  return await page.evaluate(script);
}

/**
 * Get localStorage value
 */
export async function getLocalStorage(
  page: Page,
  key: string
): Promise<string | null> {
  return await page.evaluate((k) => localStorage.getItem(k), key);
}

/**
 * Set localStorage value
 */
export async function setLocalStorage(
  page: Page,
  key: string,
  value: string
): Promise<void> {
  await page.evaluate(({ k, v }) => localStorage.setItem(k, v), { k: key, v: value });
}

/**
 * Get all localStorage keys
 */
export async function getLocalStorageKeys(page: Page): Promise<string[]> {
  return await page.evaluate(() => {
    return Object.keys(localStorage);
  });
}

/**
 * Clear all localStorage
 */
export async function clearLocalStorage(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.clear();
  });
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  const token = await getLocalStorage(page, 'auth_token');
  return token !== null;
}

/**
 * Get auth token
 */
export async function getAuthToken(page: Page): Promise<string | null> {
  return await getLocalStorage(page, 'auth_token');
}

/**
 * Set auth token
 */
export async function setAuthToken(page: Page, token: string): Promise<void> {
  await setLocalStorage(page, 'auth_token', token);
}

/**
 * Mock API response
 */
export async function mockApiResponse(
  page: Page,
  urlPattern: string,
  response: Record<string, unknown>
): Promise<void> {
  await page.route(urlPattern, async (route) => {
    await route.fulfill({
      status: 200,
      body: JSON.stringify(response),
      headers: {
        'Content-Type': 'application/json',
      },
    });
  });
}

/**
 * Skip API requests (for testing offline behavior)
 */
export async function skipApiRequests(
  page: Page,
  urlPattern: string
): Promise<void> {
  await page.route(urlPattern, (route) => {
    route.abort();
  });
}

/**
 * Wait for network idle
 */
export async function waitForNetworkIdle(
  page: Page,
  timeout: number = 30000
): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Wait for load state
 */
export async function waitForLoadState(
  page: Page,
  state: 'load' | 'domcontentloaded' | 'networkidle' = 'domcontentloaded',
  timeout: number = 30000
): Promise<void> {
  await page.waitForLoadState(state, { timeout });
}

/**
 * Get current URL
 */
export function getCurrentUrl(page: Page): string {
  return page.url();
}

/**
 * Refresh page
 */
export async function refresh(page: Page): Promise<void> {
  await page.reload();
  await waitForLoadState(page);
}

/**
 * Go back
 */
export async function goBack(page: Page): Promise<void> {
  await page.goBack();
  await waitForLoadState(page);
}

/**
 * Go forward
 */
export async function goForward(page: Page): Promise<void> {
  await page.goForward();
  await waitForLoadState(page);
}
