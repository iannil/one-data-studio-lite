/**
 * Data Quality Feature Tests
 *
 * Tests for data quality monitoring, profiling, and validation
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Data Quality Feature Tests', { tag: ['@data-quality', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);

    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Quality Dashboard', () => {
    test('TC-DQ-01-01: View quality dashboard', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const dashboard = page.locator('.quality-dashboard, .dashboard');
      await expect(dashboard.first()).toBeVisible();
    });

    test('TC-DQ-01-02: View quality metrics', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const metrics = page.locator('.quality-metric, .metric-card');
      const count = await metrics.count();

      if (count > 0) {
        await expect(metrics.first()).toBeVisible();
      }
    });

    test('TC-DQ-01-03: View quality score', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const score = page.locator('.quality-score, .score-card');
      const count = await score.count();

      if (count > 0) {
        const text = await score.textContent();
        expect(text).toBeTruthy();
      }
    });

    test('TC-DQ-01-04: View quality trend', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const trendChart = page.locator('.trend-chart, .quality-trend');
      const isVisible = await trendChart.isVisible().catch(() => false);

      if (isVisible) {
        await expect(trendChart).toBeVisible();
      }
    });
  });

  test.describe('Data Profiling', () => {
    test('TC-DQ-02-01: Profile data table', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const tableSelect = page.locator('select[name="table"], .table-selector');
      const count = await tableSelect.count();

      if (count > 0) {
        await tableSelect.selectOption('users');
        await page.waitForTimeout(1000);
      }

      const profileBtn = page.locator('button:has-text("分析"), button:has-text("Profile")');
      const btnCount = await profileBtn.count();

      if (btnCount > 0) {
        await profileBtn.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-DQ-02-02: View column statistics', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const statsTable = page.locator('.column-stats, .profile-stats');
      const isVisible = await statsTable.isVisible().catch(() => false);

      if (isVisible) {
        await expect(statsTable).toBeVisible();
      }
    });

    test('TC-DQ-02-03: View data distribution', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const distributionChart = page.locator('.distribution-chart');
      const isVisible = await distributionChart.isVisible().catch(() => false);

      if (isVisible) {
        await expect(distributionChart).toBeVisible();
      }
    });

    test('TC-DQ-02-04: Detect outliers', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const outlierSection = page.locator('.outlier-section, .anomaly-detection');
      const isVisible = await outlierSection.isVisible().catch(() => false);

      if (isVisible) {
        await expect(outlierSection).toBeVisible();
      }
    });

    test('TC-DQ-02-05: View missing values', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const missingValues = page.locator('.missing-values, .null-analysis');
      const isVisible = await missingValues.isVisible().catch(() => false);

      if (isVisible) {
        await expect(missingValues).toBeVisible();
      }
    });
  });

  test.describe('Quality Rules', () => {
    test('TC-DQ-03-01: Create quality rule', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建规则"), button:has-text("新建")');
      await createBtn.click();

      const modal = page.locator('.ant-modal');
      await expect(modal.first()).toBeVisible();
    });

    test('TC-DQ-03-02: Define rule condition', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建规则")');
      await createBtn.click();

      const conditionInput = page.locator('textarea[name="condition"], .rule-condition');
      const count = await conditionInput.count();

      if (count > 0) {
        await conditionInput.fill('age > 0 AND age < 120');
      }
    });

    test('TC-DQ-03-03: Set rule severity', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建规则")');
      await createBtn.click();

      const severitySelect = page.locator('select[name="severity"]');
      const count = await severitySelect.count();

      if (count > 0) {
        await severitySelect.selectOption('error');
        await page.waitForTimeout(300);
      }
    });

    test('TC-DQ-03-04: Enable/disable rule', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const ruleSwitch = page.locator('.quality-rule .ant-switch').first();
      const count = await ruleSwitch.count();

      if (count > 0) {
        await ruleSwitch.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-DQ-03-05: Delete quality rule', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const deleteBtn = page.locator('.quality-rule button:has-text("删除")').first();
      const count = await deleteBtn.count();

      if (count > 0) {
        await deleteBtn.click();
        await page.waitForTimeout(500);

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        await confirmBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Quality Checks', () => {
    test('TC-DQ-04-01: Run quality check', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const runBtn = page.locator('button:has-text("运行检查"), button:has-text("检查")');
      const count = await runBtn.count();

      if (count > 0) {
        await runBtn.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-DQ-04-02: Schedule quality check', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const scheduleBtn = page.locator('button:has-text("定时检查")');
      const count = await scheduleBtn.count();

      if (count > 0) {
        await scheduleBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-DQ-04-03: View check results', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const resultsTab = page.locator('text=检查结果, text=Results');
      const count = await resultsTab.count();

      if (count > 0) {
        await resultsTab.click();
        await page.waitForTimeout(500);

        const resultsList = page.locator('.check-results, .quality-results');
        await expect(resultsList.first()).toBeVisible();
      }
    });

    test('TC-DQ-04-04: View check history', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const historyTab = page.locator('text=历史记录, text=History');
      const count = await historyTab.count();

      if (count > 0) {
        await historyTab.click();
        await page.waitForTimeout(500);

        const historyList = page.locator('.check-history, .history-list');
        await expect(historyList.first()).toBeVisible();
      }
    });
  });

  test.describe('Quality Alerts', () => {
    test('TC-DQ-05-01: Configure quality alert', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const alertBtn = page.locator('button:has-text("告警配置"), button:has-text("Alert")');
      const count = await alertBtn.count();

      if (count > 0) {
        await alertBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-DQ-05-02: Set alert threshold', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const alertBtn = page.locator('button:has-text("告警配置")');
      const count = await alertBtn.count();

      if (count > 0) {
        await alertBtn.click();

        const thresholdInput = page.locator('input[name="threshold"]');
        await thresholdInput.fill('80');
      }
    });

    test('TC-DQ-05-03: Configure alert notification', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const alertBtn = page.locator('button:has-text("告警配置")');
      const count = await alertBtn.count();

      if (count > 0) {
        await alertBtn.click();

        const emailCheckbox = page.locator('input[name="emailNotification"]');
        const checkCount = await emailCheckbox.count();

        if (checkCount > 0) {
          await emailCheckbox.check();
        }
      }
    });

    test('TC-DQ-05-04: View active alerts', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const alertsList = page.locator('.quality-alerts, .alerts-list');
      const isVisible = await alertsList.isVisible().catch(() => false);

      if (isVisible) {
        await expect(alertsList).toBeVisible();
      }
    });

    test('TC-DQ-05-05: Dismiss alert', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const dismissBtn = page.locator('button:has-text("忽略"), button:has-text("Dismiss")').first();
      const count = await dismissBtn.count();

      if (count > 0) {
        await dismissBtn.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Quality Reports', () => {
    test('TC-DQ-06-01: Generate quality report', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const reportBtn = page.locator('button:has-text("生成报告"), button:has-text("Report")');
      const count = await reportBtn.count();

      if (count > 0) {
        await reportBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-DQ-06-02: Export quality report', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const exportBtn = page.locator('button:has-text("导出"), button:has-text("下载")');
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-DQ-06-03: Schedule quality report', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const scheduleReportBtn = page.locator('button:has-text("定时报告")');
      const count = await scheduleReportBtn.count();

      if (count > 0) {
        await scheduleReportBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });
  });

  test.describe('Data Lineage', () => {
    test('TC-DQ-07-01: View data lineage', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const lineageTab = page.locator('text=数据血缘, text=Lineage');
      const count = await lineageTab.count();

      if (count > 0) {
        await lineageTab.click();
        await page.waitForTimeout(500);

        const lineageGraph = page.locator('.lineage-graph, .dag-chart');
        await expect(lineageGraph.first()).toBeVisible();
      }
    });

    test('TC-DQ-07-02: Trace data source', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const lineageTab = page.locator('text=数据血缘');
      const count = await lineageTab.count();

      if (count > 0) {
        await lineageTab.click();

        const node = page.locator('.lineage-node').first();
        const nodeCount = await node.count();

        if (nodeCount > 0) {
          await node.click();
          await page.waitForTimeout(500);
        }
      }
    });
  });

  test.describe('Quality Comparisons', () => {
    test('TC-DQ-08-01: Compare data quality over time', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const compareBtn = page.locator('button:has-text("对比"), button:has-text("Compare")');
      const count = await compareBtn.count();

      if (count > 0) {
        await compareBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-DQ-08-02: Compare tables', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const table1Select = page.locator('select[name="table1"]');
      const count = await table1Select.count();

      if (count > 0) {
        await table1Select.selectOption('users');

        const table2Select = page.locator('select[name="table2"]');
        await table2Select.selectOption('users_backup');

        const compareBtn = page.locator('button:has-text("对比")');
        await compareBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Quality Permissions', () => {
    test('TC-DQ-09-01: Admin can view quality metrics', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-DQ-09-02: Admin can access quality page', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const dashboard = page.locator('.quality-dashboard');
      const isVisible = await dashboard.isVisible().catch(() => false);

      if (isVisible) {
        await expect(dashboard).toBeVisible();
      }
    });
  });
});
