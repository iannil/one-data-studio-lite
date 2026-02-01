/**
 * Global setup for Playwright tests
 * Runs once before all tests
 */

import { FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E Test Suite');
  console.log('📋 Configuration:', {
    baseURL: config.projects?.[0]?.use?.baseURL,
    workers: config.workers,
    retries: config.retries,
  });

  // Verify backend services are available
  // await verifyBackendServices();

  // Setup test database if needed
  // await setupTestDatabase();

  console.log('✅ Global setup complete');
}

export default globalSetup;
