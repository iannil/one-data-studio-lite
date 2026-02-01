/**
 * Base Page class for Playwright E2E tests
 * Provides common functionality for all page objects
 */

import { Page, Locator, expect } from '@playwright/test';
import { TIMEOUTS } from '@utils/constants';
import { wait } from '@utils/helpers';

/**
 * Base page class with common methods
 */
export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Navigate to a URL
   */
  async goto(path: string): Promise<void> {
    await this.page.goto(path, { waitUntil: 'domcontentloaded' });
    await this.waitForLoadComplete();
  }

  /**
   * Wait for page to load completely
   */
  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Wait for page load to complete (alias to avoid recursion)
   */
  async waitForLoadComplete(): Promise<void> {
    try {
      await this.page.waitForLoadState('domcontentloaded', { timeout: 10000 });
    } catch {
      // Page might already be loaded
    }
  }

  /**
   * Wait for network to be idle
   */
  async waitForNetworkIdle(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Wait for loading spinner to disappear
   */
  async waitForLoading(): Promise<void> {
    try {
      const spin = this.page.locator('.ant-spin, .loading, [data-testid="loading"]');
      await spin.waitFor({ state: 'detached', timeout: TIMEOUTS.DEFAULT });
    } catch {
      // Loading might not be present
    }
  }

  /**
   * Take a screenshot
   */
  async screenshot(filename: string): Promise<void> {
    await this.page.screenshot({
      path: `test-results/screenshots/${filename}`,
      fullPage: true,
    });
  }

  /**
   * Get error message from the page
   */
  async getErrorMessage(): Promise<string | null> {
    const errorLocator = this.page.locator('.ant-message-error, .error-message, [data-testid="error"]');
    const isVisible = await errorLocator.first().isVisible().catch(() => false);
    if (isVisible) {
      return await errorLocator.first().textContent();
    }
    return null;
  }

  /**
   * Get success message from the page
   */
  async getSuccessMessage(): Promise<string | null> {
    const successLocator = this.page.locator('.ant-message-success, .success-message, [data-testid="success"]');
    const isVisible = await successLocator.first().isVisible().catch(() => false);
    if (isVisible) {
      return await successLocator.first().textContent();
    }
    return null;
  }

  /**
   * Wait for message to appear and return it
   */
  async waitForMessage(type: 'success' | 'error' | 'warning' | 'info' = 'success'): Promise<string> {
    const selector = `.ant-message-${type}`;
    const locator = this.page.locator(selector);
    await locator.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    return (await locator.textContent()) || '';
  }

  /**
   * Click an element and wait for navigation
   */
  async clickAndWaitForNavigation(selector: string | Locator): Promise<void> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    await Promise.all([
      this.page.waitForLoadState('domcontentloaded'),
      locator.click(),
    ]);
  }

  /**
   * Fill an input field
   */
  async fillInput(selector: string | Locator, value: string): Promise<void> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    await locator.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await locator.clear();
    await locator.fill(value);
    await wait(100); // Small delay to ensure value is set
  }

  /**
   * Select an option from a select dropdown
   */
  async selectOption(selector: string | Locator, option: string): Promise<void> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    await locator.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await locator.click();
    const optionLocator = this.page.locator(`.ant-select-dropdown-option:has-text("${option}")`);
    await optionLocator.click();
  }

  /**
   * Check if an element is visible
   */
  async isElementVisible(selector: string | Locator): Promise<boolean> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    try {
      return await locator.isVisible({ timeout: TIMEOUTS.SHORT });
    } catch {
      return false;
    }
  }

  /**
   * Check if an element exists in DOM
   */
  async isElementPresent(selector: string | Locator): Promise<boolean> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    const count = await locator.count();
    return count > 0;
  }

  /**
   * Wait for element to be visible
   */
  async waitForElement(selector: string | Locator, timeout?: number): Promise<Locator> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    await locator.waitFor({ state: 'visible', timeout: timeout || TIMEOUTS.DEFAULT });
    return locator;
  }

  /**
   * Wait for element to be hidden
   */
  async waitForElementHidden(selector: string | Locator, timeout?: number): Promise<void> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : locator;
    await locator.waitFor({ state: 'hidden', timeout: timeout || TIMEOUTS.DEFAULT });
  }

  /**
   * Click a button by text
   */
  async clickButton(buttonText: string): Promise<void> {
    const button = this.page.locator(`.ant-btn:has-text("${buttonText}"), button:has-text("${buttonText}")`);
    await button.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await button.click();
  }

  /**
   * Click a primary button
   */
  async clickPrimaryButton(): Promise<void> {
    const button = this.page.locator('.ant-btn-primary');
    await button.first().click();
  }

  /**
   * Get table row count
   */
  async getTableRowCount(tableSelector: string = '.ant-table'): Promise<number> {
    const table = this.page.locator(tableSelector);
    const rows = table.locator('.ant-table-tbody .ant-table-row');
    return await rows.count();
  }

  /**
   * Get cell text from table
   */
  async getTableCellText(row: number, col: number): Promise<string> {
    const cell = this.page.locator(
      `.ant-table-tbody .ant-table-row:nth-child(${row}) .ant-table-cell:nth-child(${col})`
    );
    return (await cell.textContent()) || '';
  }

  /**
   * Wait for table to load
   */
  async waitForTable(tableSelector: string = '.ant-table'): Promise<void> {
    const table = this.page.locator(tableSelector);
    await table.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await this.waitForLoading();
  }

  /**
   * Reload the current page
   */
  async reload(): Promise<void> {
    await this.page.reload({ waitUntil: 'domcontentloaded' });
    await this.waitForPageLoad();
  }

  /**
   * Get current URL
   */
  getCurrentUrl(): string {
    return this.page.url();
  }

  /**
   * Check if current URL matches a path
   */
  isUrlPath(path: string): boolean {
    const url = new URL(this.getCurrentUrl());
    return url.pathname === path;
  }

  /**
   * Wait for URL to match a pattern
   */
  async waitForUrl(pattern: string | RegExp): Promise<void> {
    await this.page.waitForURL(pattern, { timeout: TIMEOUTS.NAVIGATION });
  }

  /**
   * Hover over an element
   */
  async hover(selector: string | Locator): Promise<void> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    await locator.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await locator.hover();
  }

  /**
   * Upload a file
   */
  async uploadFile(selector: string | Locator, filePath: string): Promise<void> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    await locator.setInputFiles(filePath);
  }

  /**
   * Execute JavaScript in the page
   */
  async evaluate<R>(fn: () => R): Promise<R> {
    return await this.page.evaluate(fn);
  }

  /**
   * Get local storage value
   */
  async getLocalStorageItem(key: string): Promise<string | null> {
    return await this.page.evaluate((k) => {
      return localStorage.getItem(k);
    }, key);
  }

  /**
   * Set local storage value
   */
  async setLocalStorageItem(key: string, value: string): Promise<void> {
    await this.page.evaluate(({ k, v }) => {
      localStorage.setItem(k, v);
    }, { k: key, v: value });
  }

  /**
   * Clear local storage
   */
  async clearLocalStorage(): Promise<void> {
    await this.page.evaluate(() => {
      localStorage.clear();
    });
  }

  /**
   * Get session storage value
   */
  async getSessionStorageItem(key: string): Promise<string | null> {
    return await this.page.evaluate((k) => {
      return sessionStorage.getItem(k);
    }, key);
  }

  /**
   * Set session storage value
   */
  async setSessionStorageItem(key: string, value: string): Promise<void> {
    await this.page.evaluate(({ k, v }) => {
      sessionStorage.setItem(k, v);
    }, { k: key, v: value });
  }

  /**
   * Get a cookie by name
   */
  async getCookie(name: string): Promise<string | undefined> {
    const cookies = await this.page.context().cookies();
    const cookie = cookies.find(c => c.name === name);
    return cookie?.value;
  }

  /**
   * Verify page title
   */
  async verifyPageTitle(title: string): Promise<void> {
    await expect(this.page).toHaveTitle(new RegExp(title));
  }

  /**
   * Verify URL contains path
   */
  async verifyUrlPath(path: string): Promise<void> {
    await expect(this.page).toHaveURL(new RegExp(path));
  }
}
