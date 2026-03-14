/**
 * LLM Store
 *
 * Zustand store for LLM chat and knowledge base functionality.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';

// Types
export type ChatRole = 'system' | 'user' | 'assistant' | 'function';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  token_count: number;
  error?: string;
  metadata?: Record<string, any>;
}

export interface ChatSession {
  session_id: string;
  user_id: number;
  model: string;
  system_prompt?: string;
  parameters: Record<string, any>;
  message_count: number;
  created_at: string;
  updated_at: string;
  title?: string;
}

export interface LLMModel {
  id: string;
  type: string;
  context_window: number;
  supports_streaming: boolean;
  supports_function_calling: boolean;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  user_id: number;
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  retrieval_top_k: number;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  kb_id: string;
  title: string;
  content: string;
  source_uri?: string;
  source_type: string;
  mime_type?: string;
  file_size?: number;
  chunk_count: number;
  status: string;
  created_at: string;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  content: string;
  score: number;
  metadata?: Record<string, any>;
}

export interface RAGAnswer {
  answer: string;
  sources: Array<{
    chunk_id: string;
    document_id: string;
    score: number;
  }>;
  context_used: number;
}

interface LLMState {
  // Chat state
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  currentMessages: ChatMessage[];
  availableModels: LLMModel[];
  streaming: boolean;
  loading: boolean;
  error: string | null;

  // Knowledge base state
  knowledgeBases: KnowledgeBase[];
  currentKB: KnowledgeBase | null;
  kbDocuments: Document[];
  searchResults: SearchResult[];

  // Chat actions
  fetchSessions: () => Promise<void>;
  createSession: (data: {
    model: string;
    system_prompt?: string;
    parameters?: Record<string, any>;
  }) => Promise<void>;
  fetchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  clearHistory: (sessionId: string) => Promise<void>;
  sendMessage: (sessionId: string, message: string, stream?: boolean) => Promise<void>;
  switchModel: (sessionId: string, newModel: string) => Promise<void>;
  updateParameters: (sessionId: string, parameters: Record<string, any>) => Promise<void>;
  fetchModels: () => Promise<void>;

  // Knowledge base actions
  fetchKnowledgeBases: () => Promise<void>;
  createKnowledgeBase: (data: {
    name: string;
    description?: string;
    embedding_model?: string;
    chunk_size?: number;
    chunk_overlap?: number;
    retrieval_top_k?: number;
  }) => Promise<void>;
  deleteKnowledgeBase: (kbId: string) => Promise<void>;
  addDocument: (kbId: string, data: {
    title: string;
    content: string;
    source_uri?: string;
    source_type?: string;
    chunk_strategy?: string;
  }) => Promise<void>;
  deleteDocument: (kbId: string, documentId: string) => Promise<void>;
  searchKnowledgeBase: (kbId: string, query: string, topK?: number) => Promise<void>;
  askQuestion: (kbId: string, question: string, sessionId?: string) => Promise<RAGAnswer>;

  // State management
  setCurrentSession: (session: ChatSession | null) => void;
  setCurrentKB: (kb: KnowledgeBase | null) => void;
  clearError: () => void;
}

export const useLLMStore = create<LLMState>()(
  persist(
    (set, get) => ({
    // Initial state
    sessions: [],
    currentSession: null,
    currentMessages: [],
    availableModels: [],
    streaming: false,
    loading: false,
    error: null,
    knowledgeBases: [],
    currentKB: null,
    kbDocuments: [],
    searchResults: [],

    // Chat actions
    fetchSessions: async () => {
      set({ loading: true, error: null });
      try {
        const response = await api.get('/llm/chat/sessions');
        set({ sessions: response.data, loading: false });
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to fetch sessions',
          loading: false,
        });
        throw error;
      }
    },

    createSession: async (data) => {
      set({ loading: true, error: null });
      try {
        const response = await api.post('/llm/chat/sessions', data);
        const session = response.data;
        set((state) => ({
          sessions: [session, ...state.sessions],
          currentSession: session,
          currentMessages: [],
          loading: false,
        }));
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to create session',
          loading: false,
        });
        throw error;
      }
    },

    fetchSession: async (sessionId: string) => {
      set({ loading: true, error: null });
      try {
        const response = await api.get(`/llm/chat/sessions/${sessionId}`);
        set({
          currentSession: response.data,
          loading: false,
        });
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to fetch session',
          loading: false,
        });
        throw error;
      }
    },

    deleteSession: async (sessionId: string) => {
      set({ loading: true, error: null });
      try {
        await api.delete(`/llm/chat/sessions/${sessionId}`);
        set((state) => ({
          sessions: state.sessions.filter((s) => s.session_id !== sessionId),
          currentSession: state.currentSession?.session_id === sessionId ? null : state.currentSession,
          loading: false,
        }));
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to delete session',
          loading: false,
        });
        throw error;
      }
    },

    clearHistory: async (sessionId: string) => {
      set({ loading: true, error: null });
      try {
        await api.post(`/llm/chat/sessions/${sessionId}/clear`);
        set((state) => ({
          currentMessages: [],
          loading: false,
        }));
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to clear history',
          loading: false,
        });
        throw error;
      }
    },

    sendMessage: async (sessionId: string, message: string, stream = false) => {
      // Add user message optimistically
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content: message,
        status: 'completed',
        created_at: new Date().toISOString(),
        token_count: 0,
      };

      set((state) => ({
        currentMessages: [...state.currentMessages, userMessage],
      }));

      // Create placeholder for assistant response
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: '',
        status: 'processing',
        created_at: new Date().toISOString(),
        token_count: 0,
      };

      set((state) => ({
        currentMessages: [...state.currentMessages, assistantMessage],
        loading: true,
      }));

      try {
        const response = await api.post(`/llm/chat/sessions/${sessionId}/message`, {
          message,
          stream,
        });

        set((state) => ({
          currentMessages: state.currentMessages.map((msg) =>
            msg.id === assistantMessage.id
              ? { ...msg, ...response.data, status: 'completed' as const }
              : msg
          ),
          loading: false,
        }));
      } catch (error: any) {
        set((state) => ({
          currentMessages: state.currentMessages.map((msg) =>
            msg.id === assistantMessage.id
              ? { ...msg, status: 'failed' as const, error: 'Failed to get response' }
              : msg
          ),
          loading: false,
          error: error.response?.data?.detail || 'Failed to send message',
        }));
        throw error;
      }
    },

    switchModel: async (sessionId: string, newModel: string) => {
      try {
        const response = await api.put(`/llm/chat/sessions/${sessionId}/model`, null, {
          params: { new_model: newModel },
        });
        set({ currentSession: response.data });
      } catch (error: any) {
        set({ error: error.response?.data?.detail || 'Failed to switch model' });
        throw error;
      }
    },

    updateParameters: async (sessionId: string, parameters: Record<string, any>) => {
      try {
        const response = await api.put(`/llm/chat/sessions/${sessionId}/parameters`, parameters);
        set({ currentSession: response.data });
      } catch (error: any) {
        set({ error: error.response?.data?.detail || 'Failed to update parameters' });
        throw error;
      }
    },

    fetchModels: async () => {
      try {
        const response = await api.get('/llm/chat/models');
        set({ availableModels: response.data });
      } catch (error: any) {
        set({ error: error.response?.data?.detail || 'Failed to fetch models' });
      }
    },

    // Knowledge base actions
    fetchKnowledgeBases: async () => {
      set({ loading: true, error: null });
      try {
        const response = await api.get('/llm/knowledge-bases');
        set({ knowledgeBases: response.data, loading: false });
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to fetch knowledge bases',
          loading: false,
        });
        throw error;
      }
    },

    createKnowledgeBase: async (data) => {
      set({ loading: true, error: null });
      try {
        const response = await api.post('/llm/knowledge-bases', data);
        set((state) => ({
          knowledgeBases: [...state.knowledgeBases, response.data],
          loading: false,
        }));
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to create knowledge base',
          loading: false,
        });
        throw error;
      }
    },

    deleteKnowledgeBase: async (kbId: string) => {
      set({ loading: true, error: null });
      try {
        await api.delete(`/llm/knowledge-bases/${kbId}`);
        set((state) => ({
          knowledgeBases: state.knowledgeBases.filter((kb) => kb.id !== kbId),
          loading: false,
        }));
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to delete knowledge base',
          loading: false,
        });
        throw error;
      }
    },

    addDocument: async (kbId: string, data) => {
      set({ loading: true, error: null });
      try {
        const response = await api.post(`/llm/knowledge-bases/${kbId}/documents`, data);
        set((state) => ({
          loading: false,
        }));
        return response.data;
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to add document',
          loading: false,
        });
        throw error;
      }
    },

    deleteDocument: async (kbId: string, documentId: string) => {
      set({ loading: true, error: null });
      try {
        await api.delete(`/llm/knowledge-bases/${kbId}/documents/${documentId}`);
        set({ loading: false });
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to delete document',
          loading: false,
        });
        throw error;
      }
    },

    searchKnowledgeBase: async (kbId: string, query: string, topK?: number) => {
      set({ loading: true, error: null });
      try {
        const response = await api.post(`/llm/knowledge-bases/${kbId}/search`, {
          query,
          top_k: topK,
        });
        set({ searchResults: response.data, loading: false });
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to search',
          loading: false,
        });
        throw error;
      }
    },

    askQuestion: async (kbId: string, question: string, sessionId?: string) => {
      set({ loading: true, error: null });
      try {
        const response = await api.post(`/llm/knowledge-bases/${kbId}/answer`, {
          question,
          session_id: sessionId,
        });
        set({ loading: false });
        return response.data;
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Failed to get answer',
          loading: false,
        });
        throw error;
      }
    },

    // State management
    setCurrentSession: (session) => set({ currentSession: session }),
    setCurrentKB: (kb) => set({ currentKB: kb }),
    clearError: () => set({ error: null }),
  }),
  {
    name: 'llm-store',
    partialize: (state) => ({
      sessions: state.sessions,
      currentSession: state.currentSession,
      knowledgeBases: state.knowledgeBases,
      currentKB: state.currentKB,
    }),
  }
));

// Selectors
export const useChatSessions = () => useLLMStore((state) => state.sessions);
export const useCurrentChatSession = () => useLLMStore((state) => state.currentSession);
export const useChatMessages = () => useLLMStore((state) => state.currentMessages);
export const useLLMLoading = () => useLLMStore((state) => state.loading);
export const useLLMError = () => useLLMStore((state) => state.error);
export const useKnowledgeBases = () => useLLMStore((state) => state.knowledgeBases);
export const useSearchResults = () => useLLMStore((state) => state.searchResults);
