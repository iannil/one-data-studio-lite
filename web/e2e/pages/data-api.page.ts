/**
 * Data API Page Object Model
 *
 * Updated to match actual component implementation at:
 * - Route: /assets/data-api
 * - Component: DataApiManage
 * - Features: Schema viewing, SQL query, subscription
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Data API Page class
 */
export class DataApiPage extends BasePage {
  // Selectors - updated to match actual implementation
  private readonly container = '[data-testid="data-api-page"], .data-api-page, div:has(h4:has-text("数据API管理"))';
  private readonly catalog = '[data-testid="api-catalog"], .api-catalog';
  private readonly endpointList = '[data-testid="api-endpoint"], .api-endpoint';
  private readonly queryEditor = '.query-editor, .sql-editor, textarea[placeholder*="SQL"]';
  private readonly executeButton = 'button:has-text("执行"), button:has-text("查询")';
  private readonly resultArea = '.query-result, .result-area';
  private readonly schemaView = '.schema-view, .table-schema';
  private readonly datasetIdInput = 'input[placeholder*="数据集"]';
  private readonly fetchSchemaButton = 'button:has-text("获取"), button:has-text("查询")';
  private readonly subscribeButton = 'button:has-text("订阅")';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to data API page
   */
  async goto(): Promise<void> {
    await super.goto('/assets/data-api');
  }

  /**
   * Navigate to API catalog
   */
  async gotoCatalog(): Promise<void> {
    await super.goto('/assets/catalog');
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
      // Fallback: wait for table or heading with "API"
      try {
        await this.page.locator('.ant-tabs').waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
      } catch {
        await this.page.locator('h1, h2, h3, h4, h5').filter({ hasText: /API|数据API/ }).first().waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
      }
    }

