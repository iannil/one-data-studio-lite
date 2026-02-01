/**
 * Audit Log Page Object Model
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Audit Log Page class
 */
export class AuditLogPage extends BasePage {
  // Selectors
  private readonly container = '[data-testid="audit-log-page"], .audit-log-page';
  private readonly table = '[data-testid="audit-log-table"], .audit-log-table';
  private readonly filterPanel = '[data-testid="audit-log-filter"], .filter-panel';
  private readonly searchInput = 'input[placeholder*="搜索"], .search-input';
  private readonly usernameFilter = 'select[name="username"], .username-filter';
  private readonly actionFilter = 'select[name="action"], .action-filter';
  private readonly dateRangePicker = '.ant-picker, .date-range-picker';
  private readonly exportButton = 'button:has-text("导出"), button:has-text("Export")';
  private readonly refreshButton = 'button:has-text("刷新"), button:has-text("Refresh")';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to audit log page
   */
  async goto(): Promise<void> {
    await super.goto('/operations/audit');
  }

  /**
   * Wait for audit log page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.waitForElement(this.container);
    await this.waitForLoading();
  }

  /**
   * Get table row count
   */
  async getLogRowCount(): Promise<number> {
    await this.waitForTable(this.table);
    const rows = this.page.locator(`${this.table} .ant-table-tbody .ant-table-row`);
    return await rows.count();
  }

  /**
   * Get cell text from specific row and column
   */
  async getCellText(row: number, col: number): Promise<string> {
    const cell = this.page.locator(
      `${this.table} .ant-table-tbody .ant-table-row:nth-child(${row}) .ant-table-cell:nth-child(${col})`
    );
    return (await cell.textContent()) || '';
  }

  /**
   * Search by username
   */
  async searchByUsername(username: string): Promise<void> {
    const searchInput = this.page.locator(this.searchInput);
    const count = await searchInput.count();

    if (count > 0) {
      await searchInput.first().fill(username);
      await this.page.waitForTimeout(500); // Debounce wait
    }
  }

  /**
   * Clear search
   */
  async clearSearch(): Promise<void> {
    const searchInput = this.page.locator(this.searchInput);
    const count = await searchInput.count();

    if (count > 0) {
      await searchInput.first().fill('');
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Filter by action type
   */
  async filterByAction(action: string): Promise<void> {
    const actionFilter = this.page.locator(this.actionFilter);
    const count = await actionFilter.count();

    if (count > 0) {
      await actionFilter.first().click();
      const option = this.page.locator(`.ant-select-dropdown-option:has-text("${action}")`);
      await option.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Select date range
   */
  async selectDateRange(startDate: string, endDate: string): Promise<void> {
    const datePicker = this.page.locator(this.dateRangePicker);
    const count = await datePicker.count();

    if (count > 0) {
      await datePicker.first().click();
      await this.page.waitForTimeout(500);

      // Date picker interaction would be more complex
      // This is a simplified version
    }
  }

  /**
   * Click export button
   */
  async exportLogs(): Promise<void> {
    const exportBtn = this.page.locator(this.exportButton);
    const count = await exportBtn.count();

    if (count > 0) {
      await exportBtn.first().click();
    }
  }

  /**
   * Refresh logs
   */
  async refreshLogs(): Promise<void> {
    const refreshBtn = this.page.locator(this.refreshButton);
    const count = await refreshBtn.count();

    if (count > 0) {
      await refreshBtn.first().click();
      await this.waitForLoading();
    }
  }

  /**
   * Get log entry data by row
   */
  async getLogEntry(row: number): Promise<{
    timestamp: string;
    username: string;
    action: string;
    resource: string;
    result: string;
  }> {
    const rows = this.page.locator(`${this.table} .ant-table-tbody .ant-table-row`);

    if (row > await rows.count()) {
      return { timestamp: '', username: '', action: '', resource: '', result: '' };
    }

    const rowElement = rows.nth(row - 1);
    const cells = rowElement.locator('.ant-table-cell');

    return {
      timestamp: await cells.nth(0).textContent() || '',
      username: await cells.nth(1).textContent() || '',
      action: await cells.nth(2).textContent() || '',
      resource: await cells.nth(3).textContent() || '',
      result: await cells.nth(4).textContent() || '',
    };
  }

  /**
   * Click on a log row to view details
   */
  async clickLogRow(row: number): Promise<void> {
    const rowElement = this.page.locator(
      `${this.table} .ant-table-tbody .ant-table-row:nth-child(${row})`
    );
    await rowElement.click();
  }

  /**
   * Check if filter panel is visible
   */
  async isFilterPanelVisible(): Promise<boolean> {
    const filter = this.page.locator(this.filterPanel);
    return await filter.isVisible().catch(() => false);
  }

  /**
   * Get pagination info
   */
  async getPaginationInfo(): Promise<{
    current: number;
    pageSize: number;
    total: number;
  }> {
    const pagination = this.page.locator('.ant-pagination');

    const current = await pagination.locator('.ant-pagination-item-active').textContent();
    const totalText = await pagination.locator('.ant-pagination-total-text').textContent();

    return {
      current: current ? parseInt(current) : 1,
      pageSize: 10,
      total: totalText ? parseInt(totalText) || 0 : 0,
    };
  }

  /**
   * Go to next page
   */
  async goToNextPage(): Promise<void> {
    const nextButton = this.page.locator('.ant-pagination-next:not(.ant-pagination-disabled)');
    const count = await nextButton.count();

    if (count > 0) {
      await nextButton.click();
      await this.waitForLoading();
    }
  }

  /**
   * Go to previous page
   */
  async goToPreviousPage(): Promise<void> {
    const prevButton = this.page.locator('.ant-pagination-prev:not(.ant-pagination-disabled)');
    const count = await prevButton.count();

    if (count > 0) {
      await prevButton.click();
      await this.waitForLoading();
    }
  }

  /**
   * Change page size
   */
  async changePageSize(size: number): Promise<void> {
    const pageSizeSelect = this.page.locator('.ant-pagination-options-size-changer');
    const count = await pageSizeSelect.count();

    if (count > 0) {
      await pageSizeSelect.click();
      await this.page.waitForTimeout(500);

      const option = this.page.locator(`.ant-select-dropdown-option:has-text("${size}")`);
      await option.click();
      await this.waitForLoading();
    }
  }

  /**
   * Verify audit log table is visible
   */
  async verifyTableVisible(): Promise<void> {
    const table = this.page.locator(this.table);
    await expect(table.first()).toBeVisible();
  }
}
