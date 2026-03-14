/**
 * IDE Store - Zustand state management for VS Code and terminal sessions
 */

import { create } from 'zustand';
import { ideApi } from '@/services/api/ide';
import {
  IDEType,
  VSCodeInstance,
  VSCodeServerConfig,
  TerminalSession,
  TerminalMessage,
  VSCodeStatus,
  TerminalStatus,
} from '@/types/ide';

interface IDEState {
  // VS Code instances
  vscodeInstances: VSCodeInstance[];
  vscodeLoading: boolean;
  vscodeError: string | null;

  // Terminal sessions
  terminalSessions: TerminalSession[];
  terminalLoading: boolean;
  terminalError: string | null;

  // Current session
  currentInstance: VSCodeInstance | null;
  currentSession: TerminalSession | null;

  // Actions
  fetchVSCodeInstances: () => Promise<void>;
  createVSCodeInstance: (notebookId: number, config?: VSCodeServerConfig) => Promise<VSCodeInstance>;
  startVSCodeInstance: (instanceId: string) => Promise<void>;
  stopVSCodeInstance: (instanceId: string) => Promise<void>;
  restartVSCodeInstance: (instanceId: string) => Promise<void>;
  deleteVSCodeInstance: (instanceId: string, removeData?: boolean) => Promise<void>;
  installExtension: (instanceId: string, extensionId: string) => Promise<void>;

  // Terminal actions
  fetchTerminalSessions: (notebookId?: number) => Promise<void>;
  createTerminalSession: (notebookId: number, config?: {
    shell?: string;
    rows?: number;
    cols?: number;
    cwd?: string;
    env_vars?: Record<string, string>;
  }) => Promise<TerminalSession>;
  sendTerminalInput: (sessionId: string, input: string) => Promise<void>;
  resizeTerminal: (sessionId: string, rows: number, cols: number) => Promise<void>;
  getTerminalOutput: (sessionId: string, since?: string) => Promise<TerminalMessage[]>;
  terminateTerminalSession: (sessionId: string) => Promise<void>;
  deleteTerminalSession: (sessionId: string) => Promise<void>;

  // Current session
  setCurrentInstance: (instance: VSCodeInstance | null) => void;
  setCurrentSession: (session: TerminalSession | null) => void;

  // Health check
  healthCheck: () => Promise<void>;
}

export const useIDEStore = create<IDEState>((set, get) => ({
  // Initial state
  vscodeInstances: [],
  vscodeLoading: false,
  vscodeError: null,
  terminalSessions: [],
  terminalLoading: false,
  terminalError: null,
  currentInstance: null,
  currentSession: null,

  // VS Code actions
  fetchVSCodeInstances: async () => {
    set({ vscodeLoading: true, vscodeError: null });
    try {
      const response = await ideApi.listVSCodeInstances();
      set({ vscodeInstances: response.data || [], vscodeLoading: false });
    } catch (error: any) {
      set({
        vscodeError: error.message || 'Failed to fetch VS Code instances',
        vscodeLoading: false,
      });
    }
  },

  createVSCodeInstance: async (notebookId, config) => {
    try {
      const response = await ideApi.createVSCodeInstance(notebookId, config);
      const instance = response.data;
      set((state) => ({
        vscodeInstances: [...state.vscodeInstances, instance],
        currentInstance: instance,
      }));
      return instance;
    } catch (error: any) {
      throw new Error(error.message || 'Failed to create VS Code instance');
    }
  },

  startVSCodeInstance: async (instanceId) => {
    try {
      await ideApi.startVSCodeInstance(instanceId);
      await get().fetchVSCodeInstances();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to start VS Code instance');
    }
  },

  stopVSCodeInstance: async (instanceId) => {
    try {
      await ideApi.stopVSCodeInstance(instanceId);
      await get().fetchVSCodeInstances();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to stop VS Code instance');
    }
  },

  restartVSCodeInstance: async (instanceId) => {
    try {
      await ideApi.restartVSCodeInstance(instanceId);
      await get().fetchVSCodeInstances();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to restart VS Code instance');
    }
  },

  deleteVSCodeInstance: async (instanceId, removeData = false) => {
    try {
      await ideApi.deleteVSCodeInstance(instanceId, removeData);
      set((state) => ({
        vscodeInstances: state.vscodeInstances.filter((i) => i.id !== instanceId),
        currentInstance: state.currentInstance?.id === instanceId ? null : state.currentInstance,
      }));
    } catch (error: any) {
      throw new Error(error.message || 'Failed to delete VS Code instance');
    }
  },

  installExtension: async (instanceId, extensionId) => {
    try {
      await ideApi.installExtension(instanceId, extensionId);
      // Refresh instances
      await get().fetchVSCodeInstances();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to install extension');
    }
  },

  // Terminal actions
  fetchTerminalSessions: async (notebookId) => {
    set({ terminalLoading: true, terminalError: null });
    try {
      const response = await ideApi.listTerminalSessions(notebookId);
      set({ terminalSessions: response.data || [], terminalLoading: false });
    } catch (error: any) {
      set({
        terminalError: error.message || 'Failed to fetch terminal sessions',
        terminalLoading: false,
      });
    }
  },

  createTerminalSession: async (notebookId, config) => {
    try {
      const response = await ideApi.createTerminalSession({
        notebook_id: notebookId,
        shell: config?.shell || '/bin/bash',
        rows: config?.rows || 24,
        cols: config?.cols || 80,
        cwd: config?.cwd || '/home/jovyan',
        env_vars: config?.env_vars || {},
      });
      const session = response.data;
      set((state) => ({
        terminalSessions: [...state.terminalSessions, session],
        currentSession: session,
      }));
      return session;
    } catch (error: any) {
      throw new Error(error.message || 'Failed to create terminal session');
    }
  },

  sendTerminalInput: async (sessionId, input) => {
    try {
      await ideApi.sendTerminalInput(sessionId, { input });
    } catch (error: any) {
      throw new Error(error.message || 'Failed to send terminal input');
    }
  },

  resizeTerminal: async (sessionId, rows, cols) => {
    try {
      await ideApi.resizeTerminal(sessionId, { rows, cols });
    } catch (error: any) {
      throw new Error(error.message || 'Failed to resize terminal');
    }
  },

  getTerminalOutput: async (sessionId, since) => {
    try {
      const response = await ideApi.getTerminalOutput(sessionId, since);
      return response.data || [];
    } catch (error: any) {
      throw new Error(error.message || 'Failed to get terminal output');
    }
  },

  terminateTerminalSession: async (sessionId) => {
    try {
      await ideApi.terminateTerminalSession(sessionId);
      await get().fetchTerminalSessions();
    } catch (error: any) {
      throw new Error(error.message || 'Failed to terminate terminal session');
    }
  },

  deleteTerminalSession: async (sessionId) => {
    try {
      await ideApi.deleteTerminalSession(sessionId);
      set((state) => ({
        terminalSessions: state.terminalSessions.filter((s) => s.id !== sessionId),
        currentSession: state.currentSession?.id === sessionId ? null : state.currentSession,
      }));
    } catch (error: any) {
      throw new Error(error.message || 'Failed to delete terminal session');
    }
  },

  // Current session setters
  setCurrentInstance: (instance) => {
    set({ currentInstance: instance });
  },

  setCurrentSession: (session) => {
    set({ currentSession: session });
  },

  // Health check
  healthCheck: async () => {
    try {
      await ideApi.healthCheck();
    } catch (error) {
      console.error('Health check failed:', error);
    }
  },
}));
