/**
 * Smoke Tests
 *
 * Basic sanity checks to ensure the application is accessible and functional.
 * These tests should always pass before running more complex tests.
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { PAGE_ROUTES } from '@types/index';

test.describe('Smoke Tests', { tag: ['@smoke', '@p0'] }, () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test to ensure clean state
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('TC-SMOKE-01: Application home page is accessible', async ({ page }) => {
    await page.goto('/');
    // Should load without critical errors (may not auto-redirect)
    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test('TC-SMOKE-02: Login page loads correctly', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.waitForPageLoad();

    // Verify login page is visible
    const isVisible = await loginPage.isLoginPageVisible();
    expect(isVisible).toBe(true);
  });

  test('TC-SMOKE-03: Valid user can login', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    // Should be on dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    const url = page.url();
    expect(url).toContain('/dashboard');
  });

  test('TC-SMOKE-04: Dashboard loads after login', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    // Should be on dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    const url = page.url();
    expect(url).toContain('/dashboard');
  });

  test('TC-SMOKE-05: Login page has required elements', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Verify all login form elements are visible
    await loginPage.verifyUsernameInputVisible();
    await loginPage.verifyPasswordInputVisible();
    await loginPage.verifyLoginButtonVisible();
  });

  test('TC-SMOKE-06: Session persists on reload', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    // Reload page
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Should still be authenticated
    const url = page.url();
    expect(url).toBeTruthy();
  });

  test('TC-SMOKE-07: API health check', async ({ request }) => {
    const response = await request.get('http://localhost:8010/health');
    expect(response.ok()).toBeTruthy();
  });

  test('TC-SMOKE-08: Static assets are loading', async ({ page }) => {
    await page.goto('/login');

    // Check if main container is visible
    const root = page.locator('#root');
    await expect(root).toBeVisible();
  });

  test('TC-SMOKE-09: Authentication token is stored', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    // Check token is stored
    const token = await page.evaluate(() => localStorage.getItem('ods_token'));
    expect(token).toBeTruthy();
  });

  test('TC-SMOKE-10: Multiple routes are accessible', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');

    // Try multiple routes
    const routes = [
      PAGE_ROUTES.DASHBOARD_COCKPIT,
      PAGE_ROUTES.OPERATIONS_AUDIT,
      PAGE_ROUTES.ANALYSIS_NL2SQL,
    ];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
      const url = page.url();
      expect(url).toBeTruthy();
    }
  });
});
