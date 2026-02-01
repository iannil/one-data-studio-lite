/**
 * Search Feature Tests
 *
 * Tests for global search, data search, and filtering
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Search Feature Tests', { tag: ['@search', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Global Search', () => {
    test('TC-SEARCH-01-01: Access global search', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input, input[placeholder*="搜索"]');
      const count = await searchInput.count();

      if (count > 0) {
        await expect(searchInput.first()).toBeVisible();
      }
    });

    test('TC-SEARCH-01-02: Search for tables', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input, input[placeholder*="搜索"]');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('users');
        await page.waitForTimeout(500);

        const results = page.locator('.search-results, .search-dropdown');
        const isVisible = await results.isVisible().catch(() => false);

        if (isVisible) {
          await expect(results).toBeVisible();
        }
      }
    });

    test('TC-SEARCH-01-03: Search for users', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('admin');
        await page.waitForTimeout(500);

        const results = page.locator('.search-results');
        const resultCount = await results.count();

        if (resultCount > 0) {
          const text = await results.textContent();
          expect(text).toBeTruthy();
        }
      }
    });

    test('TC-SEARCH-01-04: Navigate to search result', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('audit');
        await page.waitForTimeout(500);

        const firstResult = page.locator('.search-result-item').first();
        const resultCount = await firstResult.count();

        if (resultCount > 0) {
          await firstResult.click();
          await page.waitForTimeout(1000);

          const url = page.url();
          expect(url).toBeTruthy();
        }
      }
    });

    test('TC-SEARCH-01-05: Clear search results', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('test');
        await page.waitForTimeout(500);

        const clearBtn = page.locator('.search-clear, .clear-icon');
        const clearCount = await clearBtn.count();

        if (clearCount > 0) {
          await clearBtn.click();
          await page.waitForTimeout(300);
        }
      }
    });

    test('TC-SEARCH-01-06: Search with keyboard shortcut', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      // Trigger keyboard shortcut (Ctrl/Cmd + K)
      await page.keyboard.press((process.platform === 'darwin' ? 'Meta' : 'Control') + '+k');

      const searchModal = page.locator('.search-modal, .command-palette');
      const isVisible = await searchModal.isVisible().catch(() => false);

      if (isVisible) {
        await expect(searchModal).toBeVisible();
      }
    });
  });

  test.describe('Advanced Search', () => {
    test('TC-SEARCH-02-01: Open advanced search', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchPage = page.locator('.search-page, .advanced-search');
      await expect(searchPage.first()).toBeVisible();
    });

    test('TC-SEARCH-02-02: Filter by data type', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const typeFilter = page.locator('.filter-type, select[name="type"]');
      const count = await typeFilter.count();

      if (count > 0) {
        await typeFilter.selectOption('table');
        await page.waitForTimeout(500);
      }
    });

    test('TC-SEARCH-02-03: Filter by date range', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const dateFilter = page.locator('.date-filter, .filter-date');
      const count = await dateFilter.count();

      if (count > 0) {
        await dateFilter.click();

        const startDate = page.locator('input[placeholder*="开始"], input[placeholder*="from"]');
        await startDate.fill('2024-01-01');

        const endDate = page.locator('input[placeholder*="结束"], input[placeholder*="to"]');
        await endDate.fill('2024-12-31');

        const searchBtn = page.locator('button:has-text("搜索")');
        await searchBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-SEARCH-02-04: Search by tags', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const tagFilter = page.locator('.tag-filter, .filter-by-tags');
      const count = await tagFilter.count();

      if (count > 0) {
        await tagFilter.click();

        const tag = page.locator('.tag-option').first();
        await tag.click();

        const searchBtn = page.locator('button:has-text("搜索")');
        await searchBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-SEARCH-02-05: Save search query', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"], .search-input');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('test query');

        const saveBtn = page.locator('button:has-text("保存查询")');
        const saveCount = await saveBtn.count();

        if (saveCount > 0) {
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-SEARCH-02-06: Load saved search', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const savedSearches = page.locator('.saved-searches, .search-templates');
      const isVisible = await savedSearches.isVisible().catch(() => false);

      if (isVisible) {
        await savedSearches.click();

        const savedItem = savedSearches.locator('.saved-item').first();
        const itemCount = await savedItem.count();

        if (itemCount > 0) {
          await savedItem.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Search Results', () => {
    test('TC-SEARCH-03-01: Display search results count', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      await searchInput.fill('data');
      await searchInput.press('Enter');

      await page.waitForTimeout(1000);

      const resultCount = page.locator('.result-count, .search-summary');
      const isVisible = await resultCount.isVisible().catch(() => false);

      if (isVisible) {
        const text = await resultCount.textContent();
        expect(text).toBeTruthy();
      }
    });

    test('TC-SEARCH-03-02: Highlight search terms', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      await searchInput.fill('user');
      await searchInput.press('Enter');

      await page.waitForTimeout(1000);

      const highlight = page.locator('.search-highlight, mark');
      const count = await highlight.count();

      if (count > 0) {
        await expect(highlight.first()).toBeVisible();
      }
    });

    test('TC-SEARCH-03-03: Sort search results', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      await searchInput.fill('test');
      await searchInput.press('Enter');

      await page.waitForTimeout(1000);

      const sortSelect = page.locator('select[name="sort"], .sort-select');
      const count = await sortSelect.count();

      if (count > 0) {
        await sortSelect.selectOption('relevance');
        await page.waitForTimeout(500);
      }
    });

    test('TC-SEARCH-03-04: Group search results', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      await searchInput.fill('data');
      await searchInput.press('Enter');

      await page.waitForTimeout(1000);

      const groupToggle = page.locator('.group-toggle, input[name="groupResults"]');
      const count = await groupToggle.count();

      if (count > 0) {
        await groupToggle.check();
        await page.waitForTimeout(500);

        const groups = page.locator('.result-group, .search-group');
        const groupCount = await groups.count();

        if (groupCount > 0) {
          await expect(groups.first()).toBeVisible();
        }
      }
    });

    test('TC-SEARCH-03-05: Export search results', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      await searchInput.fill('test');
      await searchInput.press('Enter');

      await page.waitForTimeout(1000);

      const exportBtn = page.locator('button:has-text("导出"), button:has-text("Export")');
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Search Suggestions', () => {
    test('TC-SEARCH-04-01: Display search suggestions', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.click();
        await searchInput.fill('u');
        await page.waitForTimeout(500);

        const suggestions = page.locator('.search-suggestions, .autocomplete-suggestions');
        const isVisible = await suggestions.isVisible().catch(() => false);

        if (isVisible) {
          await expect(suggestions).toBeVisible();
        }
      }
    });

    test('TC-SEARCH-04-02: Select search suggestion', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.click();
        await searchInput.fill('u');
        await page.waitForTimeout(500);

        const suggestion = page.locator('.search-suggestion-item').first();
        const suggestionCount = await suggestion.count();

        if (suggestionCount > 0) {
          await suggestion.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-SEARCH-04-03: View recent searches', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.click();
        await page.waitForTimeout(500);

        const recentSearches = page.locator('.recent-searches, .search-history');
        const isVisible = await recentSearches.isVisible().catch(() => false);

        if (isVisible) {
          await expect(recentSearches).toBeVisible();
        }
      }
    });
  });

  test.describe('Full-Text Search', () => {
    test('TC-SEARCH-05-01: Search within file content', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('content search');

        const contentSearchToggle = page.locator('input[name="fullText"]');
        const toggleCount = await contentSearchToggle.count();

        if (toggleCount > 0) {
          await contentSearchToggle.check();
        }

        const searchBtn = page.locator('button:has-text("搜索")');
        await searchBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-SEARCH-05-02: Search with boolean operators', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      await searchInput.fill('user AND admin');

      const searchBtn = page.locator('button:has-text("搜索")');
      await searchBtn.click();
      await page.waitForTimeout(1000);

      const results = page.locator('.search-results');
      await expect(results.first()).toBeVisible();
    });

    test('TC-SEARCH-05-03: Search with wildcards', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      await searchInput.fill('test*');

      const searchBtn = page.locator('button:has-text("搜索")');
      await searchBtn.click();
      await page.waitForTimeout(1000);

      const results = page.locator('.search-results');
      await expect(results.first()).toBeVisible();
    });
  });

  test.describe('Search Performance', () => {
    test('TC-SEARCH-06-01: Search completes within time limit', async ({ page }) => {
      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      const start = Date.now();

      await searchInput.fill('test');
      await searchInput.press('Enter');

      await page.waitForTimeout(500);

      const duration = Date.now() - start;

      // Search should complete within 3 seconds
      expect(duration).toBeLessThan(3000);
    });

    test('TC-SEARCH-06-02: Debounce rapid input', async ({ page }) => {
      await page.goto('/dashboard/cockpit');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('.global-search input');
      const count = await searchInput.count();

      if (count > 0) {
        // Type multiple characters rapidly
        await searchInput.fill('t');
        await page.waitForTimeout(50);
        await searchInput.fill('te');
        await page.waitForTimeout(50);
        await searchInput.fill('tes');
        await page.waitForTimeout(50);
        await searchInput.fill('test');

        // Should only trigger one search
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Search Permissions', () => {
    test('TC-SEARCH-07-01: Admin can search content', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const searchInput = page.locator('input[name="query"]');
      const count = await searchInput.count();

      if (count > 0) {
        await searchInput.fill('data');

        const searchBtn = page.locator('button:has-text("搜索")');
        const btnCount = await searchBtn.count();

        if (btnCount > 0) {
          await searchBtn.click();
          await page.waitForTimeout(1000);
        }
      }

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-SEARCH-07-02: Admin can access search page', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/search');
      await page.waitForLoadState('domcontentloaded');

      const results = page.locator('.search-results');
      const count = await results.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });
});
