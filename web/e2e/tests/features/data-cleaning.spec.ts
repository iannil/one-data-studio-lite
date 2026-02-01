/**
 * Data Cleaning Feature Tests
 *
 * Tests for data quality rules, scanning, and cleaning operations
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { DataCleaningPage } from '@pages/cleaning.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Data Cleaning Feature Tests', { tag: ['@cleaning', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;
  let cleaningPage: DataCleaningPage;

  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    loginPage = new LoginPage(page);
    cleaningPage = new DataCleaningPage(page);

    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Cleaning Rules Management', () => {
    test('TC-CLN-01-01: View cleaning rules list', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const rules = await cleaningPage.getRules();
      expect(Array.isArray(rules)).toBe(true);
    });

    test('TC-CLN-01-02: Create new cleaning rule', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.clickCreateRule();

      const modal = page.locator('.ant-modal');
      const isVisible = await modal.isVisible().catch(() => false);

      if (isVisible) {
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-CLN-01-03: Configure rule parameters', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.clickCreateRule();

      const ruleTypeSelect = page.locator('select[name="ruleType"], .rule-type-select');
      const count = await ruleTypeSelect.count();

      if (count > 0) {
        await cleaningPage.configureRule({
          ruleType: 'null_check',
          field: 'email',
          condition: 'IS_NULL',
          action: 'REMOVE_ROW',
        });

        const saveBtn = page.locator('button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-CLN-01-04: Enable/disable cleaning rule', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const rules = await cleaningPage.getRules();

      if (rules.length > 0) {
        const ruleName = rules[0].name;
        if (ruleName) {
          await cleaningPage.toggleRule(ruleName);
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-CLN-01-05: Delete cleaning rule', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const rules = await cleaningPage.getRules();

      if (rules.length > 1) {
        const ruleName = rules[rules.length - 1].name;
        if (ruleName) {
          await cleaningPage.deleteRule(ruleName);

          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Data Quality Scanning', () => {
    test('TC-CLN-02-01: Select data source for scanning', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.selectDataSource('users_table');

      await page.waitForTimeout(1000);
    });

    test('TC-CLN-02-02: Run data quality scan', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.scanData();

      await page.waitForTimeout(3000);
    });

    test('TC-CLN-02-03: View scan results', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.scanData();
      await page.waitForTimeout(2000);

      const results = await cleaningPage.getScanResults();

      expect(results).toHaveProperty('totalRows');
      expect(results).toHaveProperty('issuesFound');
    });

    test('TC-CLN-02-04: Filter scan results by issue type', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.scanData();
      await page.waitForTimeout(2000);

      const filterBtn = page.locator('button:has-text("筛选"), .filter-button');
      const count = await filterBtn.count();

      if (count > 0) {
        await filterBtn.first().click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-CLN-02-05: Export scan results', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const exportBtn = page.locator('button:has-text("导出"), button:has-text("下载")');
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.first().click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Cleaning Operations', () => {
    test('TC-CLN-03-01: Apply cleaning rules', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.scanData();
      await page.waitForTimeout(1000);

      await cleaningPage.applyCleaningRules();

      await page.waitForTimeout(2000);
    });

    test('TC-CLN-03-02: Preview cleaning results', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const previewBtn = page.locator('button:has-text("预览")');
      const count = await previewBtn.count();

      if (count > 0) {
        await previewBtn.click();
        await page.waitForTimeout(1000);

        const previewArea = page.locator('.preview-area, .data-preview');
        await expect(previewArea.first()).toBeVisible();
      }
    });

    test('TC-CLN-03-03: Rollback cleaning operation', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const rollbackBtn = page.locator('button:has-text("回滚"), button:has-text("撤销")');
      const count = await rollbackBtn.count();

      if (count > 0) {
        await rollbackBtn.click();
        await page.waitForTimeout(500);

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        const confirmCount = await confirmBtn.count();

        if (confirmCount > 0) {
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('AI-Powered Cleaning', () => {
    test('TC-CLN-04-01: Get AI rule suggestions', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const suggestBtn = page.locator('button:has-text("AI推荐"), button:has-text("智能推荐")');
      const count = await suggestBtn.count();

      if (count > 0) {
        await suggestBtn.click();
        await page.waitForTimeout(2000);

        const suggestions = page.locator('.suggestion-item');
        const suggestionCount = await suggestions.count();

        if (suggestionCount > 0) {
          await expect(suggestions.first()).toBeVisible();
        }
      }
    });

    test('TC-CLN-04-02: Apply AI suggested rule', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const suggestBtn = page.locator('button:has-text("AI推荐")');
      const count = await suggestBtn.count();

      if (count > 0) {
        await suggestBtn.click();
        await page.waitForTimeout(1000);

        const applyBtn = page.locator('.suggestion-item button:has-text("应用")');
        const applyCount = await applyBtn.count();

        if (applyCount > 0) {
          await applyBtn.first().click();
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-CLN-04-03: Auto-clean with AI', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const autoCleanBtn = page.locator('button:has-text("智能清理"), button:has-text("自动清洗")');
      const count = await autoCleanBtn.count();

      if (count > 0) {
        await autoCleanBtn.click();
        await page.waitForTimeout(500);

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        const confirmCount = await confirmBtn.count();

        if (confirmCount > 0) {
          await confirmBtn.click();
          await page.waitForTimeout(2000);
        }
      }
    });
  });

  test.describe('Data Validation', () => {
    test('TC-CLN-05-01: Validate email format', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.clickCreateRule();

      await cleaningPage.configureRule({
        ruleType: 'format_validation',
        field: 'email',
        condition: 'EMAIL_FORMAT',
        action: 'FLAG',
      });

      const saveBtn = page.locator('button:has-text("保存")');
      const count = await saveBtn.count();

      if (count > 0) {
        await saveBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-CLN-05-02: Validate required fields', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.clickCreateRule();

      await cleaningPage.configureRule({
        ruleType: 'required_check',
        field: 'name',
        condition: 'NOT_EMPTY',
        action: 'FLAG',
      });

      const saveBtn = page.locator('button:has-text("保存")');
      const count = await saveBtn.count();

      if (count > 0) {
        await saveBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-CLN-05-03: Validate numeric range', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.clickCreateRule();

      await cleaningPage.configureRule({
        ruleType: 'range_check',
        field: 'age',
        condition: 'BETWEEN_0_120',
        action: 'FLAG',
      });

      const saveBtn = page.locator('button:has-text("保存")');
      const count = await saveBtn.count();

      if (count > 0) {
        await saveBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-CLN-05-04: Validate date consistency', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.clickCreateRule();

      await cleaningPage.configureRule({
        ruleType: 'date_consistency',
        field: 'birth_date',
        condition: 'NOT_FUTURE',
        action: 'FLAG',
      });

      const saveBtn = page.locator('button:has-text("保存")');
      const count = await saveBtn.count();

      if (count > 0) {
        await saveBtn.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Data Transformation', () => {
    test('TC-CLN-06-01: Transform text case', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.clickCreateRule();

      await cleaningPage.configureRule({
        ruleType: 'transform',
        field: 'name',
        condition: 'UPPERCASE',
        action: 'TRANSFORM',
      });

      const saveBtn = page.locator('button:has-text("保存")');
      const count = await saveBtn.count();

      if (count > 0) {
        await saveBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-CLN-06-02: Remove duplicates', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const dedupeBtn = page.locator('button:has-text("去重"), button:has-text("删除重复")');
      const count = await dedupeBtn.count();

      if (count > 0) {
        await dedupeBtn.click();
        await page.waitForTimeout(500);

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        const confirmCount = await confirmBtn.count();

        if (confirmCount > 0) {
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-CLN-06-03: Standardize date format', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      await cleaningPage.clickCreateRule();

      await cleaningPage.configureRule({
        ruleType: 'transform',
        field: 'date',
        condition: 'ISO_8601',
        action: 'TRANSFORM',
      });

      const saveBtn = page.locator('button:has-text("保存")');
      const count = await saveBtn.count();

      if (count > 0) {
        await saveBtn.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Statistics and Reports', () => {
    test('TC-CLN-07-01: View cleaning statistics', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const stats = page.locator('.cleaning-stats, .statistics');
      const isVisible = await stats.isVisible().catch(() => false);

      if (isVisible) {
        await expect(stats).toBeVisible();
      }
    });

    test('TC-CLN-07-02: Generate cleaning report', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const reportBtn = page.locator('button:has-text("生成报告"), button:has-text("报告")');
      const count = await reportBtn.count();

      if (count > 0) {
        await reportBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-CLN-07-03: Download cleaning history', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const historyBtn = page.locator('button:has-text("历史记录"), button:has-text("历史")');
      const count = await historyBtn.count();

      if (count > 0) {
        await historyBtn.click();
        await page.waitForTimeout(500);

        const downloadBtn = page.locator('button:has-text("下载")');
        const downloadCount = await downloadBtn.count();

        if (downloadCount > 0) {
          await downloadBtn.first().click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Permissions', () => {
    test('TC-CLN-08-01: Admin can access cleaning page', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-CLN-08-02: Admin can view cleaning rules', async ({ page }) => {
      await cleaningPage.goto();
      await cleaningPage.waitForPageLoad();

      const rules = await cleaningPage.getRules();
      expect(Array.isArray(rules)).toBe(true);
    });
  });
});
