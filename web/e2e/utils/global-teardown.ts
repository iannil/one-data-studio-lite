/**
 * Global teardown for Playwright tests
 * Runs once after all tests
 */

import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Cleaning up after E2E Test Suite');

  // Cleanup test data if needed
  // await cleanupTestData();

  // Close database connections
  // await closeDatabase();

  console.log('✅ Global teardown complete');
}

export default globalTeardown;
