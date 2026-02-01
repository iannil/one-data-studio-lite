/**
 * Users Management Page Object Model
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Users Page class
 */
export class UsersPage extends BasePage {
  // Selectors
  private readonly container = '[data-testid="users-page"], .users-page';
  private readonly table = '[data-testid="users-table"], .users-table';
  private readonly createButton = '[data-testid="create-user-button"], button:has-text("创建")';
  private readonly editButton = '[data-testid="edit-button"], button:has-text("编辑")';
  private readonly deleteButton = '[data-testid="delete-button"], button:has-text("删除")';
  private readonly searchInput = 'input[placeholder*="搜索"], .search-input';
  private readonly roleFilter = 'select[name="role"], .role-filter';
  private readonly statusFilter = 'select[name="status"], .status-filter';

  // Modal selectors
  private readonly modal = '.ant-modal';
  private readonly modalTitle = '.ant-modal-title';
  private readonly modalOkButton = '.ant-modal button:has-text("确定")';
  private readonly modalCancelButton = '.ant-modal button:has-text("取消")';

  // Form selectors
  private readonly usernameInput = '#username, [name="username"]';
  private readonly displayNameInput = '#displayName, [name="displayName"]';
  private readonly passwordInput = '#password, [name="password"]';
  private readonly roleSelect = 'select[name="role"], .role-select';
  private readonly emailInput = '#email, [name="email"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to users page
   */
  async goto(): Promise<void> {
    await super.goto('/operations/users');
  }

  /**
   * Wait for users page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.waitForElement(this.container);
    await this.waitForLoading();
  }

  /**
   * Get user count from table
   */
  async getUserCount(): Promise<number> {
    await this.waitForTable(this.table);
    const rows = this.page.locator(`${this.table} .ant-table-tbody .ant-table-row`);
    return await rows.count();
  }

  /**
   * Get user data by row
   */
  async getUserData(row: number): Promise<{
    username: string;
    displayName: string;
    role: string;
    status: string;
    email: string;
  }> {
    const rows = this.page.locator(`${this.table} .ant-table-tbody .ant-table-row`);

    if (row > await rows.count()) {
      return { username: '', displayName: '', role: '', status: '', email: '' };
    }

    const rowElement = rows.nth(row - 1);
    const cells = rowElement.locator('.ant-table-cell');

    return {
      username: await cells.nth(0).textContent() || '',
      displayName: await cells.nth(1).textContent() || '',
      role: await cells.nth(2).textContent() || '',
      status: await cells.nth(3).textContent() || '',
      email: await cells.nth(4).textContent() || '',
    };
  }

  /**
   * Click create user button
   */
  async clickCreateUser(): Promise<void> {
    const button = this.page.locator(this.createButton).first();
    await button.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Click edit button for specific row
   */
  async clickEditUser(row: number): Promise<void> {
    const rowElement = this.page.locator(
      `${this.table} .ant-table-tbody .ant-table-row:nth-child(${row})`
    );
    const editBtn = rowElement.locator(this.editButton);
    await editBtn.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Click delete button for specific row
   */
  async clickDeleteUser(row: number): Promise<void> {
    const rowElement = this.page.locator(
      `${this.table} .ant-table-tbody .ant-table-row:nth-child(${row})`
    );
    const deleteBtn = rowElement.locator(this.deleteButton);
    await deleteBtn.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Search users by keyword
   */
  async searchUsers(keyword: string): Promise<void> {
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
   * Filter by role
   */
  async filterByRole(role: string): Promise<void> {
    const roleFilter = this.page.locator(this.roleFilter);
    const count = await roleFilter.count();

    if (count > 0) {
      await roleFilter.first().click();
      const option = this.page.locator(`.ant-select-dropdown-option:has-text("${role}")`);
      await option.click();
      await this.page.waitForTimeout(500);
      await this.waitForLoading();
    }
  }

  /**
   * Fill user form
   */
  async fillUserForm(data: {
    username: string;
    displayName?: string;
    password?: string;
    role?: string;
    email?: string;
  }): Promise<void> {
    if (data.username) {
      await this.fillInput(this.usernameInput, data.username);
    }

    if (data.displayName) {
      await this.fillInput(this.displayNameInput, data.displayName);
    }

    if (data.password) {
      await this.fillInput(this.passwordInput, data.password);
    }

    if (data.email) {
      await this.fillInput(this.emailInput, data.email);
    }

    if (data.role) {
      const roleSelect = this.page.locator(this.roleSelect);
      const count = await roleSelect.count();

      if (count > 0) {
        await roleSelect.first().click();
        const option = this.page.locator(`.ant-select-dropdown-option:has-text("${data.role}")`);
        await option.click();
      }
    }
  }

  /**
   * Submit user form (click OK in modal)
   */
  async submitUserForm(): Promise<void> {
    const okButton = this.page.locator(this.modalOkButton);
    await okButton.click();
    await this.waitForLoading();
  }

  /**
   * Cancel user form (click Cancel in modal)
   */
  async cancelUserForm(): Promise<void> {
    const cancelButton = this.page.locator(this.modalCancelButton);
    await cancelButton.click();
  }

  /**
   * Check if modal is visible
   */
  async isModalVisible(): Promise<boolean> {
    const modal = this.page.locator(this.modal);
    return await modal.isVisible().catch(() => false);
  }

  /**
   * Get modal title
   */
  async getModalTitle(): Promise<string> {
    const title = this.page.locator(this.modalTitle);
    return (await title.textContent()) || '';
  }

  /**
   * Verify user exists in table
   */
  async verifyUserExists(username: string): Promise<boolean> {
    const userCell = this.page.locator(`${this.table} td:has-text("${username}")`);
    return await userCell.count() > 0;
  }

  /**
   * Confirm delete action
   */
  async confirmDelete(): Promise<void> {
    // Look for confirmation in modal or popconfirm
    const confirmButton = this.page.locator(
      '.ant-modal button:has-text("确定"), .ant-popconfirm button:has-text("确定")'
    );
    const count = await confirmButton.count();

    if (count > 0) {
      await confirmButton.first().click();
      await this.waitForLoading();
    }
  }

  /**
   * Cancel delete action
   */
  async cancelDelete(): Promise<void> {
    const cancelButton = this.page.locator(
      '.ant-modal button:has-text("取消"), .ant-popconfirm button:has-text("取消")'
    );
    const count = await cancelButton.count();

    if (count > 0) {
      await cancelButton.first().click();
    }
  }

  /**
   * Get user status by username
   */
  async getUserStatus(username: string): Promise<string | null> {
    const userRow = this.page.locator(`${this.table} tr:has-text("${username}")`);
    const count = await userRow.count();

    if (count > 0) {
      const statusCell = userRow.locator('td').nth(3); // Assuming status is 4th column
      return await statusCell.textContent();
    }

    return null;
  }

  /**
   * Verify users table is visible
   */
  async verifyTableVisible(): Promise<void> {
    const table = this.page.locator(this.table);
    await expect(table.first()).toBeVisible();
  }
}
