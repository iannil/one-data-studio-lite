/**
 * Page fixtures for E2E tests
 */

import { test as base, Page, BrowserContext } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { DashboardPage } from '@pages/dashboard.page';

/**
 * Extended test with page fixtures
 */
export interface PageFixtures {
  authenticatedPage: Page;
  cleanPage: Page;
}

/**
 * Base test with page fixtures
 */
export const test = base.extend<PageFixtures>({
  /**
   * Authenticated page (logged in as admin by default)
   */
  authenticatedPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await page.goto('/login');
    await loginPage.login('admin', 'admin123');
    await use(page);
  },

  /**
   * Clean page with no localStorage/sessionStorage
   */
  cleanPage: async ({ browser, context }, use) => {
    // Create a new context with no storage
    const cleanContext = await browser.newContext({
      storageState: undefined,
    });
    const cleanPage = await cleanContext.newPage();
    await use(cleanPage);
    await cleanContext.close();
  },
});

/**
 * Setup authenticated page for a specific role
 */
export async function setupAuthenticatedPage(
  page: Page,
  username: string,
  password: string
): Promise<void> {
  const loginPage = new LoginPage(page);
  await page.goto('/login');
  await loginPage.login(username, password);
}

/**
 * Setup authenticated page for a specific user
 */
export async function setupPageForUser(
  page: Page,
  role: 'superAdmin' | 'admin' | 'dataScientist' | 'analyst' | 'viewer'
): Promise<void> {
  const users = {
    superAdmin: { username: 'superadmin', password: 'admin123' },
    admin: { username: 'admin', password: 'admin123' },
    dataScientist: { username: 'scientist', password: 'sci123' },
    analyst: { username: 'analyst', password: 'ana123' },
    viewer: { username: 'viewer', password: 'view123' },
  };

  const user = users[role];
  await setupAuthenticatedPage(page, user.username, user.password);
}

/**
 * Cleanup and reset page state
 */
export async function resetPageState(page: Page): Promise<void> {
  await page.context().clearCookies();
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

/**
 * Create a fresh page with storage state
 */
export async function createPageWithStorage(
  context: BrowserContext,
  storageStatePath?: string
): Promise<Page> {
  if (storageStatePath) {
    const newContext = await context.browser().newContext({
      storageState: storageStatePath,
    });
    return await newContext.newPage();
  }
  return await context.newPage();
}

/**
 * Export base expect
 */
export { expect } from '@playwright/test';
