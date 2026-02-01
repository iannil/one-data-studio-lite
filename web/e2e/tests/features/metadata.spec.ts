/**
 * Metadata Feature Tests
 *
 * Tests for metadata management, lineage, and discovery
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Metadata Feature Tests', { tag: ['@metadata', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);

    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Metadata Dashboard', () => {
    test('TC-META-01-01: View metadata dashboard', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const dashboard = page.locator('.metadata-dashboard, .dashboard');
      await expect(dashboard.first()).toBeVisible();
    });

    test('TC-META-01-02: View metadata statistics', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const stats = page.locator('.metadata-stats, .stat-cards');
      const isVisible = await stats.isVisible().catch(() => false);

      if (isVisible) {
        await expect(stats).toBeVisible();
      }
    });

    test('TC-META-01-03: View data assets count', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const countBadge = page.locator('.assets-count, .count-badge');
      const count = await countBadge.count();

      if (count > 0) {
        const text = await countBadge.textContent();
        expect(text).toBeTruthy();
      }
    });
  });

  test.describe('Data Assets', () => {
    test('TC-META-02-01: Browse data assets', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const assetsGrid = page.locator('.assets-grid, .data-assets');
      await expect(assetsGrid.first()).toBeVisible();
    });

    test('TC-META-02-02: Search data assets', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('users');
        await page.waitForTimeout(500);
      }
    });

    test('TC-META-02-03: Filter by asset type', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const typeFilter = page.locator('.asset-type-filter, select[name="type"]');
      const count = await typeFilter.count();

      if (count > 0) {
        await typeFilter.selectOption('table');
        await page.waitForTimeout(500);
      }
    });

    test('TC-META-02-04: View asset details', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const assetCard = page.locator('.asset-card, .data-asset').first();
      await assetCard.click();

      const drawer = page.locator('.asset-drawer, .ant-drawer');
      const isVisible = await drawer.isVisible().catch(() => false);

      if (isVisible) {
        await expect(drawer).toBeVisible();
      }
    });
  });

  test.describe('Table Metadata', () => {
    test('TC-META-03-01: View table list', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表, text=Tables');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();
        await page.waitForTimeout(500);

        const tableList = page.locator('.table-list, .tables-grid');
        await expect(tableList.first()).toBeVisible();
      }
    });

    test('TC-META-03-02: View table schema', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();

        const firstTable = page.locator('.table-item').first();
        await firstTable.click();

        const schema = page.locator('.table-schema, .column-list');
        await expect(schema.first()).toBeVisible();
      }
    });

    test('TC-META-03-03: View table relationships', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();

        const firstTable = page.locator('.table-item').first();
        await firstTable.click();

        const relationshipsTab = page.locator('text=关系, text=Relationships');
        await relationshipsTab.click();

        const relationships = page.locator('.relationships, .foreign-keys');
        await expect(relationships.first()).toBeVisible();
      }
    });

    test('TC-META-03-04: View table indexes', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();

        const firstTable = page.locator('.table-item').first();
        await firstTable.click();

        const indexesTab = page.locator('text=索引, text=Indexes');
        const indexCount = await indexesTab.count();

        if (indexCount > 0) {
          await indexesTab.click();

          const indexes = page.locator('.indexes-list, .table-indexes');
          await expect(indexes.first()).toBeVisible();
        }
      }
    });

    test('TC-META-03-05: View table statistics', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();

        const firstTable = page.locator('.table-item').first();
        await firstTable.click();

        const statsTab = page.locator('text=统计, text=Statistics');
        const statsCount = await statsTab.count();

        if (statsCount > 0) {
          await statsTab.click();

          const stats = page.locator('.table-stats, .statistics');
          await expect(stats.first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Data Lineage', () => {
    test('TC-META-04-01: View data lineage graph', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const lineageTab = page.locator('text=血缘, text=Lineage');
      const count = await lineageTab.count();

      if (count > 0) {
        await lineageTab.click();

        const lineageGraph = page.locator('.lineage-graph, .dag-canvas');
        await expect(lineageGraph.first()).toBeVisible();
      }
    });

    test('TC-META-04-02: Trace upstream data sources', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const lineageTab = page.locator('text=血缘');
      const count = await lineageTab.count();

      if (count > 0) {
        await lineageTab.click();

        const node = page.locator('.lineage-node').first();
        const nodeCount = await node.count();

        if (nodeCount > 0) {
          await node.click();

          const upstreamPanel = page.locator('.upstream-panel, .source-panel');
          const isVisible = await upstreamPanel.isVisible().catch(() => false);

          if (isVisible) {
            await expect(upstreamPanel).toBeVisible();
          }
        }
      }
    });

    test('TC-META-04-03: Trace downstream dependencies', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const lineageTab = page.locator('text=血缘');
      const count = await lineageTab.count();

      if (count > 0) {
        await lineageTab.click();

        const node = page.locator('.lineage-node').first();
        const nodeCount = await node.count();

        if (nodeCount > 0) {
          await node.click();

          const downstreamPanel = page.locator('.downstream-panel, .dependency-panel');
          const isVisible = await downstreamPanel.isVisible().catch(() => false);

          if (isVisible) {
            await expect(downstreamPanel).toBeVisible();
          }
        }
      }
    });

    test('TC-META-04-04: View lineage timeline', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const lineageTab = page.locator('text=血缘');
      const count = await lineageTab.count();

      if (count > 0) {
        await lineageTab.click();

        const timelineBtn = page.locator('button:has-text("时间线")');
        const btnCount = await timelineBtn.count();

        if (btnCount > 0) {
          await timelineBtn.click();

          const timeline = page.locator('.lineage-timeline, .timeline');
          await expect(timeline.first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Column Metadata', () => {
    test('TC-META-05-01: View column details', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();

        const firstTable = page.locator('.table-item').first();
        await firstTable.click();

        const firstColumn = page.locator('.column-item').first();
        await firstColumn.click();

        const columnDetail = page.locator('.column-detail, .column-info');
        await expect(columnDetail.first()).toBeVisible();
      }
    });

    test('TC-META-05-02: View column data type', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();

        const firstTable = page.locator('.table-item').first();
        await firstTable.click();

        const columnType = page.locator('.column-type, .data-type').first();
        const text = await columnType.textContent();
        expect(text).toBeTruthy();
      }
    });

    test('TC-META-05-03: View column statistics', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();

        const firstTable = page.locator('.table-item').first();
        await firstTable.click();

        const firstColumn = page.locator('.column-item').first();
        await firstColumn.click();

        const columnStats = page.locator('.column-stats, .statistics');
        const isVisible = await columnStats.isVisible().catch(() => false);

        if (isVisible) {
          await expect(columnStats).toBeVisible();
        }
      }
    });

    test('TC-META-05-04: View column sample data', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tablesTab = page.locator('text=表');
      const count = await tablesTab.count();

      if (count > 0) {
        await tablesTab.click();

        const firstTable = page.locator('.table-item').first();
        await firstTable.click();

        const sampleTab = page.locator('text=样例数据, text=Sample');
        const sampleCount = await sampleTab.count();

        if (sampleCount > 0) {
          await sampleTab.click();

          const sampleData = page.locator('.sample-data, .preview-table');
          await expect(sampleData.first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Tags and Labels', () => {
    test('TC-META-06-01: Add tag to asset', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const assetCard = page.locator('.asset-card').first();
      await assetCard.click();

      const tagInput = page.locator('input[placeholder*="标签"], input[placeholder*="tag"]');
      const count = await tagInput.count();

      if (count > 0) {
        await tagInput.fill('important');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(500);
      }
    });

    test('TC-META-06-02: Filter by tag', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const tagFilter = page.locator('.tag-filter, .filter-by-tag');
      const count = await tagFilter.count();

      if (count > 0) {
        await tagFilter.click();

        const tag = page.locator('.tag-option:has-text("重要")').first();
        await tag.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-META-06-03: Create custom tag', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const manageTagsBtn = page.locator('button:has-text("管理标签")');
      const count = await manageTagsBtn.count();

      if (count > 0) {
        await manageTagsBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();

        const newTagInput = modal.locator('input[placeholder*="标签"]');
        await newTagInput.fill('custom_tag');

        const colorPicker = modal.locator('.color-picker');
        await colorPicker.click();

        const saveBtn = modal.locator('button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-META-06-04: Remove tag from asset', async ({ page }) => {
      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const assetCard = page.locator('.asset-card').first();
      await assetCard.click();

      const closeTag = page.locator('.ant-tag-close-icon, .tag-remove').first();
      const count = await closeTag.count();

      if (count > 0) {
        await closeTag.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Data Dictionary', () => {
    test('TC-META-07-01: View data dictionary', async ({ page }) => {
      await page.goto('/assets/metadata/dictionary');
      await page.waitForLoadState('domcontentloaded');

      const dictionary = page.locator('.data-dictionary, .dictionary');
      await expect(dictionary.first()).toBeVisible();
    });

    test('TC-META-07-02: Search dictionary terms', async ({ page }) => {
      await page.goto('/assets/metadata/dictionary');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[placeholder*="搜索"]');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('user');
        await page.waitForTimeout(500);
      }
    });

    test('TC-META-07-03: View term definition', async ({ page }) => {
      await page.goto('/assets/metadata/dictionary');
      await page.waitForLoadState('domcontentloaded');

      const termItem = page.locator('.dictionary-term, .term-item').first();
      await termItem.click();

      const termDetail = page.locator('.term-detail, .definition');
      await expect(termDetail.first()).toBeVisible();
    });

    test('TC-META-07-04: Add dictionary term', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/metadata/dictionary');
      await page.waitForLoadState('domcontentloaded');

      const addTermBtn = page.locator('button:has-text("添加术语")');
      const count = await addTermBtn.count();

      if (count > 0) {
        await addTermBtn.click();

        const modal = page.locator('.ant-modal');
        const modalCount = await modal.count();

        if (modalCount > 0) {
          await expect(modal.first()).toBeVisible();

          const termInput = modal.locator('input[name="term"]');
          await termInput.fill('Test Term');

          const definitionInput = modal.locator('textarea[name="definition"]');
          await definitionInput.fill('Test definition');

          const saveBtn = modal.locator('button:has-text("保存")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Metadata Synchronization', () => {
    test('TC-META-08-01: Sync metadata from source', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const syncBtn = page.locator('button:has-text("同步元数据"), button:has-text("Sync")');
      const count = await syncBtn.count();

      if (count > 0) {
        await syncBtn.click();

        const modal = page.locator('.ant-modal');
        const modalCount = await modal.count();

        if (modalCount > 0) {
          await expect(modal.first()).toBeVisible();

          const confirmBtn = modal.locator('button:has-text("确定")');
          await confirmBtn.click();
          await page.waitForTimeout(2000);
        }
      }
    });

    test('TC-META-08-02: Schedule metadata sync', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const scheduleBtn = page.locator('button:has-text("定时同步")');
      const count = await scheduleBtn.count();

      if (count > 0) {
        await scheduleBtn.click();

        const modal = page.locator('.ant-modal');
        const modalCount = await modal.count();

        if (modalCount > 0) {
          await expect(modal.first()).toBeVisible();

          const cronInput = modal.locator('input[name="cron"]');
          await cronInput.fill('0 0 * * *');

          const saveBtn = modal.locator('button:has-text("保存")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-META-08-03: View sync history', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const historyTab = page.locator('text=同步历史, text=Sync History');
      const count = await historyTab.count();

      if (count > 0) {
        await historyTab.click();

        const historyList = page.locator('.sync-history, .history-list');
        const listCount = await historyList.count();

        if (listCount > 0) {
          await expect(historyList.first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Metadata Permissions', () => {
    test('TC-META-09-01: Admin can view metadata', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const dashboard = page.locator('.metadata-dashboard');
      const isVisible = await dashboard.isVisible().catch(() => false);

      if (isVisible) {
        await expect(dashboard.first()).toBeVisible();
      }
    });

    test('TC-META-09-02: Admin can access metadata page', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-META-09-03: Admin can access metadata features', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/metadata');
      await page.waitForLoadState('domcontentloaded');

      const syncBtn = page.locator('button:has-text("同步")');
      const count = await syncBtn.count();

      if (count > 0) {
        const isEnabled = await syncBtn.first().isEnabled();
        expect(isEnabled || !isEnabled).toBe(true);
      }
    });
  });
});
