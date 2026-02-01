/**
 * API Testing Utilities
 *
 * Helper functions for API testing
 */

import { APIRequestContext, APIResponse, expect } from '@playwright/test';
import { TIMEOUTS } from './constants';

/**
 * API request options
 */
export interface ApiRequestOptions {
  headers?: Record<string, string>;
  params?: Record<string, string | number>;
  timeout?: number;
}

/**
 * API test result
 */
export interface ApiTestResult {
  url: string;
  method: string;
  status: number;
  statusText: string;
  headers: Record<string, string>;
  body: unknown;
  duration: number;
  size: number;
}

/**
 * API Client for testing
 */
export class ApiTester {
  private baseURL: string;
  private token: string | null = null;
  private defaultHeaders: Record<string, string>;

  constructor(
    private request: APIRequestContext,
    baseURL: string,
    options?: { token?: string; headers?: Record<string, string> }
  ) {
    this.baseURL = baseURL;
    this.token = options?.token || null;
    this.defaultHeaders = options?.headers || {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Set authentication token
   */
  setToken(token: string): void {
    this.token = token;
  }

  /**
   * Get request headers
   */
  private getHeaders(): Record<string, string> {
    const headers = { ...this.defaultHeaders };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    return headers;
  }

  /**
   * Make a GET request
   */
  async get(
    endpoint: string,
    options?: ApiRequestOptions
  ): Promise<ApiTestResult> {
    const startTime = Date.now();

    const url = this.buildUrl(endpoint, options?.params);
    const headers = { ...this.getHeaders(), ...options?.headers };

    const response = await this.request.get(url, {
      headers,
      timeout: options?.timeout || TIMEOUTS.DEFAULT,
    });

    return await this.buildResult(response, startTime);
  }

  /**
   * Make a POST request
   */
  async post(
    endpoint: string,
    data?: unknown,
    options?: ApiRequestOptions
  ): Promise<ApiTestResult> {
    const startTime = Date.now();

    const url = this.buildUrl(endpoint, options?.params);
    const headers = { ...this.getHeaders(), ...options?.headers };

    const response = await this.request.post(url, {
      headers,
      data,
      timeout: options?.timeout || TIMEOUTS.DEFAULT,
    });

    return await this.buildResult(response, startTime);
  }

  /**
   * Make a PUT request
   */
  async put(
    endpoint: string,
    data?: unknown,
    options?: ApiRequestOptions
  ): Promise<ApiTestResult> {
    const startTime = Date.now();

    const url = this.buildUrl(endpoint, options?.params);
    const headers = { ...this.getHeaders(), ...options?.headers };

    const response = await this.request.put(url, {
      headers,
      data,
      timeout: options?.timeout || TIMEOUTS.DEFAULT,
    });

    return await this.buildResult(response, startTime);
  }

  /**
   * Make a PATCH request
   */
  async patch(
    endpoint: string,
    data?: unknown,
    options?: ApiRequestOptions
  ): Promise<ApiTestResult> {
    const startTime = Date.now();

    const url = this.buildUrl(endpoint, options?.params);
    const headers = { ...this.getHeaders(), ...options?.headers };

    const response = await this.request.patch(url, {
      headers,
      data,
      timeout: options?.timeout || TIMEOUTS.DEFAULT,
    });

    return await this.buildResult(response, startTime);
  }

  /**
   * Make a DELETE request
   */
  async delete(
    endpoint: string,
    options?: ApiRequestOptions
  ): Promise<ApiTestResult> {
    const startTime = Date.now();

    const url = this.buildUrl(endpoint, options?.params);
    const headers = { ...this.getHeaders(), ...options?.headers };

    const response = await this.request.delete(url, {
      headers,
      timeout: options?.timeout || TIMEOUTS.DEFAULT,
    });

    return await this.buildResult(response, startTime);
  }

  /**
   * Build URL with query params
   */
  private buildUrl(
    endpoint: string,
    params?: Record<string, string | number>
  ): string {
    let url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;

    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value));
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }

    return url;
  }

  /**
   * Build test result from response
   */
  private async buildResult(
    response: APIResponse,
    startTime: number
  ): Promise<ApiTestResult> {
    const duration = Date.now() - startTime;
    const headers: Record<string, string> = {};

    response.headers().forEach((value, key) => {
      headers[key] = value;
    });

    let body: unknown;
    try {
      body = await response.json().catch(() => response.text());
    } catch {
      body = await response.text();
    }

    return {
      url: response.url(),
      method: response.request().method(),
      status: response.status(),
      statusText: response.statusText(),
      headers,
      body,
      duration,
      size: parseInt(headers['content-length'] || '0', 10),
    };
  }
}

/**
 * Create API tester for portal service
 */
export function createPortalApiTester(
  request: APIRequestContext,
  options?: { token?: string }
): ApiTester {
  return new ApiTester(
    request,
    process.env.PORTAL_API_URL || 'http://localhost:8010',
    options
  );
}

/**
 * Create API tester for NL2SQL service
 */
export function createNL2SQLApiTester(
  request: APIRequestContext,
  options?: { token?: string }
): ApiTester {
  return new ApiTester(
    request,
    process.env.NL2SQL_API_URL || 'http://localhost:8011',
    options
  );
}

/**
 * API test assertions
 */
export class ApiAssertions {
  constructor(private result: ApiTestResult) {}

