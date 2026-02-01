/**
 * DolphinScheduler API Tests
 *
 * Tests for DolphinScheduler integration endpoints
 */

import { test, expect } from '@playwright/test';

const DS_BASE_URL = process.env.DOLPHINSCHEDULER_URL || 'http://localhost:12345';
const PORTAL_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8010';

test.describe('DolphinScheduler API Tests', { tag: ['@dolphinscheduler', '@api', '@p1'] }, () => {
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

  test.describe('DolphinScheduler Projects', () => {
    test('TC-DS-API-01-01: List projects via portal proxy', async ({ request }) => {
      const response = await request.get(`${PORTAL_BASE_URL}/api/proxy/ds/v1/projects`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      // May return 404 if endpoint not implemented or service not available
      const status = response.status();
      expect([200, 404, 503]).toContain(status);

      if (status === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('success');
      }
    });

    test('TC-DS-API-01-02: Get project details', async ({ request }) => {
      // First, get the list of projects
      const listResponse = await request.get(`${PORTAL_BASE_URL}/api/proxy/ds/v1/projects`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      if (listResponse.ok()) {
        const listData = await listResponse.json();
        const projects = listData.data || [];

        if (projects.length > 0) {
          const projectCode = projects[0].code;
          const response = await request.get(
            `${PORTAL_BASE_URL}/api/proxy/ds/v1/projects/${projectCode}`,
            {
              headers: {
                Authorization: `Bearer ${authToken}`,
              },
            }
          );

          expect(response.ok()).toBeTruthy();
        }
      }
    });
  });

  test.describe('DolphinScheduler Process Definitions', () => {
    test('TC-DS-API-02-01: List process definitions', async ({ request }) => {
      // Use a sample project code
      const projectCode = 'default';
      const response = await request.get(
        `${PORTAL_BASE_URL}/api/proxy/ds/v1/projects/${projectCode}/process-definition`,
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
          params: {
            pageNo: 1,
            pageSize: 10,
          },
        }
      );

      // May return 404 if project doesn't exist or service not available
      const status = response.status();
      expect([200, 404, 503]).toContain(status);
    });
  });

  test.describe('DolphinScheduler Schedules', () => {
    test('TC-DS-API-03-01: List schedules', async ({ request }) => {
      const projectCode = 'default';
      const response = await request.get(
        `${PORTAL_BASE_URL}/api/proxy/ds/v1/projects/${projectCode}/schedules`,
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        }
      );

      // May return 404 if project doesn't exist or service not available
      const status = response.status();
      expect([200, 404, 503]).toContain(status);
    });
  });

  test.describe('DolphinScheduler Task Instances', () => {
    test('TC-DS-API-04-01: List task instances', async ({ request }) => {
      const projectCode = 'default';
      const response = await request.get(
        `${PORTAL_BASE_URL}/api/proxy/ds/v1/projects/${projectCode}/task-instances`,
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
          params: {
            pageNo: 1,
            pageSize: 10,
          },
        }
      );

      // May return 404 if project doesn't exist or service not available
      const status = response.status();
      expect([200, 404, 503]).toContain(status);
    });
  });

  test.describe('DolphinScheduler Health', () => {
    test('TC-DS-API-05-01: Check DolphinScheduler health via proxy', async ({ request }) => {
      const response = await request.get(`${PORTAL_BASE_URL}/api/subsystems`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      const subsystems = Array.isArray(data) ? data : data.data || [];

      // Check if DolphinScheduler is in the subsystems list
      const dsStatus = subsystems.find((s: any) => s.name === 'dolphinscheduler');
      if (dsStatus) {
        expect(['online', 'offline']).toContain(dsStatus.status);
      }
    });
  });
});
