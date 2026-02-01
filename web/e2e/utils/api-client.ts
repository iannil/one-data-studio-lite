/**
 * API Client for E2E tests
 * Provides direct API access for setup/teardown and verification
 */

import { APIResponse, request } from '@playwright/test';
import { API_ENDPOINTS, TIMEOUTS } from './constants';

/**
 * API Client configuration
 */
interface ApiClientConfig {
  baseURL: string;
  timeout?: number;
}

/**
 * Login credentials
 */
export interface LoginCredentials {
  username: string;
  password: string;
}

/**
 * API Client class
 */
export class ApiClient {
  private baseURL: string;
  private timeout: number;
  private token: string | null = null;

  constructor(config: ApiClientConfig) {
    this.baseURL = config.baseURL;
    this.timeout = config.timeout || TIMEOUTS.DEFAULT;
  }

  /**
   * Set authentication token
   */
  setToken(token: string): void {
    this.token = token;
  }

  /**
   * Get authentication token
   */
  getToken(): string | null {
    return this.token;
  }

  /**
   * Clear authentication token
   */
  clearToken(): void {
    this.token = null;
  }

  /**
   * Get default headers
   */
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    return headers;
  }

  /**
   * Make an API request
   */
  private async request(
    method: string,
    endpoint: string,
    data?: unknown
  ): Promise<APIResponse> {
    const context = await request.newContext({
      baseURL: this.baseURL,
      extraHTTPHeaders: this.getHeaders(),
      timeout: this.timeout,
    });

    const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;

    let response: APIResponse;

    switch (method.toUpperCase()) {
      case 'GET':
        response = await context.get(url);
        break;
      case 'POST':
        response = await context.post(url, { data });
        break;
      case 'PUT':
        response = await context.put(url, { data });
        break;
      case 'PATCH':
        response = await context.patch(url, { data });
        break;
      case 'DELETE':
        response = await context.delete(url);
        break;
      default:
        throw new Error(`Unsupported HTTP method: ${method}`);
    }

    await context.dispose();
    return response;
  }

  /**
   * GET request
   */
  async get(endpoint: string): Promise<APIResponse> {
    return this.request('GET', endpoint);
  }

  /**
   * POST request
   */
  async post(endpoint: string, data?: unknown): Promise<APIResponse> {
    return this.request('POST', endpoint, data);
  }

  /**
   * PUT request
   */
  async put(endpoint: string, data?: unknown): Promise<APIResponse> {
    return this.request('PUT', endpoint, data);
  }

  /**
   * PATCH request
   */
  async patch(endpoint: string, data?: unknown): Promise<APIResponse> {
    return this.request('PATCH', endpoint, data);
  }

  /**
   * DELETE request
   */
  async delete(endpoint: string): Promise<APIResponse> {
    return this.request('DELETE', endpoint);
  }

  /**
   * Login with username and password
   */
  async login(credentials: LoginCredentials): Promise<{ success: boolean; token?: string; user?: unknown }> {
    const response = await this.post(API_ENDPOINTS.LOGIN, credentials);
    const data = await response.json();

    if (response.ok() && data.success) {
      this.token = data.data?.token || data.data?.access_token;
      return {
        success: true,
        token: this.token || undefined,
        user: data.data?.user,
      };
    }

    return { success: false };
  }

  /**
   * Logout
   */
  async logout(): Promise<boolean> {
    const response = await this.post(API_ENDPOINTS.LOGOUT);
    this.clearToken();
    return response.ok();
  }

  /**
   * Get user info
   */
  async getUserInfo(): Promise<unknown> {
    const response = await this.get(API_ENDPOINTS.USER_INFO);
    const data = await response.json();
    return data.data;
  }

  /**
   * Validate token
   */
  async validateToken(): Promise<boolean> {
    const response = await this.get(API_ENDPOINTS.VALIDATE);
    const data = await response.json();
    return data.success;
  }

  /**
   * Get subsystems status
   */
  async getSubsystems(): Promise<unknown> {
    const response = await this.get(API_ENDPOINTS.SUBSYSTEMS);
    const data = await response.json();
    return data.data;
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.get('/health');
      return response.ok();
    } catch {
      return false;
    }
  }
}

/**
 * Create API client for portal service
 */
export function createPortalClient(): ApiClient {
  return new ApiClient({
    baseURL: process.env.PORTAL_API_URL || 'http://localhost:8010',
  });
}

/**
 * Create API client for NL2SQL service
 */
export function createNL2SQLClient(): ApiClient {
  return new ApiClient({
    baseURL: process.env.NL2SQL_API_URL || 'http://localhost:8011',
  });
}

/**
 * Create API client for Audit Log service
 */
export function createAuditLogClient(): ApiClient {
  return new ApiClient({
    baseURL: process.env.AUDIT_LOG_API_URL || 'http://localhost:8016',
  });
}

/**
 * Create API client for Data API service
 */
export function createDataApiClient(): ApiClient {
  return new ApiClient({
    baseURL: process.env.DATA_API_URL || 'http://localhost:8014',
  });
}

/**
 * Create API client for Sensitive Detection service
 */
export function createSensitiveDetectClient(): ApiClient {
  return new ApiClient({
    baseURL: process.env.SENSITIVE_DETECT_API_URL || 'http://localhost:8015',
  });
}
