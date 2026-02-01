/**
 * Data Catalog Page Object Model
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Data Catalog Page class
 */
export class DataCatalogPage extends BasePage {
  // Selectors
  private readonly container = '[data-testid="data-catalog-page"], .data-catalog-page';
  private readonly searchInput = 'input[placeholder*="搜索"], .catalog-search';
  private readonly categoryList = '.category-list, .catalog-categories';
  private readonly datasetGrid = '.dataset-grid, .catalog-grid';
  private readonly datasetCard = '.dataset-card, .catalog-item';
  private readonly filterPanel = '.filter-panel, .catalog-filters';
  private readonly tableList = '.table-list, .catalog-tables';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to data catalog page
   */
  async goto(): Promise<void> {
    await super.goto('/assets/catalog');
  }

  /**
   * Wait for page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.waitForElement(this.container);
    await this.waitForLoading();
  }

  /**
   * Search datasets
   */
  async searchDatasets(keyword: string): Promise<void> {
    const searchInput = this.page.locator(this.searchInput);
    const count = await searchInput.count();

    if (count > 0) {
      await searchInput.first().fill(keyword);
      await this.page.waitForTimeout(500); // Debounce wait
      await this.waitForLoading();
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
      await this.waitForLoading();
    }
  }

  /**
   * Get dataset list
   */
  async getDatasets(): Promise<Array<{
    name: string;
    description: string;
    type: string;
    rowCount: number;
    tags: string[];
  }>> {
    const cards = this.page.locator(this.datasetCard);
    const count = await cards.count();

    const datasets: Array<{
      name: string;
      description: string;
      type: string;
      rowCount: number;
      tags: string[];
    }> = [];

    for (let i = 0; i < count; i++) {
      const card = cards.nth(i);
      const name = await card.locator('.dataset-name, .card-title').textContent() || '';
      const description = await card.locator('.dataset-desc, .card-desc').textContent() || '';
      const type = await card.locator('.dataset-type, .data-type').textContent() || '';
      const rowCountText = await card.locator('.row-count').textContent();
      const rowCount = rowCountText ? parseInt(rowCountText.match(/\d+/)?.[0] || '0') : 0;

      const tagElements = card.locator('.tag, .dataset-tag');
      const tagCount = await tagElements.count();
      const tags: string[] = [];

      for (let j = 0; j < tagCount; j++) {
        const tag = await tagElements.nth(j).textContent();
        if (tag) tags.push(tag);
      }

      datasets.push({ name, description, type, rowCount, tags });
    }

    return datasets;
  }

  /**
   * Click on dataset
   */
  async clickDataset(datasetName: string): Promise<void> {
    const datasetCard = this.page.locator(`${this.datasetCard}:has-text("${datasetName}")`);
    const count = await datasetCard.count();

    if (count > 0) {
      await datasetCard.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Get dataset details
   */
  async getDatasetDetails(): Promise<{
    name: string;
    description: string;
    owner: string;
    createdAt: string;
    updatedAt: string;
    schema: Array<{ name: string; type: string; description: string }>;
  }> {
    const detailPanel = this.page.locator('.dataset-detail, .catalog-detail');
    const isVisible = await detailPanel.isVisible().catch(() => false);

    if (!isVisible) {
      return {
        name: '',
        description: '',
        owner: '',
        createdAt: '',
        updatedAt: '',
        schema: [],
      };
    }

    const name = await detailPanel.locator('.detail-name').textContent() || '';
    const description = await detailPanel.locator('.detail-desc').textContent() || '';
    const owner = await detailPanel.locator('.detail-owner').textContent() || '';
    const createdAt = await detailPanel.locator('.detail-created').textContent() || '';
    const updatedAt = await detailPanel.locator('.detail-updated').textContent() || '';

    // Get schema
    const schema: Array<{ name: string; type: string; description: string }> = [];
    const schemaItems = detailPanel.locator('.schema-item, .column-item');
    const schemaCount = await schemaItems.count();

    for (let i = 0; i < schemaCount; i++) {
      const item = schemaItems.nth(i);
      const colName = await item.locator('.column-name').textContent() || '';
      const colType = await item.locator('.column-type').textContent() || '';
      const colDesc = await item.locator('.column-desc').textContent() || '';

      schema.push({ name: colName, type: colType, description: colDesc });
    }

    return { name, description, owner, createdAt, updatedAt, schema };
  }

  /**
   * Filter by category
   */
  async filterByCategory(category: string): Promise<void> {
    const categoryItem = this.page.locator(`${this.categoryList} .category-item:has-text("${category}")`);
    const count = await categoryItem.count();

    if (count > 0) {
      await categoryItem.click();
      await this.waitForLoading();
    }
  }

  /**
   * Filter by tag
   */
  async filterByTag(tag: string): Promise<void> {
    const tagItem = this.page.locator(`.tag-filter:has-text("${tag}")`);
    const count = await tagItem.count();

    if (count > 0) {
      await tagItem.click();
      await this.waitForLoading();
    }
  }

  /**
   * Get available categories
   */
  async getCategories(): Promise<string[]> {
    const categoryItems = this.page.locator(`${this.categoryList} .category-item`);
    const count = await categoryItems.count();
    const categories: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await categoryItems.nth(i).textContent();
      if (text) categories.push(text.trim());
    }

    return categories;
  }

  /**
   * Get available tags
   */
  async getTags(): Promise<string[]> {
    const tagItems = this.page.locator('.tag-filter, .catalog-tag');
    const count = await tagItems.count();
    const tags: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await tagItems.nth(i).textContent();
      if (text) tags.push(text.trim());
    }

    return tags;
  }

