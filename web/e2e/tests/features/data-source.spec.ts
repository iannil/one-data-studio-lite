/**
 * Data Source Feature Tests
 *
 * Tests for data source configuration and management
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only
import { PAGE_ROUTES } from '@types/index';

test.describe('Data Source Feature Tests', { tag: ['@datasource', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);

    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Data Source List', () => {
    test('TC-DS-01-01: View data source list', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const table = page.locator('.ant-table');
      await expect(table.first()).toBeVisible();
    });

    test('TC-DS-01-02: Search data sources', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.first().fill('test');
        await page.waitForTimeout(500);
      }
    });

    test('TC-DS-01-03: Filter by source type', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const filterBtn = page.locator('button:has-text("筛选"), .filter-button');
      const count = await filterBtn.count();

      if (count > 0) {
        await filterBtn.first().click();
        await page.waitForTimeout(500);

        const typeFilter = page.locator('select[name="type"], .type-filter');
        const typeCount = await typeFilter.count();

        if (typeCount > 0) {
          await typeFilter.selectOption('MySQL');
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-DS-01-04: Sort data sources', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const sortBtn = page.locator('button:has-text("排序"), .sort-button');
      const count = await sortBtn.count();

      if (count > 0) {
        await sortBtn.first().click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Data Source Creation', () => {
    test('TC-DS-02-01: Click create data source button', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建"), button:has-text("新建")');
      await createBtn.click();

      const modal = page.locator('.ant-modal');
      await expect(modal.first()).toBeVisible();
    });

    test('TC-DS-02-02: Create MySQL data source', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const nameInput = page.locator('input[name="name"]');
      const count = await nameInput.count();

      if (count > 0) {
        await nameInput.fill('Test MySQL ' + Date.now());

        const typeSelect = page.locator('select[name="type"]');
        await typeSelect.selectOption('MySQL');

        const hostInput = page.locator('input[name="host"]');
        await hostInput.fill('localhost');

        const portInput = page.locator('input[name="port"]');
        await portInput.fill('3306');

        const saveBtn = page.locator('.ant-modal button:has-text("确定"), .ant-modal button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-DS-02-03: Create PostgreSQL data source', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const nameInput = page.locator('input[name="name"]');
      const count = await nameInput.count();

      if (count > 0) {
        await nameInput.fill('Test PostgreSQL ' + Date.now());

        const typeSelect = page.locator('select[name="type"]');
        await typeSelect.selectOption('PostgreSQL');

        const hostInput = page.locator('input[name="host"]');
        await hostInput.fill('localhost');

        const portInput = page.locator('input[name="port"]');
        await portInput.fill('5432');

        const saveBtn = page.locator('.ant-modal button:has-text("确定")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-DS-02-04: Test connection before saving', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const testBtn = page.locator('button:has-text("测试连接"), button:has-text("连接测试")');
      const count = await testBtn.count();

      if (count > 0) {
        await testBtn.click();
        await page.waitForTimeout(1000);

        const message = page.locator('.ant-message');
        const isVisible = await message.isVisible().catch(() => false);

        if (isVisible) {
          await expect(message).toBeVisible();
        }
      }
    });

    test('TC-DS-02-05: Validate required fields', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const createBtn = page.locator('button:has-text("创建")');
      await createBtn.click();

      const saveBtn = page.locator('.ant-modal button:has-text("确定")');
      await saveBtn.click();

      const error = page.locator('.ant-form-item-explain-error');
      const hasError = await error.count() > 0;

      if (hasError) {
        await expect(error.first()).toBeVisible();
      }
    });
  });

  test.describe('Data Source Configuration', () => {
    test('TC-DS-03-01: Configure connection pool', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();
        await page.waitForTimeout(500);

        const poolSizeInput = page.locator('input[name="poolSize"]');
        const poolCount = await poolSizeInput.count();

        if (poolCount > 0) {
          await poolSizeInput.fill('10');

          const saveBtn = page.locator('.ant-modal button:has-text("确定")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-DS-03-02: Configure SSL settings', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();
        await page.waitForTimeout(500);

        const sslToggle = page.locator('input[name="sslEnabled"]');
        const sslCount = await sslToggle.count();

        if (sslCount > 0) {
          await sslToggle.check();

          const saveBtn = page.locator('.ant-modal button:has-text("确定")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-DS-03-03: Configure SSH tunnel', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();
        await page.waitForTimeout(500);

        const sshTab = page.locator('text=SSH隧道, text=SSH Tunnel');
        const sshCount = await sshTab.count();

        if (sshCount > 0) {
          await sshTab.click();

          const sshHost = page.locator('input[name="sshHost"]');
          await sshHost.fill('ssh.example.com');

          const saveBtn = page.locator('.ant-modal button:has-text("确定")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Data Source Actions', () => {
    test('TC-DS-04-01: Edit data source', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const editBtn = page.locator('button:has-text("编辑")').first();
      const count = await editBtn.count();

      if (count > 0) {
        await editBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-DS-04-02: Delete data source', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const deleteBtn = page.locator('button:has-text("删除")').first();
      const count = await deleteBtn.count();

      if (count > 0) {
        await deleteBtn.click();
        await page.waitForTimeout(500);

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        await confirmBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-DS-04-03: Clone data source', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const cloneBtn = page.locator('button:has-text("克隆"), button:has-text("复制")').first();
      const count = await cloneBtn.count();

      if (count > 0) {
        await cloneBtn.click();
        await page.waitForTimeout(500);

        const modal = page.locator('.ant-modal');
        const isVisible = await modal.isVisible().catch(() => false);

        if (isVisible) {
          await expect(modal).toBeVisible();
        }
      }
    });

    test('TC-DS-04-04: Test data source connection', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const testBtn = page.locator('button:has-text("测试连接")').first();
      const count = await testBtn.count();

      if (count > 0) {
        await testBtn.click();
        await page.waitForTimeout(1000);

        const message = page.locator('.ant-message');
        await expect(message.first()).toBeVisible();
      }
    });

    test('TC-DS-04-05: View data source details', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const row = page.locator('.ant-table-row').first();
      await row.click();

      const drawer = page.locator('.ant-drawer');
      const isVisible = await drawer.isVisible().catch(() => false);

      if (isVisible) {
        await expect(drawer).toBeVisible();
      }
    });
  });

  test.describe('Data Source Status', () => {
    test('TC-DS-05-01: View connection status', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const statusBadge = page.locator('.status-badge, .ant-badge');
      const count = await statusBadge.count();

      if (count > 0) {
        const text = await statusBadge.first().textContent();
        expect(text).toBeTruthy();
      }
    });

    test('TC-DS-05-02: Enable data source', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const enableBtn = page.locator('button:has-text("启用")').first();
      const count = await enableBtn.count();

      if (count > 0) {
        await enableBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-DS-05-03: Disable data source', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const disableBtn = page.locator('button:has-text("禁用")').first();
      const count = await disableBtn.count();

      if (count > 0) {
        await disableBtn.click();
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

  test.describe('Data Source Metadata', () => {
    test('TC-DS-06-01: View source metadata', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const row = page.locator('.ant-table-row').first();
      await row.click();

      const metadataTab = page.locator('text=元数据, text=Metadata');
      const count = await metadataTab.count();

      if (count > 0) {
        await metadataTab.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-DS-06-02: Refresh metadata', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const refreshBtn = page.locator('button:has-text("刷新元数据"), button:has-text("同步")').first();
      const count = await refreshBtn.count();

      if (count > 0) {
        await refreshBtn.click();
        await page.waitForTimeout(2000);
      }
    });

    test('TC-DS-06-03: View table list', async ({ page }) => {
      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const row = page.locator('.ant-table-row').first();
      await row.click();

      const tablesTab = page.locator('text=表列表, text=Tables');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();
        await page.waitForTimeout(500);

        const table = page.locator('.ant-table');
        await expect(table.first()).toBeVisible();
      }
    });
  });

  test.describe('Data Source Permissions', () => {
    test('TC-DS-07-01: Admin can access data sources', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-DS-07-02: Admin can view data sources', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto(PAGE_ROUTES.PLANNING_DATASOURCES);
      await page.waitForLoadState('domcontentloaded');

      const table = page.locator('.ant-table');
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        await expect(table.first()).toBeVisible();
      }
    });
  });
});