    await this.waitForLoading();
  }

  /**
   * Get available API endpoints
   */
  async getApiEndpoints(): Promise<Array<{
    name: string;
    method: string;
    path: string;
    description: string;
  }>> {
    const endpointList = this.page.locator(this.endpointList);
    const items = endpointList.locator('.endpoint-item, .api-item');
    const count = await items.count();

    const endpoints: Array<{
      name: string;
      method: string;
      path: string;
      description: string;
    }> = [];

    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const name = await item.locator('.endpoint-name').textContent() || '';
      const method = await item.locator('.method-badge').textContent() || '';
      const path = await item.locator('.endpoint-path').textContent() || '';
      const description = await item.locator('.endpoint-desc').textContent() || '';

      endpoints.push({ name, method, path, description });
    }

    return endpoints;
  }

  /**
   * Execute SQL query
   */
  async executeQuery(sql: string): Promise<void> {
    const editor = this.page.locator(this.queryEditor);
    const isVisible = await editor.isVisible().catch(() => false);

    if (isVisible) {
      await editor.fill(sql);
      const executeBtn = this.page.locator(this.executeButton);
      await executeBtn.click();
      await this.waitForLoading();
    }
  }

  /**
   * Get query results
   */
  async getQueryResults(): Promise<{
    rows: Array<Record<string, string>>;
    rowCount: number;
    executionTime: number;
  }> {
    const resultArea = this.page.locator(this.resultArea);
    const isVisible = await resultArea.isVisible().catch(() => false);

    if (!isVisible) {
      return { rows: [], rowCount: 0, executionTime: 0 };
    }

    const table = resultArea.locator('.ant-table');
    const rows = table.locator('.ant-table-tbody .ant-table-row');
    const rowCount = await rows.count();

    const resultRows: Array<Record<string, string>> = [];

    // Get column headers
    const headers = table.locator('.ant-table-thead .ant-table-cell');
    const headerCount = await headers.count();
    const columnNames: string[] = [];

    for (let i = 0; i < headerCount; i++) {
      const name = await headers.nth(i).textContent();
      if (name) columnNames.push(name.trim());
    }

    // Get row data
    for (let i = 0; i < rowCount; i++) {
      const row = rows.nth(i);
      const cells = row.locator('.ant-table-cell');
      const rowData: Record<string, string> = {};

      for (let j = 0; j < columnNames.length; j++) {
        const value = await cells.nth(j).textContent();
        if (value) rowData[columnNames[j]] = value.trim();
      }

      resultRows.push(rowData);
    }

    // Get execution time
    const timeElement = resultArea.locator('.execution-time, .query-time');
    const timeText = await timeElement.textContent();
    const executionTime = timeText ? parseFloat(timeText.match(/[\d.]+/)?.[0] || '0') : 0;

    return { rows: resultRows, rowCount, executionTime };
  }

  /**
   * View table schema
   */
  async viewTableSchema(tableName: string): Promise<void> {
    // Click on table in catalog
    const tableItem = this.page.locator(`.table-item:has-text("${tableName}")`);
    const count = await tableItem.count();

    if (count > 0) {
      await tableItem.click();
      await this.waitForLoading();
    }
  }

  /**
   * Get table schema
   * Updated to work with the actual table-based implementation
   */
  async getTableSchema(): Promise<Array<{
    name: string;
    type: string;
    nullable: boolean;
    description: string;
  }>> {
    const schema: Array<{
      name: string;
      type: string;
      nullable: boolean;
      description: string;
    }> = [];

    // Try to get schema from the table (actual implementation)
    const tables = this.page.locator('.ant-table');
    const tableCount = await tables.count();

    if (tableCount > 0) {
      // The schema table has columns: 字段名, 类型, 描述, 可为空
      const rows = await tables.first().locator('.ant-table-tbody .ant-table-row').all();
      for (let i = 0; i < rows.length; i++) {
        const cells = await rows[i].locator('.ant-table-cell').all();
        if (cells.length >= 4) {
          const name = (await cells[0].textContent() || '').trim();
          const type = (await cells[1].textContent() || '').trim();
          const description = (await cells[2].textContent() || '').trim();
          const nullableText = (await cells[3].textContent() || '').trim();
          schema.push({
            name,
            type,
            nullable: nullableText === '是' || nullableText.toLowerCase() === 'yes',
            description,
          });
        }
      }
      return schema;
    }

    // Fallback to old schema view implementation
    const schemaView = this.page.locator(this.schemaView);
    const isVisible = await schemaView.isVisible().catch(() => false);

    if (!isVisible) {
      return [];
    }

    const columns = schemaView.locator('.schema-column, .column-item');
    const count = await columns.count();

    for (let i = 0; i < count; i++) {
      const column = columns.nth(i);
      const name = await column.locator('.column-name').textContent() || '';
      const type = await column.locator('.column-type').textContent() || '';
      const nullableText = await column.locator('.column-nullable').textContent() || '';
      const description = await column.locator('.column-desc').textContent() || '';

      schema.push({
        name,
        type,
        nullable: nullableText.toLowerCase().includes('yes') || nullableText.includes('是'),
        description,
      });
    }

    return schema;
  }

  /**
   * Get API documentation
   */
  async getApiDocumentation(): Promise<{
    baseUrl: string;
    endpoints: Array<{
      path: string;
      method: string;
      description: string;
      parameters: Array<{ name: string; type: string; required: boolean }>;
    }>;
  }> {
    const baseUrl = await this.page.locator('.base-url, .api-base-url').textContent() || '';

    const endpoints: Array<{
      path: string;
      method: string;
      description: string;
      parameters: Array<{ name: string; type: string; required: boolean }>;
    }> = [];

    const endpointItems = this.page.locator('.api-doc-endpoint');
    const count = await endpointItems.count();

    for (let i = 0; i < count; i++) {
      const item = endpointItems.nth(i);
      const path = await item.locator('.endpoint-path').textContent() || '';
      const method = await item.locator('.method').textContent() || '';
      const description = await item.locator('.description').textContent() || '';

      const params: Array<{ name: string; type: string; required: boolean }> = [];
      const paramItems = item.locator('.parameter-item');
      const paramCount = await paramItems.count();

      for (let j = 0; j < paramCount; j++) {
        const param = paramItems.nth(j);
        const paramName = await param.locator('.param-name').textContent() || '';
        const paramType = await param.locator('.param-type').textContent() || '';
        const requiredText = await param.locator('.param-required').textContent() || '';

        params.push({
          name: paramName,
          type: paramType,
          required: requiredText.toLowerCase().includes('required') || requiredText.includes('必填'),
        });
      }

      endpoints.push({ path, method, description, parameters: params });
    }

    return { baseUrl, endpoints };
  }

  /**
   * Test API endpoint
   */
  async testEndpoint(endpoint: string, method: string, params?: Record<string, string>): Promise<void> {
    // Navigate to API tester
    const testerButton = this.page.locator('button:has-text("API测试"), button:has-text("测试")');
    const count = await testerButton.count();

    if (count > 0) {
      await testerButton.click();

      // Fill in endpoint details
      const endpointInput = this.page.locator('input[name="endpoint"]');
      await endpointInput.fill(endpoint);

      const methodSelect = this.page.locator('select[name="method"]');
      await methodSelect.selectOption(method);

      if (params) {
        for (const [key, value] of Object.entries(params)) {
          const paramInput = this.page.locator(`input[name="${key}"]`);
          const paramCount = await paramInput.count();
          if (paramCount > 0) {
            await paramInput.fill(value);
          }
        }
      }

      // Click send
      const sendButton = this.page.locator('button:has-text("发送"), button:has-text("Send")');
      await sendButton.click();
      await this.waitForLoading();
    }
  }

  /**
   * Get API response
   */
  async getApiResponse(): Promise<{
    status: number;
    body: string;
    headers: Record<string, string>;
  }> {
    const responseArea = this.page.locator('.api-response, .response-area');
    const isVisible = await responseArea.isVisible().catch(() => false);

    if (!isVisible) {
      return { status: 0, body: '', headers: {} };
    }

    const statusText = await responseArea.locator('.response-status').textContent() || '';
    const status = parseInt(statusText.match(/\d+/)?.[0] || '0');

    const body = await responseArea.locator('.response-body').textContent() || '';

    const headers: Record<string, string> = {};
    const headerItems = responseArea.locator('.response-header');
    const headerCount = await headerItems.count();

    for (let i = 0; i < headerCount; i++) {
      const headerText = await headerItems.nth(i).textContent() || '';
      const [key, value] = headerText.split(':').map(s => s.trim());
      if (key && value) {
        headers[key] = value;
      }
    }

    return { status, body, headers };
  }

  /**
   * Generate API key
   */
  async generateApiKey(): Promise<string> {
    const generateButton = this.page.locator('button:has-text("生成密钥"), button:has-text("Generate Key")');
    const count = await generateButton.count();

    if (count > 0) {
      await generateButton.click();
      await this.waitForLoading();

      const keyDisplay = this.page.locator('.api-key-display, .generated-key');
      return await keyDisplay.textContent() || '';
    }

    return '';
  }

  /**
   * Revoke API key
   */
  async revokeApiKey(keyId: string): Promise<void> {
    const revokeButton = this.page.locator(`button[data-key-id="${keyId}"], .revoke-key:has-text("${keyId}")`);
    const count = await revokeButton.count();

    if (count > 0) {
      await revokeButton.click();
      await this.page.waitForTimeout(500);

      // Confirm revocation
      const confirmButton = this.page.locator('.ant-modal button:has-text("确定")');
      const confirmCount = await confirmButton.count();
      if (confirmCount > 0) {
        await confirmButton.click();
        await this.waitForLoading();
      }
    }
  }
}
