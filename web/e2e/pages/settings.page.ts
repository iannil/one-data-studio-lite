/**
 * Settings Page Object Model
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { TIMEOUTS } from '@utils/constants';

/**
 * Settings Page class
 */
export class SettingsPage extends BasePage {
  // Selectors
  private readonly container = '[data-testid="settings-page"], .settings-page';
  private readonly saveButton = 'button:has-text("保存"), button:save';
  private readonly resetButton = 'button:has-text("重置"), button:reset';
  private readonly tabList = '.settings-tabs, .ant-tabs';
  private readonly formSection = '.settings-form, .settings-section';
  private readonly successMessage = '.ant-message-success, .success-message';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to settings page
   */
  async goto(): Promise<void> {
    await super.goto('/settings');
  }

  /**
   * Navigate to settings tab
   */
  async gotoTab(tabName: string): Promise<void> {
    await super.goto();
    await this.waitForPageLoad();

    const tab = this.page.locator(`.ant-tabs-tab:has-text("${tabName}")`);
    const count = await tab.count();

    if (count > 0) {
      await tab.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Wait for page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.waitForElement(this.container);
    await this.waitForLoading();
  }

  /**
   * Get all settings tabs
   */
  async getSettingsTabs(): Promise<string[]> {
    const tabs = this.page.locator(`${this.tabList} .ant-tabs-tab`);
    const count = await tabs.count();
    const labels: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await tabs.nth(i).textContent();
      if (text) labels.push(text.trim());
    }

    return labels;
  }

  /**
   * Fill setting field
   */
  async fillSetting(fieldLabel: string, value: string): Promise<void> {
    const input = this.page.locator(`.ant-form-item-label:has-text("${fieldLabel}")`)
      .locator('input, textarea, .ant-input');

    const count = await input.count();

    if (count > 0) {
      await input.first().fill(value);
    }
  }

  /**
   * Select setting option
   */
  async selectSetting(fieldLabel: string, option: string): Promise<void> {
    const select = this.page.locator(`.ant-form-item-label:has-text("${fieldLabel}")`)
      .locator('.ant-select');

    await select.click();
    await this.page.waitForTimeout(300);

    const optionLocator = this.page.locator(`.ant-select-dropdown-option:has-text("${option}")`);
    await optionLocator.click();
  }

