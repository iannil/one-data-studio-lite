"""
Knowledge Base Service Package

Provides RAG (Retrieval-Augmented Generation) functionality:
- Vector storage backends (ChromaDB, Faiss, PGVector, Memory)
- Embedding service (OpenAI, Cohere, HuggingFace, BGE)
- RAG engine for question answering
- Enterprise permissions and multi-tenant support
"""

from .vector_store import (
    VectorStoreBackend,
    MemoryVectorStore,
    FaissVectorStore,
    ChromaDBVectorStore,
    PGVectorStore,
    VectorResult,
    get_vector_store,
)

from .embedding import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    CohereEmbeddingProvider,
    HuggingFaceEmbeddingProvider,
    BGEEmbeddingProvider,
    CustomEmbeddingProvider,
    EmbeddingService,
    EmbeddingResult,
    get_embedding_service,
    embed_texts,
    embed_text,
)

from .rag import (
    RAGEngine,
    SearchResult,
    RAGAnswer,
    TextChunker,
    get_rag_engine,
)

__all__ = [
    # Vector Store
    "VectorStoreBackend",
    "MemoryVectorStore",
    "FaissVectorStore",
    "ChromaDBVectorStore",
    "PGVectorStore",
    "VectorResult",
    "get_vector_store",
    # Embedding
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "CohereEmbeddingProvider",
    "HuggingFaceEmbeddingProvider",
    "BGEEmbeddingProvider",
    "CustomEmbeddingProvider",
    "EmbeddingService",
    "EmbeddingResult",
    "get_embedding_service",
    "embed_texts",
    "embed_text",
    # RAG
    "RAGEngine",
    "SearchResult",
    "RAGAnswer",
    "TextChunker",
    "get_rag_engine",
]
