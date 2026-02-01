/**
 * API fixtures for E2E tests
 */

import { test as base, APIRequestContext } from '@playwright/test';
import { ApiClient, createPortalClient } from '@utils/api-client';
import { TEST_USERS } from '@types/index';

/**
 * API fixtures interface
 */
export interface ApiFixtures {
  apiClient: ApiClient;
  authenticatedApiClient: ApiClient;
  adminApiClient: ApiClient;
  superAdminApiClient: ApiClient;
  analystApiClient: ApiClient;
  viewerApiClient: ApiClient;
}

/**
 * Create authenticated API client
 */
async function createAuthenticatedApiClient(
  username: string,
  password: string
): Promise<ApiClient> {
  const client = createPortalClient();
  const result = await client.login({ username, password });
  if (!result.success || !result.token) {
    throw new Error(`Failed to authenticate user: ${username}`);
  }
  return client;
}

/**
 * Base test with API fixtures
 */
export const test = base.extend<ApiFixtures>({
  /**
   * Unauthenticated API client
   */
  apiClient: async ({ }, use) => {
    const client = createPortalClient();
    await use(client);
  },

  /**
   * Authenticated API client (admin)
   */
  authenticatedApiClient: async ({ }, use) => {
    const adminUser = TEST_USERS.admin;
    const client = await createAuthenticatedApiClient(adminUser.username, adminUser.password);
    await use(client);
  },

  /**
   * Admin API client
   */
  adminApiClient: async ({ }, use) => {
    const adminUser = TEST_USERS.admin;
    const client = await createAuthenticatedApiClient(adminUser.username, adminUser.password);
    await use(client);
  },

  /**
   * Super admin API client
   */
  superAdminApiClient: async ({ }, use) => {
    const superAdminUser = TEST_USERS.superAdmin;
    const client = await createAuthenticatedApiClient(
      superAdminUser.username,
      superAdminUser.password
    );
    await use(client);
  },

  /**
   * Analyst API client
   */
  analystApiClient: async ({ }, use) => {
    const analystUser = TEST_USERS.analyst;
    const client = await createAuthenticatedApiClient(analystUser.username, analystUser.password);
    await use(client);
  },

  /**
   * Viewer API client
   */
  viewerApiClient: async ({ }, use) => {
    const viewerUser = TEST_USERS.viewer;
    const client = await createAuthenticatedApiClient(viewerUser.username, viewerUser.password);
    await use(client);
  },
});

/**
 * Export base expect
 */
export { expect } from '@playwright/test';
