/**
 * Sensitive Data Page Object Model
 *
 * Updated to match actual component implementation at:
 * - Route: /security/sensitive
 * - Component: Sensitive
 * - Features: Scan sensitive data, manage detection rules, view reports
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Sensitive Data Page class
 */
export class SensitiveDataPage extends BasePage {
  // Selectors - updated to match actual implementation
  private readonly container = '[data-testid="sensitive-data-page"], .sensitive-data-page, div:has(h4:has-text("敏感数据检测"))';
  private readonly scanButton = '[data-testid="sensitive-scan"], button:has-text("扫描")';
  private readonly scanResult = '[data-testid="sensitive-result"], .scan-result';
  private readonly table = '.ant-table, .result-table';
  private readonly statusIndicator = '.scan-status, .status-indicator';
  private readonly progressBar = '.ant-progress, .scan-progress';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to sensitive data page
   */
  async goto(): Promise<void> {
    await super.goto('/security/sensitive');
  }

  /**
   * Wait for page to load
   * Uses multiple possible selectors for flexibility
   */
  async waitForPageLoad(): Promise<void> {
    // Try each possible container selector
    const selectors = this.container.split(', ');
    let loaded = false;

    for (const selector of selectors) {
      try {
        await this.page.locator(selector).waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
        loaded = true;
        break;
      } catch {
        // Try next selector
      }
    }

    if (!loaded) {
      // Fallback: wait for tabs or heading
      try {
        await this.page.locator('.ant-tabs').waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
      } catch {
        await this.page.locator('h1, h2, h3, h4, h5').filter({ hasText: /敏感|Sensitive/ }).first().waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
      }
    }

    await this.waitForLoading();
  }

  /**
   * Start sensitive data scan
   */
  async startScan(): Promise<void> {
    const button = this.page.locator(this.scanButton);
    await button.click();
  }

  /**
   * Wait for scan to complete
   */
  async waitForScanCompletion(): Promise<void> {
    const progressBar = this.page.locator(this.progressBar);

    // Wait for progress bar to disappear
    try {
      await progressBar.waitFor({ state: 'detached', timeout: 60000 });
    } catch {
      // Progress bar might not be present
    }

    await this.waitForLoading();
  }

  /**
   * Get scan status
   */
  async getScanStatus(): Promise<string> {
    const status = this.page.locator(this.statusIndicator);
    const isVisible = await status.isVisible().catch(() => false);

    if (isVisible) {
      return (await status.textContent()) || '';
    }
    return '';
  }

  /**
   * Get scan results
   */
  async getScanResults(): Promise<{
    totalRows: number;
    sensitiveRows: number;
    fields: Array<{ field: string; type: string; count: number }>;
  }> {
    const resultArea = this.page.locator(this.scanResult);
    const isVisible = await resultArea.isVisible().catch(() => false);

    if (!isVisible) {
      return { totalRows: 0, sensitiveRows: 0, fields: [] };
    }

    // Parse results from the page
    const totalText = await this.page.locator('text=/总行数.*\\d+/').textContent();
    const sensitiveText = await this.page.locator('text=/敏感行.*\\d+/').textContent();

    const totalRows = totalText ? parseInt(totalText.match(/\d+/)?.[0] || '0') : 0;
    const sensitiveRows = sensitiveText ? parseInt(sensitiveText.match(/\d+/)?.[0] || '0') : 0;

    const fields: Array<{ field: string; type: string; count: number }> = [];
    const fieldRows = this.page.locator('.field-row, .sensitive-field');
    const count = await fieldRows.count();

    for (let i = 0; i < count; i++) {
      const row = fieldRows.nth(i);
      const field = await row.locator('.field-name').textContent() || '';
      const type = await row.locator('.field-type').textContent() || '';
      const fieldCount = parseInt(await row.locator('.field-count').textContent() || '0');
      fields.push({ field, type, count: fieldCount });
    }

    return { totalRows, sensitiveRows, fields };
  }

  /**
   * Select table to scan
   */
  async selectTable(tableName: string): Promise<void> {
    const tableSelect = this.page.locator('.table-select, select[name="table"]');
    const count = await tableSelect.count();

    if (count > 0) {
      await tableSelect.first().click();
      const option = this.page.locator(`.ant-select-dropdown-option:has-text("${tableName}")`);
      await option.click();
    }
  }

  /**
   * Configure scan options
   */
  async configureScanOptions(options: {
    scanEmail?: boolean;
    scanPhone?: boolean;
    scanIdCard?: boolean;
    scanAddress?: boolean;
  }): Promise<void> {
    // Configure checkboxes for different data types
    if (options.scanEmail !== undefined) {
      const checkbox = this.page.locator('input[type="checkbox"][value="email"]');
      const count = await checkbox.count();
      if (count > 0 && (await checkbox.isChecked()) !== options.scanEmail) {
        await checkbox.setChecked(options.scanEmail);
      }
    }

    if (options.scanPhone !== undefined) {
      const checkbox = this.page.locator('input[type="checkbox"][value="phone"]');
      const count = await checkbox.count();
      if (count > 0 && (await checkbox.isChecked()) !== options.scanPhone) {
        await checkbox.setChecked(options.scanPhone);
      }
    }

    if (options.scanIdCard !== undefined) {
      const checkbox = this.page.locator('input[type="checkbox"][value="id_card"]');
      const count = await checkbox.count();
      if (count > 0 && (await checkbox.isChecked()) !== options.scanIdCard) {
        await checkbox.setChecked(options.scanIdCard);
      }
    }

    if (options.scanAddress !== undefined) {
      const checkbox = this.page.locator('input[type="checkbox"][value="address"]');
      const count = await checkbox.count();
      if (count > 0 && (await checkbox.isChecked()) !== options.scanAddress) {
        await checkbox.setChecked(options.scanAddress);
      }
    }
  }

  /**
   * Export scan report
   */
  async exportReport(): Promise<void> {
    const exportButton = this.page.locator('button:has-text("导出报告"), button:has-text("导出")');
    const count = await exportButton.count();

    if (count > 0) {
      await exportButton.first().click();
    }
  }

  /**
   * Get scan history
   */
  async getScanHistory(): Promise<Array<{
    id: string;
    table: string;
    date: string;
    status: string;
    sensitiveCount: number;
  }>> {
    const historyTable = this.page.locator('.history-table, .scan-history');
    const rows = historyTable.locator('.ant-table-tbody .ant-table-row');
    const count = await rows.count();

    const history: Array<{
      id: string;
      table: string;
      date: string;
      status: string;
      sensitiveCount: number;
    }> = [];

    for (let i = 0; i < count; i++) {
      const row = rows.nth(i);
      const cells = row.locator('.ant-table-cell');

      history.push({
        id: await cells.nth(0).textContent() || '',
        table: await cells.nth(1).textContent() || '',
        date: await cells.nth(2).textContent() || '',
        status: await cells.nth(3).textContent() || '',
        sensitiveCount: parseInt(await cells.nth(4).textContent() || '0'),
      });
    }

    return history;
  }

  /**
   * Verify scan completed successfully
   */
  async verifyScanCompleted(): Promise<void> {
    const status = await this.getScanStatus();
    expect(status).toMatch(/完成|成功|completed/i);
  }

  /**
   * Verify sensitive data found
   */
  async verifySensitiveDataFound(): Promise<boolean> {
    const results = await this.getScanResults();
    return results.sensitiveRows > 0;
  }
}
