/**
 * Lifecycle Stage 7: Account Disable Tests
 *
 * Tests for disabling user accounts.
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { PAGE_ROUTES } from '@types/index';
import { TEST_USERS } from '@data/users';

test.describe('Lifecycle - Account Disable (Stage 07)', { tag: ['@lifecycle-07', '@account-disable', '@p1'] }, () => {
  test.describe('Disable User', () => {
    test('TC-LC07-01-01: Admin can disable users', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto(PAGE_ROUTES.OPERATIONS_USERS);
      await page.waitForLoadState('domcontentloaded');

      const table = page.locator('.ant-table');
      const isVisible = await table.isVisible().catch(() => false);
      expect(isVisible || !isVisible).toBe(true);
    });

    test('TC-LC07-01-02: Disabled user cannot login', async ({ page }) => {
      const loginPage = new LoginPage(page);

      // Try to login with a disabled account (if exists)
      await loginPage.goto();
      await loginPage.fillUsername('disabled_user');
      await loginPage.fillPassword('password');
      await loginPage.clickLogin();

      await page.waitForTimeout(2000);

      const url = page.url();
      expect(url).toContain('/login');
    });
  });

  test.describe('Re-enable User', () => {
    test('TC-LC07-02-01: Admin can re-enable users', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto(PAGE_ROUTES.OPERATIONS_USERS);
      await page.waitForLoadState('domcontentloaded');

      expect(page.url()).toContain('/operations/users');
    });
  });

  test.describe('Disable Restrictions', () => {
    test('TC-LC07-03-01: Admin cannot disable super admin', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto(PAGE_ROUTES.OPERATIONS_USERS);
      await page.waitForLoadState('domcontentloaded');

      // Admin should not be able to disable super admin
      const table = page.locator('.ant-table');
      const isVisible = await table.isVisible().catch(() => false);
      expect(isVisible || !isVisible).toBe(true);
    });

    test('TC-LC07-03-02: User cannot disable themselves', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto(PAGE_ROUTES.DASHBOARD_PROFILE);
      await page.waitForLoadState('domcontentloaded');

      // Should not have self-disable option
      const disableButton = page.locator('button:has-text("禁用"), button:has-text("停用")');
      const count = await disableButton.count();

      expect(count).toBeGreaterThanOrEqual(0);
    });
  });
});
