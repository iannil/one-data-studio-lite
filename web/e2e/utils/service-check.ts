/**
 * Service health check utility for E2E tests
 *
 * Checks availability of backend services and frontend
 * Marks tests as skipped when services are unavailable
 */

import { FullConfig } from '@playwright/test';

export interface ServiceStatus {
  name: string;
  url: string;
  available: boolean;
  error?: string;
}

export interface HealthCheckResult {
  frontend: ServiceStatus;
  portal: ServiceStatus;
  nl2sql: ServiceStatus;
  dataApi: ServiceStatus;
  cleaning: ServiceStatus;
  metadata: ServiceStatus;
  sensitive: ServiceStatus;
  audit: ServiceStatus;
  allAvailable: boolean;
}

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

const SERVICES = {
  frontend: { name: 'Frontend', url: BASE_URL },
  portal: { name: 'Portal API', url: 'http://localhost:8010' },
  nl2sql: { name: 'NL2SQL Service', url: 'http://localhost:8011' },
  dataApi: { name: 'Data API Service', url: 'http://localhost:8014' },
  cleaning: { name: 'AI Cleaning Service', url: 'http://localhost:8012' },
  metadata: { name: 'Metadata Sync Service', url: 'http://localhost:8013' },
  sensitive: { name: 'Sensitive Detect Service', url: 'http://localhost:8015' },
  audit: { name: 'Audit Log Service', url: 'http://localhost:8016' },
} as const;

/**
 * Check if a service is available
 */
async function checkService(name: string, url: string): Promise<ServiceStatus> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const response = await fetch(`${url}/health`, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
      },
    }).catch(async (err) => {
      // If /health fails, try root endpoint
      return fetch(`${url}/`, {
        method: 'GET',
        signal: controller.signal,
      });
    });

    clearTimeout(timeoutId);

    return {
      name,
      url,
      available: response.status < 500,
    };
  } catch (err) {
    return {
      name,
      url,
      available: false,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

/**
 * Check all services availability
 */
export async function checkServices(): Promise<HealthCheckResult> {
  const results = {
    frontend: await checkService(SERVICES.frontend.name, SERVICES.frontend.url),
    portal: await checkService(SERVICES.portal.name, SERVICES.portal.url),
    nl2sql: await checkService(SERVICES.nl2sql.name, SERVICES.nl2sql.url),
    dataApi: await checkService(SERVICES.dataApi.name, SERVICES.dataApi.url),
    cleaning: await checkService(SERVICES.cleaning.name, SERVICES.cleaning.url),
    metadata: await checkService(SERVICES.metadata.name, SERVICES.metadata.url),
    sensitive: await checkService(SERVICES.sensitive.name, SERVICES.sensitive.url),
    audit: await checkService(SERVICES.audit.name, SERVICES.audit.url),
  };

  const allAvailable = Object.values(results).every(s => s.available);

  return {
    ...results,
    allAvailable,
  };
}

/**
 * Get available services
 */
export function getAvailableServices(status: HealthCheckResult): string[] {
  return Object.entries(status)
    .filter(([key, value]) => key !== 'allAvailable' && value.available)
    .map(([key]) => key);
}

/**
 * Check if specific services are available
 */
export function areServicesAvailable(
  status: HealthCheckResult,
  services: Array<keyof Omit<HealthCheckResult, 'allAvailable'>>
): boolean {
  return services.every(service => status[service].available);
}

/**
 * Print service status summary
 */
export function printServiceStatus(status: HealthCheckResult): void {
  console.log('\n📊 Service Status:');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  for (const [key, service] of Object.entries(status)) {
    if (key === 'allAvailable') continue;

    const icon = service.available ? '✅' : '❌';
    const statusText = service.available ? 'Available' : 'Unavailable';
    console.log(`${icon} ${service.name.padEnd(25)} ${statusText}`);

    if (!service.available && service.error) {
      console.log(`   └─ Error: ${service.error}`);
    }
  }

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
}

/**
 * Skip test annotation for services
 * Use in test.beforeEach to skip tests when required services are unavailable
 */
export function skipIfServicesUnavailable(
  status: HealthCheckResult,
  requiredServices: Array<keyof Omit<HealthCheckResult, 'allAvailable'>>,
  testInfo: { skip: (reason: string) => void }
): void {
  const unavailable = requiredServices.filter(s => !status[s].available);
  if (unavailable.length > 0) {
    const services = unavailable.map(s => status[s].name).join(', ');
    testInfo.skip(`Required services unavailable: ${services}`);
  }
}

/**
 * Global setup for service checks
 */
export async function setupServiceChecks(config: FullConfig): Promise<HealthCheckResult> {
  console.log('🔍 Checking service availability...');

  const status = await checkServices();
  printServiceStatus(status);

  // Store results in process.env for tests to access
  process.env.E2E_FRONTEND_AVAILABLE = status.frontend.available ? '1' : '0';
  process.env.E2E_PORTAL_AVAILABLE = status.portal.available ? '1' : '0';
  process.env.E2E_NL2SQL_AVAILABLE = status.nl2sql.available ? '1' : '0';
  process.env.E2E_DATA_API_AVAILABLE = status.dataApi.available ? '1' : '0';
  process.env.E2E_CLEANING_AVAILABLE = status.cleaning.available ? '1' : '0';
  process.env.E2E_METADATA_AVAILABLE = status.metadata.available ? '1' : '0';
  process.env.E2E_SENSITIVE_AVAILABLE = status.sensitive.available ? '1' : '0';
  process.env.E2E_AUDIT_AVAILABLE = status.audit.available ? '1' : '0';

  return status;
}

/**
 * Check if service is available from environment variable
 */
export function isServiceAvailable(service: keyof Omit<HealthCheckResult, 'allAvailable'>): boolean {
  const envVar = `E2E_${service.toUpperCase()}_AVAILABLE`;
  return process.env[envVar] === '1';
}
