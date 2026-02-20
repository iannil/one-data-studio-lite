/**
 * E2E tests for Celery task scheduling workflows.
 *
 * These tests verify the complete user workflow for scheduling
 * and managing data collection tasks.
 */

import { test, expect } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:5501";

test.describe("Celery Task Scheduling", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto(BASE_URL);

    // Login as admin
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', "admin@example.com");
    await page.fill('input[name="password"]', "admin");
    await page.click('button[type="submit"]');

    // Wait for navigation to dashboard
    await page.waitForURL("**/dashboard");
  });

  test("should create a new scheduled collection task", async ({ page }) => {
    // Navigate to collection page
    await page.click('text=Data Collection');
    await page.waitForURL("**/collect");

    // Click "New Task" button
    await page.click('button:has-text("New Task")');

    // Fill in task details
    await page.fill('input[name="name"]', "E2E Test Scheduled Task");

    // Select data source
    await page.click('select[name="source_id"]');
    await page.click('select[name="source_id"] option:first-child');

    // Enter table names
    await page.fill('input[name="source_table"]', "source_test_table");
    await page.fill('input[name="target_table"]', "target_test_table");

    // Set cron schedule (daily at midnight)
    await page.fill('input[name="schedule_cron"]', "0 0 * * *");

    // Enable the task
    await page.check('input[name="is_active"]');

    // Submit form
    await page.click('button:has-text("Create")');

    // Verify success message
    await expect(page.locator("text=Task created successfully")).toBeVisible();

    // Verify task appears in list
    await expect(page.locator('text=E2E Test Scheduled Task')).toBeVisible();
  });

  test("should pause and resume a scheduled task", async ({ page }) => {
    // Navigate to collection page
    await page.click('text=Data Collection');
    await page.waitForURL("**/collect");

    // Find a scheduled task (create one if needed)
    const taskRow = page.locator('tr').filter({ hasText: "E2E Test Scheduled Task" });

    // Click pause button
    await taskRow.locator('button:has-text("Pause")').click();

    // Verify task is paused (status badge)
    await expect(taskRow.locator('text=Paused')).toBeVisible();

    // Click resume button
    await taskRow.locator('button:has-text("Resume")').click();

    // Verify task is active again
    await expect(taskRow.locator('text=Active')).toBeVisible();
  });

  test("should delete a scheduled task", async ({ page }) => {
    // Navigate to collection page
    await page.click('text=Data Collection');
    await page.waitForURL("**/collect");

    // Create a task for deletion
    await page.click('button:has-text("New Task")');
    await page.fill('input[name="name"]', "Delete Test Task");
    await page.click('select[name="source_id"]');
    await page.click('select[name="source_id"] option:first-child');
    await page.fill('input[name="source_table"]', "source_table");
    await page.fill('input[name="target_table"]', "target_table");
    await page.click('button:has-text("Create")');

    // Find and delete the task
    const taskRow = page.locator('tr').filter({ hasText: "Delete Test Task" });
    await taskRow.locator('button:has-text("Delete")').click();

    // Confirm deletion
    await page.click('button:has-text("Confirm")');

    // Verify task is removed
    await expect(page.locator('text=Delete Test Task')).not.toBeVisible();
  });

  test("should view task execution history", async ({ page }) => {
    // Navigate to collection page
    await page.click('text=Data Collection');
    await page.waitForURL("**/collect");

    // Click on a task to view details
    const taskRow = page.locator('tr').filter({ hasText: "E2E Test Scheduled Task" });
    await taskRow.click();

    // Wait for details page
    await page.waitForURL("**/collect/**");

    // Verify execution history section
    await expect(page.locator('text=Execution History')).toBeVisible();

    // Check for execution status badges
    const statusElements = page.locator('[class*="status"]');
    expect(await statusElements.count()).toBeGreaterThan(0);
  });

  test("should trigger manual task execution", async ({ page }) => {
    // Navigate to collection page
    await page.click('text=Data Collection');
    await page.waitForURL("**/collect");

    // Create a task
    await page.click('button:has-text("New Task")');
    await page.fill('input[name="name"]', "Manual Execute Task");
    await page.click('select[name="source_id"]');
    await page.click('select[name="source_id"] option:first-child');
    await page.fill('input[name="source_table"]', "source_table");
    await page.fill('input[name="target_table"]', "target_table");
    await page.click('button:has-text("Create")');

    // Click "Run Now" button
    const taskRow = page.locator('tr').filter({ hasText: "Manual Execute Task" });
    await taskRow.locator('button:has-text("Run Now")').click();

    // Verify execution started notification
    await expect(page.locator("text=Task execution started")).toBeVisible();

    // Check for running status
    await expect(taskRow.locator('text=Running')).toBeVisible({ timeout: 5000 });
  });

  test("should display Celery worker status", async ({ page }) => {
    // Navigate to settings or monitoring page
    await page.click('text=Settings');
    await page.click('text=Celery Monitoring');

    // Verify worker status section
    await expect(page.locator('text=Worker Status')).toBeVisible();

    // Check for worker information
    await expect(page.locator('text=Online')).toBeVisible();

    // Check for queue information
    await expect(page.locator('text=Queue')).toBeVisible();
  });
});

test.describe("Celery Flower Monitoring", () => {
  test("should link to Flower monitoring UI", async ({ page }) => {
    // Navigate to settings
    await page.goto(`${BASE_URL}/settings`);
    await page.click('text=Celery Monitoring');

    // Click "Open Flower" button
    const [newPage] = await Promise.all([
      page.context().waitForEvent("page"),
      page.click('a:has-text("Open Flower")'),
    ]);

    // Verify Flower page opens
    await newPage.waitForLoadState();
    expect(newPage.url()).toContain("flower");
  });
});

test.describe("Celery Task Status Indicators", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', "admin@example.com");
    await page.fill('input[name="password"]', "admin");
    await page.click('button[type="submit"]');
    await page.waitForURL("**/dashboard");
    await page.click('text=Data Collection');
    await page.waitForURL("**/collect");
  });

  test("should display correct status colors", async ({ page }) => {
    // Check for status badges with correct colors
    const activeBadge = page.locator('.ant-badge:has-text("Active")');
    const pausedBadge = page.locator('.ant-badge:has-text("Paused")');
    const failedBadge = page.locator('.ant-badge:has-text("Failed")');

    // Verify badges exist and have appropriate styling
    if ((await activeBadge.count()) > 0) {
      await expect(activeBadge).toHaveCSS("color", /rgb(22, 119, 255|green)/);
    }
    if ((await pausedBadge.count()) > 0) {
      await expect(pausedBadge).toHaveCSS("color", /orange/);
    }
    if ((await failedBadge.count()) > 0) {
      await expect(failedBadge).toHaveCSS("color", /red/);
    }
  });

  test("should show next run time for scheduled tasks", async ({ page }) => {
    // Find a task with a schedule
    const taskRow = page.locator('tr').filter({ hasText: "E2E Test Scheduled Task" });

    // Click to view details
    await taskRow.click();

    // Verify next run time is displayed
    await expect(page.locator('text=Next Run')).toBeVisible();
    const nextRunTime = page.locator('[data-testid="next-run-time"]');
    expect(await nextRunTime.count()).toBeGreaterThan(0);
  });
});
