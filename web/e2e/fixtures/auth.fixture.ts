/**
 * Authentication fixtures for E2E tests
 */

import { test as base, Page } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { DashboardPage } from '@pages/dashboard.page';
import { TEST_USERS, UserRole } from '@types/index';
import { ApiClient, createPortalClient } from '@utils/api-client';

/**
 * Extended test interface with auth fixtures
 */
export interface TestFixtures {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
  apiClient: ApiClient;
  authenticatedPage: Page;
}

/**
 * Auth fixture options
 */
export interface AuthFixtureOptions {
  role?: keyof typeof TEST_USERS;
  username?: string;
  password?: string;
}

/**
 * Create authenticated page
 */
async function createAuthenticatedPage(
  page: Page,
  username: string,
  password: string
): Promise<Page> {
  const loginPage = new LoginPage(page);
  await page.goto('/login');
  await loginPage.login(username, password);
  return page;
}

/**
 * Extend base test with auth fixtures
 */
export const test = base.extend<TestFixtures>({
  /**
   * Login page fixture
   */
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await use(loginPage);
  },

  /**
   * Dashboard page fixture (assumes user is already logged in)
   */
  dashboardPage: async ({ page }, use) => {
    const dashboardPage = new DashboardPage(page);
    await use(dashboardPage);
  },

  /**
   * API client fixture
   */
  apiClient: async ({ }, use) => {
    const client = createPortalClient();
    await use(client);
  },

  /**
   * Authenticated page as admin
   */
  authenticatedPage: async ({ page }, use) => {
    const adminUser = TEST_USERS.admin;
    await createAuthenticatedPage(page, adminUser.username, adminUser.password);
    await use(page);
  },
});

/**
 * Create role-based authenticated page fixture
 */
export function createAuthenticatedFixture(role: keyof typeof TEST_USERS) {
  return base.extend<{ authenticatedPage: Page }, {}>({
    authenticatedPage: async ({ page }, use) => {
      const user = TEST_USERS[role];
      await createAuthenticatedPage(page, user.username, user.password);
      await use(page);
    },
  });
}

/**
 * Role-specific fixtures
 */
export const asSuperAdmin = createAuthenticatedFixture('superAdmin');
export const asAdmin = createAuthenticatedFixture('admin');
export const asDataScientist = createAuthenticatedFixture('dataScientist');
export const asAnalyst = createAuthenticatedFixture('analyst');
export const asViewer = createAuthenticatedFixture('viewer');

/**
 * Export base expect
 */
export { expect } from '@playwright/test';
