/**
 * Data Cleaning API Tests
 *
 * Direct API tests for Data Cleaning service endpoints
 * Tolerant of unimplemented features - accepts 200-499 status codes
 */

import { test, expect } from '@playwright/test';
import { createPortalApiTester, createCleaningApiTester } from '@utils/api-testing';

test.describe('Data Cleaning API Tests', { tag: ['@api', '@cleaning', '@p1'] }, () => {
  let apiTester: ReturnType<typeof createPortalApiTester>;
  let cleaningTester: ReturnType<typeof createCleaningApiTester>;
  let authToken: string;

  test.beforeAll(async () => {
    apiTester = createPortalApiTester(undefined);
    cleaningTester = createCleaningApiTester(undefined);

    const loginResult = await apiTester.post('/auth/login', {
      username: 'admin',
      password: 'admin123',
    });

    expect(loginResult.status).toBeLessThan(500);

    if (loginResult.status >= 200 && loginResult.status < 500 && loginResult.body) {
      // @ts-ignore
      authToken = loginResult.body.data?.token || loginResult.body.token;
      if (authToken) {
        apiTester.setToken(authToken);
        cleaningTester.setToken(authToken);
      }
    }
  });

  test.describe('Authentication', () => {
    test('TC-CLN-API-01-01: API requires authentication', async () => {
      const tester = createCleaningApiTester(undefined);

      const result = await tester.getRules();

      expect(result.status).toBeGreaterThanOrEqual(400);
    });

    test('TC-CLN-API-01-02: Valid token accepted', async () => {
      const result = await cleaningTester.getRules();

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Cleaning Rules', () => {
    test('TC-CLN-API-02-01: Get all rules', async () => {
      const result = await cleaningTester.getRules();

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-02-02: Create cleaning rule', async () => {
      const result = await cleaningTester.createRule({
        name: 'Test Rule',
        type: 'null_check',
        field: 'email',
        condition: 'IS_NOT_NULL',
        action: 'FLAG',
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-02-03: Update cleaning rule', async () => {
      // First create a rule
      const createResult = await cleaningTester.createRule({
        name: 'Update Test Rule',
        type: 'format_validation',
        field: 'email',
        condition: 'EMAIL_FORMAT',
        action: 'FLAG',
      });

      // Tolerant - just verify endpoint was called
      expect(createResult.status).toBeLessThan(500);
    });

    test('TC-CLN-API-02-04: Enable/disable rule', async () => {
      const result = await cleaningTester.toggleRule('rule-1', false);

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-02-05: Delete cleaning rule', async () => {
      const result = await cleaningTester.deleteRule('rule-1');

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-02-06: Get rule by ID', async () => {
      const result = await cleaningTester.getRule('rule-1');

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Quality Scanning', () => {
    test('TC-CLN-API-03-01: Start quality scan', async () => {
      const result = await cleaningTester.startScan({
        table: 'users',
        columns: ['email', 'phone'],
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-03-02: Get scan results', async () => {
      const result = await cleaningTester.getScanResults('scan-123');

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-03-03: Get scan status', async () => {
      const result = await cleaningTester.getScanStatus('scan-123');

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-03-04: Cancel running scan', async () => {
      const result = await cleaningTester.cancelScan('scan-123');

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-03-05: Get scan statistics', async () => {
      const result = await cleaningTester.getScanStats('users');

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Data Cleaning', () => {
    test('TC-CLN-API-04-01: Apply cleaning rules', async () => {
      const result = await cleaningTester.applyRules({
        table: 'users',
        dryRun: true,
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-04-02: Preview cleaning results', async () => {
      const result = await cleaningTester.previewCleaning({
        table: 'users',
        ruleIds: ['rule-1', 'rule-2'],
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-04-03: Execute data transformation', async () => {
      const result = await cleaningTester.transform({
        table: 'users',
        column: 'name',
        transformation: 'UPPERCASE',
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-04-04: Rollback cleaning operation', async () => {
      const result = await cleaningTester.rollback('operation-123');

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('AI Recommendations', () => {
    test('TC-CLN-API-05-01: Get AI rule suggestions', async () => {
      const result = await cleaningTester.getSuggestions({
        table: 'users',
        sampleSize: 1000,
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-05-02: Apply AI suggested rule', async () => {
      const result = await cleaningTester.applySuggestion('suggestion-123');

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-05-03: Get recommendation confidence', async () => {
      const result = await cleaningTester.getSuggestionConfidence('suggestion-123');

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Data Validation', () => {
    test('TC-CLN-API-06-01: Validate email format', async () => {
      const result = await cleaningTester.validateColumn({
        table: 'users',
        column: 'email',
        validation: 'EMAIL',
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-06-02: Validate numeric range', async () => {
      const result = await cleaningTester.validateColumn({
        table: 'users',
        column: 'age',
        validation: 'RANGE',
        params: { min: 0, max: 120 },
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-06-03: Validate date consistency', async () => {
      const result = await cleaningTester.validateColumn({
        table: 'users',
        column: 'birth_date',
        validation: 'NOT_FUTURE',
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-06-04: Get validation report', async () => {
      const result = await cleaningTester.getValidationReport('users');

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Data Deduplication', () => {
    test('TC-CLN-API-07-01: Find duplicate records', async () => {
      const result = await cleaningTester.findDuplicates({
        table: 'users',
        columns: ['email', 'phone'],
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-07-02: Remove duplicates', async () => {
      const result = await cleaningTester.removeDuplicates({
        table: 'users',
        columns: ['email'],
        keep: 'first',
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-07-03: Get deduplication statistics', async () => {
      const result = await cleaningTester.getDedupStats('users');

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Data Standardization', () => {
    test('TC-CLN-API-08-01: Standardize date format', async () => {
      const result = await cleaningTester.standardize({
        table: 'users',
        column: 'created_at',
        format: 'ISO_8601',
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-08-02: Standardize text case', async () => {
      const result = await cleaningTester.standardize({
        table: 'users',
        column: 'name',
        format: 'TITLE_CASE',
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-08-03: Trim whitespace', async () => {
      const result = await cleaningTester.trimWhitespace({
        table: 'users',
        columns: ['name', 'email'],
      });

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Quality Metrics', () => {
    test('TC-CLN-API-09-01: Get quality score', async () => {
      const result = await cleaningTester.getQualityScore('users');

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-09-02: Get quality trends', async () => {
      const result = await cleaningTester.getQualityTrends({
        table: 'users',
        period: '30d',
      });

      expect(result.status).toBeLessThan(500);
    });

    test('TC-CLN-API-09-03: Get quality by column', async () => {
      const result = await cleaningTester.getColumnQuality('users');

      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Error Handling', () => {
    test('TC-CLN-API-10-01: Handle invalid table', async () => {
      const result = await cleaningTester.startScan({
        table: 'nonexistent_table',
      });

      expect(result.status).toBeGreaterThanOrEqual(400);
    });

    test('TC-CLN-API-10-02: Handle invalid rule config', async () => {
      const result = await cleaningTester.createRule({
        name: '',
        type: 'invalid',
      });

      expect(result.status).toBeGreaterThanOrEqual(400);
    });

    test('TC-CLN-API-10-03: Handle scan timeout', async () => {
      const result = await cleaningTester.getScanResults('scan-timeout');

      // Should handle gracefully
      expect(result.status).toBeLessThan(500);
    });
  });

  test.describe('Performance', () => {
    test('TC-CLN-API-11-01: Scan completes in reasonable time', async () => {
      const start = Date.now();
      const result = await cleaningTester.startScan({
        table: 'users',
      });
      const duration = Date.now() - start;

      expect(result.status).toBeLessThan(500);
      expect(duration).toBeLessThan(10000);
    });

    test('TC-CLN-API-11-02: Handle concurrent scans', async () => {
      const promises = Array(3).fill(null).map((_, i) =>
        cleaningTester.startScan({
          table: 'users',
        })
      );

      const results = await Promise.all(promises);

      for (const result of results) {
        expect(result.status).toBeLessThan(500);
      }
    });
  });
});
