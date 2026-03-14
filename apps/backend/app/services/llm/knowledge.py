"""
Knowledge Base RAG (Retrieval-Augmented Generation) Service

Provides private knowledge base functionality with:
- Document upload and processing
- Text chunking and embedding
- Vector storage and retrieval
- RAG-based question answering
"""

import asyncio
import hashlib
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)
from dataclasses import dataclass

from app.core.config import settings


class DocumentStatus(str, Enum):
    """Document processing status"""

    PENDING = "pending"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"


class ChunkStrategy(str, Enum):
    """Text chunking strategies"""

    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"


@dataclass
class DocumentChunk:
    """A chunk of a document"""

    id: str
    document_id: str
    content: str
    chunk_index: int
    start_pos: int
    end_pos: int
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Document:
    """A document in the knowledge base"""

    id: str
    kb_id: str
    title: str
    content: str
    source_uri: Optional[str]
    source_type: str  # upload, url, file
    mime_type: Optional[str]
    file_size: Optional[int]
    chunks: List[DocumentChunk]
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    error: Optional[str] = None


class KnowledgeBase:
    """A knowledge base containing documents"""

    def __init__(
        self,
        id: str,
        name: str,
        description: Optional[str],
        user_id: int,
        embedding_model: str = "bge-large-zh",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        retrieval_top_k: int = 5,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.user_id = user_id
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.retrieval_top_k = retrieval_top_k
        self.documents: Dict[str, Document] = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.metadata: Dict[str, Any] = {}

    def add_document(self, document: Document) -> None:
        """Add a document to the knowledge base"""
        self.documents[document.id] = document
        self.updated_at = datetime.utcnow()

    def remove_document(self, document_id: str) -> bool:
        """Remove a document from the knowledge base"""
        if document_id in self.documents:
            del self.documents[document_id]
            self.updated_at = datetime.utcnow()
            return True
        return False

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        return self.documents.get(document_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "retrieval_top_k": self.retrieval_top_k,
            "document_count": len(self.documents),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TextChunker:
    """Splits documents into chunks for embedding and retrieval"""

    def __init__(self):
        pass

    def chunk(
        self,
        text: str,
        strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> List[DocumentChunk]:
        """
        Split text into chunks.

        Args:
            text: Text to chunk
            strategy: Chunking strategy
            chunk_size: Size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of document chunks
        """
        if strategy == ChunkStrategy.FIXED_SIZE:
            return self._fixed_size_chunk(text, chunk_size, overlap)
        elif strategy == ChunkStrategy.PARAGRAPH:
            return self._paragraph_chunk(text, chunk_size)
        elif strategy == ChunkStrategy.SENTENCE:
            return self._sentence_chunk(text)
        else:
            return self._fixed_size_chunk(text, chunk_size, overlap)

    def _fixed_size_chunk(
        self, text: str, chunk_size: int, overlap: int
    ) -> List[DocumentChunk]:
        """Fixed size chunking with overlap"""
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            chunks.append(
                DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id="",
                    content=chunk_text,
                    chunk_index=index,
                    start_pos=start,
                    end_pos=end,
                )
            )

            start = end - overlap
            index += 1

        return chunks

    def _paragraph_chunk(
        self, text: str, max_chunk_size: int
    ) -> List[DocumentChunk]:
        """Paragraph-based chunking"""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        start_pos = 0
        index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
                chunks.append(
                    DocumentChunk(
                        id=str(uuid.uuid4()),
                        document_id="",
                        content=current_chunk.strip(),
                        chunk_index=index,
                        start_pos=start_pos,
                        end_pos=start_pos + len(current_chunk),
                    )
                )
                start_pos += len(current_chunk)
                current_chunk = para
                index += 1
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(
                DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id="",
                    content=current_chunk.strip(),
                    chunk_index=index,
                    start_pos=start_pos,
                    end_pos=len(text),
                )
            )

        return chunks

    def _sentence_chunk(self, text: str) -> List[DocumentChunk]:
        """Sentence-based chunking"""
        # Simple sentence splitting (in production, use NLP library)
        sentences = text.replace(". ", ". "★").replace("!", "!★").replace("?", "?★")
        sentences = sentences.split("★")
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        start = 0

        for i, sentence in enumerate(sentences):
            end = start + len(sentence)
            chunks.append(
                DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id="",
                    content=sentence,
                    chunk_index=i,
                    start_pos=start,
                    end_pos=end,
                )
            )
            start = end + 1

        return chunks


class EmbeddingService:
    """Service for generating embeddings"""

    def __init__(self, default_model: str = "bge-large-zh"):
        self.default_model = default_model
        self.embedding_dim = 1024  # BGE-large dimension

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Simulate embedding generation
        # In production, call actual embedding service
        await asyncio.sleep(0.1)

        embeddings = []
        for text in texts:
            # Generate pseudo-random embedding based on text hash
            hash_val = hashlib.md5(text.encode()).hexdigest()
            vector = [float(int(hash_val[i:i+2], 16)) / 255.0 for i in range(0, min(len(hash_val), self.embedding_dim * 2), 2)]
            # Pad to full dimension
            vector.extend([0.0] * (self.embedding_dim - len(vector)))
            embeddings.append(vector)

        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query"""
        embeddings = await self.embed([query])
        return embeddings[0]


class VectorStore:
    """Simple in-memory vector store (in production, use Milvus/Qdrant)"""

    def __init__(self):
        self.chunks: Dict[str, DocumentChunk] = {}
        self.chunk_embeddings: Dict[str, List[float]] = {}

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        """Add chunks with embeddings to the store"""
        for chunk, embedding in zip(chunks, embeddings):
            self.chunks[chunk.id] = chunk
            self.chunk_embeddings[chunk.id] = embedding

    def remove_document_chunks(self, document_id: str) -> int:
        """Remove all chunks for a document"""
        to_remove = [
            chunk_id for chunk_id, chunk in self.chunks.items()
            if chunk.document_id == document_id
        ]
        for chunk_id in to_remove:
            del self.chunks[chunk_id]
            del self.chunk_embeddings[chunk_id]
        return len(to_remove)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> List[tuple[DocumentChunk, float]]:
        """
        Search for similar chunks using cosine similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            document_id: Optional document ID to filter by

        Returns:
            List of (chunk, score) tuples
        """
        results = []

        for chunk_id, chunk in self.chunks.items():
            if document_id and chunk.document_id != document_id:
                continue

            chunk_embedding = self.chunk_embeddings.get(chunk_id)
            if not chunk_embedding:
                continue

            # Cosine similarity
            score = self._cosine_similarity(query_embedding, chunk_embedding)
            results.append((chunk, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(y * y for y in b) ** 0.5
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        return dot_product / (magnitude_a * magnitude_b)


class RAGService:
    """
    Retrieval-Augmented Generation service.
    Combines vector search with LLM generation.
    """

    def __init__(self):
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self.chunker = TextChunker()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

    def create_knowledge_base(
        self,
        name: str,
        description: Optional[str],
        user_id: int,
        **config,
    ) -> KnowledgeBase:
        """Create a new knowledge base"""
        kb_id = str(uuid.uuid4())
        kb = KnowledgeBase(
            id=kb_id,
            name=name,
            description=description,
            user_id=user_id,
            **config,
        )
        self.knowledge_bases[kb_id] = kb
        return kb

    def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Get a knowledge base by ID"""
        return self.knowledge_bases.get(kb_id)

    def list_knowledge_bases(self, user_id: int) -> List[KnowledgeBase]:
        """List knowledge bases for a user"""
        return [kb for kb in self.knowledge_bases.values() if kb.user_id == user_id]

    def delete_knowledge_base(self, kb_id: str, user_id: int) -> bool:
        """Delete a knowledge base"""
        kb = self.knowledge_bases.get(kb_id)
        if not kb or kb.user_id != user_id:
            return False
        del self.knowledge_bases[kb_id]
        return True

    async def add_document(
        self,
        kb_id: str,
        title: str,
        content: str,
        source_uri: Optional[str],
        source_type: str,
        mime_type: Optional[str] = None,
        file_size: Optional[int] = None,
        chunk_strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE,
    ) -> Document:
        """
        Add a document to a knowledge base.

        Args:
            kb_id: Knowledge base ID
            title: Document title
            content: Document content
            source_uri: Source URI or path
            source_type: Type of source (upload, url, file)
            mime_type: MIME type
            file_size: File size in bytes
            chunk_strategy: Strategy for chunking

        Returns:
            Created document
        """
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            raise ValueError(f"Knowledge base {kb_id} not found")

        doc_id = str(uuid.uuid4())

        # Chunk the document
        chunks = self.chunker.chunk(
            content,
            strategy=chunk_strategy,
            chunk_size=kb.chunk_size,
            overlap=kb.chunk_overlap,
        )

        # Set document ID for chunks
        for chunk in chunks:
            chunk.document_id = doc_id

        # Generate embeddings
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_service.embed(chunk_texts)

        # Add to vector store
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        self.vector_store.add_chunks(chunks, embeddings)

        # Create document
        document = Document(
            id=doc_id,
            kb_id=kb_id,
            title=title,
            content=content,
            source_uri=source_uri,
            source_type=source_type,
            mime_type=mime_type,
            file_size=file_size,
            chunks=chunks,
            status=DocumentStatus.INDEXED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={},
        )

        kb.add_document(document)
        return document

    async def search(
        self,
        kb_id: str,
        query: str,
        top_k: Optional[int] = None,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search a knowledge base.

        Args:
            kb_id: Knowledge base ID
            query: Search query
            top_k: Number of results
            document_id: Optional document ID to filter by

        Returns:
            List of search results with chunks and scores
        """
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            raise ValueError(f"Knowledge base {kb_id} not found")

        top_k = top_k or kb.retrieval_top_k

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_query(query)

        # Search vector store
        results = self.vector_store.search(query_embedding, top_k, document_id)

        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "score": score,
                "metadata": chunk.metadata,
            }
            for chunk, score in results
        ]

    async def answer(
        self,
        kb_id: str,
        question: str,
        llm_service: Any,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG.

        Args:
            kb_id: Knowledge base ID
            question: User question
            llm_service: LLM chat service for generation
            session_id: Optional chat session ID

        Returns:
            Answer with sources
        """
        # Search for relevant chunks
        search_results = await self.search(kb_id, question)

        if not search_results:
            return {
                "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                "sources": [],
            }

        # Build context from chunks
        context_parts = []
        sources = []

        for i, result in enumerate(search_results[:3]):  # Use top 3 chunks
            context_parts.append(f"[Source {i+1}]: {result['content']}")
            sources.append({
                "chunk_id": result['chunk_id'],
                "document_id": result['document_id'],
                "score": result['score'],
            })

        context = "\n\n".join(context_parts)

        # Build RAG prompt
        rag_prompt = f"""You are a helpful assistant that answers questions based on the provided context.

Context:
{context}

Question: {question}

Answer the question using only the information from the context above. If the context doesn't contain enough information to answer the question, say "I don't have enough information to answer this question."

Answer:"""

        # Generate answer using LLM
        # In production, call actual LLM service
        await asyncio.sleep(0.5)
        answer = f"Based on the knowledge base, here's what I found:\n\n{search_results[0]['content'][:200]}..."

        return {
            "answer": answer,
            "sources": sources,
            "context_used": len(context_parts),
        }

    def delete_document(self, kb_id: str, document_id: str, user_id: int) -> bool:
        """Delete a document from a knowledge base"""
        kb = self.get_knowledge_base(kb_id)
        if not kb or kb.user_id != user_id:
            return False

        # Remove from KB
        if not kb.remove_document(document_id):
            return False

        # Remove from vector store
        self.vector_store.remove_document_chunks(document_id)

        return True


# Global service instance
rag_service = RAGService()
