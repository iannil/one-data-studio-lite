/**
 * Tenant Store
 *
 * Zustand store for managing multi-tenant resources.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';
import {
  Tenant,
  ResourceQuota,
  QuotaUsage,
  QuotaSummary,
  TenantUser,
  TenantApiKey,
  AuditLog,
  TenantStatus,
  TenantTier,
  TenantUserRole,
  CreateTenantRequest,
  UpdateTenantRequest,
  InviteUserRequest,
  AddUserRequest,
  CreateAPIKeyRequest,
  QuotaCheckResult,
  QuotaCheckRequest,
} from '../types/tenant';

interface TenantState {
  // Data
  tenants: Tenant[];
  currentTenant: Tenant | null;
  quotaSummary: QuotaSummary | null;
  tenantUsers: TenantUser[];
  apiKeys: TenantApiKey[];
  auditLogs: AuditLog[];

  // UI State
  loading: boolean;
  error: string | null;
  currentTenantId: number | null;

  // Tenant Actions
  fetchTenants: () => Promise<Tenant[]>;
  fetchTenant: (tenantId: number) => Promise<Tenant>;
  createTenant: (request: CreateTenantRequest) => Promise<Tenant>;
  updateTenant: (tenantId: number, request: UpdateTenantRequest) => Promise<Tenant>;
  changeTier: (tenantId: number, tier: TenantTier) => Promise<void>;
  suspendTenant: (tenantId: number, reason?: string) => Promise<void>;
  activateTenant: (tenantId: number) => Promise<void>;
  setCurrentTenant: (tenantId: number | null) => void;

  // Quota Actions
  fetchQuotaSummary: (tenantId: number) => Promise<QuotaSummary>;
  checkQuota: (tenantId: number, request: QuotaCheckRequest) => Promise<QuotaCheckResult>;
  allocateQuota: (tenantId: number, resourceType: string, count: number) => Promise<void>;
  releaseQuota: (tenantId: number, resourceType: string, count: number) => Promise<void>;

  // User Actions
  fetchTenantUsers: (tenantId: number) => Promise<TenantUser[]>;
  addTenantUser: (tenantId: number, request: AddUserRequest) => Promise<void>;
  removeTenantUser: (tenantId: number, userId: number) => Promise<void>;
  updateUserRole: (tenantId: number, userId: number, role: TenantUserRole) => Promise<void>;
  inviteUser: (tenantId: number, request: InviteUserRequest) => Promise<any>;

  // API Key Actions
  fetchAPIKeys: (tenantId: number) => Promise<TenantApiKey[]>;
  createAPIKey: (tenantId: number, request: CreateAPIKeyRequest) => Promise<any>;
  revokeAPIKey: (tenantId: number, keyId: number) => Promise<void>;

  // Audit Actions
  fetchAuditLogs: (tenantId: number, filters?: any) => Promise<AuditLog[]>;

  // Utility
  clearError: () => void;
  setError: (error: string) => void;
}

export const useTenantStore = create<TenantState>()(
  persist(
    (set, get) => ({
      // Initial state
      tenants: [],
      currentTenant: null,
      quotaSummary: null,
      tenantUsers: [],
      apiKeys: [],
      auditLogs: [],
      loading: false,
      error: null,
      currentTenantId: null,

      // Fetch all tenants
      fetchTenants: async () => {
        set({ loading: true, error: null });
        try {
          const response = await api.get('/tenant/');
          const tenants: Tenant[] = response.data;
          set({ tenants, loading: false });
          return tenants;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Fetch single tenant
      fetchTenant: async (tenantId) => {
        set({ loading: true, error: null });
        try {
          const response = await api.get(`/tenant/${tenantId}`);
          const tenant: Tenant = response.data;
          set({ currentTenant: tenant, loading: false });
          return tenant;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Create tenant
      createTenant: async (request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.post('/tenant/', {
            name: request.name,
            slug: request.slug,
            contact_email: request.contactEmail,
            contact_name: request.contactName,
            description: request.description,
            tier: request.tier,
            trial_days: request.trialDays,
            settings: request.settings,
          });
          const tenant: Tenant = response.data;
          await get().fetchTenants();
          set({ loading: false });
          return tenant;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Update tenant
      updateTenant: async (tenantId, request) => {
        set({ loading: true, error: null });
        try {
          const response = await api.put(`/tenant/${tenantId}`, {
            name: request.name,
            description: request.description,
            contact_email: request.contactEmail,
            contact_name: request.contactName,
            contact_phone: request.contactPhone,
            billing_email: request.billingEmail,
            billing_address: request.billingAddress,
            settings: request.settings,
          });
          const tenant: Tenant = response.data;
          await get().fetchTenants();
          set({ loading: false });
          return tenant;
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Change tier
      changeTier: async (tenantId, tier) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/tenant/${tenantId}/tier`, { tier });
          await get().fetchTenants();
          set({ loading: false });
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Suspend tenant
      suspendTenant: async (tenantId, reason) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/tenant/${tenantId}/suspend`, null, {
            params: { reason },
          });
          await get().fetchTenants();
          set({ loading: false });
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Activate tenant
      activateTenant: async (tenantId) => {
        set({ loading: true, error: null });
        try {
          await api.post(`/tenant/${tenantId}/activate`);
          await get().fetchTenants();
          set({ loading: false });
        } catch (error: any) {
          set({ error: error.message, loading: false });
          throw error;
        }
      },

      // Set current tenant
      setCurrentTenant: (tenantId) => {
        set({ currentTenantId: tenantId });
        const tenant = get().tenants.find((t) => t.id === tenantId);
        if (tenant) {
          set({ currentTenant: tenant });
        }
      },

      // Fetch quota summary
      fetchQuotaSummary: async (tenantId) => {
        try {
          const response = await api.get(`/tenant/${tenantId}/quota`);
          const summary: QuotaSummary = response.data;
          set({ quotaSummary: summary });
          return summary;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Check quota
      checkQuota: async (tenantId, request) => {
        try {
          const response = await api.post(`/tenant/${tenantId}/quota/check`, {
            resource_type: request.resourceType,
            count: request.count,
          });
          return response.data as QuotaCheckResult;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Allocate quota
      allocateQuota: async (tenantId, resourceType, count) => {
        try {
          await api.post(`/tenant/${tenantId}/quota/allocate`, {
            resource_type: resourceType,
            count,
          });
          await get().fetchQuotaSummary(tenantId);
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Release quota
      releaseQuota: async (tenantId, resourceType, count) => {
        try {
          await api.post(`/tenant/${tenantId}/quota/release`, {
            resource_type: resourceType,
            count,
          });
          await get().fetchQuotaSummary(tenantId);
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Fetch tenant users
      fetchTenantUsers: async (tenantId) => {
        try {
          const response = await api.get(`/tenant/${tenantId}/users`);
          const users: TenantUser[] = response.data;
          set({ tenantUsers: users });
          return users;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Add tenant user
      addTenantUser: async (tenantId, request) => {
        try {
          await api.post(`/tenant/${tenantId}/users`, {
            user_id: request.userId,
            role: request.role,
            is_primary: request.isPrimary,
          });
          await get().fetchTenantUsers(tenantId);
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Remove tenant user
      removeTenantUser: async (tenantId, userId) => {
        try {
          await api.delete(`/tenant/${tenantId}/users/${userId}`);
          await get().fetchTenantUsers(tenantId);
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Update user role
      updateUserRole: async (tenantId, userId, role) => {
        try {
          await api.put(`/tenant/${tenantId}/users/${userId}/role`, { role });
          await get().fetchTenantUsers(tenantId);
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Invite user
      inviteUser: async (tenantId, request) => {
        try {
          const response = await api.post(`/tenant/${tenantId}/invite`, {
            email: request.email,
            role: request.role,
          });
          return response.data;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Fetch API keys
      fetchAPIKeys: async (tenantId) => {
        try {
          const response = await api.get(`/tenant/${tenantId}/api-keys`);
          const keys: TenantApiKey[] = response.data;
          set({ apiKeys: keys });
          return keys;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Create API key
      createAPIKey: async (tenantId, request) => {
        try {
          const response = await api.post(`/tenant/${tenantId}/api-keys`, {
            name: request.name,
            scopes: request.scopes,
            expires_in_days: request.expiresInDays,
          });
          await get().fetchAPIKeys(tenantId);
          return response.data;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Revoke API key
      revokeAPIKey: async (tenantId, keyId) => {
        try {
          await api.delete(`/tenant/${tenantId}/api-keys/${keyId}`);
          await get().fetchAPIKeys(tenantId);
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Fetch audit logs
      fetchAuditLogs: async (tenantId, filters) => {
        try {
          const params = filters || {};
          const response = await api.get(`/tenant/${tenantId}/audit-logs`, { params });
          const logs: AuditLog[] = response.data;
          set({ auditLogs: logs });
          return logs;
        } catch (error: any) {
          set({ error: error.message });
          throw error;
        }
      },

      // Clear error
      clearError: () => set({ error: null }),

      // Set error
      setError: (error) => set({ error }),
    }),
    {
      name: 'tenant-storage',
      partialize: (state) => ({
        currentTenantId: state.currentTenantId,
      }),
    }
  )
);

// Selectors
export const selectActiveTenants = (state: TenantState) =>
  state.tenants.filter((t) => t.status === TenantStatus.ACTIVE);

export const selectTenantById = (tenantId: number) => (state: TenantState) =>
  state.tenants.find((t) => t.id === tenantId);

export const selectTenantBySlug = (slug: string) => (state: TenantState) =>
  state.tenants.find((t) => t.slug === slug);

export const selectTenantOwners = (tenantId: number) => (state: TenantState) =>
  state.tenantUsers.filter((u) => u.role === TenantUserRole.OWNER);

export const selectTenantAdmins = (tenantId: number) => (state: TenantState) =>
  state.tenantUsers.filter((u) => u.role === TenantUserRole.ADMIN);

export const selectOverQuotaResources = (state: TenantState) => {
  if (!state.quotaSummary) return [];
  const over: string[] = [];
  const summary = state.quotaSummary;

  Object.entries(summary).forEach(([key, value]: [string, any]) => {
    if (typeof value === 'object' && value !== null && 'percent' in value) {
      if (value.percent > 100) {
        over.push(key);
      }
    }
  });

  return over;
};
