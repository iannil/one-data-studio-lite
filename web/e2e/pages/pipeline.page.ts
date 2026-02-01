/**
 * Pipeline Page Object Model
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Pipeline Page class
 */
export class PipelinePage extends BasePage {
  // Selectors
  private readonly container = '[data-testid="pipeline-page"], .pipeline-page';
  private readonly pipelineList = '.pipeline-list, [data-testid="pipeline-list"]';
  private readonly createButton = '[data-testid="create-pipeline-button"], button:has-text("创建")';
  private readonly runButton = '[data-testid="run-pipeline-button"], button:has-text("运行")';
  private readonly stopButton = '[data-testid="stop-pipeline-button"], button:has-text("停止")';
  private readonly deleteButton = '[data-testid="delete-pipeline-button"], button:has-text("删除")';
  private readonly pipelineCard = '.pipeline-card, .pipeline-item';
  private readonly graphCanvas = '.pipeline-canvas, .graph-view';
  private readonly nodePalette = '.node-palette, .palette';
  private readonly propertiesPanel = '.properties-panel';
  private readonly executionLog = '.execution-log, .pipeline-log';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to pipeline page
   */
  async goto(): Promise<void> {
    await super.goto('/analysis/pipelines');
  }

  /**
   * Wait for page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.waitForElement(this.container);
    await this.waitForLoading();
  }

  /**
   * Get pipeline list
   */
  async getPipelines(): Promise<Array<{
    id: string;
    name: string;
    status: string;
    lastRun: string;
    schedule: string;
  }>> {
    await this.waitForTable(this.pipelineList);

    const cards = this.page.locator(`${this.pipelineCard}, .ant-table-tbody .ant-table-row`);
    const count = await cards.count();
    const pipelines: Array<{
      id: string;
      name: string;
      status: string;
      lastRun: string;
      schedule: string;
    }> = [];

    for (let i = 0; i < count; i++) {
      const item = cards.nth(i);

      if (await item.evaluate((el: HTMLElement) => el.classList.contains('ant-table-row'))) {
        // Table row format
        const cells = item.locator('.ant-table-cell');
        pipelines.push({
          id: await cells.nth(0).textContent() || '',
          name: await cells.nth(1).textContent() || '',
          status: await cells.nth(2).textContent() || '',
          lastRun: await cells.nth(3).textContent() || '',
          schedule: await cells.nth(4).textContent() || '',
        });
      } else {
        // Card format
        const name = await item.locator('.pipeline-name, .card-title').textContent();
        const status = await item.locator('.pipeline-status, .status-badge').textContent();
        pipelines.push({
          id: `pipeline-${i}`,
          name: name || '',
          status: status || '',
          lastRun: '',
          schedule: '',
        });
      }
    }

    return pipelines;
  }

