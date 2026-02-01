/**
 * Login Page Object Model
 */

import { Page, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';
import { TEST_USERS, TestUser, PAGE_ROUTES } from '@types/index';

/**
 * Login Page class
 */
export class LoginPage extends BasePage {
  // Selectors - Using data-testid for stable testing
  private readonly container = '[data-testid="login-page"]';
  private readonly title = '[data-testid="login-title"]';
  private readonly form = '[data-testid="login-form"]';
  private readonly usernameInput = '[data-testid="username-input"]';
  private readonly passwordInput = '[data-testid="password-input"]';
  private readonly submitButton = '[data-testid="login-button"]';
  private readonly loginButton = '[data-testid="login-button"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to login page
   */
  async goto(): Promise<void> {
    await this.page.goto(PAGE_ROUTES.LOGIN);
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Wait for login page to be loaded
   */
  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('domcontentloaded');
    // Wait for the login page container to be attached to DOM
    await this.page.waitForSelector(this.container, { state: 'attached', timeout: TIMEOUTS.DEFAULT });
  }

  /**
   * Check if login page is visible
   */
  async isLoginPageVisible(): Promise<boolean> {
    const loginPageLocator = this.page.locator(this.container);
    return await loginPageLocator.isVisible().catch(() => false);
  }

  /**
   * Get page title text
   */
  async getTitleText(): Promise<string> {
    const titleLocator = this.page.locator(this.title);
    return (await titleLocator.textContent()) || '';
  }

  /**
   * Fill in username
   */
  async fillUsername(username: string): Promise<void> {
    const input = this.page.locator(this.usernameInput);
    await input.waitFor({ state: 'attached', timeout: TIMEOUTS.DEFAULT });
    await input.fill(username);
  }

  /**
   * Fill in password
   */
  async fillPassword(password: string): Promise<void> {
    const input = this.page.locator(this.passwordInput);
    await input.waitFor({ state: 'attached', timeout: TIMEOUTS.DEFAULT });
    await input.fill(password);
  }

  /**
   * Fill in both username and password
   */
  async fillCredentials(username: string, password: string): Promise<void> {
    await this.fillUsername(username);
    await this.fillPassword(password);
  }

  /**
   * Click login button
   */
  async clickLogin(): Promise<void> {
    const button = this.page.locator(this.submitButton);
    await button.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    await button.click();
  }

  /**
   * Perform login with username and password
   */
  async login(username: string, password: string): Promise<void> {
    await this.goto();
    await this.fillCredentials(username, password);
    await this.clickLogin();
    // Wait for navigation to dashboard
    await this.page.waitForURL(/\/dashboard/, { timeout: TIMEOUTS.NAVIGATION });
  }

  /**
   * Perform login as a test user
   */
  async loginAs(user: TestUser): Promise<void> {
    await this.login(user.username, user.password);
  }

  /**
   * Perform login as a predefined test user role
   */
  async loginAsRole(role: keyof typeof TEST_USERS): Promise<void> {
    const user = TEST_USERS[role];
    await this.login(user.username, user.password);
  }

  /**
   * Perform login and expect failure
   */
  async loginWithExpectation(username: string, password: string, shouldSucceed: boolean): Promise<void> {
    await this.goto();
    await this.fillCredentials(username, password);
    await this.clickLogin();

    if (shouldSucceed) {
      // Should redirect to dashboard
      await this.page.waitForURL(/\/dashboard/, { timeout: TIMEOUTS.NAVIGATION });
    } else {
      // Should show error message
      await this.waitForErrorMessage();
    }
  }

  /**
   * Wait for error message to appear
   */
  async waitForErrorMessage(): Promise<string> {
    const errorLocator = this.page.locator('.ant-message-error');
    await errorLocator.waitFor({ state: 'visible', timeout: TIMEOUTS.DEFAULT });
    return (await errorLocator.textContent()) || '';
  }

  /**
   * Get error message text
   */
  async getErrorMessage(): Promise<string | null> {
    const errorLocator = this.page.locator('.ant-message-error');
    const isVisible = await errorLocator.isVisible().catch(() => false);
    if (isVisible) {
      return await errorLocator.textContent();
    }
    return null;
  }

  /**
   * Verify login form is visible
   */
  async verifyFormVisible(): Promise<void> {
    const formLocator = this.page.locator(this.form);
    await expect(formLocator).toBeVisible();
  }

  /**
   * Verify username input is visible
   */
  async verifyUsernameInputVisible(): Promise<void> {
    const inputLocator = this.page.locator(this.usernameInput);
    await expect(inputLocator).toBeVisible();
  }

  /**
   * Verify password input is visible
   */
  async verifyPasswordInputVisible(): Promise<void> {
    const inputLocator = this.page.locator(this.passwordInput);
    await expect(inputLocator).toBeVisible();
  }

  /**
   * Verify login button is visible
   */
  async verifyLoginButtonVisible(): Promise<void> {
    const buttonLocator = this.page.locator(this.submitButton);
    await expect(buttonLocator).toBeVisible();
  }

  /**
   * Verify all login form elements are visible
   */
  async verifyLoginPageElements(): Promise<void> {
    await this.verifyFormVisible();
    await this.verifyUsernameInputVisible();
    await this.verifyPasswordInputVisible();
    await this.verifyLoginButtonVisible();
  }

  /**
   * Check if login button is enabled
   */
  async isLoginButtonEnabled(): Promise<boolean> {
    const button = this.page.locator(this.submitButton);
    return await button.isEnabled();
  }

  /**
   * Get authentication token from localStorage
   */
  async getAuthToken(): Promise<string | null> {
    return await this.getLocalStorageItem('auth_token');
  }

  /**
   * Check if user is authenticated
   */
  async isAuthenticated(): Promise<boolean> {
    const token = await this.getAuthToken();
    return token !== null;
  }

  /**
   * Verify successful login by checking URL
   */
  async verifySuccessfulLogin(): Promise<void> {
    await this.page.waitForURL(/\/dashboard/, { timeout: TIMEOUTS.NAVIGATION });
    const currentUrl = this.getCurrentUrl();
    expect(currentUrl).toMatch(/\/dashboard/);
  }

  /**
   * Verify login failed (still on login page or error shown)
   */
  async verifyLoginFailed(): Promise<void> {
    const errorMessage = await this.getErrorMessage();
    expect(errorMessage).toBeTruthy();
  }
}
