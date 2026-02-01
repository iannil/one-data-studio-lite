/**
 * Data Cleaning Page Object Model
 *
 * Updated to match actual component implementation at:
 * - Route: /development/cleaning
 * - Component: CleaningRules (data-testid="cleaning-rules-page")
 * - Features: AI recommendation, rule templates (no CRUD operations yet)
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Data Cleaning Page class
 */
export class DataCleaningPage extends BasePage {
  // Selectors - updated to match actual implementation
  private readonly container = '[data-testid="cleaning-rules-page"], [data-testid="cleaning-page"], .cleaning-page, div:has(h4:has-text("清洗规则配置"))';
  private readonly tableNameInput = '[data-testid="table-name-input"]';
  private readonly aiRecommendButton = '[data-testid="ai-recommend-button"], button:has-text("AI 推荐")';
  private readonly cleaningTabs = '[data-testid="cleaning-tabs"], .ant-tabs';
  private readonly recommendTab = '.ant-tabs-tab:has-text("AI 推荐")';
  private readonly templatesTab = '.ant-tabs-tab:has-text("规则模板")';
  private readonly rulesTable = '.ant-table';

  // Legacy selectors for features not yet implemented
  private readonly rulesList = '.rules-list, [data-testid="rules-list"]';
  private readonly createRuleButton = '[data-testid="create-rule-button"], button:has-text("创建规则")';
  private readonly ruleCard = '.rule-card, .cleaning-rule';
  private readonly scanButton = '[data-testid="scan-button"], button:has-text("扫描")';
  private readonly applyButton = '[data-testid="apply-button"], button:has-text("应用")';
  private readonly previewArea = '.preview-area, .data-preview';
  private readonly rulesEngine = '.rules-engine, .cleaning-engine';
  private readonly dataSelector = '.data-selector, select[name="data"]';
  private readonly tablePreview = '.table-preview, .data-preview';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to data cleaning page
   */
  async goto(): Promise<void> {
    await super.goto('/development/cleaning');
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
      // Fallback: wait for any heading with "清洗" or "Cleaning"
      await this.page.locator('h1, h2, h3, h4, h5').filter({ hasText: /清洗|Cleaning/ }).first().waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    }

