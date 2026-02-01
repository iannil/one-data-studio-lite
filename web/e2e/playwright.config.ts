import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Test Configuration
 *
 * Test environment for ONE-DATA-STUDIO-LITE platform
 * - Frontend: http://localhost:3000
 * - Backend API: http://localhost:8010-8016
 */
export default defineConfig({
  // Test directory
  testDir: './tests',

  // Ignore patterns - exclude src and vitest tests
  testIgnore: ['**/node_modules/**', '**/dist/**', '**/src/**/*.test.{ts,tsx,js,jsx}', '**/src/**/*.spec.{ts,tsx,js,jsx}'],

  // Fully parallel test execution
  fullyParallel: true,

  // Number of workers (reduce in CI for resource constraints)
  workers: process.env.CI ? 2 : 4,

  // Fail the test on the first error
  forbidOnly: !!process.env.CI,

  // Retry on failure (only in CI)
  retries: process.env.CI ? 2 : 0,

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'],
  ],

  // Shared settings for all tests
  use: {
    // Base URL for tests
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // Collect trace when retrying the failed test
    trace: 'retain-on-failure',

    // Screenshot configuration
    screenshot: 'only-on-failure',

    // Video configuration
    video: 'retain-on-failure',

    // Action timeout
    actionTimeout: 10000,

    // Navigation timeout
    navigationTimeout: 30000,

    // Locale
    locale: 'zh-CN',

    // Timezone
    timezoneId: 'Asia/Shanghai',

    // User agent
    userAgent: 'ONE-DATA-STUDIO-E2E-Test',
  },

  // Test projects
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.BASE_URL || 'http://localhost:3000',
      },
    },
    // Firefox and WebKit can be added later
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'], baseURL: process.env.BASE_URL || 'http://localhost:3000' },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'], baseURL: process.env.BASE_URL || 'http://localhost:3000' },
    // },
  ],

  // Global setup and teardown
  globalSetup: require.resolve('./utils/global-setup'),
  globalTeardown: require.resolve('./utils/global-teardown'),

  // Output directory
  outputDir: 'test-results/artifacts',

  // Test timeout
  timeout: 60 * 1000,

  // Expect timeout
  expect: {
    timeout: 5000,
  },

  // Skip tests if services are not available
  // Set E2E_SKIP_UNAVAILABLE=1 to enable this behavior
  workers: process.env.CI ? 2 : 1,
});