  /**
   * Get tables in dataset
   */
  async getTables(): Promise<Array<{
    name: string;
    type: string;
    rowCount: number;
    description: string;
  }>> {
    const tableItems = this.page.locator(`${this.tableList} .table-item`);
    const count = await tableItems.count();

    const tables: Array<{
      name: string;
      type: string;
      rowCount: number;
      description: string;
    }> = [];

    for (let i = 0; i < count; i++) {
      const item = tableItems.nth(i);
      const name = await item.locator('.table-name').textContent() || '';
      const type = await item.locator('.table-type').textContent() || '';
      const rowCountText = await item.locator('.row-count').textContent();
      const rowCount = rowCountText ? parseInt(rowCountText.match(/\d+/)?.[0] || '0') : 0;
      const description = await item.locator('.table-desc').textContent() || '';

      tables.push({ name, type, rowCount, description });
    }

    return tables;
  }

  /**
   * Preview table data
   */
  async previewTable(tableName: string): Promise<void> {
    const tableItem = this.page.locator(`${this.tableList} .table-item:has-text("${tableName}")`);
    const count = await tableItem.count();

    if (count > 0) {
      const previewButton = tableItem.locator('button:has-text("预览"), button:has-text("预览数据")');
      const previewCount = await previewButton.count();

      if (previewCount > 0) {
        await previewButton.click();
        await this.page.waitForTimeout(500);
      }
    }
  }

  /**
   * Get table preview data
   */
  async getTablePreview(): Promise<{
    columns: string[];
    rows: Array<Record<string, string>>;
  }> {
    const previewPanel = this.page.locator('.table-preview, .data-preview');
    const isVisible = await previewPanel.isVisible().catch(() => false);

    if (!isVisible) {
      return { columns: [], rows: [] };
    }

    const table = previewPanel.locator('.ant-table');

    // Get columns
    const headers = table.locator('.ant-table-thead .ant-table-cell');
    const headerCount = await headers.count();
    const columns: string[] = [];

    for (let i = 0; i < headerCount; i++) {
      const text = await headers.nth(i).textContent();
      if (text) columns.push(text.trim());
    }

    // Get rows
    const rows = table.locator('.ant-table-tbody .ant-table-row');
    const rowCount = await rows.count();
    const rowData: Array<Record<string, string>> = [];

    for (let i = 0; i < rowCount; i++) {
      const row = rows.nth(i);
      const cells = row.locator('.ant-table-cell');
      const rowRecord: Record<string, string> = {};

      for (let j = 0; j < columns.length; j++) {
        const value = await cells.nth(j).textContent();
        if (value) rowRecord[columns[j]] = value.trim();
      }

      rowData.push(rowRecord);
    }

    return { columns, rows: rowData };
  }

  /**
   * Add to favorites
   */
  async addToFavorite(datasetName: string): Promise<void> {
    const datasetCard = this.page.locator(`${this.datasetCard}:has-text("${datasetName}")`);
    const favoriteButton = datasetCard.locator('.favorite-button, .fav-btn');
    const count = await favoriteButton.count();

    if (count > 0) {
      await favoriteButton.click();
    }
  }

  /**
   * Get favorite datasets
   */
  async getFavoriteDatasets(): Promise<string[]> {
    const favoriteCards = this.page.locator(`${this.datasetCard}.is-favorite, ${this.datasetCard}.favorite`);
    const count = await favoriteCards.count();
    const names: string[] = [];

    for (let i = 0; i < count; i++) {
      const name = await favoriteCards.nth(i).locator('.dataset-name').textContent();
      if (name) names.push(name);
    }

    return names;
  }

  /**
   * Export dataset metadata
   */
  async exportMetadata(datasetName: string): Promise<void> {
    const datasetCard = this.page.locator(`${this.datasetCard}:has-text("${datasetName}")`);
    const exportButton = datasetCard.locator('button:has-text("导出"), button:has-text("元数据")');
    const count = await exportButton.count();

    if (count > 0) {
      await exportButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Verify dataset exists
   */
  async verifyDatasetExists(datasetName: string): Promise<boolean> {
    const datasetCard = this.page.locator(`${this.datasetCard}:has-text("${datasetName}")`);
    return await datasetCard.count() > 0;
  }
}
