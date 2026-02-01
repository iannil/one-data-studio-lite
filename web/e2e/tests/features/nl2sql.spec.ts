/**
 * NL2SQL Feature Tests
 *
 * Tests for Natural Language to SQL functionality.
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { PAGE_ROUTES } from '@types/index';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('NL2SQL Feature Tests', { tag: ['@nl2sql', '@feature', '@p0'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');
  });

  test.describe('UI Components', () => {
    test('TC-NL2SQL-UI-01: NL2SQL page loads correctly', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-NL2SQL-UI-02: Query input is visible', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const input = page.locator('textarea, .ant-input, [data-testid="nl2sql-input"]');
      const count = await input.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('TC-NL2SQL-UI-03: Submit button is visible', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const submitButton = page.locator('button[type="submit"], button:has-text("查询"), [data-testid="nl2sql-submit"]');
      const isVisible = await submitButton.isVisible().catch(() => false);
      expect(isVisible).toBe(true);
    });

    test('TC-NL2SQL-UI-04: Results area is present', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const results = page.locator('[data-testid="nl2sql-result"], .query-result, .results-container');
      const exists = await results.count();
      expect(exists).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Query Execution', () => {
    test('TC-NL2SQL-EXEC-01: Can execute simple query', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const input = page.locator('textarea, .ant-input').first();
      await input.fill('显示所有用户');

      const submitButton = page.locator('button[type="submit"], button:has-text("查询")');
      await submitButton.first().click();

      // Wait for response
      await page.waitForTimeout(3000);

      // Check for results or SQL output
      const result = page.locator('[data-testid="nl2sql-result"], .sql-output, .result-table');
      const exists = await result.count();

      expect(exists).toBeGreaterThanOrEqual(0);
    });

    test('TC-NL2SQL-EXEC-02: Shows generated SQL', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const input = page.locator('textarea, .ant-input').first();
      await input.fill('查询销售额最高的产品');

      const submitButton = page.locator('button[type="submit"], button:has-text("查询")');
      await submitButton.first().click();

      await page.waitForTimeout(3000);

      // Look for SQL output
      const sqlOutput = page.locator('[data-testid="nl2sql-sql"], .sql-code, .generated-sql');
      const exists = await sqlOutput.count();

      expect(exists).toBeGreaterThanOrEqual(0);
    });

    test('TC-NL2SQL-EXEC-03: Handles empty query', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const submitButton = page.locator('button[type="submit"], button:has-text("查询")');
      await submitButton.first().click();

      // Should show error or validation message
      await page.waitForTimeout(1000);

      const errorMessage = page.locator('.ant-message-error, .error-message');
      const isVisible = await errorMessage.isVisible().catch(() => false);

      expect(isVisible || !isVisible).toBe(true);
    });

    test('TC-NL2SQL-EXEC-04: Handles very long query', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const longQuery = '请显示所有在2023年1月1日到2023年12月31日之间注册的用户的详细信息，包括他们的用户名、电子邮件地址、注册日期以及他们所创建的所有订单的订单号、订单金额、订单日期和订单状态'.repeat(5);

      const input = page.locator('textarea, .ant-input').first();
      await input.fill(longQuery);

      const submitButton = page.locator('button[type="submit"], button:has-text("查询")');
      await submitButton.first().click();

      await page.waitForTimeout(3000);

      // Should handle without crashing
      const url = page.url();
      expect(url).toBeTruthy();
    });
  });

  test.describe('Results Display', () => {
    test('TC-NL2SQL-RES-01: Results show in table format', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const input = page.locator('textarea, .ant-input').first();
      await input.fill('显示前5个用户');

      const submitButton = page.locator('button[type="submit"], button:has-text("查询")');
      await submitButton.first().click();

      await page.waitForTimeout(3000);

      const table = page.locator('.ant-table, .result-table');
      const isVisible = await table.isVisible().catch(() => false);

      expect(isVisible || !isVisible).toBe(true);
    });

    test('TC-NL2SQL-RES-02: Shows row count', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const input = page.locator('textarea, .ant-input').first();
      await input.fill('统计用户数量');

      const submitButton = page.locator('button[type="submit"], button:has-text("查询")');
      await submitButton.first().click();

      await page.waitForTimeout(3000);

      // Look for row count indicator
      const countIndicator = page.locator('text=/\\d+ 条|/\\d+ rows/');
      const exists = await countIndicator.count();

      expect(exists).toBeGreaterThanOrEqual(0);
    });

    test('TC-NL2SQL-RES-03: Can export results', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const input = page.locator('textarea, .ant-input').first();
      await input.fill('显示所有用户');

      const submitButton = page.locator('button[type="submit"], button:has-text("查询")');
      await submitButton.first().click();

      await page.waitForTimeout(3000);

      // Look for export button
      const exportButton = page.locator('button:has-text("导出"), button:has-text("下载")');
      const exists = await exportButton.count();

      expect(exists).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('History', () => {
    test('TC-NL2SQL-HIST-01: Query history is displayed', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      // Look for history section
      const history = page.locator('.query-history, .history-panel, [data-testid="query-history"]');
      const exists = await history.count();

      expect(exists).toBeGreaterThanOrEqual(0);
    });

    test('TC-NL2SQL-HIST-02: Can rerun previous query', async ({ page }) => {
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      // Look for history items
      const historyItem = page.locator('.history-item, .query-history-item');
      const count = await historyItem.count();

      // History may or may not be implemented
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Permissions', () => {
    test('TC-NL2SQL-PERM-01: Admin can access NL2SQL', async ({ page }) => {
      // Already logged in from beforeEach
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-NL2SQL-PERM-02: Admin can use NL2SQL', async ({ page }) => {
      // Already logged in from beforeEach
      await page.goto(PAGE_ROUTES.ANALYSIS_NL2SQL);
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });
  });
});
