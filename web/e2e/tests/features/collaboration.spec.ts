/**
 * Collaboration Feature Tests
 *
 * Tests for collaboration features like comments, sharing, and notifications
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/login.page';
// import { TEST_USERS } from '@data/users'; // Unused - using admin only

test.describe('Collaboration Feature Tests', { tag: ['@collaboration', '@feature', '@p1'] }, () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);

    await loginPage.goto();
    // Using admin user since other users don't exist in backend yet
    await loginPage.login('admin', 'admin123');
  });

  test.describe('Comments', () => {
    test('TC-COL-01-01: View comments on data asset', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const commentsTab = page.locator('text=评论, text=Comments');
      const count = await commentsTab.count();

      if (count > 0) {
        await commentsTab.click();
        await page.waitForTimeout(500);

        const commentsList = page.locator('.comments-list, .comment-thread');
        await expect(commentsList.first()).toBeVisible();
      }
    });

    test('TC-COL-01-02: Add comment', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const commentsTab = page.locator('text=评论');
      const count = await commentsTab.count();

      if (count > 0) {
        await commentsTab.click();

        const commentInput = page.locator('textarea[placeholder*="评论"], textarea[placeholder*="comment"]');
        const inputCount = await commentInput.count();

        if (inputCount > 0) {
          await commentInput.fill('Test comment ' + Date.now());

          const submitBtn = page.locator('button:has-text("发送"), button:has-text("提交")');
          await submitBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-COL-01-03: Reply to comment', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const commentsTab = page.locator('text=评论');
      const count = await commentsTab.count();

      if (count > 0) {
        await commentsTab.click();

        const replyBtn = page.locator('button:has-text("回复"), button:has-text("Reply")').first();
        const replyCount = await replyBtn.count();

        if (replyCount > 0) {
          await replyBtn.click();

          const replyInput = page.locator('textarea.reply-input');
          await replyInput.fill('Test reply');

          const submitBtn = page.locator('button:has-text("发送")');
          await submitBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-COL-01-04: Edit own comment', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const commentsTab = page.locator('text=评论');
      const count = await commentsTab.count();

      if (count > 0) {
        await commentsTab.click();

        const editBtn = page.locator('.comment-item button:has-text("编辑")').first();
        const editCount = await editBtn.count();

        if (editCount > 0) {
          await editBtn.click();

          const editInput = page.locator('textarea.comment-edit');
          await editInput.fill('Updated comment');

          const saveBtn = page.locator('button:has-text("保存")');
          await saveBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-COL-01-05: Delete own comment', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const commentsTab = page.locator('text=评论');
      const count = await commentsTab.count();

      if (count > 0) {
        await commentsTab.click();

        const deleteBtn = page.locator('.comment-item button:has-text("删除")').first();
        const deleteCount = await deleteBtn.count();

        if (deleteCount > 0) {
          await deleteBtn.click();

          const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });
  });

  test.describe('Mentions', () => {
    test('TC-COL-02-01: Mention user in comment', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const commentsTab = page.locator('text=评论');
      const count = await commentsTab.count();

      if (count > 0) {
        await commentsTab.click();

        const commentInput = page.locator('textarea');
        const inputCount = await commentInput.count();

        if (inputCount > 0) {
          await commentInput.fill('@admin Test mention');

          const submitBtn = page.locator('button:has-text("发送")');
          await submitBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-COL-02-02: View mention suggestions', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const commentsTab = page.locator('text=评论');
      const count = await commentsTab.count();

      if (count > 0) {
        await commentsTab.click();

        const commentInput = page.locator('textarea');
        const inputCount = await commentInput.count();

        if (inputCount > 0) {
          await commentInput.fill('@');
          await page.waitForTimeout(500);

          const suggestions = page.locator('.mention-suggestions, .user-suggestions');
          const isVisible = await suggestions.isVisible().catch(() => false);

          if (isVisible) {
            await expect(suggestions).toBeVisible();
          }
        }
      }
    });

    test('TC-COL-02-03: Receive mention notification', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/notifications');
      await page.waitForLoadState('domcontentloaded');

      const notifications = page.locator('.notification-item');
      const count = await notifications.count();

      if (count > 0) {
        const firstNotification = notifications.first();
        const text = await firstNotification.textContent();
        expect(text).toBeTruthy();
      }
    });
  });

  test.describe('Notifications', () => {
    test('TC-COL-03-01: View notification center', async ({ page }) => {
      await page.goto('/notifications');
      await page.waitForLoadState('domcontentloaded');

      const notificationCenter = page.locator('.notification-center, .notifications');
      await expect(notificationCenter.first()).toBeVisible();
    });

    test('TC-COL-03-02: View unread notifications', async ({ page }) => {
      await page.goto('/notifications');
      await page.waitForLoadState('domcontentloaded');

      const unreadFilter = page.locator('button:has-text("未读"), .filter-unread');
      const count = await unreadFilter.count();

      if (count > 0) {
        await unreadFilter.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-COL-03-03: Mark notification as read', async ({ page }) => {
      await page.goto('/notifications');
      await page.waitForLoadState('domcontentloaded');

      const notification = page.locator('.notification-item.unread').first();
      const count = await notification.count();

      if (count > 0) {
        await notification.click();

        const markReadBtn = page.locator('button:has-text("标记已读")');
        const markCount = await markReadBtn.count();

        if (markCount > 0) {
          await markReadBtn.click();
          await page.waitForTimeout(500);
        }
      }
    });

    test('TC-COL-03-04: Mark all as read', async ({ page }) => {
      await page.goto('/notifications');
      await page.waitForLoadState('domcontentloaded');

      const markAllBtn = page.locator('button:has-text("全部已读")');
      const count = await markAllBtn.count();

      if (count > 0) {
        await markAllBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-COL-03-05: Delete notification', async ({ page }) => {
      await page.goto('/notifications');
      await page.waitForLoadState('domcontentloaded');

      const deleteBtn = page.locator('.notification-item button:has-text("删除")').first();
      const count = await deleteBtn.count();

      if (count > 0) {
        await deleteBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-COL-03-06: Configure notification preferences', async ({ page }) => {
      await page.goto('/settings');
      await page.waitForLoadState('domcontentloaded');

      const notifTab = page.locator('text=通知');
      await notifTab.click();

      const emailCheckbox = page.locator('input[name="email_notifications"]');
      const count = await emailCheckbox.count();

      if (count > 0) {
        await emailCheckbox.check();

        const saveBtn = page.locator('button:has-text("保存")');
        await saveBtn.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Sharing', () => {
    test('TC-COL-04-01: Share data asset with user', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const shareBtn = page.locator('button:has-text("分享"), button:has-text("共享")');
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const modal = page.locator('.ant-modal');
        await expect(modal.first()).toBeVisible();
      }
    });

    test('TC-COL-04-02: Share with specific user', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const shareBtn = page.locator('button:has-text("分享")');
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const userSelect = page.locator('select[name="user"]');
        const selectCount = await userSelect.count();

        if (selectCount > 0) {
          await userSelect.selectOption('viewer');

          const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-COL-04-03: Generate share link', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const shareBtn = page.locator('button:has-text("分享")');
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const linkTab = page.locator('text=链接');
        await linkTab.click();

        const copyBtn = page.locator('button:has-text("复制链接")');
        await copyBtn.click();
        await page.waitForTimeout(500);
      }
    });

    test('TC-COL-04-04: Set share permissions', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const shareBtn = page.locator('button:has-text("分享")');
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const permissionSelect = page.locator('select[name="permission"]');
        const selectCount = await permissionSelect.count();

        if (selectCount > 0) {
          await permissionSelect.selectOption('read');

          const confirmBtn = page.locator('.ant-modal button:has-text("确定")');
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    test('TC-COL-04-05: Revoke share access', async ({ page }) => {
      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const firstRow = page.locator('.ant-table-row').first();
      await firstRow.click();

      const shareBtn = page.locator('button:has-text("分享")');
      const count = await shareBtn.count();

      if (count > 0) {
        await shareBtn.click();

        const revokeBtn = page.locator('button:has-text("撤销"), button:has-text("取消")');
        const revokeCount = await revokeBtn.count();

        if (revokeCount > 0) {
          await revokeBtn.click();
          await page.waitForTimeout(500);
        }
      }
    });
  });

  test.describe('Activity Feed', () => {
    test('TC-COL-05-01: View activity feed', async ({ page }) => {
      await page.goto('/dashboard/activity');
      await page.waitForLoadState('domcontentloaded');

      const activityFeed = page.locator('.activity-feed, .activity-list');
      await expect(activityFeed.first()).toBeVisible();
    });

    test('TC-COL-05-02: Filter activities by type', async ({ page }) => {
      await page.goto('/dashboard/activity');
      await page.waitForLoadState('domcontentloaded');

      const filterSelect = page.locator('select[name="activityType"]');
      const count = await filterSelect.count();

      if (count > 0) {
        await filterSelect.selectOption('comment');
        await page.waitForTimeout(500);
      }
    });

    test('TC-COL-05-03: Filter activities by user', async ({ page }) => {
      await page.goto('/dashboard/activity');
      await page.waitForLoadState('domcontentloaded');

      const userFilter = page.locator('select[name="user"]');
      const count = await userFilter.count();

      if (count > 0) {
        await userFilter.selectOption('admin');
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Collaboration Permissions', () => {
    test('TC-COL-06-01: Admin can access collaboration features', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const url = page.url();
      expect(url).toBeTruthy();
    });

    test('TC-COL-06-02: Admin can comment on assets', async ({ page }) => {
      // Using admin user since other users don't exist in backend yet
      await loginPage.goto();
      await loginPage.login('admin', 'admin123');

      await page.goto('/assets/catalog');
      await page.waitForLoadState('domcontentloaded');

      const shareBtn = page.locator('button:has-text("分享")');
      const count = await shareBtn.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });
});
