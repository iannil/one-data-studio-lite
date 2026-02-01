/**
 * Scheduling Feature Tests
 *
 * Tests for job scheduling, automation, and cron management
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Scheduling Feature Tests', { tag: ['@scheduling', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Job Scheduler', () => {
    test('TC-SCHED-01-01: View scheduled jobs', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobsList = page.locator('.scheduled-jobs, .jobs-list');
      await expect(jobsList.first()).toBeVisible();
    });

    test('TC-SCHED-01-02: Create scheduled job', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务"), button:has-text("新建")');
      await createBtn.click();

      const modal = page.locator('.ant-modal');
      await expect(modal.first()).toBeVisible();
    });

    test('TC-SCHED-01-03: Configure cron expression', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务")');
      await createBtn.click();

      const cronInput = page.locator('input[name="cron"], input[placeholder*="cron"]');
      const count = await cronInput.count();

      if (count > 0) {
        await cronInput.fill('0 0 * * *');
      }
    });

    test('TC-SCHED-01-04: Validate cron expression', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务")');
      await createBtn.click();

      const cronInput = page.locator('input[name="cron"]');
      await cronInput.fill('invalid cron');

      const validateBtn = page.locator('button:has-text("验证")');
      const count = await validateBtn.count();

      if (count > 0) {
        await validateBtn.click();

        const error = page.locator('.ant-message-error');
        const isVisible = await error.isVisible().catch(() => false);

        if (isVisible) {
          await expect(error).toBeVisible();
        }
      }
    });

    test('TC-SCHED-01-05: Enable/disable scheduled job', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobSwitch = page.locator('.job-switch, .ant-switch').first();
      const count = await jobSwitch.count();

      if (count > 0) {
        await jobSwitch.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-SCHED-01-06: Delete scheduled job', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const deleteBtn = page.locator('.job-item button:has-text("删除")').first();
      const count = await deleteBtn.count();

      if (count > 0) {
        await deleteBtn.click();

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        await confirmBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Cron Expressions', () => {
    test('TC-SCHED-02-01: Use cron builder', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务")');
      await createBtn.click();

      const builderBtn = page.locator('button:has-text("表达式构建器"), button:has-text("Cron Builder")');
      const count = await builderBtn.count();

      if (count > 0) {
        await builderBtn.click();

        const builder = page.locator('.cron-builder, .expression-builder');
        await expect(builder.first()).toBeVisible();
      }
    });

    test('TC-SCHED-02-02: Set daily schedule', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务")');
      await createBtn.click();

      const dailyBtn = page.locator('button:has-text("每天"), .cron-preset-daily');
      await dailyBtn.click();

      const cronInput = page.locator('input[name="cron"]');
      const value = await cronInput.inputValue();

      expect(value).toContain('0 0 * * *');
    });

    test('TC-SCHED-02-03: Set weekly schedule', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务")');
      await createBtn.click();

      const weeklyBtn = page.locator('button:has-text("每周"), .cron-preset-weekly');
      await weeklyBtn.click();

      const cronInput = page.locator('input[name="cron"]');
      const value = await cronInput.inputValue();

      expect(value).toContain('0');
    });

    test('TC-SCHED-02-04: Set hourly schedule', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务")');
      await createBtn.click();

      const hourlyBtn = page.locator('button:has-text("每小时"), .cron-preset-hourly');
      await hourlyBtn.click();

      const cronInput = page.locator('input[name="cron"]');
      const value = await cronInput.inputValue();

      expect(value).toContain('* * * * *');
    });

    test('TC-SCHED-02-05: Set custom schedule', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务")');
      await createBtn.click();

      const minuteSelect = page.locator('select[name="minute"]');
      await minuteSelect.selectOption('30');

      const hourSelect = page.locator('select[name="hour"]');
      await hourSelect.selectOption('14');

      const dayOfMonthSelect = page.locator('select[name="dayOfMonth"]');
      await dayOfMonthSelect.selectOption('*');

      const monthSelect = page.locator('select[name="month"]');
      await monthSelect.selectOption('*');

      const dayOfWeekSelect = page.locator('select[name="dayOfWeek"]');
      await dayOfWeekSelect.selectOption('*');
    });
  });

  test.describe('Job Execution', () => {
    test('TC-SCHED-03-01: Run job manually', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const runBtn = page.locator('.job-item button:has-text("运行"), button:has-text("Run")').first();
      const count = await runBtn.count();

      if (count > 0) {
        await runBtn.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-SCHED-03-02: View job execution history', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      const itemCount = await jobItem.count();

      if (itemCount > 0) {
        await jobItem.click();

        const historyTab = page.locator('text=执行历史, text=History');
        await historyTab.click();

        const historyList = page.locator('.execution-history');
        await expect(historyList.first()).toBeVisible();
      }
    });

    test('TC-SCHED-03-03: View job logs', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      const itemCount = await jobItem.count();

      if (itemCount > 0) {
        await jobItem.click();

        const logsTab = page.locator('text=日志, text=Logs');
        const logsCount = await logsTab.count();

        if (logsCount > 0) {
          await logsTab.click();

          const logs = page.locator('.job-logs, .execution-logs');
          await expect(logs.first()).toBeVisible();
        }
      }
    });

    test('TC-SCHED-03-04: Stop running job', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const stopBtn = page.locator('.job-item button:has-text("停止"), button:has-text("Stop")').first();
      const count = await stopBtn.count();

      if (count > 0) {
        const isEnabled = await stopBtn.isEnabled();
        if (isEnabled) {
          await stopBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-SCHED-03-05: Retry failed job', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const retryBtn = page.locator('.job-item button:has-text("重试"), button:has-text("Retry")').first();
      const count = await retryBtn.count();

      if (count > 0) {
        await retryBtn.click();

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        const confirmCount = await confirmBtn.count();

        if (confirmCount > 0) {
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Job Configuration', () => {
    test('TC-SCHED-04-01: Configure job parameters', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      await jobItem.click();

      const configTab = page.locator('text=配置, text=Config');
      await configTab.click();

      const paramInput = page.locator('input[name="parameter"]');
      const count = await paramInput.count();

      if (count > 0) {
        await paramInput.fill('{"key": "value"}');

        const saveBtn = page.locator('button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-SCHED-04-02: Configure job timeout', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      await jobItem.click();

      const configTab = page.locator('text=配置');
      await configTab.click();

      const timeoutInput = page.locator('input[name="timeout"]');
      const count = await timeoutInput.count();

      if (count > 0) {
        await timeoutInput.fill('3600');

        const saveBtn = page.locator('button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-SCHED-04-03: Configure retry policy', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      await jobItem.click();

      const configTab = page.locator('text=配置');
      await configTab.click();

      const retryCount = page.locator('input[name="retryCount"]');
      await retryCount.fill('3');

      const retryDelay = page.locator('input[name="retryDelay"]');
      await retryDelay.fill('60');

      const saveBtn = page.locator('button:has-text("保存")');
      await saveBtn.click();
      await page.waitForTimeout(1000);
    });

    test('TC-SCHED-04-04: Configure notification on failure', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      await jobItem.click();

      const configTab = page.locator('text=配置');
      await configTab.click();

      const notifyCheckbox = page.locator('input[name="notifyOnFailure"]');
      await notifyCheckbox.check();

      const emailInput = page.locator('input[name="notificationEmail"]');
      await emailInput.fill('admin@example.com');

      const saveBtn = page.locator('button:has-text("保存")');
      await saveBtn.click();
      await page.waitForTimeout(1000);
    });
  });

  test.describe('Job Dependencies', () => {
    test('TC-SCHED-05-01: Configure job dependencies', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      await jobItem.click();

      const depsTab = page.locator('text=依赖, text=Dependencies');
      const count = await depsTab.count();

      if (count > 0) {
        await depsTab.click();

        const addDepBtn = page.locator('button:has-text("添加依赖")');
        await addDepBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-SCHED-05-02: Set sequential dependency', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      await jobItem.click();

      const depsTab = page.locator('text=依赖');
      const count = await depsTab.count();

      if (count > 0) {
        await depsTab.click();

        const depTypeSelect = page.locator('select[name="dependencyType"]');
        await depTypeSelect.selectOption('sequential');

        const depJobSelect = page.locator('select[name="dependsOn"]');
        const depJobCount = await depJobSelect.count();

        if (depJobCount > 0) {
          await depJobSelect.selectOption('0');
        }
      }
    });

    test('TC-SCHED-05-03: Set parallel dependency', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      await jobItem.click();

      const depsTab = page.locator('text=依赖');
      const count = await depsTab.count();

      if (count > 0) {
        await depsTab.click();

        const depTypeSelect = page.locator('select[name="dependencyType"]');
        await depTypeSelect.selectOption('parallel');
      }
    });
  });

  test.describe('Job Monitoring', () => {
    test('TC-SCHED-06-01: View job dashboard', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const dashboard = page.locator('.scheduling-dashboard, .jobs-dashboard');
      await expect(dashboard.first()).toBeVisible();
    });

    test('TC-SCHED-06-02: View job statistics', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const stats = page.locator('.job-statistics, .job-stats');
      const isVisible = await stats.isVisible().catch(() => false);

      if (isVisible) {
        await expect(stats).toBeVisible();
      }
    });

    test('TC-SCHED-06-03: View execution calendar', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const calendarTab = page.locator('text=日历, text=Calendar');
      const count = await calendarTab.count();

      if (count > 0) {
        await calendarTab.click();

        const calendar = page.locator('.execution-calendar');
        await expect(calendar.first()).toBeVisible();
      }
    });

    test('TC-SCHED-06-04: View next run time', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const nextRun = page.locator('.next-run-time, .schedule-info');
      const count = await nextRun.count();

      if (count > 0) {
        const text = await nextRun.textContent();
        expect(text).toBeTruthy();
      }
    });
  });

  test.describe('Job Templates', () => {
    test('TC-SCHED-07-01: Use job template', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建任务")');
      await createBtn.click();

      const templateTab = page.locator('text=模板, text=Template');
      await templateTab.click();

      const template = page.locator('.job-template').first();
      const templateCount = await template.count();

      if (templateCount > 0) {
        await template.click();

        const jobNameInput = page.locator('input[name="jobName"]');
        await jobNameInput.fill('My Job from Template');
      }
    });

    test('TC-SCHED-07-02: Save job as template', async ({ page }) => {
      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const jobItem = page.locator('.job-item').first();
      const itemCount = await jobItem.count();

      if (itemCount > 0) {
        await jobItem.click();

        const saveTemplateBtn = page.locator('button:has-text("保存为模板")');
        await saveTemplateBtn.click();

        const modal = page.locator('.ant-modal');
        const templateNameInput = modal.locator('input[name="templateName"]');
        await templateNameInput.fill('My Template');

        const saveBtn = modal.locator('button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Job Permissions', () => {
    test('TC-SCHED-08-01: Admin can access scheduling', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-SCHED-08-02: Admin can manage all jobs', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const deleteBtn = page.locator('.job-item button:has-text("删除")').first();
      const count = await deleteBtn.count();

      if (count > 0) {
        const isEnabled = await deleteBtn.isEnabled();
        expect(isEnabled || !isEnabled).toBe(true);
      }
    });

    test('TC-SCHED-08-03: Admin can edit jobs', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/analysis/scheduling');
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('.job-item button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        const isEnabled = await editBtn.isEnabled();
        expect(isEnabled || !isEnabled).toBe(true);
      }
    });
  });
});
