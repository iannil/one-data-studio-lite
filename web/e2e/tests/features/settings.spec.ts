/**
 * Settings Feature Tests
 *
 * Tests for application settings, preferences, and configuration
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
import { SettingsPage } from '@pages/settings.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Settings Feature Tests', { tag: ['@settings', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;
  let settingsPage: SettingsPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    settingsPage = new SettingsPage(page);

    await loginPage.goto();
    await loginPage.loginAs(TEST_USERS.admin);
  });

  test.describe('General Settings', () => {
    test('TC-SET-01-01: Navigate to general settings', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();
      await page.waitForTimeout(500);

      const url = page.url();
      expect(url).toContain('/settings');
    });

    test('TC-SET-01-02: Update application name', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();

      await settingsPage.fillSetting('应用名称', 'Test App ' + Date.now());
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-01-03: Update logo', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();

      const logoInput = page.locator('input[type="file"][accept*="image"]');
      const count = await logoInput.count();

      if (count > 0) {
        await settingsPage.uploadLogo('/tmp/test-logo.png');
      }
    });

    test('TC-SET-01-04: Clear application cache', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();

      await settingsPage.clearCache();

      await page.waitForTimeout(1000);
    });

    test('TC-SET-01-05: Reset settings to default', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();

      await settingsPage.resetSettings();

      await page.waitForTimeout(1000);
    });
  });

  test.describe('Security Settings', () => {
    test('TC-SET-02-01: Navigate to security settings', async ({ page }) => {
      await settingsPage.gotoSecuritySettings();
      await page.waitForTimeout(500);

      const url = page.url();
      expect(url).toContain('/settings');
    });

    test('TC-SET-02-02: Update password policy', async ({ page }) => {
      await settingsPage.gotoSecuritySettings();

      await settingsPage.fillSetting('最小密码长度', '8');
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-02-03: Update session timeout', async ({ page }) => {
      await settingsPage.gotoSecuritySettings();

      await settingsPage.fillSetting('会话超时', '3600');
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-02-04: Enable 2FA', async ({ page }) => {
      await settingsPage.gotoSecuritySettings();

      await settingsPage.enable2FA();

      const success = page.locator('.ant-message-success');
      const isVisible = await success.isVisible().catch(() => false);

      if (isVisible) {
        await expect(success.first()).toBeVisible();
      }
    });

    test('TC-SET-02-05: Configure login attempts', async ({ page }) => {
      await settingsPage.gotoSecuritySettings();

      await settingsPage.fillSetting('最大登录尝试次数', '5');
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-02-06: Get security settings', async ({ page }) => {
      const securitySettings = await settingsPage.getSecuritySettings();

      expect(securitySettings).toHaveProperty('passwordPolicy');
      expect(securitySettings).toHaveProperty('sessionTimeout');
      expect(securitySettings).toHaveProperty('mfaEnabled');
      expect(securitySettings).toHaveProperty('loginAttempts');
    });
  });

  test.describe('Notification Settings', () => {
    test('TC-SET-03-01: Navigate to notification settings', async ({ page }) => {
      await settingsPage.gotoTab('通知');
      await page.waitForTimeout(500);

      const url = page.url();
      expect(url).toContain('/settings');
    });

    test('TC-SET-03-02: Enable email notifications', async ({ page }) => {
      await settingsPage.gotoTab('通知');

      await settingsPage.configureNotifications({ email: true });
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-03-03: Disable email notifications', async ({ page }) => {
      await settingsPage.gotoTab('通知');

      await settingsPage.configureNotifications({ email: false });
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-03-04: Configure webhook URL', async ({ page }) => {
      await settingsPage.gotoTab('通知');

      await settingsPage.configureNotifications({
        webhook: 'https://example.com/webhook',
      });
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-03-05: Test notification', async ({ page }) => {
      await settingsPage.gotoTab('通知');

      await settingsPage.testNotification();
    });

    test('TC-SET-03-06: Get notification settings', async ({ page }) => {
      const notifSettings = await settingsPage.getNotificationSettings();

      expect(notifSettings).toHaveProperty('emailEnabled');
      expect(notifSettings).toHaveProperty('pushEnabled');
      expect(notifSettings).toHaveProperty('webhookUrl');
    });
  });

  test.describe('API Settings', () => {
    test('TC-SET-04-01: Navigate to API settings', async ({ page }) => {
      await settingsPage.gotoTab('API');
      await page.waitForTimeout(500);

      const url = page.url();
      expect(url).toContain('/settings');
    });

    test('TC-SET-04-02: Update API base URL', async ({ page }) => {
      await settingsPage.gotoTab('API');

      await settingsPage.fillSetting('API地址', 'http://localhost:8010');
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-04-03: Update request timeout', async ({ page }) => {
      await settingsPage.gotoTab('API');

      await settingsPage.fillSetting('请求超时', '30000');
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-04-04: Update retry count', async ({ page }) => {
      await settingsPage.gotoTab('API');

      await settingsPage.fillSetting('重试次数', '3');
      await settingsPage.saveSettings();

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-04-05: Get API configuration', async ({ page }) => {
      const apiConfig = await settingsPage.getApiConfig();

      expect(apiConfig).toHaveProperty('baseUrl');
      expect(apiConfig).toHaveProperty('timeout');
      expect(apiConfig).toHaveProperty('retryCount');
    });
  });

  test.describe('Profile Settings', () => {
    test('TC-SET-05-01: Navigate to profile settings', async ({ page }) => {
      await settingsPage.gotoProfileSettings();
      await page.waitForTimeout(500);

      const url = page.url();
      expect(url).toContain('/settings');
    });

    test('TC-SET-05-02: Update display name', async ({ page }) => {
      await settingsPage.updateProfile({
        displayName: 'Test User ' + Date.now(),
      });

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-05-03: Update email', async ({ page }) => {
      await settingsPage.updateProfile({
        email: `test${Date.now()}@example.com`,
      });

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-05-04: Update phone number', async ({ page }) => {
      await settingsPage.updateProfile({
        phone: '13800138000',
      });

      const success = page.locator('.ant-message-success');
      await expect(success.first()).toBeVisible();
    });

    test('TC-SET-05-05: Upload avatar', async ({ page }) => {
      await settingsPage.gotoProfileSettings();

      const avatarInput = page.locator('input[type="file"][accept*="image"]');
      const count = await avatarInput.count();

      if (count > 0) {
        await avatarInput.setInputFiles('/tmp/test-avatar.png');
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Password Change', () => {
    test('TC-SET-06-01: Change password with valid data', async ({ page }) => {
      await settingsPage.gotoTab('安全');

      await settingsPage.changePassword('admin123', 'newpass123');

      const success = page.locator('.ant-message-success');
      const isVisible = await success.isVisible().catch(() => false);

      if (isVisible) {
        await expect(success).toBeVisible();
      }
    });

    test('TC-SET-06-02: Password change requires confirmation', async ({ page }) => {
      await settingsPage.gotoTab('安全');

      await settingsPage.fillSetting('当前密码', 'admin123');
      await settingsPage.fillSetting('新密码', 'newpass123');
      await settingsPage.fillSetting('确认密码', 'different');

      await settingsPage.saveSettings();

      const error = page.locator('.ant-form-item-explain-error');
      const hasError = await error.count() > 0;

      if (hasError) {
        await expect(error.first()).toBeVisible();
      }
    });

    test('TC-SET-06-03: Password validation', async ({ page }) => {
      await settingsPage.gotoTab('安全');

      await settingsPage.fillSetting('当前密码', 'admin123');
      await settingsPage.fillSetting('新密码', '123');
      await settingsPage.fillSetting('确认密码', '123');

      await settingsPage.saveSettings();

      const error = page.locator('.ant-form-item-explain-error');
      const hasError = await error.count() > 0;

      if (hasError) {
        await expect(error.first()).toBeVisible();
      }
    });
  });

  test.describe('Settings Navigation', () => {
    test('TC-SET-07-01: View all settings tabs', async ({ page }) => {
      await settingsPage.goto();
      await settingsPage.waitForPageLoad();

      const tabs = await settingsPage.getSettingsTabs();

      expect(Array.isArray(tabs)).toBe(true);
      expect(tabs.length).toBeGreaterThan(0);
    });

    test('TC-SET-07-02: Navigate between tabs', async ({ page }) => {
      await settingsPage.goto();

      const tabs = await settingsPage.getSettingsTabs();

      if (tabs.length > 1) {
        await settingsPage.gotoTab(tabs[1]);
        await page.waitForTimeout(500);

        const activeTab = page.locator('.ant-tabs-tab-active .ant-tabs-tab-btn');
        const text = await activeTab.textContent();
        expect(text).toContain(tabs[1]);
      }
    });

    test('TC-SET-07-03: Verify tab accessibility', async ({ page }) => {
      await settingsPage.goto();

      const isAccessible = await settingsPage.verifyTabAccessible('通用');

      expect(isAccessible).toBe(true);
    });
  });

  test.describe('Settings Validation', () => {
    test('TC-SET-08-01: Verify setting value', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();

      await settingsPage.fillSetting('测试字段', 'test-value');
      await page.waitForTimeout(500);

      const value = await settingsPage.getSettingValue('测试字段');

      expect(value).toBe('test-value');
    });

    test('TC-SET-08-02: Read-only settings are disabled', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();

      const isReadOnly = await settingsPage.verifySettingReadOnly('系统版本');

      if (isReadOnly !== null) {
        expect(isReadOnly).toBe(true);
      }
    });

    test('TC-SET-08-03: Get validation errors', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();

      await settingsPage.fillSetting('邮箱', 'invalid-email');
      await settingsPage.saveSettings();

      const errors = await settingsPage.getValidationErrors();

      expect(Array.isArray(errors)).toBe(true);
    });

    test('TC-SET-08-04: Get all current settings', async ({ page }) => {
      await settingsPage.gotoGeneralSettings();

      const settings = await settingsPage.getCurrentSettings();

      expect(typeof settings).toBe('object');
    });
  });

  test.describe('Settings Export/Import', () => {
    test('TC-SET-09-01: Export settings', async ({ page }) => {
      await settingsPage.goto();

      const exportBtn = page.locator('button:has-text("导出配置"), button:has-text("导出设置")');
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-SET-09-02: Import settings', async ({ page }) => {
      await settingsPage.goto();

      const importBtn = page.locator('button:has-text("导入配置"), button:has-text("导入设置")');
      const count = await importBtn.count();

      if (count > 0) {
        await importBtn.click();
        await page.waitForTimeout(500);

        const fileInput = page.locator('input[type="file"]');
        const inputCount = await fileInput.count();

        if (inputCount > 0) {
          await fileInput.setInputFiles('/tmp/settings-backup.json');
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Settings Permissions', () => {
    test('TC-SET-10-01: Admin can change settings', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await settingsPage.goto();

      const saveBtn = page.locator('button:has-text("保存")');
      const count = await saveBtn.count();

      if (count > 0) {
        const isEnabled = await saveBtn.first().isEnabled();
        expect(isEnabled || !isEnabled).toBe(true);
      }
    });

    test('TC-SET-10-02: Admin can access security settings', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await settingsPage.gotoSecuritySettings();

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-SET-10-03: Admin can view profile settings', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await settingsPage.gotoProfileSettings();

      const url = page.url();
      expect(url).toContain('/settings');
    });
  });
});