  /**
   * Assert status code
   */
  assertStatus(expected: number): void {
    expect(this.result.status).toBe(expected);
  }

  /**
   * Assert status in range
   */
  assertStatusInRange(min: number, max: number): void {
    expect(this.result.status).toBeGreaterThanOrEqual(min);
    expect(this.result.status).toBeLessThanOrEqual(max);
  }

  /**
   * Assert success status (2xx)
   */
  assertSuccess(): void {
    expect(this.result.status).toBeGreaterThanOrEqual(200);
    expect(this.result.status).toBeLessThan(300);
  }

  /**
   * Assert client error (4xx)
   */
  assertClientError(): void {
    expect(this.result.status).toBeGreaterThanOrEqual(400);
    expect(this.result.status).toBeLessThan(500);
  }

  /**
   * Assert server error (5xx)
   */
  assertServerError(): void {
    expect(this.result.status).toBeGreaterThanOrEqual(500);
    expect(this.result.status).toBeLessThan(600);
  }

  /**
   * Assert response header
   */
  assertHeader(name: string, value: string): void {
    expect(this.result.headers[name.toLowerCase()]).toBe(value);
  }

  /**
   * Assert content type
   */
  assertContentType(type: string): void {
    const contentType = this.result.headers['content-type'];
    expect(contentType).toContain(type);
  }

  /**
   * Assert JSON response
   */
  async assertJson(): Promise<void> {
    this.assertContentType('application/json');
    expect(typeof this.result.body).toBe('object');
  }

  /**
   * Assert response body property
   */
  assertBodyProperty<K extends keyof unknown>(path: string, value: unknown): void {
    const props = path.split('.');
    // @ts-ignore
    let current: unknown = this.result.body;

    for (const prop of props) {
      expect(current).toBeDefined();
      // @ts-ignore
      current = current[prop];
    }

    expect(current).toEqual(value);
  }

  /**
   * Assert response time
   */
  assertResponseTime(maxMs: number): void {
    expect(this.result.duration).toBeLessThanOrEqual(maxMs);
  }

  /**
   * Assert response size
   */
  assertResponseSize(maxBytes: number): void {
    expect(this.result.size).toBeLessThanOrEqual(maxBytes);
  }

  /**
   * Assert body contains
   */
  assertBodyContains(text: string): void {
    const bodyStr = typeof this.result.body === 'string'
      ? this.result.body
      : JSON.stringify(this.result.body);
    expect(bodyStr).toContain(text);
  }

  /**
   * Assert body matches regex
   */
  assertBodyMatches(pattern: RegExp): void {
    const bodyStr = typeof this.result.body === 'string'
      ? this.result.body
      : JSON.stringify(this.result.body);
    expect(bodyStr).toMatch(pattern);
  }

  /**
   * Get body as typed object
   */
  getBody<T>(): T {
    return this.result.body as T;
  }
}

/**
 * Create assertions from API result
 */
export function assertApi(result: ApiTestResult): ApiAssertions {
  return new ApiAssertions(result);
}

/**
 * API test suite runner
 */
export class ApiTestSuite {
  private tests: Array<{
    name: string;
    fn: (tester: ApiTester) => Promise<void>;
  }> = [];

  constructor(
    private request: APIRequestContext,
    private baseURL: string,
    private token?: string
  ) {}

  /**
   * Add a test to the suite
   */
  test(name: string, fn: (tester: ApiTester) => Promise<void>): void {
    this.tests.push({ name, fn });
  }

  /**
   * Run all tests in the suite
   */
  async runAll(): Promise<
    Array<{ name: string; passed: boolean; error?: string; duration: number }>
  > {
    const tester = new ApiTester(this.request, this.baseURL, {
      token: this.token,
    });

    const results = [];

    for (const test of this.tests) {
      const startTime = Date.now();

      try {
        await test.fn(tester);
        results.push({
          name: test.name,
          passed: true,
          duration: Date.now() - startTime,
        });
      } catch (error) {
        results.push({
          name: test.name,
          passed: false,
          error: (error as Error).message,
          duration: Date.now() - startTime,
        });
      }
    }

    return results;
  }

  /**
   * Get test results summary
   */
  static summarize(
    results: Array<{ name: string; passed: boolean; error?: string; duration: number }>
  ): {
    total: number;
    passed: number;
    failed: number;
    duration: number;
    failures: string[];
  } {
    const passed = results.filter((r) => r.passed).length;
    const failed = results.filter((r) => !r.passed);
    const totalDuration = results.reduce((sum, r) => sum + r.duration, 0);

    return {
      total: results.length,
      passed,
      failed: failed.length,
      duration: totalDuration,
      failures: failed.map((f) => `${f.name}: ${f.error}`),
    };
  }
}

/**
 * Create API test suite
 */
export function createApiTestSuite(
  request: APIRequestContext,
  baseURL: string,
  token?: string
): ApiTestSuite {
  return new ApiTestSuite(request, baseURL, token);
}

/**
 * Login and get API tester with token
 */
export async function loginAndGetApiTester(
  request: APIRequestContext,
  baseURL: string,
  credentials: { username: string; password: string }
): Promise<ApiTester> {
  const tester = new ApiTester(request, baseURL);

  const result = await tester.post('/auth/login', credentials);

  if (result.status === 200 && result.body) {
    // @ts-ignore
    const token = result.body.data?.token || result.body.token;
    if (token) {
      tester.setToken(token);
    }
  }

  return tester;
}
