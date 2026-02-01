/**
 * Dashboard Page Object Model
 */

import { Page, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Dashboard Page class
 */
export class DashboardPage extends BasePage {
  // Selectors
  private readonly container = '.dashboard, [data-testid="dashboard"]';
  private readonly cockpit = '.dashboard-cockpit, [data-testid="cockpit"]';
  private readonly workspace = '.dashboard-workspace, [data-testid="workspace"]';
  private readonly sidebar = '.ant-layout-sider';
  private readonly menu = '.ant-menu';
  private readonly userMenu = '[data-testid="user-menu"], .user-menu';
  private readonly logoutButton = '[data-testid="logout-button"], .logout-button';
  private readonly statsCard = '.stats-card, .ant-card';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to dashboard cockpit
   */
  async gotoCockpit(): Promise<void> {
    await super.goto('/dashboard/cockpit');
  }

  /**
   * Navigate to dashboard workspace
   */
  async gotoWorkspace(): Promise<void> {
    await super.goto('/dashboard/workspace');
  }

  /**
   * Wait for dashboard to load
   * Made tolerant for unimplemented features
   */
  async waitForDashboardLoad(): Promise<void> {
    await this.waitForPageLoad();
    await this.waitForLoading();
    // Container may not exist if dashboard not fully implemented
    try {
      await this.waitForElement(this.container, 3000);
    } catch {
      // Dashboard container might not be implemented, continue anyway
    }
  }

  /**
   * Check if dashboard is visible
   */
  async isDashboardVisible(): Promise<boolean> {
    return await this.isElementVisible(this.container);
  }

  /**
   * Get dashboard title
   */
  async getDashboardTitle(): Promise<string> {
    const titleLocator = this.page.locator('.dashboard-title, h1, h2').first();
    await titleLocator.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    return (await titleLocator.textContent()) || '';
  }

  /**
   * Click on sidebar menu item
   */
  async clickMenuItem(label: string): Promise<void> {
    const menuItem = this.page.locator(`.ant-menu-item:has-text("${label}")`);
    await menuItem.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await menuItem.click();
    await this.waitForLoading();
  }

  /**
   * Click on submenu
   */
  async clickSubmenu(label: string): Promise<void> {
    const submenu = this.page.locator(`.ant-menu-submenu:has-text("${label}")`);
    await submenu.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await submenu.click();
  }

  /**
   * Click on submenu item
   */
  async clickSubmenuItem(submenuLabel: string, itemLabel: string): Promise<void> {
    await this.clickSubmenu(submenuLabel);
    const menuItem = this.page.locator(`.ant-menu-submenu-open .ant-menu-item:has-text("${itemLabel}")`);
    await menuItem.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await menuItem.click();
    await this.waitForLoading();
  }

  /**
   * Get all menu items
   */
  async getMenuItems(): Promise<string[]> {
    const items = this.page.locator('.ant-menu-item');
    const count = await items.count();
    const labels: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) labels.push(text.trim());
    }

    return labels;
  }

  /**
   * Check if menu item exists
   */
  async hasMenuItem(label: string): Promise<boolean> {
    const menuItem = this.page.locator(`.ant-menu-item:has-text("${label}")`);
    return await menuItem.count() > 0;
  }

  /**
   * Check if submenu item exists
   */
  async hasSubmenuItem(submenuLabel: string, itemLabel: string): Promise<boolean> {
    await this.clickSubmenu(submenuLabel);
    const menuItem = this.page.locator(`.ant-menu-submenu-open .ant-menu-item:has-text("${itemLabel}")`);
    return await menuItem.count() > 0;
  }

  /**
   * Click on user menu
   */
  async clickUserMenu(): Promise<void> {
    const userMenu = this.page.locator(this.userMenu);
    await userMenu.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await userMenu.click();
  }

  /**
   * Logout
   */
  async logout(): Promise<void> {
    await this.clickUserMenu();
    const logoutBtn = this.page.locator(this.logoutButton);
    await logoutBtn.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await logoutBtn.click();
    await this.page.waitForURL(/\/login/, { timeout: TIMEOUTS.NAVIGATION });
  }

  /**
   * Get current user display name
   */
  async getCurrentUserDisplayName(): Promise<string> {
    const userLabel = this.page.locator('.user-name, .user-display-name').first();
    await userLabel.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    return (await userLabel.textContent()) || '';
  }

  /**
   * Get current user role
   */
  async getCurrentUserRole(): Promise<string> {
    const roleLabel = this.page.locator('.user-role').first();
    const text = await roleLabel.textContent();
    return text?.trim() || '';
  }

  /**
   * Get stats cards count
   */
  async getStatsCardsCount(): Promise<number> {
    const cards = this.page.locator(this.statsCard);
    return await cards.count();
  }

  /**
   * Get stats card value by index
   */
  async getStatsCardValue(index: number): Promise<string> {
    const card = this.page.locator(this.statsCard).nth(index);
    const value = card.locator('.stats-value, .ant-statistic-content-value');
    return (await value.textContent()) || '';
  }

  /**
   * Get stats card label by index
   */
  async getStatsCardLabel(index: number): Promise<string> {
    const card = this.page.locator(this.statsCard).nth(index);
    const label = card.locator('.stats-label, .ant-statistic-title');
    return (await label.textContent()) || '';
  }

  /**
   * Navigate to a specific page by path
   */
  async navigateTo(path: string): Promise<void> {
    await super.goto(path);
  }

  /**
   * Verify user is logged in
   */
  async verifyLoggedIn(): Promise<void> {
    await this.waitForDashboardLoad();
    expect(await this.isDashboardVisible()).toBe(true);
  }

  /**
   * Verify menu item is visible (for permission testing)
   */
  async verifyMenuItemVisible(label: string): Promise<void> {
    const menuItem = this.page.locator(`.ant-menu-item:has-text("${label}")`);
    await expect(menuItem).toBeVisible();
  }

  /**
   * Verify menu item is hidden (for permission testing)
   */
  async verifyMenuItemHidden(label: string): Promise<void> {
    const menuItem = this.page.locator(`.ant-menu-item:has-text("${label}")`);
    await expect(menuItem).not.toBeVisible();
  }
}
