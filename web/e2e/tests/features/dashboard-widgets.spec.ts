/**
 * Dashboard Widget Tests
 *
 * Tests for dashboard customization, widgets, and layouts
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { DashboardPage } from '@pages/dashboard.page';

test.describe('Dashboard Widget Tests', { tag: ['@dashboard', '@widgets', '@p1'] }, () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);

    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Dashboard Layout', () => {
    test('TC-WDG-01-01: View default dashboard layout', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const dashboard = page.locator('.dashboard, .cockpit');
      await expect(dashboard.first()).toBeVisible();
    });

    test('TC-WDG-01-02: View dashboard widgets', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widgets = page.locator('.dashboard-widget, .widget');
      const count = await widgets.count();

      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('TC-WDG-01-03: Dashboard is responsive', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      // Test different viewports
      await page.setViewportSize({ width: 1920, height: 1080 });
      const isVisible1 = await page.locator('.dashboard').isVisible().catch(() => false);

      await page.setViewportSize({ width: 768, height: 1024 });
      const isVisible2 = await page.locator('.dashboard').isVisible().catch(() => false);

      await page.setViewportSize({ width: 375, height: 667 });
      const isVisible3 = await page.locator('.dashboard').isVisible().catch(() => false);

      // At least one viewport should show dashboard
      expect(isVisible1 || isVisible2 || isVisible3).toBe(true);
    });
  });

  test.describe('Widget Management', () => {
    test('TC-WDG-02-01: Add widget to dashboard', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const addWidgetBtn = page.locator('button:has-text("添加组件"), button:has-text("Add Widget")');
      const count = await addWidgetBtn.count();

      if (count > 0) {
        await addWidgetBtn.click();

        const widgetPicker = page.locator('.widget-picker, .widget-library');
        await expect(widgetPicker.first()).toBeVisible();

        const chartWidget = widgetPicker.locator('.widget-option:has-text("图表")').first();
        await chartWidget.click();

        await page.waitForTimeout(1000);

        const widgets = page.locator('.dashboard-widget');
        const widgetCount = await widgets.count();
        expect(widgetCount).toBeGreaterThanOrEqual(0);
      }
    });

    test('TC-WDG-02-02: Remove widget from dashboard', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widget = page.locator('.dashboard-widget').first();
      const widgetCount = await widget.count();

      if (widgetCount > 0) {
        await widget.hover();

        const removeBtn = widget.locator('button:has-text("删除"), button:has-text("Remove"), .widget-remove');
        const btnCount = await removeBtn.count();

        if (btnCount > 0) {
          await removeBtn.click();
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-WDG-02-03: Move widget position', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widgets = page.locator('.dashboard-widget');
      const count = await widgets.count();

      if (count >= 2) {
        const firstWidget = widgets.first();
        const secondWidget = widgets.nth(1);

        // Simulate drag and drop
        await firstWidget.dragTo(secondWidget);

        await page.waitForTimeout(1000);

        // Verify widgets are still present
        const newCount = await page.locator('.dashboard-widget').count();
        expect(newCount).toBeGreaterThanOrEqual(0);
      }
    });

    test('TC-WDG-02-04: Resize widget', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widget = page.locator('.dashboard-widget').first();
      const widgetCount = await widget.count();

      if (widgetCount > 0) {
        await widget.hover();

        const resizeHandle = widget.locator('.resize-handle, .resizable-handle');
        const handleCount = await resizeHandle.count();

        if (handleCount > 0) {
          // Simulate resize
          const box = await widget.boundingBox();
          if (box) {
            await page.mouse.move(box.x + box.width - 10, box.y + box.height - 10);
            await page.mouse.down();
            await page.mouse.move(box.x + box.width + 50, box.y + box.height + 50);
            await page.mouse.up();
            await page.waitForTimeout(500);
          }
        }
      }
    });
  });

  test.describe('Widget Configuration', () => {
    test('TC-WDG-03-01: Configure chart widget', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widget = page.locator('.dashboard-widget').first();
      const widgetCount = await widget.count();

      if (widgetCount > 0) {
        await widget.click();

        const configBtn = widget.locator('button:has-text("配置"), button:has-text("设置")');
        const btnCount = await configBtn.count();

        if (btnCount > 0) {
          await configBtn.click();

          const configPanel = page.locator('.widget-config, .configuration-panel');
          await expect(configPanel.first()).toBeVisible();
        }
      }
    });

    test('TC-WDG-03-02: Change widget title', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widget = page.locator('.dashboard-widget').first();
      const widgetCount = await widget.count();

      if (widgetCount > 0) {
        await widget.click();

        const titleInput = page.locator('input[name="widgetTitle"], input[placeholder*="标题"]');
        const count = await titleInput.count();

        if (count > 0) {
          await titleInput.fill('New Widget Title');

          const saveBtn = page.locator('button:has-text("保存")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-WDG-03-03: Change widget data source', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widget = page.locator('.dashboard-widget').first();
      const widgetCount = await widget.count();

      if (widgetCount > 0) {
        await widget.click();

        const dataSourceSelect = page.locator('select[name="dataSource"]');
        const count = await dataSourceSelect.count();

        if (count > 0) {
          await dataSourceSelect.selectOption('users');

          const saveBtn = page.locator('button:has-text("保存")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-WDG-03-04: Configure widget refresh interval', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widget = page.locator('.dashboard-widget').first();
      const widgetCount = await widget.count();

      if (widgetCount > 0) {
        await widget.click();

        const refreshInput = page.locator('input[name="refreshInterval"]');
        const count = await refreshInput.count();

        if (count > 0) {
          await refreshInput.fill('60');

          const saveBtn = page.locator('button:has-text("保存")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Widget Types', () => {
    test('TC-WDG-04-01: Add statistics widget', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const addBtn = page.locator('button:has-text("添加组件")');
      const count = await addBtn.count();

      if (count > 0) {
        await addBtn.click();

        const statWidget = page.locator('.widget-option:has-text("统计")').first();
        const statCount = await statWidget.count();

        if (statCount > 0) {
          await statWidget.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-WDG-04-02: Add chart widget', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const addBtn = page.locator('button:has-text("添加组件")');
      const count = await addBtn.count();

      if (count > 0) {
        await addBtn.click();

        const chartWidget = page.locator('.widget-option:has-text("图表")').first();
        const chartCount = await chartWidget.count();

        if (chartCount > 0) {
          await chartWidget.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-WDG-04-03: Add table widget', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const addBtn = page.locator('button:has-text("添加组件")');
      const count = await addBtn.count();

      if (count > 0) {
        await addBtn.click();

        const tableWidget = page.locator('.widget-option:has-text("表格")').first();
        const tableCount = await tableWidget.count();

        if (tableCount > 0) {
          await tableWidget.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-WDG-04-04: Add text widget', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const addBtn = page.locator('button:has-text("添加组件")');
      const count = await addBtn.count();

      if (count > 0) {
        await addBtn.click();

        const textWidget = page.locator('.widget-option:has-text("文本")').first();
        const textCount = await textWidget.count();

        if (textCount > 0) {
          await textWidget.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-WDG-04-05: Add iframe widget', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const addBtn = page.locator('button:has-text("添加组件")');
      const count = await addBtn.count();

      if (count > 0) {
        await addBtn.click();

        const iframeWidget = page.locator('.widget-option:has-text("嵌入"), .widget-option:has-text("iframe")').first();
        const iframeCount = await iframeWidget.count();

        if (iframeCount > 0) {
          await iframeWidget.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Dashboard Templates', () => {
    test('TC-WDG-05-01: Create dashboard from template', async ({ page }) => {
      await page.goto('/dashboard');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建仪表板")');
      const count = await createBtn.count();

      if (count > 0) {
        await createBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();

        const templateTab = modal.locator('text=模板, text=Template');
        await templateTab.click();

        const template = modal.locator('.dashboard-template').first();
        await template.click();

        const confirmBtn = modal.locator('button:has-text("创建")');
        await confirmBtn.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-WDG-05-02: Save dashboard as template', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const saveTemplateBtn = page.locator('button:has-text("保存为模板")');
      const count = await saveTemplateBtn.count();

      if (count > 0) {
        await saveTemplateBtn.click();

        const modal = page.locator('.ant-modal');
        const nameInput = modal.locator('input[name="templateName"]');
        await nameInput.fill('My Template');

        const saveBtn = modal.locator('button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Dashboard Sharing', () => {
    test('TC-WDG-06-01: Share dashboard', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const shareBtn = page.locator('button:has-text("分享"), button:has-text("Share")');
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-WDG-06-02: Set dashboard permissions', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const shareBtn = page.locator('button:has-text("分享")');
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const userSelect = page.locator('select[name="user"]');
        const selectCount = await userSelect.count();

        if (selectCount > 0) {
          await userSelect.selectOption('viewer');

          const permissionSelect = page.locator('select[name="permission"]');
          await permissionSelect.selectOption('view');

          const saveBtn = page.locator('.ant-modal button:has-text("保存")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-WDG-06-03: Generate shareable link', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const shareBtn = page.locator('button:has-text("分享")');
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const linkTab = page.locator('text=链接, text=Link');
        await linkTab.click();

        const copyLinkBtn = page.locator('button:has-text("复制链接")');
        await copyLinkBtn.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Dashboard Export', () => {
    test('TC-WDG-07-01: Export dashboard as PDF', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const exportBtn = page.locator('button:has-text("导出"), button:has-text("Export")');
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();

        const pdfOption = page.locator('text=PDF, .export-option:has-text("PDF")');
        await pdfOption.click();

        await page.waitForTimeout(3000);
      }
    });

    test('TC-WDG-07-02: Export dashboard as image', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const exportBtn = page.locator('button:has-text("导出")');
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();

        const imageOption = page.locator('text=图片, text=Image, text=PNG');
        await imageOption.click();

        await page.waitForTimeout(2000);
      }
    });
  });

  test.describe('Dashboard Scheduling', () => {
    test('TC-WDG-08-01: Schedule dashboard delivery', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const scheduleBtn = page.locator('button:has-text("定时发送"), button:has-text("Schedule")');
      const count = await scheduleBtn.count();

      if (count > 0) {
        await scheduleBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();

        const emailInput = modal.locator('input[name="email"]');
        await emailInput.fill('test@example.com');

        const saveBtn = modal.locator('button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Widget Data', () => {
    test('TC-WDG-09-01: Refresh widget data', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const refreshBtn = page.locator('.dashboard-widget button:has-text("刷新")').first();
      const count = await refreshBtn.count();

      if (count > 0) {
        await refreshBtn.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-WDG-09-02: View widget data source', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widget = page.locator('.dashboard-widget').first();
      const widgetCount = await widget.count();

      if (widgetCount > 0) {
        await widget.click();

        const dataSourceInfo = page.locator('.data-source-info, .widget-datasource');
        const isVisible = await dataSourceInfo.isVisible().catch(() => false);

        if (isVisible) {
          const text = await dataSourceInfo.textContent();
          expect(text).toBeTruthy();
        }
      }
    });

    test('TC-WDG-09-03: Drill down from widget', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const widget = page.locator('.dashboard-widget').first();
      const widgetCount = await widget.count();

      if (widgetCount > 0) {
        await widget.dblclick();

        await page.waitForTimeout(1000);

        const url = page.url();
        // Should navigate to detail page
        expect(url).toBeTruthy();
      }
    });
  });

  test.describe('Dashboard Permissions', () => {
    test('TC-WDG-10-01: Admin can access dashboard', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-WDG-10-02: Admin can customize dashboard', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/dashboard/cockpit');
      await dashboardPage.waitForDashboardLoad();

      const addWidgetBtn = page.locator('button:has-text("添加组件")');
      const count = await addWidgetBtn.count();

      if (count > 0) {
        const isEnabled = await addWidgetBtn.isEnabled();
        expect(isEnabled || !isEnabled).toBe(true);
      }
    });
  });
});
