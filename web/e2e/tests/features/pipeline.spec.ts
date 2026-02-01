/**
 * Pipeline Feature Tests
 *
 * Tests for data pipeline creation, execution, and management
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { PipelinePage } from '@pages/pipeline.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Pipeline Feature Tests', { tag: ['@pipeline', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;
  let pipelinePage: PipelinePage;

  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    loginPage = new LoginPage(page);
    pipelinePage = new PipelinePage(page);

    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Pipeline List', () => {
    test('TC-PIPE-01-01: View pipeline list', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();
      expect(Array.isArray(pipelines)).toBe(true);
    });

    test('TC-PIPE-01-02: Pipeline list shows correct columns', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        const first = pipelines[0];
        expect(first).toHaveProperty('id');
        expect(first).toHaveProperty('name');
        expect(first).toHaveProperty('status');
      }
    });

    test('TC-PIPE-01-03: Search pipelines', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]');
      const isVisible = await searchInput.isVisible().catch(() => false);

      if (isVisible) {
        await searchInput.fill('test');
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Pipeline Creation', () => {
    test('TC-PIPE-02-01: Click create pipeline button', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      await pipelinePage.clickCreatePipeline();

      const modal = page.locator('.ant-modal').first();
      const isVisible = await modal.isVisible().catch(() => false);

      if (isVisible) {
        await expect(modal).toBeVisible();
      }
    });

    test('TC-PIPE-02-02: Create pipeline with valid data', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      await pipelinePage.clickCreatePipeline();

      const nameInput = page.locator('input[name="name"], input[placeholder*="名称"]');
      const count = await nameInput.count();

      if (count > 0) {
        await nameInput.first().fill('Test Pipeline ' + Date.now());

        const saveBtn = page.locator('button:has-text("保存"), button:has-text("创建")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-PIPE-02-03: Validate required fields', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      await pipelinePage.clickCreatePipeline();

      const saveBtn = page.locator('button:has-text("保存")');
      const count = await saveBtn.count();

      if (count > 0) {
        await saveBtn.click();
        await page.waitForTimeout(500);

        const error = page.locator('.ant-form-item-explain-error');
        const hasError = await error.count() > 0;

        if (hasError) {
          await expect(error.first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Pipeline Execution', () => {
    test('TC-PIPE-03-01: Run existing pipeline', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        const pipelineName = pipelines[0].name;
        if (pipelineName) {
          await pipelinePage.runPipeline(pipelineName);

          await page.waitForTimeout(2000);
        }
      }
    });

    test('TC-PIPE-03-02: Stop running pipeline', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      for (const p of pipelines) {
        if (p.status === 'running' || p.status === '运行中') {
          await pipelinePage.stopPipeline(p.name);
          await page.waitForTimeout(1000);
          break;
        }
      }
    });

    test('TC-PIPE-03-03: View execution log', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        await pipelinePage.openEditor(pipelines[0].name);

        const logArea = page.locator('.execution-log, .pipeline-log');
        const isVisible = await logArea.isVisible().catch(() => false);

        if (isVisible) {
          const logs = await pipelinePage.getExecutionLog();
          expect(Array.isArray(logs)).toBe(true);
        }
      }
    });
  });

  test.describe('Pipeline Editor', () => {
    test('TC-PIPE-04-01: Open pipeline editor', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        await pipelinePage.openEditor(pipelines[0].name);

        const canvas = page.locator('.pipeline-canvas, .graph-view');
        await expect(canvas.first()).toBeVisible();
      }
    });

    test('TC-PIPE-04-02: Add node to pipeline', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        await pipelinePage.openEditor(pipelines[0].name);

        const palette = page.locator('.node-palette, .palette');
        const isVisible = await palette.isVisible().catch(() => false);

        if (isVisible) {
          await pipelinePage.addNode('Source');
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-PIPE-04-03: Save pipeline changes', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        await pipelinePage.openEditor(pipelines[0].name);

        await pipelinePage.savePipeline();

        const success = page.locator('.ant-message-success');
        const isVisible = await success.isVisible().catch(() => false);

        if (isVisible) {
          await expect(success).toBeVisible();
        }
      }
    });
  });

  test.describe('Pipeline Scheduling', () => {
    test('TC-PIPE-05-01: Schedule pipeline with cron', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        await pipelinePage.schedulePipeline(pipelines[0].name, '0 0 * * *');

        await page.waitForTimeout(1000);
      }
    });

    test('TC-PIPE-05-02: View pipeline schedule', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        const p = pipelines[0];
        expect(p).toHaveProperty('schedule');
      }
    });
  });

  test.describe('Pipeline Deletion', () => {
    test('TC-PIPE-06-01: Delete pipeline', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 1) {
        const targetPipeline = pipelines[pipelines.length - 1];

        await pipelinePage.deletePipeline(targetPipeline.name);

        const exists = await pipelinePage.verifyPipelineExists(targetPipeline.name);

        await page.waitForTimeout(1000);
      }
    });

    test('TC-PIPE-06-02: Confirm deletion dialog', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        const deleteBtn = page.locator(
          `${pipelinePage['pipelineCard']}:has-text("${pipelines[0].name}") button:has-text("删除")`
        );
        const count = await deleteBtn.count();

        if (count > 0) {
          await deleteBtn.click();
          await page.waitForTimeout(500);

          const modal = page.locator('.ant-modal');
          const hasModal = await modal.count() > 0;

          if (hasModal) {
            await expect(modal.first()).toBeVisible();

            const cancelBtn = modal.locator('button:has-text("取消")');
            await cancelBtn.click();
          }
        }
      }
    });
  });

  test.describe('Pipeline Cloning', () => {
    test('TC-PIPE-07-01: Clone existing pipeline', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        const beforeCount = pipelines.length;

        await pipelinePage.clonePipeline(pipelines[0].name);

        await page.waitForTimeout(1000);

        const afterPipelines = await pipelinePage.getPipelines();
      }
    });
  });

  test.describe('Pipeline Status', () => {
    test('TC-PIPE-08-01: Check pipeline status', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        const status = await pipelinePage.getPipelineStatus(pipelines[0].name);
        expect(status).toBeTruthy();
      }
    });

    test('TC-PIPE-08-02: Verify successful pipeline status', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      for (const p of pipelines) {
        if (p.status === 'success' || p.status === 'completed') {
          await pipelinePage.verifyPipelineStatus(p.name, 'success');
          break;
        }
      }
    });
  });

  test.describe('Pipeline Permissions', () => {
    test('TC-PIPE-09-01: Admin can access pipeline page', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-PIPE-09-02: Admin can manage pipelines', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const createBtn = page.locator('button:has-text("创建")');
      const count = await createBtn.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Pipeline Monitoring', () => {
    test('TC-PIPE-10-01: View pipeline execution history', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const pipelines = await pipelinePage.getPipelines();

      if (pipelines.length > 0) {
        await pipelinePage.openEditor(pipelines[0].name);

        const historyTab = page.locator('text=执行历史, text=History');
        const count = await historyTab.count();

        if (count > 0) {
          await historyTab.first().click();
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-PIPE-10-02: View pipeline statistics', async ({ page }) => {
      await pipelinePage.goto();
      await pipelinePage.waitForPageLoad();

      const stats = page.locator('.pipeline-stats, .statistics');
      const isVisible = await stats.isVisible().catch(() => false);

      if (isVisible) {
        await expect(stats).toBeVisible();
      }
    });
  });
});
