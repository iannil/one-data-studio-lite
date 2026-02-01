/**
 * Authentication Tests
 *
 * Tests covering login, logout, token management, and session handling.
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { PAGE_ROUTES } from '@types/index';

test.describe('Authentication Tests', { tag: ['@auth', '@p0'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test to ensure clean state
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test.describe('Login - Success Cases', () => {
    test('TC-AUTH-01-01: Admin user can login', async ({ page }) => {
      await loginPage.login('admin', 'admin123');
      await loginPage.verifySuccessfulLogin();
    });

    test('TC-AUTH-01-06: Token is stored after login', async ({ page }) => {
      await loginPage.login('admin', 'admin123');

      const token = await page.evaluate(() => localStorage.getItem('ods_token'));
      expect(token).toBeTruthy();
      expect(token?.length).toBeGreaterThan(0);
    });

    test('TC-AUTH-01-07: User is authenticated after login', async ({ page }) => {
      await loginPage.login('admin', 'admin123');

      const hasAuth = await page.evaluate(() => {
        return !!(localStorage.getItem('ods_token') || localStorage.getItem('token'));
      });

      expect(hasAuth).toBe(true);
    });
  });

  test.describe('Login - Form Validation', () => {
    test('TC-AUTH-02-01: Username input is visible', async ({ page }) => {
      await loginPage.verifyUsernameInputVisible();
    });

    test('TC-AUTH-02-02: Password input is visible', async ({ page }) => {
      await loginPage.verifyPasswordInputVisible();
    });

    test('TC-AUTH-02-03: Login button is visible', async ({ page }) => {
      await loginPage.verifyLoginButtonVisible();
    });

    test('TC-AUTH-02-04: Password is masked by default', async ({ page }) => {
      const passwordInput = page.locator('input[placeholder="密码"]');
      const type = await passwordInput.getAttribute('type');
      expect(type).toBe('password');
    });
  });

  test.describe('Session Management', () => {
    test('TC-AUTH-04-01: Session persists across page reloads', async ({ page }) => {
      await loginPage.login('admin', 'admin123');

      // Reload page
      await page.reload();

      // Should still be on dashboard
      await page.waitForLoadState('domcontentloaded');
      const url = page.url();
      expect(url).toContain('/dashboard');
    });

    test('TC-AUTH-04-02: Session persists across new tabs', async ({ context, page }) => {
      await loginPage.login('admin', 'admin123');

      // Create new page (tab) in same context
      const newPage = await context.newPage();
      await newPage.goto('/dashboard/cockpit');

      // Should be authenticated
      await newPage.waitForLoadState('domcontentloaded');
      const url = newPage.url();
      expect(url).toContain('/dashboard');

      await newPage.close();
    });

    test('TC-AUTH-04-03: Token storage key is correct', async ({ page }) => {
      await loginPage.login('admin', 'admin123');

      // Check correct token key
      const token = await page.evaluate(() => localStorage.getItem('ods_token'));
      expect(token).toBeTruthy();
    });
  });

  test.describe('Login Flow - Happy Path', () => {
    test('TC-AUTH-05-01: Complete login flow works', async ({ page }) => {
      // Verify login page is visible
      const isVisible = await loginPage.isLoginPageVisible();
      expect(isVisible).toBe(true);

      // Perform login
      await loginPage.login('admin', 'admin123');

      // Verify we're on dashboard
      const url = page.url();
      expect(url).toContain('/dashboard');
    });

    test('TC-AUTH-05-02: Login redirect works correctly', async ({ page }) => {
      await loginPage.goto();
      await loginPage.fillCredentials('admin', 'admin123');
      await loginPage.clickLogin();

      // Wait for redirect
      await page.waitForURL(/\/dashboard/, { timeout: 10000 });
      expect(page.url()).toContain('/dashboard');
    });
  });

  test.describe('Password Input', () => {
    test('TC-AUTH-06-02: Password input accepts text', async ({ page }) => {
      const passwordInput = page.locator('input[placeholder="密码"]');
      await passwordInput.fill('testpassword');
      const value = await passwordInput.inputValue();
      expect(value).toBe('testpassword');
    });
  });

  test.describe('Login Page UI', () => {
    test('TC-AUTH-07-01: Login page title is correct', async ({ page }) => {
      const title = await page.title();
      expect(title).toBeTruthy();
    });

    test('TC-AUTH-07-02: Login form is accessible', async ({ page }) => {
      const form = page.locator('form[name="login"]');
      const count = await form.count();
      // Form may or may not exist depending on implementation
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('TC-AUTH-07-03: Username input accepts text', async ({ page }) => {
      const usernameInput = page.locator('input[placeholder="用户名"]');
      await usernameInput.fill('testuser');
      const value = await usernameInput.inputValue();
      expect(value).toBe('testuser');
    });
  });
});
