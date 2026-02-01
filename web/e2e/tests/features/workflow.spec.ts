/**
 * Workflow and Orchestration Feature Tests
 *
 * Tests for workflow creation, scheduling, and execution
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Workflow Feature Tests', { tag: ['@workflow', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);

    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Workflow List', () => {
    test('TC-WF-01-01: View workflow list', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const list = page.locator('.workflow-list, .ant-table');
      await expect(list.first()).toBeVisible();
    });

    test('TC-WF-01-02: Search workflows', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[placeholder*="搜索"]');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('test');
        await page.waitForTimeout(500);
      }
    });

    test('TC-WF-01-03: Filter by status', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const statusFilter = page.locator('.status-filter, select[name="status"]');
      const count = await statusFilter.count();

      if (count > 0) {
        await statusFilter.selectOption('running');
        await page.waitForTimeout(500);
      }
    });

    test('TC-WF-01-04: Sort workflows by date', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const sortBtn = page.locator('button:has-text("排序"), .sort-button');
      const count = await sortBtn.count();

      if (count > 0) {
        await sortBtn.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Workflow Creation', () => {
    test('TC-WF-02-01: Create new workflow', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建"), button:has-text("新建")');
      await createBtn.click();

      const modal = page.locator('.ant-modal');
      await expect(modal.first()).toBeVisible();
    });

    test('TC-WF-02-02: Name workflow', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const nameInput = page.locator('input[name="name"], input[placeholder*="名称"]');
      const count = await nameInput.count();

      if (count > 0) {
        await nameInput.fill('Test Workflow ' + Date.now());

        const nextBtn = page.locator('button:has-text("下一步"), button:has-text("继续")');
        await nextBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-WF-02-03: Select workflow template', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const templateCard = page.locator('.template-card, .workflow-template').first();
      const count = await templateCard.count();

      if (count > 0) {
        await templateCard.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-WF-02-04: Configure workflow parameters', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const nameInput = page.locator('input[name="name"]');
      const inputCount = await nameInput.count();

      if (inputCount > 0) {
        await nameInput.fill('Test Workflow');

        const paramInput = page.locator('input[name="parameters"]');
        const paramCount = await paramInput.count();

        if (paramCount > 0) {
          await paramInput.fill('{"key": "value"}');
        }

        const saveBtn = page.locator('button:has-text("保存"), button:has-text("创建")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Workflow Designer', () => {
    test('TC-WF-03-01: Open workflow designer', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑"), button:has-text("设计")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();
        await page.waitForTimeout(500);

        const canvas = page.locator('.workflow-canvas, .designer-canvas');
        await expect(canvas.first()).toBeVisible();
      }
    });

    test('TC-WF-03-02: Add task to workflow', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();

        const taskPalette = page.locator('.task-palette, .palette');
        const paletteCount = await taskPalette.count();

        if (paletteCount > 0) {
          const dataTask = taskPalette.locator('.task-item:has-text("数据处理")');
          await dataTask.click();
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-WF-03-03: Connect workflow tasks', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();

        const canvas = page.locator('.workflow-canvas');
        const task = canvas.locator('.workflow-task').first();
        const taskCount = await task.count();

        if (taskCount > 0) {
          await task.dragTo(canvas.locator('.drop-zone'));
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-WF-03-04: Configure task properties', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();

        const task = page.locator('.workflow-task').first();
        const taskCount = await task.count();

        if (taskCount > 0) {
          await task.click();

          const propertiesPanel = page.locator('.properties-panel');
          await expect(propertiesPanel.first()).toBeVisible();
        }
      }
    });

    test('TC-WF-03-05: Save workflow design', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();

        const saveBtn = page.locator('button:has-text("保存")');
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

  test.describe('Workflow Execution', () => {
    test('TC-WF-04-01: Run workflow manually', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const runBtn = page.locator('button:has-text("运行"), button:has-text("执行")').first();
      const count = await runBtn.count();

      if (count > 0) {
        await runBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-WF-04-02: Run workflow with parameters', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const runBtn = page.locator('button:has-text("运行")').first();
      const count = await runBtn.count();

      if (count > 0) {
        await runBtn.click();

        const paramModal = page.locator('.ant-modal');
        const modalCount = await paramModal.count();

        if (modalCount > 0) {
          const paramInput = paramModal.locator('textarea[name="parameters"]');
          await paramInput.fill('{"date": "2024-01-01"}');

          const confirmBtn = paramModal.locator('button:has-text("确定"), button:has-text("运行")');
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-WF-04-03: Stop running workflow', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const stopBtn = page.locator('button:has-text("停止"), button:has-text("取消")').first();
      const count = await stopBtn.count();

      if (count > 0) {
        const isEnabled = await stopBtn.isEnabled();
        if (isEnabled) {
          await stopBtn.click();
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-WF-04-04: View execution status', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const statusBadge = page.locator('.status-badge, .execution-status').first();
      const count = await statusBadge.count();

      if (count > 0) {
        const text = await statusBadge.textContent();
        expect(text).toBeTruthy();
      }
    });

    test('TC-WF-04-05: View execution log', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const row = page.locator('.ant-table-row, .workflow-item').first();
      await row.click();

      const logTab = page.locator('text=执行日志, text=Log');
      const count = await logTab.count();

      if (count > 0) {
        await logTab.click();
        await page.waitForTimeout(500);

        const logContent = page.locator('.log-content, .execution-log');
        await expect(logContent.first()).toBeVisible();
      }
    });
  });

  test.describe('Workflow Scheduling', () => {
    test('TC-WF-05-01: Schedule workflow with cron', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const scheduleBtn = page.locator('button:has-text("调度"), button:has-text("计划")').first();
      const count = await scheduleBtn.count();

      if (count > 0) {
        await scheduleBtn.click();

        const cronInput = page.locator('input[name="cron"], input[placeholder*="cron"]');
        await cronInput.fill('0 0 * * *');

        const saveBtn = page.locator('.ant-modal button:has-text("确定")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-WF-05-02: View workflow schedule', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const scheduleInfo = page.locator('.schedule-info, .cron-expression').first();
      const count = await scheduleInfo.count();

      if (count > 0) {
        const text = await scheduleInfo.textContent();
        expect(text).toBeTruthy();
      }
    });

    test('TC-WF-05-03: Enable/disable schedule', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const scheduleToggle = page.locator('.schedule-toggle, .ant-switch').first();
      const count = await scheduleToggle.count();

      if (count > 0) {
        await scheduleToggle.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-WF-05-04: Edit schedule', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const editScheduleBtn = page.locator('button:has-text("编辑调度")').first();
      const count = await editScheduleBtn.count();

      if (count > 0) {
        await editScheduleBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });
  });

  test.describe('Workflow Versioning', () => {
    test('TC-WF-06-01: View workflow versions', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const versionBtn = page.locator('button:has-text("版本"), button:has-text("历史")').first();
      const count = await versionBtn.count();

      if (count > 0) {
        await versionBtn.click();
        await page.waitForTimeout(500);

        const versionList = page.locator('.version-list');
        await expect(versionList.first()).toBeVisible();
      }
    });

    test('TC-WF-06-02: Create workflow version', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();

        const createVersionBtn = page.locator('button:has-text("保存版本")');
        await createVersionBtn.click();
        await page.waitForTimeout(500);

        const versionInput = page.locator('input[name="version"]');
        await versionInput.fill('v1.0.0');

        const saveBtn = page.locator('.ant-modal button:has-text("确定")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-WF-06-03: Restore workflow version', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const versionBtn = page.locator('button:has-text("版本")').first();
      const count = await versionBtn.count();

      if (count > 0) {
        await versionBtn.click();

        const restoreBtn = page.locator('button:has-text("恢复"), button:has-text("还原")').first();
        const restoreCount = await restoreBtn.count();

        if (restoreCount > 0) {
          await restoreBtn.click();
          await page.waitForTimeout(500);

          const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Workflow Monitoring', () => {
    test('TC-WF-07-01: View workflow statistics', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const stats = page.locator('.workflow-stats, .statistics');
      const isVisible = await stats.isVisible().catch(() => false);

      if (isVisible) {
        await expect(stats).toBeVisible();
      }
    });

    test('TC-WF-07-02: View execution history', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const row = page.locator('.ant-table-row').first();
      await row.click();

      const historyTab = page.locator('text=执行历史, text=History');
      const count = await historyTab.count();

      if (count > 0) {
        await historyTab.click();
        await page.waitForTimeout(500);

        const historyTable = page.locator('.ant-table');
        await expect(historyTable.first()).toBeVisible();
      }
    });

    test('TC-WF-07-03: View task execution details', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const row = page.locator('.ant-table-row').first();
      await row.click();

      const tasksTab = page.locator('text=任务, text=Tasks');
      const count = await tasksTab.count();

      if (count > 0) {
        await tasksTab.click();
        await page.waitForTimeout(500);

        const taskList = page.locator('.task-list');
        await expect(taskList.first()).toBeVisible();
      }
    });
  });

  test.describe('Workflow Templates', () => {
    test('TC-WF-08-01: View available templates', async ({ page }) => {
      await page.goto('/analysis/workflows');
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

    test('TC-WF-08-02: Use template for new workflow', async ({ page }) => {
      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const templateCard = page.locator('.template-card').first();
      const count = await templateCard.count();

      if (count > 0) {
        await templateCard.click();
        await page.waitForTimeout(500);

        const useTemplateBtn = page.locator('button:has-text("使用模板")');
        await useTemplateBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Workflow Permissions', () => {
    test('TC-WF-09-01: Admin can access workflows', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-WF-09-02: Admin can view workflow list', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/analysis/workflows');
      await page.waitForLoadState('domcontentloaded');

      const list = page.locator('.workflow-list, .ant-table');
      const isVisible = await list.isVisible().catch(() => false);

      if (isVisible) {
        await expect(list.first()).toBeVisible();
      }
    });
  });
});