  /**
   * Click create pipeline button
   */
  async clickCreatePipeline(): Promise<void> {
    const button = this.page.locator(this.createButton);
    const count = await button.count();

    if (count > 0) {
      await button.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Run a pipeline
   */
  async runPipeline(pipelineName: string): Promise<void> {
    const card = this.page.locator(`${this.pipelineCard}:has-text("${pipelineName}")`);
    const runButton = card.locator(this.runButton);

    const count = await runButton.count();
    if (count > 0) {
      await runButton.click();
    } else {
      // Try table row
      const row = this.page.locator(`.ant-table-tbody .ant-table-row:has-text("${pipelineName}")`);
      const rowButton = row.locator(this.runButton);
      await rowButton.click();
    }

    await this.page.waitForTimeout(1000);
  }

  /**
   * Stop a running pipeline
   */
  async stopPipeline(pipelineName: string): Promise<void> {
    const card = this.page.locator(`${this.pipelineCard}:has-text("${pipelineName}")`);
    const stopButton = card.locator(this.stopButton);

    const count = await stopButton.count();
    if (count > 0) {
      await stopButton.click();
    } else {
      // Try table row
      const row = this.page.locator(`.ant-table-tbody .ant-table-row:has-text("${pipelineName}")`);
      const rowButton = row.locator(this.stopButton);
      await rowButton.click();
    }
  }

  /**
   * Delete a pipeline
   */
  async deletePipeline(pipelineName: string): Promise<void> {
    const card = this.page.locator(`${this.pipelineCard}:has-text("${pipelineName}")`);
    const deleteButton = card.locator(this.deleteButton);

    const count = await deleteButton.count();
    if (count > 0) {
      await deleteButton.click();
      await this.page.waitForTimeout(500);

      // Confirm deletion
      const confirmButton = this.page.locator('.ant-modal button:has-text("确定")');
      await confirmButton.click();
      await this.waitForLoading();
    } else {
      // Try table row
      const row = this.page.locator(`.ant-table-tbody .ant-table-row:has-text("${pipelineName}")`);
      const rowButton = row.locator(this.deleteButton);
      await rowButton.click();
    }
  }

  /**
   * Get pipeline status
   */
  async getPipelineStatus(pipelineName: string): Promise<string> {
    const card = this.page.locator(`${this.pipelineCard}:has-text("${pipelineName}")`);
    const statusBadge = card.locator('.status-badge, .pipeline-status');

    const text = await statusBadge.textContent();
    return text || '';
  }

  /**
   * Open pipeline editor
   */
  async openEditor(pipelineName: string): Promise<void> {
    const card = this.page.locator(`${this.pipelineCard}:has-text("${pipelineName}")`);
    const editButton = card.locator('button:has-text("编辑"), button:has-text("设计")');

    const count = await editButton.count();
    if (count > 0) {
      await editButton.click();
      await this.page.waitForTimeout(500);
    }

    // Wait for editor to load
    await this.waitForElement(this.graphCanvas);
  }

  /**
   * Add node to pipeline
   */
  async addNode(nodeType: string): Promise<void> {
    const palette = this.page.locator(this.nodePalette);
    const nodeItem = palette.locator(`.node-item:has-text("${nodeType}")`);

    const count = await nodeItem.count();
    if (count > 0) {
      await nodeItem.click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Connect two nodes
   */
  async connectNodes(sourceNodeId: string, targetNodeId: string): Promise<void> {
    // This would involve drag and drop or clicking connection points
    const sourceNode = this.page.locator(`[data-node-id="${sourceNodeId}"]`);
    const targetNode = this.page.locator(`[data-node-id="${targetNodeId}"]`);

    await sourceNode.hover();
    await targetNode.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Save pipeline
   */
  async savePipeline(): Promise<void> {
    const saveButton = this.page.locator('button:has-text("保存"), button:has-text("保存")');
    const count = await saveButton.count();

    if (count > 0) {
      await saveButton.click();
      await this.waitForLoading();
    }
  }

  /**
   * Get execution log
   */
  async getExecutionLog(): Promise<string[]> {
    const logLines = this.page.locator(`${this.executionLog} .log-line`);
    const count = await logLines.count();
    const logs: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await logLines.nth(i).textContent();
      if (text) logs.push(text);
    }

    return logs;
  }

  /**
   * Schedule pipeline
   */
  async schedulePipeline(pipelineName: string, cron: string): Promise<void> {
    const card = this.page.locator(`${this.pipelineCard}:has-text("${pipelineName}")`);
    const scheduleButton = card.locator('button:has-text("调度"), button:has-text("计划")');

    const count = await scheduleButton.count();
    if (count > 0) {
      await scheduleButton.click();
      await this.page.waitForTimeout(500);

      // Fill cron expression
      const cronInput = this.page.locator('input[name="cron"], input[placeholder*="cron"]');
      await cronInput.fill(cron);

      const confirmButton = this.page.locator('.ant-modal button:has-text("确定")');
      await confirmButton.click();
      await this.waitForLoading();
    }
  }

  /**
   * Clone pipeline
   */
  async clonePipeline(pipelineName: string): Promise<void> {
    const card = this.page.locator(`${this.pipelineCard}:has-text("${pipelineName}")`);
    const cloneButton = card.locator('button:has-text("克隆"), button:has-text("复制")');

    const count = await cloneButton.count();
    if (count > 0) {
      await cloneButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Verify pipeline exists
   */
  async verifyPipelineExists(pipelineName: string): Promise<boolean> {
    const card = this.page.locator(`${this.pipelineCard}:has-text("${pipelineName}")`);
    return await card.count() > 0;
  }

  /**
   * Verify pipeline status
   */
  async verifyPipelineStatus(pipelineName: string, expectedStatus: string): Promise<void> {
    const status = await this.getPipelineStatus(pipelineName);
    expect(status).toContain(expectedStatus);
  }
}