  /**
   * Toggle switch setting
   */
  async toggleSetting(fieldLabel: string): Promise<void> {
    const switch_ = this.page.locator(`.ant-form-item-label:has-text("${fieldLabel}")`)
      .locator('.ant-switch');

    await switch_.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Save settings
   */
  async saveSettings(): Promise<void> {
    const button = this.page.locator(this.saveButton);
    await button.click();
    await this.waitForLoading();

    // Verify success message
    const message = this.page.locator(this.successMessage);
    await expect(message.first()).toBeVisible();
  }

  /**
   * Reset settings to default
   */
  async resetSettings(): Promise<void> {
    const button = this.page.locator(this.resetButton);
    const count = await button.count();

    if (count > 0) {
      await button.click();
      await this.page.waitForTimeout(500);

      // Confirm reset
      const confirmButton = this.page.locator('.ant-modal button:has-text("确定")');
      const confirmCount = await confirmButton.count();

      if (confirmCount > 0) {
        await confirmButton.click();
        await this.waitForLoading();
      }
    }
  }

  /**
   * Get setting value
   */
  async getSettingValue(fieldLabel: string): Promise<string> {
    const input = this.page.locator(`.ant-form-item-label:has-text("${fieldLabel}")`)
      .locator('input, textarea, .ant-input');

    const value = await input.inputValue();
    return value || '';
  }

  /**
   * Verify setting value
   */
  async verifySettingValue(fieldLabel: string, expectedValue: string): Promise<void> {
    const value = await this.getSettingValue(fieldLabel);
    expect(value).toBe(expectedValue);
  }

  /**
   * Navigate to general settings
   */
  async gotoGeneralSettings(): Promise<void> {
    await this.gotoTab('通用');
  }

  /**
   * Navigate to security settings
   */
  async gotoSecuritySettings(): Promise<void> {
    await this.gotoTab('安全');
  }

  /**
   * Get current settings
   */
  async getCurrentSettings(): Promise<Record<string, string>> {
    const settings: Record<string, string> = {};

    const formItems = this.page.locator('.ant-form-item');
    const count = await formItems.count();

    for (let i = 0; i < count; i++) {
      const item = formItems.nth(i);
      const label = await item.locator('.ant-form-item-label > label, label').textContent();
      const input = item.locator('input, select, .ant-switch, .ant-checkbox-wrapper');

      const value = await input.evaluate((el) => {
        if (el instanceof HTMLInputElement) {
          return el.type === 'checkbox' ? String(el.checked) : el.value;
        }
        if (el instanceof HTMLSelectElement) {
          return el.value;
        }
        if (el instanceof HTMLElement && el.classList.contains('ant-switch')) {
          return el.getAttribute('aria-checked') || 'false';
        }
        return '';
      });

      if (label) {
        settings[label.trim()] = value;
      }
    }

    return settings;
  }

  /**
   * Upload logo
   */
  async uploadLogo(filePath: string): Promise<void> {
    const uploadInput = this.page.locator('input[type="file"][accept*="image"]');
    const count = await uploadInput.count();

    if (count > 0) {
      await uploadInput.setInputFiles(filePath);
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Clear cache
   */
  async clearCache(): Promise<void> {
    const clearButton = this.page.locator('button:has-text("清除缓存"), button:has-text("清理缓存")');
    const count = await clearButton.count();

    if (count > 0) {
      await clearButton.click();
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Test notification
   */
  async testNotification(): Promise<void> {
    const testButton = this.page.locator('button:has-text("测试通知"), button:has-text("发送测试通知")');
    const count = await testButton.count();

    if (count > 0) {
      await testButton.click();
      await this.page.waitForTimeout(2000);

      const message = this.page.locator('.ant-message');
      await expect(message.first()).toBeVisible();
    }
  }

  /**
   * Verify settings were saved
   */
  async verifySettingsSaved(): Promise<void> {
    const message = this.page.locator('.ant-message-success');
    await expect(message.first()).toBeVisible();
  }

  /**
   * Get API configuration
   */
  async getApiConfig(): Promise<{
    baseUrl: string;
    timeout: number;
    retryCount: number;
  }> {
    await this.gotoTab('API');

    const baseUrl = await this.getSettingValue('API地址');
    const timeout = parseInt(await this.getSettingValue('请求超时') || '30000');
    const retryCount = parseInt(await this.getSettingValue('重试次数') || '3');

    return {
      baseUrl,
      timeout,
      retryCount,
    };
  }

  /**
   * Get security settings
   */
  async getSecuritySettings(): Promise<{
    passwordPolicy: string;
    sessionTimeout: number;
    mfaEnabled: boolean;
    loginAttempts: number;
  }> {
    await this.gotoTab('安全');

    const passwordPolicy = await this.getSettingValue('密码策略');
    const sessionTimeout = parseInt(await this.getSettingValue('会话超时') || '3600');
    const mfaEnabled = (await this.getSettingValue('启用MFA') === 'true');
    const loginAttempts = parseInt(await this.getSettingValue('登录尝试次数') || '5');

    return {
      passwordPolicy,
      sessionTimeout,
      mfaEnabled,
      loginAttempts,
    };
  }

  /**
   * Verify setting is readonly
   */
  async verifySettingReadOnly(fieldLabel: string): Promise<boolean> {
    const input = this.page.locator(`.ant-form-item-label:has-text("${fieldLabel}")`)
      .locator('input, textarea, .ant-input');

    return await input.isDisabled();
  }

  /**
   * Get all form validation errors
   */
  async getValidationErrors(): Promise<Array<{ field: string; message: string }>> {
    const errors = this.page.locator('.ant-form-item-explain-error, .error-message');
    const count = await errors.count();
    const validationErrors: Array<{ field: string; message: string }> = [];

    for (let i = 0; i < count; i++) {
      const error = errors.nth(i);
      const field = await error.locator('.ant-form-item-label > label, label').textContent() || '';
      const message = await error.textContent() || '';
      validationErrors.push({ field, message: message.trim() });
    }

    return validationErrors;
  }

  /**
   * Navigate to profile settings
   */
  async gotoProfileSettings(): Promise<void> {
    await this.gotoTab('个人资料');
  }

  /**
   * Update profile settings
   */
  async updateProfile(data: {
    displayName?: string;
    email?: string;
    phone?: string;
  }): Promise<void> {
    await this.gotoProfileSettings();

    if (data.displayName) {
      await this.fillSetting('显示名称', data.displayName);
    }

    if (data.email) {
      await this.fillSetting('邮箱', data.email);
    }

    if (data.phone) {
      await this.fillSetting('手机号', data.phone);
    }

    await this.saveSettings();
  }

  /**
   * Change password
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.gotoTab('安全');

    await this.fillSetting('当前密码', currentPagePassword);
    await this.fillSetting('新密码', newPassword);
    await this.fillSetting('确认密码', newPassword);

    await this.saveSettings();

    const successMessage = this.page.locator('.ant-message-success');
    await expect(successMessage.first()).toBeVisible();
  }

  /**
   * Enable two-factor authentication
   */
  async enable2FA(): Promise<void> {
    await this.gotoTab('安全');

    const mfaSwitch = this.page.locator('input[name="mfa_enabled"], .ant-switch');
    await mfaSwitch.click();
    await this.page.waitForTimeout(300);

    await this.saveSettings();
  }

  /**
   * Get notification settings
   */
  async getNotificationSettings(): Promise<{
    emailEnabled: boolean;
    pushEnabled: boolean;
    webhookUrl: string;
    notifyOn: string[];
  }> {
    await this.gotoTab('通知');

    const emailEnabled = (await this.page.locator('input[name="email_enabled"]').isChecked()) ?? false;
    const pushEnabled = (await this.page.locator('input[name="push_enabled"]').isChecked()) ?? false;
    const webhookUrl = await this.page.locator('input[name="webhook_url"]').inputValue() || '';

    return {
      emailEnabled,
      pushEnabled,
      webhookUrl,
      notifyOn: [],
    };
  }

  /**
   * Configure notifications
   */
  async configureNotifications(settings: {
    email?: boolean;
    push?: boolean;
    webhook?: string;
  }): Promise<void> {
    await this.gotoTab('通知');

    if (settings.email !== undefined) {
      const emailSwitch = this.page.locator('input[name="email_enabled"]');
      const current = await emailSwitch.isChecked();
      if (current !== settings.email) {
        await emailSwitch.click();
      }
    }

    if (settings.push !== undefined) {
      const pushSwitch = this.page.locator('input[name="push_enabled"]');
      const current = await pushSwitch.isChecked();
      if (current !== settings.push) {
        await pushSwitch.click();
      }
    }

    if (settings.webhook) {
      await this.fillSetting('Webhook URL', settings.webhook);
    }

    await this.saveSettings();
  }

  /**
   * Verify settings tab is accessible
   */
  async verifyTabAccessible(tabName: string): Promise<boolean> {
    await super.goto();

    const tab = this.page.locator(`.ant-tabs-tab:has-text("${tabName}")`);
    return await tab.count() > 0;
  }
}
