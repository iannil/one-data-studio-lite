/**
 * Extended test fixtures with service availability checks
 *
 * Provides test decorators and helpers for conditionally skipping tests
 */

import { test as base } from '@playwright/test';
import { isServiceAvailable } from './service-check';

export type ServiceKey = 'frontend' | 'portal' | 'nl2sql' | 'dataApi' | 'cleaning' | 'metadata' | 'sensitive' | 'audit';

/**
 * Extended test fixture with service checks
 */
export const test = base.extend({
  /**
   * Skip test if required services are unavailable
   */
  requireServices: async ({}, use, testInfo) => {
    const require = (services: ServiceKey[]) => {
      const unavailable = services.filter(s => !isServiceAvailable(s));
      if (unavailable.length > 0) {
        testInfo.skip(`Required services unavailable: ${unavailable.join(', ')}`);
      }
    };
    await use(require);
  },
});

/**
 * Test decorator that requires specific services
 * Usage: test.describe(requireServices(['portal', 'nl2sql']), () => { ... })
 */
export function requireServices(services: ServiceKey[]) {
  return function (target: unknown, context: unknown) {
    // This is a marker - actual check happens in test.beforeEach
    (target as any).__requiredServices = services;
  };
}

/**
 * Check if services are available in test
 */
export function checkServices(...services: ServiceKey[]): boolean {
  return services.every(s => isServiceAvailable(s));
}

/**
 * Skip test conditionally based on service availability
 */
export function skipIfNotAvailable(...services: ServiceKey[]): string | undefined {
  if (!checkServices(...services)) {
    return `Services unavailable: ${services.join(', ')}`;
  }
  return undefined;
}

/**
 * Annotate test to skip if frontend is unavailable
 */
export function requireFrontend() {
  return skipIfNotAvailable('frontend');
}

/**
 * Annotate test to skip if portal is unavailable
 */
export function requirePortal() {
  return skipIfNotAvailable('portal');
}

/**
 * Annotate test to skip if NL2SQL is unavailable
 */
export function requireNL2SQL() {
  return skipIfNotAvailable('nl2sql');
}

/**
 * Annotate test to skip if Data API is unavailable
 */
export function requireDataApi() {
  return skipIfNotAvailable('dataApi');
}

/**
 * Annotate test to skip if Cleaning service is unavailable
 */
export function requireCleaning() {
  return skipIfNotAvailable('cleaning');
}

/**
 * Annotate test to skip if Sensitive Detect is unavailable
 */
export function requireSensitive() {
  return skipIfNotAvailable('sensitive');
}

/**
 * Annotate test to skip if Metadata Sync is unavailable
 */
export function requireMetadata() {
  return skipIfNotAvailable('metadata');
}

/**
 * Annotate test to skip if Audit Log is unavailable
 */
export function requireAudit() {
  return skipIfNotAvailable('audit');
}

/**
 * Helper to create test.describe that skips when services are unavailable
 */
export function describeWithServices(
  services: ServiceKey[],
  title: string,
  fn: () => void
) {
  test.describe(title + ` [requires: ${services.join(', ')}]`, () => {
    test.beforeEach(async ({}, testInfo) => {
      const skipReason = skipIfNotAvailable(...services);
      if (skipReason) {
        testInfo.skip(skipReason);
      }
    });
    fn();
  });
}

/**
 * Re-export everything from playwright/test
 */
export { expect } from '@playwright/test';
