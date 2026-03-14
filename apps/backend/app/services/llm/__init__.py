"""
LLM Services Package

Provides large language model capabilities including:
- Chat/completion
- Knowledge base RAG
- Inference service management
"""

from app.services.llm.chat import (
    ChatRole,
    MessageStatus,
    ChatMessage,
    ChatSession,
    ChatParameters,
    LLMRouter,
    LLMChatService,
    llm_chat_service,
)
from app.services.llm.knowledge import (
    DocumentStatus,
    ChunkStrategy,
    DocumentChunk,
    Document,
    KnowledgeBase,
    TextChunker,
    EmbeddingService,
    VectorStore,
    RAGService,
    rag_service,
)

__all__ = [
    # Chat
    "ChatRole",
    "MessageStatus",
    "ChatMessage",
    "ChatSession",
    "ChatParameters",
    "LLMRouter",
    "LLMChatService",
    "llm_chat_service",
    # Knowledge
    "DocumentStatus",
    "ChunkStrategy",
    "DocumentChunk",
    "Document",
    "KnowledgeBase",
    "TextChunker",
    "EmbeddingService",
    "VectorStore",
    "RAGService",
    "rag_service",
]
