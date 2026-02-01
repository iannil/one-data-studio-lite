/**
 * NL2SQL Page Object Model
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * NL2SQL Page class
 */
export class NL2SQLPage extends BasePage {
  // Selectors
  private readonly container = '[data-testid="nl2sql-page"], .nl2sql-page';
  private readonly queryInput = '[data-testid="nl2sql-input"], textarea.query-input';
  private readonly submitButton = '[data-testid="nl2sql-submit"], button.submit-button';
  private readonly resultArea = '[data-testid="nl2sql-result"], .query-result';
  private readonly sqlOutput = '[data-testid="nl2sql-sql"], .sql-output';
  private readonly tableResult = '.ant-table, .result-table';
  private readonly historyPanel = '[data-testid="query-history"], .query-history';
  private readonly saveButton = 'button:has-text("保存"), button:has-text("Save")';
  private readonly exportButton = 'button:has-text("导出"), button:has-text("Export")';
  private readonly clearButton = 'button:has-text("清空"), button:has-text("Clear")';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to NL2SQL page
   */
  async goto(): Promise<void> {
    await super.goto('/analysis/nl2sql');
  }

  /**
   * Wait for NL2SQL page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.waitForElement(this.container);
    await this.waitForLoading();
  }

  /**
   * Fill in natural language query
   */
  async fillQuery(query: string): Promise<void> {
    await this.fillInput(this.queryInput, query);
  }

  /**
   * Submit the query
   */
  async submitQuery(): Promise<void> {
    const button = this.page.locator(this.submitButton);
    await button.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await button.click();
    await this.waitForLoading();
  }

  /**
   * Execute a query (fill and submit)
   */
  async executeQuery(query: string): Promise<void> {
    await this.fillQuery(query);
    await this.submitQuery();
  }

  /**
   * Get generated SQL
   */
  async getGeneratedSQL(): Promise<string> {
    const sqlElement = this.page.locator(this.sqlOutput);
    const isVisible = await sqlElement.isVisible().catch(() => false);

    if (isVisible) {
      return (await sqlElement.textContent()) || '';
    }
    return '';
  }

  /**
   * Get result table row count
   */
  async getResultRowCount(): Promise<number> {
    const table = this.page.locator(this.tableResult);
    const isVisible = await table.isVisible().catch(() => false);

    if (isVisible) {
      const rows = table.locator('.ant-table-tbody .ant-table-row');
      return await rows.count();
    }
    return 0;
  }

  /**
   * Get cell text from results
   */
  async getResultCellText(row: number, col: number): Promise<string> {
    const cell = this.page.locator(
      `.ant-table-tbody .ant-table-row:nth-child(${row}) .ant-table-cell:nth-child(${col})`
    );
    return (await cell.textContent()) || '';
  }

  /**
   * Check if results are displayed
   */
  async hasResults(): Promise<boolean> {
    const result = this.page.locator(this.resultArea);
    const isVisible = await result.isVisible().catch(() => false);
    return isVisible;
  }

  /**
   * Get query result message
   */
  async getResultMessage(): Promise<string> {
    const message = this.page.locator('.ant-message, .query-message');
    const text = await message.textContent();
    return text || '';
  }

  /**
   * Save the current query
   */
  async saveQuery(): Promise<void> {
    const saveBtn = this.page.locator(this.saveButton);
    const isVisible = await saveBtn.isVisible().catch(() => false);

    if (isVisible) {
      await saveBtn.click();
    }
  }

  /**
   * Export results
   */
  async exportResults(): Promise<void> {
    const exportBtn = this.page.locator(this.exportButton);
    const isVisible = await exportBtn.isVisible().catch(() => false);

    if (isVisible) {
      await exportBtn.click();
    }
  }

  /**
   * Clear query input
   */
  async clearQuery(): Promise<void> {
    const clearBtn = this.page.locator(this.clearButton);
    const isVisible = await clearBtn.isVisible().catch(() => false);

    if (isVisible) {
      await clearBtn.click();
    } else {
      // Fallback: clear the input directly
      const input = this.page.locator(this.queryInput);
      await input.fill('');
    }
  }

  /**
   * Click on history item
   */
  async clickHistoryItem(index: number): Promise<void> {
    const historyItem = this.page.locator('.history-item, .query-history-item').nth(index);
    await historyItem.click();
  }

  /**
   * Get history item count
   */
  async getHistoryItemCount(): Promise<number> {
    const historyItems = this.page.locator('.history-item, .query-history-item');
    return await historyItems.count();
  }

  /**
   * Verify SQL is displayed
   */
  async verifySQLDisplayed(): Promise<void> {
    const sql = this.page.locator(this.sqlOutput);
    await expect(sql.first()).toBeVisible();
  }

  /**
   * Verify results table is displayed
   */
  async verifyResultsTableDisplayed(): Promise<void> {
    const table = this.page.locator(this.tableResult);
    await expect(table.first()).toBeVisible();
  }

  /**
   * Wait for query to complete
   */
  async waitForQueryCompletion(): Promise<void> {
    await this.waitForLoading();
    // Additional wait for async operations
    await this.page.waitForTimeout(2000);
  }

  /**
   * Get execution time
   */
  async getExecutionTime(): Promise<string | null> {
    const timeElement = this.page.locator('.execution-time, .query-time');
    const isVisible = await timeElement.isVisible().catch(() => false);

    if (isVisible) {
      return await timeElement.textContent();
    }
    return null;
  }

  /**
   * Get row count indicator
   */
  async getRowCountIndicator(): Promise<string | null> {
    const countElement = this.page.locator('text=/\\d+ 条|/\\d+ rows/');
    const isVisible = await countElement.isVisible().catch(() => false);

    if (isVisible) {
      return await countElement.textContent();
    }
    return null;
  }
}