    await this.waitForLoading();
  }

  /**
   * Check if AI recommendation feature is available
   */
  async hasAiRecommendation(): Promise<boolean> {
    const button = this.page.locator(this.aiRecommendButton);
    return await button.count() > 0;
  }

  /**
   * Check if rule templates feature is available
   */
  async hasRuleTemplates(): Promise<boolean> {
    const tabs = this.page.locator(this.cleaningTabs);
    return await tabs.count() > 0;
  }

  /**
   * Get cleaning rules
   * Updated to work with the actual table-based implementation
   */
  async getRules(): Promise<Array<{
    id: string;
    name: string;
    type: string;
    condition: string;
    action: string;
    enabled: boolean;
  }>> {
    const rules: Array<{
      id: string;
      name: string;
      type: string;
      condition: string;
      action: string;
      enabled: boolean;
    }> = [];

    // First try to get rules from the templates table (actual implementation)
    const tables = this.page.locator(this.rulesTable);
    const tableCount = await tables.count();

    if (tableCount > 0) {
      // Get data from the first table
      const rows = await tables.first().locator('.ant-table-tbody .ant-table-row').all();
      for (let i = 0; i < rows.length; i++) {
        const cells = await rows[i].locator('.ant-table-cell').all();
        if (cells.length >= 2) {
          const name = await cells[0].textContent() || '';
          const type = await cells[1].textContent() || '';
          rules.push({
            id: `rule-${i}`,
            name: name.trim(),
            type: type.trim(),
            condition: '',
            action: '',
            enabled: true,
          });
        }
      }
      return rules;
    }

    // Fallback to old card-based implementation (if it exists)
    const cards = this.page.locator(this.ruleCard);
    const count = await cards.count();

    for (let i = 0; i < count; i++) {
      const card = cards.nth(i);

      const name = await card.locator('.rule-name, .card-title').textContent() || '';
      const type = await card.locator('.rule-type').textContent() || '';
      const enabled = await card.locator('.rule-switch, .ant-switch').isChecked() ?? true;

      rules.push({
        id: `rule-${i}`,
        name,
        type,
        condition: '',
        action: '',
        enabled,
      });
    }

    return rules;
  }

  /**
   * Click create rule button
   */
  async clickCreateRule(): Promise<void> {
    const button = this.page.locator(this.createRuleButton);
    const count = await button.count();

    if (count > 0) {
      await button.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Configure rule
   */
  async configureRule(config: {
    ruleType?: string;
    field?: string;
    condition?: string;
    action?: string;
  }): Promise<void> {
    // Rule type selector
    const ruleTypeSelect = this.page.locator('select[name="ruleType"], .rule-type-select');
    const typeCount = await ruleTypeSelect.count();

    if (config.ruleType && typeCount > 0) {
      await ruleTypeSelect.selectOption(config.ruleType);
      await this.page.waitForTimeout(300);
    }

    // Field selector
    const fieldSelect = this.page.locator('select[name="field"], .field-select');
    const fieldCount = await fieldSelect.count();

    if (config.field && fieldCount > 0) {
      await fieldSelect.selectOption(config.field);
      await this.page.waitForTimeout(300);
    }

    // Condition input
    if (config.condition) {
      const conditionInput = this.page.locator('input[name="condition"], textarea[name="condition"]');
      const count = await conditionInput.count();

      if (count > 0) {
        await conditionInput.first().fill(config.condition);
      }
    }

    // Action selector
    const actionSelect = this.page.locator('select[name="action"], .action-select');
    const actionCount = await actionSelect.count();

    if (config.action && actionCount > 0) {
      await actionSelect.selectOption(config.action);
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Enable/disable rule
   */
  async toggleRule(ruleName: string): Promise<void> {
    const card = this.page.locator(`${this.ruleCard}:has-text("${ruleName}")`);
    const switchToggle = card.locator('.ant-switch');

    await switchToggle.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Delete rule
   */
  async deleteRule(ruleName: string): Promise<void> {
    const card = this.page.locator(`${this.ruleCard}:has-text("${ruleName}")`);
    const deleteButton = card.locator('button:has-text("删除")');

    const count = await deleteButton.count();
    if (count > 0) {
      await deleteButton.click();
      await this.page.waitForTimeout(500);

      // Confirm deletion
      const confirmButton = this.page.locator('.ant-modal button:has-text("确定")');
      const confirmCount = await confirmButton.count();

      if (confirmCount > 0) {
        await confirmButton.click();
        await this.waitForLoading();
      }
    }
  }

  /**
   * Select data source
   */
  async selectDataSource(dataSource: string): Promise<void> {
    const selector = this.page.locator(this.dataSelector);
    const count = await selector.count();

    if (count > 0) {
      await selector.selectOption(dataSource);
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Scan data for quality issues
   */
  async scanData(): Promise<void> {
    const button = this.page.locator(this.scanButton);
    const count = await button.count();

    if (count > 0) {
      await button.click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Get scan results
   */
  async getScanResults(): Promise<{
    totalRows: number;
    issuesFound: number;
    criticalIssues: number;
    issues: Array<{
      type: string;
      count: number;
      description: string;
    }>;
  }> {
    const resultsArea = this.page.locator('.scan-results, .quality-results');
    const isVisible = await resultsArea.isVisible().catch(() => false);

    if (!isVisible) {
      return { totalRows: 0, issuesFound: 0, criticalIssues: 0, issues: [] };
    }

    const totalText = await resultsArea.locator('text=/总行数.*\\d+/').textContent();
    const totalRows = totalText ? parseInt(totalText.match(/\d+/)?.[0] || '0') : 0;

    const issuesText = await resultsArea.locator('text=/问题.*\\d+/').textContent();
    const issuesFound = issuesText ? parseInt(issuesText.match(/\d+/)?.[0] || '0') : 0;

    return {
      totalRows,
      issuesFound,
      criticalIssues: 0,
      issues: [],
    };
  }

  /**
   * Apply cleaning rules
   */
  async applyCleaningRules(): Promise<void> {
    const button = this.page.locator(this.applyButton);
    const count = await button.count();

    if (count > 0) {
      await button.click();
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Preview cleaning results
   */
  async previewCleaningResults(): Promise<void> {
    const previewButton = this.page.locator('button:has-text("预览")');
    const count = await previewButton.count();

    if (count > 0) {
      await previewButton.click();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Get rule suggestions from AI
   */
  async getRuleSuggestions(): Promise<string[]> {
    const suggestButton = this.page.locator('button:has-text("AI推荐"), button:has-text("智能推荐")');
    const count = await suggestButton.count();

    if (count > 0) {
      await suggestButton.click();
      await this.page.waitForTimeout(1000);

      const suggestions = this.page.locator('.suggestion-item');
      const suggestionCount = await suggestions.count();
      const results: string[] = [];

      for (let i = 0; i < suggestionCount; i++) {
        const text = await suggestions.nth(i).textContent();
        if (text) results.push(text);
      }

      return results;
    }

    return [];
  }

  /**
   * Get cleaning statistics
   */
  async getCleaningStatistics(): Promise<{
    rulesCreated: number;
    rulesActive: number;
    dataScanned: number;
    issuesResolved: number;
  }> {
    const stats = this.page.locator('.cleaning-stats, .statistics');

    return {
      rulesCreated: parseInt(await stats.locator('.stat-created').textContent() || '0'),
      rulesActive: parseInt(await stats.locator('.stat-active').textContent() || '0'),
      dataScanned: parseInt(await stats.locator('.stat-scanned').textContent() || '0'),
      issuesResolved: parseInt(await stats.locator('.stat-resolved').textContent() || '0'),
    };
  }
}
