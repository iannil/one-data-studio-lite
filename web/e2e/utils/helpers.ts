/**
 * Helper utility functions for E2E tests
 */

import { TIMEOUTS } from './constants';

/**
 * Wait for a specified duration
 */
export const wait = (ms: number = TIMEOUTS.DEFAULT): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Retry a function with exponential backoff
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    delay?: number;
    backoff?: number;
  } = {}
): Promise<T> {
  const { maxRetries = 3, delay = 1000, backoff = 2 } = options;

  let lastError: Error | undefined;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (i < maxRetries - 1) {
        await wait(delay * Math.pow(backoff, i));
      }
    }
  }

  throw lastError;
}

/**
 * Generate a random string
 */
export function randomString(length: number = 8): string {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Generate a random email address
 */
export function randomEmail(): string {
  return `test_${randomString(12)}@example.com`;
}

/**
 * Generate a random username
 */
export function randomUsername(): string {
  return `test_user_${randomString(8)}`;
}

/**
 * Format timestamp for test identification
 */
export function timestamp(): string {
  const now = new Date();
  return now.toISOString().replace(/[:.]/g, '-').slice(0, -5);
}

/**
 * Sleep for a short duration (useful for animations)
 */
export const sleep = (ms: number = TIMEOUTS.ANIMATION): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Create a test ID that includes timestamp
 */
export function createTestId(prefix: string): string {
  return `${prefix}_${timestamp()}`;
}

/**
 * Truncate string to max length
 */
export function truncate(str: string, maxLength: number = 50): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + '...';
}

/**
 * Check if value is defined
 */
export function isDefined<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

/**
 * Parse URL query parameters
 */
export function parseQueryParams(url: string): Record<string, string> {
  const queryStart = url.indexOf('?');
  if (queryStart === -1) return {};

  const query = url.slice(queryStart + 1);
  const params = new URLSearchParams(query);
  const result: Record<string, string> = {};

  params.forEach((value, key) => {
    result[key] = value;
  });

  return result;
}

/**
 * Build URL with query parameters
 */
export function buildUrl(base: string, params: Record<string, string | number | boolean>): string {
  const url = new URL(base);
  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.set(key, String(value));
  });
  return url.toString();
}

/**
 * Format test case ID
 * Format: TC-{ROLE}-{STAGE}-{SEQ}-{SUBSEQ}
 */
export function formatTestCaseId(
  role: string,
  stage: string,
  seq: string,
  subSeq: string = '01'
): string {
  return `TC-${role}-${stage}-${seq}-${subSeq}`;
}

/**
 * Parse test case ID
 */
export function parseTestCaseId(id: string): {
  role: string;
  stage: string;
  seq: string;
  subSeq: string;
} | null {
  const match = id.match(/^TC-([A-Z]+)-(\d+)-(\d+)-(\d+)$/);
  if (!match) return null;

  return {
    role: match[1],
    stage: match[2],
    seq: match[3],
    subSeq: match[4],
  };
}

/**
 * Convert camelCase to snake_case
 */
export function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
}

/**
 * Convert snake_case to camelCase
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Deep clone an object
 */
export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Get a nested property from an object safely
 */
export function getNestedValue<T = unknown>(
  obj: Record<string, unknown>,
  path: string,
  defaultValue?: T
): T | undefined {
  const value = path.split('.').reduce((current, key) => {
    return current?.[key] as Record<string, unknown> | undefined;
  }, obj);

  return value !== undefined ? (value as T) : defaultValue;
}

/**
 * Batch an array into chunks
 */
export function chunk<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

/**
 * Deduplicate an array
 */
export function unique<T>(array: T[]): T[] {
  return Array.from(new Set(array));
}

/**
 * Group array by key
 */
export function groupBy<T>(
  array: T[],
  keyFn: (item: T) => string
): Record<string, T[]> {
  return array.reduce((result, item) => {
    const key = keyFn(item);
    if (!result[key]) {
      result[key] = [];
    }
    result[key].push(item);
    return result;
  }, {} as Record<string, T[]>);
}

/**
 * Measure execution time of an async function
 */
export async function measureTime<T>(
  fn: () => Promise<T>
): Promise<{ result: T; duration: number }> {
  const start = performance.now();
  const result = await fn();
  const duration = performance.now() - start;
  return { result, duration };
}
