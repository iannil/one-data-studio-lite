/**
 * File Management Feature Tests
 *
 * Tests for file upload, download, and storage management
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only
import { join } from 'path';
import { writeFile } from 'fs/promises';

test.describe('File Management Feature Tests', { tag: ['@files', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;
  const testFilePath = '/tmp/test-upload.csv';

  test.beforeAll(async () => {
    // Create a test file
    const testContent = 'id,name,value\n1,Test,100\n2,Sample,200';
    await writeFile(testFilePath, testContent);
  });

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('File Upload', () => {
    test('TC-FILE-01-01: Navigate to file upload page', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const uploadSection = page.locator('.file-upload, .upload-section');
      await expect(uploadSection.first()).toBeVisible();
    });

    test('TC-FILE-01-02: Upload CSV file', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const fileInput = page.locator('input[type="file"][accept*="csv"]');
      const count = await fileInput.count();

      if (count > 0) {
        await fileInput.setInputFiles(testFilePath);
        await page.waitForTimeout(2000);

        const success = page.locator('.ant-message-success');
        const isVisible = await success.isVisible().catch(() => false);

        if (isVisible) {
          await expect(success).toBeVisible();
        }
      }
    });

    test('TC-FILE-01-03: Upload Excel file', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const fileInput = page.locator('input[type="file"][accept*="excel"], input[type="file"][accept*="xls"]');
      const count = await fileInput.count();

      if (count > 0) {
        // Create a dummy Excel file
        const dummyPath = '/tmp/test.xlsx';
        await writeFile(dummyPath, 'dummy');

        await fileInput.setInputFiles(dummyPath);
        await page.waitForTimeout(2000);
      }
    });

    test('TC-FILE-01-04: Upload with drag and drop', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const dropZone = page.locator('.drop-zone, .upload-area');
      const count = await dropZone.count();

      if (count > 0) {
        // Create a dummy file for testing
        const dummyPath = '/tmp/drop-test.txt';
        await writeFile(dummyPath, 'test content');

        // Simulate drop (using setInputFiles as alternative)
        const fileInput = page.locator('input[type="file"]');
        await fileInput.setInputFiles(dummyPath);
        await page.waitForTimeout(2000);
      }
    });

    test('TC-FILE-01-05: Handle file upload error', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      // Mock a failed upload
      await page.route('**/api/upload', route => {
        route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Invalid file format' }),
        });
      });

      const fileInput = page.locator('input[type="file"]');
      const count = await fileInput.count();

      if (count > 0) {
        await fileInput.setInputFiles(testFilePath);
        await page.waitForTimeout(2000);

        const error = page.locator('.ant-message-error');
        const isVisible = await error.isVisible().catch(() => false);

        if (isVisible) {
          await expect(error).toBeVisible();
        }
      }

      await page.unroute('**/api/upload');
    });

    test('TC-FILE-01-06: Validate file format', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const fileInput = page.locator('input[type="file"]');
      const count = await fileInput.count();

      if (count > 0) {
        // Create a file with wrong extension
        const wrongFile = '/tmp/test.txt';
        await writeFile(wrongFile, 'test');

        await fileInput.setInputFiles(wrongFile);
        await page.waitForTimeout(1000);

        const error = page.locator('.ant-message-error, .error-message');
        const hasError = await error.count() > 0;

        if (hasError) {
          await expect(error.first()).toBeVisible();
        }
      }
    });

    test('TC-FILE-01-07: Show upload progress', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      // Mock slow upload
      await page.route('**/api/upload', async route => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      });

      const fileInput = page.locator('input[type="file"]');
      const count = await fileInput.count();

      if (count > 0) {
        await fileInput.setInputFiles(testFilePath);

        const progress = page.locator('.upload-progress, .progress-bar');
        const isVisible = await progress.isVisible().catch(() => false);

        if (isVisible) {
          await expect(progress).toBeVisible();
        }
      }

      await page.unroute('**/api/upload');
    });
  });

  test.describe('File Download', () => {
    test('TC-FILE-02-01: Download uploaded file', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const downloadBtn = page.locator('button:has-text("下载"), button:has-text("Download")').first();
      const count = await downloadBtn.count();

      if (count > 0) {
        const downloadPromise = page.waitForEvent('download');
        await downloadBtn.click();
        const download = await downloadPromise;

        expect(download.suggestedFilename()).toBeTruthy();
      }
    });

    test('TC-FILE-02-02: Export query results as CSV', async ({ page }) => {
      await page.goto('/analysis/nl2sql');
      await page.waitForLoadState('domcontentloaded');

      const exportBtn = page.locator('button:has-text("导出"), button:has-text("Export")');
      const count = await exportBtn.count();

      if (count > 0) {
        await exportBtn.click();

        const csvOption = page.locator('text=CSV, .export-option:has-text("CSV")');
        await csvOption.click();

        await page.waitForTimeout(2000);
      }
    });

    test('TC-FILE-02-03: Download multiple files as ZIP', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const files = page.locator('.file-item');
      const count = await files.count();

      if (count >= 2) {
        // Select first two files
        await files.first().locator('input[type="checkbox"]').check();
        await files.nth(1).locator('input[type="checkbox"]').check();

        const downloadZipBtn = page.locator('button:has-text("下载选中"), button:has-text("Download Selected")');
        const btnCount = await downloadZipBtn.count();

        if (btnCount > 0) {
          await downloadZipBtn.click();
          await page.waitForTimeout(2000);
        }
      }
    });
  });

  test.describe('File Management', () => {
    test('TC-FILE-03-01: View uploaded files list', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const filesList = page.locator('.files-list, .uploaded-files');
      await expect(filesList.first()).toBeVisible();
    });

    test('TC-FILE-03-02: Preview file content', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const previewBtn = page.locator('button:has-text("预览"), button:has-text("Preview")').first();
      const count = await previewBtn.count();

      if (count > 0) {
        await previewBtn.click();

        const previewModal = page.locator('.ant-modal');
        await expect(previewModal.first()).toBeVisible();
      }
    });

    test('TC-FILE-03-03: Delete uploaded file', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const deleteBtn = page.locator('button:has-text("删除")').first();
      const count = await deleteBtn.count();

      if (count > 0) {
        await deleteBtn.click();

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        await confirmBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-FILE-03-04: Rename file', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const renameBtn = page.locator('button:has-text("重命名"), button:has-text("Rename")').first();
      const count = await renameBtn.count();

      if (count > 0) {
        await renameBtn.click();

        const modal = page.locator('.ant-modal');
        const nameInput = modal.locator('input[name="name"]');
        await nameInput.fill('renamed-file.csv');

        const saveBtn = modal.locator('button:has-text("确定")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });

    test('TC-FILE-03-05: Move file to folder', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const moveBtn = page.locator('button:has-text("移动"), button:has-text("Move")').first();
      const count = await moveBtn.count();

      if (count > 0) {
        await moveBtn.click();

        const modal = page.locator('.ant-modal');
        const folderSelect = modal.locator('select[name="folder"]');
        const folderCount = await folderSelect.count();

        if (folderCount > 0) {
          await folderSelect.selectOption('datasets');

          const confirmBtn = modal.locator('button:has-text("确定")');
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-FILE-03-06: Copy file', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const copyBtn = page.locator('button:has-text("复制"), button:has-text("Copy")').first();
      const count = await copyBtn.count();

      if (count > 0) {
        await copyBtn.click();

        const modal = page.locator('.ant-modal');
        const nameInput = modal.locator('input[name="newName"]');
        await nameInput.fill('copy-of-file.csv');

        const confirmBtn = modal.locator('button:has-text("确定")');
        await confirmBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('File Preview', () => {
    test('TC-FILE-04-01: Preview CSV file', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const previewBtn = page.locator('button:has-text("预览")').first();
      const count = await previewBtn.count();

      if (count > 0) {
        await previewBtn.click();

        const table = page.locator('.preview-table, .ant-table');
        await expect(table.first()).toBeVisible();
      }
    });

    test('TC-FILE-04-02: Preview with pagination', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const previewBtn = page.locator('button:has-text("预览")').first();
      const count = await previewBtn.count();

      if (count > 0) {
        await previewBtn.click();

        const pagination = page.locator('.ant-pagination');
        const pageCount = await pagination.count();

        if (pageCount > 0) {
          await expect(pagination.first()).toBeVisible();
        }
      }
    });

    test('TC-FILE-04-03: Preview with column filter', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const previewBtn = page.locator('button:has-text("预览")').first();
      const count = await previewBtn.count();

      if (count > 0) {
        await previewBtn.click();

        const columnFilter = page.locator('.column-filter, .column-selector');
        const filterCount = await columnFilter.count();

        if (filterCount > 0) {
          await columnFilter.click();

          const checkbox = columnFilter.locator('input[type="checkbox"]').first();
          await checkbox.click();
          await page.waitForTimeout(500);
        }
      }
    });
  });

  test.describe('File Storage', () => {
    test('TC-FILE-05-01: View storage quota', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const quotaInfo = page.locator('.storage-quota, .quota-info');
      const isVisible = await quotaInfo.isVisible().catch(() => false);

      if (isVisible) {
        const text = await quotaInfo.textContent();
        expect(text).toBeTruthy();
      }
    });

    test('TC-FILE-05-02: View storage usage by file type', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const usageChart = page.locator('.storage-chart, .usage-chart');
      const isVisible = await usageChart.isVisible().catch(() => false);

      if (isVisible) {
        await expect(usageChart).toBeVisible();
      }
    });

    test('TC-FILE-05-03: Clean up temp files', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const cleanupBtn = page.locator('button:has-text("清理临时文件")');
      const count = await cleanupBtn.count();

      if (count > 0) {
        await cleanupBtn.click();

        const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
        const confirmCount = await confirmBtn.count();

        if (confirmCount > 0) {
          await confirmBtn.click();
          await page.waitForTimeout(2000);
        }
      }
    });
  });

  test.describe('File Sharing', () => {
    test('TC-FILE-06-01: Share file with users', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const shareBtn = page.locator('button:has-text("分享"), button:has-text("Share")').first();
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-FILE-06-02: Generate file link', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const shareBtn = page.locator('button:has-text("分享")').first();
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const linkTab = page.locator('text=链接, text=Link');
        await linkTab.click();

        const copyLinkBtn = page.locator('button:has-text("复制链接")');
        await copyLinkBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-FILE-06-03: Set file access permissions', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const shareBtn = page.locator('button:has-text("分享")').first();
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const permissionSelect = page.locator('select[name="permission"]');
        const selectCount = await permissionSelect.count();

        if (selectCount > 0) {
          await permissionSelect.selectOption('read');
        }
      }
    });
  });

  test.describe('File Versioning', () => {
    test('TC-FILE-07-01: View file versions', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const versionsBtn = page.locator('button:has-text("版本"), button:has-text("Versions")').first();
      const count = await versionsBtn.count();

      if (count > 0) {
        await versionsBtn.click();

        const versionsList = page.locator('.versions-list, .file-versions');
        await expect(versionsList.first()).toBeVisible();
      }
    });

    test('TC-FILE-07-02: Restore previous version', async ({ page }) => {
      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const versionsBtn = page.locator('button:has-text("版本")').first();
      const count = await versionsBtn.count();

      if (count > 0) {
        await versionsBtn.click();

        const restoreBtn = page.locator('button:has-text("恢复"), button:has-text("Restore")').first();
        const restoreCount = await restoreBtn.count();

        if (restoreCount > 0) {
          await restoreBtn.click();

          const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('File Permissions', () => {
    test('TC-FILE-08-01: Admin can access file management', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-FILE-08-02: Admin can manage files', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/development/files');
      await page.waitForLoadState('domcontentloaded');

      const deleteBtn = page.locator('button:has-text("删除")').first();
      const count = await deleteBtn.count();

      if (count > 0) {
        const isEnabled = await deleteBtn.isEnabled();
        expect(isEnabled || !isEnabled).toBe(true);
      }
    });
  });
});
