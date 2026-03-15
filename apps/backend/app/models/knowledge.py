"""
Knowledge Base Models

Models for RAG (Retrieval-Augmented Generation) functionality including
knowledge bases, documents, vector indices, and retrieval results.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON, Float, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChunkStrategy(str):
    """Text chunking strategies"""
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"


class DocumentStatus(str):
    """Document processing status"""
    PENDING = "pending"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"


class VectorBackend(str):
    """Vector storage backends"""
    CHROMADB = "chromadb"
    FAISS = "faiss"
    PGVECTOR = "pgvector"
    QDRANT = "qdrant"
    MILVUS = "milvus"
    MEMORY = "memory"


class EmbeddingProvider(str):
    """Embedding model providers"""
    OPENAI = "openai"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    SENTENCETRANSFORMERS = "sentencetransformers"
    BGE = "bge"
    CUSTOM = "custom"


class KnowledgeBase(Base):
    """Knowledge Base for RAG"""
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    kb_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Embedding configuration
    embedding_model: Mapped[str] = mapped_column(String(100), default="bge-large-zh")
    embedding_provider: Mapped[str] = mapped_column(String(50), default=EmbeddingProvider.BGE)
    embedding_dim: Mapped[int] = mapped_column(Integer, default=1024)

    # Chunking configuration
    chunk_strategy: Mapped[str] = mapped_column(String(50), default=ChunkStrategy.FIXED_SIZE)
    chunk_size: Mapped[int] = mapped_column(Integer, default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50)

    # Retrieval configuration
    retrieval_top_k: Mapped[int] = mapped_column(Integer, default=5)
    retrieval_score_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rerank_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rerank_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Vector storage
    vector_backend: Mapped[str] = mapped_column(String(50), default=VectorBackend.MEMORY)
    vector_collection: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Permissions
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_roles: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    allowed_users: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Tags and metadata
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    record_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Statistics
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    total_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<KnowledgeBase {self.kb_id}:{self.name}>"


class KnowledgeDocument(Base):
    """Document in a Knowledge Base"""
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    doc_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Knowledge base reference
    kb_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Document info
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For smaller docs
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256

    # Source information
    source_uri: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # upload, url, file, crawler
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Storage path (for larger files)
    storage_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    storage_backend: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Processing status
    status: Mapped[str] = mapped_column(String(50), default=DocumentStatus.PENDING)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    indexed_chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Chunking info
    chunk_strategy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chunk_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_overlap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    record_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Access control
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # Owner
    uploader_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<KnowledgeDocument {self.doc_id}:{self.title}>"


class DocumentChunk(Base):
    """Chunk of a document for vector search"""
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    chunk_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # References
    doc_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    kb_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Chunk content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_length: Mapped[int] = mapped_column(Integer, nullable=False)  # character count

    # Position in document
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_pos: Mapped[int] = mapped_column(Integer, default=0)
    end_pos: Mapped[int] = mapped_column(Integer, default=0)

    # Embedding (for pgvector backend)
    embedding: Mapped[Optional[list]] = mapped_column(ARRAY(Float), nullable=True)

    # Metadata
    record_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # For vector ID in external stores (ChromaDB, Qdrant, etc.)
    vector_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DocumentChunk {self.chunk_id}>"


class VectorIndex(Base):
    """Vector Index configuration for different backends"""
    __tablename__ = "vector_indices"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    index_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Index info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Backend configuration
    backend: Mapped[str] = mapped_column(String(50), nullable=False)  # chromadb, faiss, pgvector, etc.
    collection_name: Mapped[str] = mapped_column(String(256), nullable=False)

    # Embedding configuration
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)

    # Index configuration
    index_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # HNSW, IVF, FLAT
    metric: Mapped[str] = mapped_column(String(20), default="cosine")  # cosine, l2, ip

    # Index parameters
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Example for HNSW: {"M": 16, "ef_construction": 200}

    # Connection info
    endpoint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    api_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Statistics
    vector_count: Mapped[int] = mapped_column(Integer, default=0)
    index_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<VectorIndex {self.index_id}:{self.name}>"


class RetrievalResult(Base):
    """Logged retrieval results for analytics"""
    __tablename__ = "retrieval_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Query info
    kb_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding: Mapped[Optional[list]] = mapped_column(ARRAY(Float), nullable=True)

    # Results
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0)

    # Retrieved chunks
    chunk_ids: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    scores: Mapped[Optional[list]] = mapped_column(ARRAY(Float), nullable=True)

    # Performance
    retrieval_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # User context
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Feedback
    helpful: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RetrievalResult {self.id}>"


class RAGSession(Base):
    """RAG Chat Session"""
    __tablename__ = "rag_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Knowledge base
    kb_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Session info
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # Configuration
    model: Mapped[str] = mapped_column(String(100), default="gpt-4")
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2000)

    # Owner
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RAGSession {self.session_id}>"


class RAGMessage(Base):
    """RAG Chat Message"""
    __tablename__ = "rag_messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Session reference
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Message content
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Retrieval context
    retrieved_chunks: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    retrieval_scores: Mapped[Optional[list]] = mapped_column(ARRAY(Float), nullable=True)

    # Token usage
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Cost estimation (USD)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timing
    generation_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Feedback
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RAGMessage {self.id}:{self.role}>"
