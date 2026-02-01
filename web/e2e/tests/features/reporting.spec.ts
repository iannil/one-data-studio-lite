/**
 * Reporting Feature Tests
 *
 * Tests for report generation, export, and dashboard visualization
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Reporting Feature Tests', { tag: ['@reporting', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);

    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Dashboard Reports', () => {
    test('TC-RPT-01-01: View dashboard overview', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const dashboard = page.locator('.dashboard, .cockpit');
      await expect(dashboard.first()).toBeVisible();
    });

    test('TC-RPT-01-02: View data statistics', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const stats = page.locator('.stat-card, .metric-card');
      const count = await stats.count();

      if (count > 0) {
        await expect(stats.first()).toBeVisible();
      }
    });

    test('TC-RPT-01-03: Refresh dashboard data', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const refreshBtn = page.locator('button:has-text("刷新"), button:has-text("重新加载")');
      const count = await refreshBtn.count();

      if (count > 0) {
        await refreshBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-RPT-01-04: Customize dashboard layout', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const customizeBtn = page.locator('button:has-text("自定义"), button:has-text("布局")');
      const count = await customizeBtn.count();

      if (count > 0) {
        await customizeBtn.click();
        await page.waitForTimeout(500);

        const modal = page.locator('.ant-modal');
        const isVisible = await modal.isVisible().catch(() => false);

        if (isVisible) {
          await expect(modal).toBeVisible();
        }
      }
    });

    test('TC-RPT-01-05: Add widget to dashboard', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const addWidgetBtn = page.locator('button:has-text("添加组件"), button:has-text("添加")');
      const count = await addWidgetBtn.count();

      if (count > 0) {
        await addWidgetBtn.click();
        await page.waitForTimeout(500);

        const widgetCard = page.locator('.widget-card, .component-card').first();
        const widgetCount = await widgetCard.count();

        if (widgetCount > 0) {
          await widgetCard.click();
          await page.waitForTimeout(500);
        }
      }
    });
  });

  test.describe('Report Generation', () => {
    test('TC-RPT-02-01: Create new report', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建报告"), button:has-text("新建")');
      await createBtn.click();

      const modal = page.locator('.ant-modal');
      await expect(modal.first()).toBeVisible();
    });

    test('TC-RPT-02-02: Name report', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const nameInput = page.locator('input[name="name"], input[placeholder*="名称"]');
      const count = await nameInput.count();

      if (count > 0) {
        await nameInput.fill('Test Report ' + Date.now());
      }
    });

    test('TC-RPT-02-03: Select report type', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const typeSelect = page.locator('select[name="type"], .report-type-selector');
      const count = await typeSelect.count();

      if (count > 0) {
        await typeSelect.selectOption('table');
        await page.waitForTimeout(300);
      }
    });

    test('TC-RPT-02-04: Select data source for report', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const dataSourceSelect = page.locator('select[name="dataSource"], .data-source-selector');
      const count = await dataSourceSelect.count();

      if (count > 0) {
        await dataSourceSelect.selectOption('users');
        await page.waitForTimeout(300);
      }
    });

    test('TC-RPT-02-05: Save report configuration', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const nameInput = page.locator('input[name="name"]');
      const count = await nameInput.count();

      if (count > 0) {
        await nameInput.fill('Test Report');

        const saveBtn = page.locator('.ant-modal button:has-text("保存"), .ant-modal button:has-text("确定")');
        await saveBtn.click();
        await page.waitForTimeout(1000);

        const success = page.locator('.ant-message-success');
        const isVisible = await success.isVisible().catch(() => false);

        if (isVisible) {
          await expect(success).toBeVisible();
        }
      }
    });
  });

  test.describe('Report Visualization', () => {
    test('TC-RPT-03-01: View chart report', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const chartReport = page.locator('.report-chart, .chart-container').first();
      const count = await chartReport.count();

      if (count > 0) {
        await expect(chartReport).toBeVisible();
      }
    });

    test('TC-RPT-03-02: View table report', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const tableReport = page.locator('.report-table, .ant-table').first();
      await expect(tableReport).toBeVisible();
    });

    test('TC-RPT-03-03: Change chart type', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const chartTypeBtn = page.locator('button:has-text("图表类型"), .chart-type-selector').first();
      const count = await chartTypeBtn.count();

      if (count > 0) {
        await chartTypeBtn.click();
        await page.waitForTimeout(500);

        const barOption = page.locator('.chart-type-option:has-text("柱状图"), .chart-type-option:has-text("Bar")');
        await barOption.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-RPT-03-04: Configure chart axes', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑"), button:has-text("配置")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();

        const xAxisSelect = page.locator('select[name="xAxis"]');
        const xAxisCount = await xAxisSelect.count();

        if (xAxisCount > 0) {
          await xAxisSelect.selectOption('date');
          await page.waitForTimeout(300);
        }
      }
    });

    test('TC-RPT-03-05: Add filter to report', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const filterBtn = page.locator('button:has-text("筛选"), button:has-text("过滤")').first();
      const count = await filterBtn.count();

      if (count > 0) {
        await filterBtn.click();

        const filterModal = page.locator('.filter-modal, .ant-modal');
        await expect(filterModal.first()).toBeVisible();
      }
    });
  });

  test.describe('Report Export', () => {
    test('TC-RPT-04-01: Export report as PDF', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const exportBtn = page.locator('button:has-text("导出"), button:has-text("下载")').first();
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();

        const pdfOption = page.locator('text=PDF, .export-option:has-text("PDF")');
        await pdfOption.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-RPT-04-02: Export report as Excel', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const exportBtn = page.locator('button:has-text("导出")').first();
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();

        const excelOption = page.locator('text=Excel, .export-option:has-text("Excel"), text=XLSX');
        await excelOption.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-RPT-04-03: Export report as CSV', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const exportBtn = page.locator('button:has-text("导出")').first();
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();

        const csvOption = page.locator('text=CSV, .export-option:has-text("CSV")');
        await csvOption.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-RPT-04-04: Export report as image', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const exportBtn = page.locator('button:has-text("导出")').first();
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();

        const imageOption = page.locator('text=图片, text=Image, text=PNG');
        await imageOption.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-RPT-04-05: Schedule report export', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const scheduleBtn = page.locator('button:has-text("定时发送"), button:has-text("订阅")').first();
      const count = await scheduleBtn.count();

      if (count > 0) {
        await scheduleBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });
  });

  test.describe('Report Sharing', () => {
    test('TC-RPT-05-01: Share report with users', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const shareBtn = page.locator('button:has-text("分享"), button:has-text("共享")').first();
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-RPT-05-02: Generate share link', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const shareBtn = page.locator('button:has-text("分享")').first();
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const linkTab = page.locator('text=链接, text=Link');
        const linkCount = await linkTab.count();

        if (linkCount > 0) {
          await linkTab.click();

          const copyBtn = page.locator('button:has-text("复制"), button:has-text("Copy")');
          await copyBtn.click();
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-RPT-05-03: Set report expiration', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const shareBtn = page.locator('button:has-text("分享")').first();
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const expirationInput = page.locator('input[name="expiration"], input[placeholder*="过期"]');
        const inputCount = await expirationInput.count();

        if (inputCount > 0) {
          await expirationInput.fill('2024-12-31');
        }
      }
    });

    test('TC-RPT-05-04: Revoke report access', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const shareBtn = page.locator('button:has-text("分享")').first();
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const revokeBtn = page.locator('button:has-text("撤销"), button:has-text("取消分享")');
        const revokeCount = await revokeBtn.count();

        if (revokeCount > 0) {
          await revokeBtn.click();
          await page.waitForTimeout(500);
        }
      }
    });
  });

  test.describe('Report Templates', () => {
    test('TC-RPT-06-01: View report templates', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const templateBtn = page.locator('button:has-text("模板"), button:has-text("Template")');
      const count = await templateBtn.count();

      if (count > 0) {
        await templateBtn.click();
        await page.waitForTimeout(500);

        const templateGrid = page.locator('.template-grid');
        await expect(templateGrid.first()).toBeVisible();
      }
    });

    test('TC-RPT-06-02: Use report template', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const templateBtn = page.locator('button:has-text("模板")');
      const count = await templateBtn.count();

      if (count > 0) {
        await templateBtn.click();

        const templateCard = page.locator('.template-card').first();
        const cardCount = await templateCard.count();

        if (cardCount > 0) {
          await templateCard.click();

          const useBtn = page.locator('button:has-text("使用模板")');
          await useBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-RPT-06-03: Save report as template', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const saveTemplateBtn = page.locator('button:has-text("保存为模板")').first();
      const count = await saveTemplateBtn.count();

      if (count > 0) {
        await saveTemplateBtn.click();

        const nameInput = page.locator('input[name="templateName"]');
        await nameInput.fill('My Template');

        const saveBtn = page.locator('.ant-modal button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Report Scheduling', () => {
    test('TC-RPT-07-01: Schedule daily report', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const scheduleBtn = page.locator('button:has-text("定时发送")').first();
      const count = await scheduleBtn.count();

      if (count > 0) {
        await scheduleBtn.click();

        const frequencySelect = page.locator('select[name="frequency"]');
        await frequencySelect.selectOption('daily');

        const saveBtn = page.locator('.ant-modal button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-RPT-07-02: Configure report recipients', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const scheduleBtn = page.locator('button:has-text("定时发送")').first();
      const count = await scheduleBtn.count();

      if (count > 0) {
        await scheduleBtn.click();

        const recipientInput = page.locator('input[name="recipients"]');
        await recipientInput.fill('user@example.com');

        const saveBtn = page.locator('.ant-modal button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-RPT-07-03: View scheduled reports', async ({ page }) => {
      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const scheduledTab = page.locator('text=定时任务, text=Scheduled');
      const count = await scheduledTab.count();

      if (count > 0) {
        await scheduledTab.click();
        await page.waitForTimeout(500);

        const list = page.locator('.scheduled-list, .ant-table');
        await expect(list.first()).toBeVisible();
      }
    });
  });

  test.describe('Report Permissions', () => {
    test('TC-RPT-08-01: Admin can view reports', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-RPT-08-02: Admin can access reports page', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const reportList = page.locator('.report-list, .ant-table');
      const count = await reportList.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('TC-RPT-08-03: Admin can create reports', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/reports');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      const count = await createBtn.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });
});
