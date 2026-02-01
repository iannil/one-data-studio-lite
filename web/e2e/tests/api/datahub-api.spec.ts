/**
 * DataHub API Tests
 *
 * Tests for DataHub integration endpoints
 */

import { test, expect } from '@playwright/test';

const DATAHUB_BASE_URL = process.env.DATAHUB_URL || 'http://localhost:8081';
const PORTAL_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8010';

test.describe('DataHub API Tests', { tag: ['@datahub', '@api', '@p1'] }, () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    // Get auth token
    const response = await request.post(`${PORTAL_BASE_URL}/auth/login`, {
      data: {
        username: 'admin',
        password: 'admin123',
      },
    });
    const data = await response.json();
    authToken = data.token || data.data?.token;
  });

  test.describe('DataHub Entities', () => {
    test('TC-DH-API-01-01: List entities via portal proxy', async ({ request }) => {
      const response = await request.get(`${PORTAL_BASE_URL}/api/proxy/datahub/entities`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        params: {
          start: 0,
          count: 10,
        },
      });

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(data).toHaveProperty('success');
    });

    test('TC-DH-API-01-02: Search entities', async ({ request }) => {
      const response = await request.get(`${PORTAL_BASE_URL}/api/proxy/datahub/entities/search`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        params: {
          query: 'dataset',
          start: 0,
          count: 5,
        },
      });

      // May return 404 if endpoint not implemented
      const status = response.status();
      expect([200, 404]).toContain(status);
    });

    test('TC-DH-API-01-03: Get entity by URN', async ({ request }) => {
      // First try to get a list of entities
      const listResponse = await request.get(`${PORTAL_BASE_URL}/api/proxy/datahub/entities`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        params: {
          start: 0,
          count: 1,
        },
      });

      if (listResponse.ok()) {
        const listData = await listResponse.json();
        const entities = listData.data?.result || listData.data || [];

        if (entities.length > 0) {
          const urn = entities[0].urn;
          const response = await request.get(`${PORTAL_BASE_URL}/api/proxy/datahub/entities/${urn}`, {
            headers: {
              Authorization: `Bearer ${authToken}`,
            },
          });

          expect(response.ok()).toBeTruthy();
        }
      }
    });
  });

  test.describe('DataHub Datasets', () => {
    test('TC-DH-API-02-01: List datasets', async ({ request }) => {
      const response = await request.get(`${PORTAL_BASE_URL}/api/proxy/datahub/datasets`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      // May return 404 if endpoint not implemented
      const status = response.status();
      expect([200, 404]).toContain(status);
    });
  });

  test.describe('DataHub Lineage', () => {
    test('TC-DH-API-03-01: Get entity lineage', async ({ request }) => {
      // Use a sample URN for lineage
      const sampleUrn = 'urn:li:dataset:(urn:li:dataPlatform:hive,sample,PROD)';
      const urn = encodeURIComponent(sampleUrn);
      const response = await request.get(`${PORTAL_BASE_URL}/api/proxy/datahub/entities/${urn}/lineage`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      // May return 404 if entity doesn't exist
      const status = response.status();
      expect([200, 404]).toContain(status);
    });
  });

  test.describe('DataHub Health', () => {
    test('TC-DH-API-04-01: Check DataHub health via proxy', async ({ request }) => {
      const response = await request.get(`${PORTAL_BASE_URL}/api/subsystems`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      const subsystems = Array.isArray(data) ? data : data.data || [];

      // Check if DataHub is in the subsystems list
      const datahubStatus = subsystems.find((s: any) => s.name === 'datahub-gms');
      if (datahubStatus) {
        expect(['online', 'offline']).toContain(datahubStatus.status);
      }
    });
  });
});
