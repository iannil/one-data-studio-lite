/**
 * Planning and Metadata E2E Tests
 *
 * Tests for data planning, metadata management, and related features
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';

test.describe('Planning Tests', { tag: ['@planning', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Data Sources Management', () => {
    test('TC-PLAN-01-01: Can navigate to data sources page', async ({ page }) => {
      await page.goto('/planning/datasources');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/planning/datasources');
    });

    test('TC-PLAN-01-02: Data sources page loads without errors', async ({ page }) => {
      await page.goto('/planning/datasources');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check page content exists
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);
    });

    test('TC-PLAN-01-03: Data sources has table or content area', async ({ page }) => {
      await page.goto('/planning/datasources');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for table or content
      const table = page.locator('.ant-table');
      const hasTable = await table.count() > 0;

      const content = page.locator('.ant-card');
      const hasContent = await content.count() > 0;

      expect(hasTable || hasContent).toBe(true);
    });
  });

  test.describe('Metadata Browser', () => {
    test('TC-PLAN-02-01: Can navigate to metadata browser', async ({ page }) => {
      await page.goto('/planning/metadata');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/planning/metadata');
    });

    test('TC-PLAN-02-02: Metadata page loads successfully', async ({ page }) => {
      await page.goto('/planning/metadata');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for any content
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);
    });
  });

  test.describe('Tags Management', () => {
    test('TC-PLAN-03-01: Can navigate to tags page', async ({ page }) => {
      await page.goto('/planning/tags');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/planning/tags');
    });

    test('TC-PLAN-03-02: Tags page loads without errors', async ({ page }) => {
      await page.goto('/planning/tags');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for content
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);
    });
  });

  test.describe('Data Standards', () => {
    test('TC-PLAN-04-01: Can navigate to standards page', async ({ page }) => {
      await page.goto('/planning/standards');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/planning/standards');
    });

    test('TC-PLAN-04-02: Standards page has table', async ({ page }) => {
      await page.goto('/planning/standards');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for table
      const table = page.locator('.ant-table');
      const tableCount = await table.count();

      // Standards page should have a table
      expect(tableCount).toBeGreaterThan(0);
    });
  });

  test.describe('Data Lineage', () => {
    test('TC-PLAN-05-01: Can navigate to lineage page', async ({ page }) => {
      await page.goto('/planning/lineage');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/planning/lineage');
    });

    test('TC-PLAN-05-02: Lineage page loads', async ({ page }) => {
      await page.goto('/planning/lineage');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for content
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);
    });
  });
});

test.describe('Assets Tests', { tag: ['@assets', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Assets Catalog', () => {
    test('TC-ASSET-01-01: Can navigate to assets catalog', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/assets/catalog');
    });

    test('TC-ASSET-01-02: Catalog page loads', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for content
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);
    });
  });

  test.describe('Assets Search', () => {
    test('TC-ASSET-02-01: Can navigate to assets search', async ({ page }) => {
      await page.goto('/assets/search');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/assets/search');
    });

    test('TC-ASSET-02-02: Search page has search input', async ({ page }) => {
      await page.goto('/assets/search');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for search input
      const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"], .ant-input-search');
      const hasSearch = await searchInput.count() > 0;

      expect(hasSearch).toBe(true);
    });
  });
});

test.describe('Development Tests', { tag: ['@development', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Cleaning Rules', () => {
    test('TC-DEV-01-01: Can navigate to cleaning rules page', async ({ page }) => {
      await page.goto('/development/cleaning');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/development/cleaning');
    });

    test('TC-DEV-01-02: Cleaning page loads', async ({ page }) => {
      await page.goto('/development/cleaning');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for content
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);
    });
  });

  test.describe('Quality Check', () => {
    test('TC-DEV-02-01: Can navigate to quality check page', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/development/quality');
    });

    test('TC-DEV-02-02: Quality check page loads', async ({ page }) => {
      await page.goto('/development/quality');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for content
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);
    });
  });

  test.describe('Field Mapping', () => {
    test('TC-DEV-03-01: Can navigate to field mapping page', async ({ page }) => {
      await page.goto('/development/field-mapping');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toContain('/development/field-mapping');
    });

    test('TC-DEV-03-02: Field mapping page loads', async ({ page }) => {
      await page.goto('/development/field-mapping');
      await page.waitForLoadState('domcontentloaded');

      // Wait for page to render
      await page.waitForTimeout(1000);

      // Check for content
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);
    });
  });
});
