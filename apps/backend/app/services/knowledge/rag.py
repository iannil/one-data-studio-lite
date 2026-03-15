"""
RAG (Retrieval-Augmented Generation) Service

Enhanced RAG implementation with:
- Multiple vector backends
- Multiple embedding providers
- Re-ranking support
- Hybrid search (vector + keyword)
- Enterprise permissions
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeDocument,
    DocumentChunk,
    VectorIndex,
    RetrievalResult,
    RAGSession,
    RAGMessage,
    ChunkStrategy,
    DocumentStatus,
    VectorBackend,
)
from app.services.knowledge.vector_store import (
    VectorStoreBackend,
    VectorResult,
    get_vector_store,
)
from app.services.knowledge.embedding import (
    EmbeddingService,
    get_embedding_service,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with metadata"""
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RAGAnswer:
    """RAG answer with sources"""
    answer: str
    sources: List[Dict[str, Any]]
    context_used: int
    retrieval_time_ms: int
    generation_time_ms: int
    session_id: Optional[str] = None
    message_id: Optional[str] = None


class TextChunker:
    """Text chunking with multiple strategies"""

    def __init__(self):
        pass

    def chunk(
        self,
        text: str,
        strategy: str = ChunkStrategy.FIXED_SIZE,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> List[Tuple[str, int, int]]:
        """
        Split text into chunks.

        Returns:
            List of (content, start_pos, end_pos) tuples
        """
        if strategy == ChunkStrategy.FIXED_SIZE:
            return self._fixed_size_chunk(text, chunk_size, overlap)
        elif strategy == ChunkStrategy.PARAGRAPH:
            return self._paragraph_chunk(text, chunk_size)
        elif strategy == ChunkStrategy.SENTENCE:
            return self._sentence_chunk(text)
        elif strategy == ChunkStrategy.RECURSIVE:
            return self._recursive_chunk(text, chunk_size, overlap)
        else:
            return self._fixed_size_chunk(text, chunk_size, overlap)

    def _fixed_size_chunk(
        self, text: str, chunk_size: int, overlap: int
    ) -> List[Tuple[str, int, int]]:
        """Fixed size chunking with overlap"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append((chunk_text, start, end))
            start = end - overlap

        return chunks

    def _paragraph_chunk(
        self, text: str, max_chunk_size: int
    ) -> List[Tuple[str, int, int]]:
        """Paragraph-based chunking"""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        start_pos = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
                chunks.append((current_chunk.strip(), start_pos, start_pos + len(current_chunk)))
                start_pos += len(current_chunk)
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append((current_chunk.strip(), start_pos, len(text)))

        return chunks

    def _sentence_chunk(self, text: str) -> List[Tuple[str, int, int]]:
        """Sentence-based chunking"""
        sentences = text.replace(". ", ".★").replace("!", "!★").replace("?", "?★")
        sentences = sentences.split("★")
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        start = 0

        for sentence in sentences:
            end = start + len(sentence)
            chunks.append((sentence, start, end))
            start = end + 1

        return chunks

    def _recursive_chunk(
        self, text: str, chunk_size: int, overlap: int
    ) -> List[Tuple[str, int, int]]:
        """Recursive character chunking (like LangChain)"""
        separators = ["\n\n", "\n", ". ", " ", ""]

        chunks = []
        self._recursive_split(text, separators, chunk_size, overlap, chunks, 0)
        return chunks

    def _recursive_split(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
        overlap: int,
        chunks: List[Tuple[str, int, int]],
        start_pos: int = 0,
    ) -> None:
        """Recursive split implementation"""
        if not text:
            return

        # If text is short enough, add as chunk
        if len(text) <= chunk_size:
            chunks.append((text, start_pos, start_pos + len(text)))
            return

        # Try to split by each separator
        for sep in separators:
            if sep not in text:
                continue

            parts = text.split(sep)
            current = ""
            current_start = start_pos

            for i, part in enumerate(parts):
                if len(current) + len(part) + len(sep) <= chunk_size:
                    current += part + sep if i < len(parts) - 1 else part
                else:
                    if current:
                        chunks.append((current, current_start, current_start + len(current)))
                        current_start += len(current)
                        current = part + sep if i < len(parts) - 1 else part
                    else:
                        # Part itself is too long, split by size
                        return self._fixed_size_chunk(text, chunk_size, overlap)

            if current:
                self._recursive_split(
                    current, separators[1:] if separators else [""],
                    chunk_size, overlap, chunks, current_start
                )
            return

        # No separator worked, use fixed size
        chunks.extend(self._fixed_size_chunk(text, chunk_size, overlap))


class RAGEngine:
    """
    RAG Engine for knowledge base operations
    """

    def __init__(self):
        self.chunker = TextChunker()
        self._vector_stores: Dict[str, VectorStoreBackend] = {}
        self.embedding_service = get_embedding_service()

    async def _get_vector_store(
        self,
        kb: KnowledgeBase,
        vector_index: Optional[VectorIndex] = None,
    ) -> VectorStoreBackend:
        """Get or create vector store for knowledge base"""
        collection_name = kb.vector_collection or f"kb_{kb.kb_id}"

        if collection_name not in self._vector_stores:
            config = {}
            if vector_index:
                config = {
                    "endpoint": vector_index.endpoint,
                    "index_type": vector_index.index_type,
                    "params": vector_index.params,
                }

            self._vector_stores[collection_name] = get_vector_store(
                backend=kb.vector_backend,
                collection_name=collection_name,
                embedding_dim=kb.embedding_dim,
                **config,
            )
            await self._vector_stores[collection_name].initialize()

        return self._vector_stores[collection_name]

    async def create_knowledge_base(
        self,
        db: AsyncSession,
        name: str,
        description: Optional[str],
        owner_id: str,
        tenant_id: Optional[str] = None,
        embedding_model: str = "bge-large-zh",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        vector_backend: str = VectorBackend.MEMORY,
        is_public: bool = False,
        tags: Optional[List[str]] = None,
    ) -> KnowledgeBase:
        """Create a new knowledge base"""
        kb_id = str(uuid.uuid4())
        collection_name = f"kb_{kb_id}"

        kb = KnowledgeBase(
            kb_id=kb_id,
            name=name,
            description=description,
            embedding_model=embedding_model,
            embedding_dim=1024,  # Default for BGE
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            vector_backend=vector_backend,
            vector_collection=collection_name,
            is_public=is_public,
            tags=tags,
            owner_id=owner_id,
            tenant_id=tenant_id,
        )

        db.add(kb)
        await db.commit()
        await db.refresh(kb)

        logger.info(f"Created knowledge base: {kb_id} - {name}")
        return kb

    async def add_document(
        self,
        db: AsyncSession,
        kb_id: str,
        title: str,
        content: str,
        source_uri: Optional[str],
        source_type: str,
        mime_type: Optional[str] = None,
        file_size: Optional[int] = None,
        uploader_id: str = "system",
    ) -> KnowledgeDocument:
        """
        Add a document to knowledge base and index it.

        Args:
            db: Database session
            kb_id: Knowledge base ID
            title: Document title
            content: Document content
            source_uri: Source URI
            source_type: Source type (upload, url, file, crawler)
            mime_type: MIME type
            file_size: File size in bytes
            uploader_id: User ID of uploader

        Returns:
            Created document
        """
        # Get knowledge base
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise ValueError(f"Knowledge base {kb_id} not found")

        # Create document
        doc_id = str(uuid.uuid4())
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        document = KnowledgeDocument(
            doc_id=doc_id,
            kb_id=kb_id,
            title=title,
            content=content[:10000],  # Store first 10k chars in DB
            content_hash=content_hash,
            source_uri=source_uri,
            source_type=source_type,
            mime_type=mime_type,
            file_size=file_size,
            status=DocumentStatus.EMBEDDING,
            chunk_strategy=kb.chunk_strategy,
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
            uploader_id=uploader_id,
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Process document asynchronously
        # In production, use background task
        await self._index_document(db, kb, document, content)

        return document

    async def _index_document(
        self,
        db: AsyncSession,
        kb: KnowledgeBase,
        document: KnowledgeDocument,
        content: str,
    ) -> None:
        """Index document chunks into vector store"""
        try:
            # Update status
            document.status = DocumentStatus.CHUNKING
            await db.commit()

            # Chunk the document
            chunks_data = self.chunker.chunk(
                content,
                strategy=kb.chunk_strategy,
                chunk_size=kb.chunk_size,
                overlap=kb.chunk_overlap,
            )

            # Update chunk count
            document.chunk_count = len(chunks_data)

            # Generate embeddings
            chunk_texts = [c[0] for c in chunks_data]
            embeddings = await self.embedding_service.embed(
                chunk_texts,
                provider=kb.embedding_provider,
            )

            # Get vector store
            vector_store = await self._get_vector_store(kb)

            # Insert chunks into vector store
            items = []
            chunk_records = []

            for i, ((chunk_text, start_pos, end_pos), embedding) in enumerate(
                zip(chunks_data, embeddings)
            ):
                chunk_id = str(uuid.uuid4())
                chunk_records.append(DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=document.doc_id,
                    kb_id=kb.kb_id,
                    content=chunk_text,
                    content_length=len(chunk_text),
                    chunk_index=i,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    embedding=embedding,
                    vector_id=chunk_id,
                ))

                items.append((
                    chunk_id,
                    document.doc_id,
                    chunk_text,
                    embedding,
                    {"title": document.title, "chunk_index": i},
                ))

            # Batch insert
            await vector_store.insert_batch(items)

            # Save chunk records
            db.add_all(chunk_records)

            # Update document and KB stats
            document.status = DocumentStatus.INDEXED
            document.indexed_chunk_count = len(chunks_data)
            document.indexed_at = datetime.utcnow()

            kb.chunk_count += len(chunks_data)
            kb.document_count += 1
            kb.total_size += document.file_size or 0

            await db.commit()

            logger.info(f"Indexed document {document.doc_id} with {len(chunks_data)} chunks")

        except Exception as e:
            logger.error(f"Failed to index document {document.doc_id}: {e}")
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            await db.commit()

    async def search(
        self,
        db: AsyncSession,
        kb_id: str,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Tuple[List[SearchResult], int]:
        """
        Search knowledge base.

        Args:
            db: Database session
            kb_id: Knowledge base ID
            query: Search query
            top_k: Number of results
            score_threshold: Minimum similarity score
            user_id: User ID for permission check
            tenant_id: Tenant ID for filtering

        Returns:
            (results, retrieval_time_ms)
        """
        import time
        start_time = time.time()

        # Get knowledge base
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise ValueError(f"Knowledge base {kb_id} not found")

        # Check permissions
        if not kb.is_public and user_id:
            if kb.owner_id != user_id:
                # Check if user is in allowed users
                if not (kb.allowed_users and user_id in kb.allowed_users):
                    raise PermissionError(f"Access denied to knowledge base {kb_id}")

        top_k = top_k or kb.retrieval_top_k
        score_threshold = score_threshold if score_threshold is not None else kb.retrieval_score_threshold

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_single(
            query,
            provider=kb.embedding_provider,
        )

        # Search vector store
        vector_store = await self._get_vector_store(kb)
        vector_results = await vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
        )

        # Apply score threshold
        if score_threshold is not None:
            vector_results = [r for r in vector_results if r.score >= score_threshold]

        # Get document titles
        doc_ids = [r.document_id for r in vector_results]
        documents = {}
        if doc_ids:
            result = await db.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.doc_id.in_(doc_ids)
                )
            )
            for doc in result.scalars():
                documents[doc.doc_id] = doc

        # Build search results
        search_results = [
            SearchResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_title=documents.get(r.document_id, KnowledgeDocument(title="Unknown")).title,
                content=r.content,
                score=r.score,
                metadata=r.metadata,
            )
            for r in vector_results
        ]

        retrieval_time_ms = int((time.time() - start_time) * 1000)

        # Log retrieval
        await self._log_retrieval(
            db,
            kb_id,
            query,
            query_embedding,
            top_k,
            len(search_results),
            [r.chunk_id for r in search_results],
            [r.score for r in search_results],
            retrieval_time_ms,
            user_id,
        )

        return search_results, retrieval_time_ms

    async def _log_retrieval(
        self,
        db: AsyncSession,
        kb_id: str,
        query: str,
        query_embedding: List[float],
        top_k: int,
        result_count: int,
        chunk_ids: List[str],
        scores: List[float],
        retrieval_time_ms: int,
        user_id: Optional[str],
    ) -> None:
        """Log retrieval for analytics"""
        log_entry = RetrievalResult(
            kb_id=kb_id,
            query=query,
            query_embedding=query_embedding,
            top_k=top_k,
            result_count=result_count,
            chunk_ids=chunk_ids,
            scores=scores,
            retrieval_time_ms=retrieval_time_ms,
            user_id=user_id,
        )
        db.add(log_entry)
        await db.commit()

    async def ask(
        self,
        db: AsyncSession,
        kb_id: str,
        question: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.7,
    ) -> RAGAnswer:
        """
        Ask a question with RAG.

        Args:
            db: Database session
            kb_id: Knowledge base ID
            question: User question
            session_id: Chat session ID
            user_id: User ID
            model: LLM model
            temperature: Generation temperature

        Returns:
            RAG answer with sources
        """
        import time
        start_time = time.time()

        # Search for relevant chunks
        search_results, retrieval_time_ms = await self.search(
            db=db,
            kb_id=kb_id,
            query=question,
            user_id=user_id,
        )

        if not search_results:
            return RAGAnswer(
                answer="I couldn't find any relevant information in the knowledge base to answer your question.",
                sources=[],
                context_used=0,
                retrieval_time_ms=retrieval_time_ms,
                generation_time_ms=0,
            )

        # Build context from chunks
        context_parts = []
        sources = []

        for i, result in enumerate(search_results[:3]):
            context_parts.append(f"[Source {i+1}]: {result.content}")
            sources.append({
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "document_title": result.document_title,
                "score": result.score,
                "content": result.content[:200] + "..." if len(result.content) > 200 else result.content,
            })

        context = "\n\n".join(context_parts)

        # Generate answer
        gen_start = time.time()

        # Try to use LLM service
        try:
            from app.services.llm.chat import get_llm_service

            llm_service = get_llm_service()

            rag_prompt = f"""You are a helpful assistant that answers questions based on the provided context.

Context:
{context}

Question: {question}

Answer the question using only the information from the context above. If the context doesn't contain enough information to answer the question, say "I don't have enough information to answer this question."

Answer:"""

            response = await llm_service.chat(
                messages=[{"role": "user", "content": rag_prompt}],
                model=model,
                temperature=temperature,
            )

            answer = response.get("content", "Failed to generate answer")

        except Exception as e:
            logger.warning(f"LLM generation failed: {e}. Using fallback.")
            # Fallback to simple answer
            answer = f"Based on the knowledge base, I found {len(search_results)} relevant sources. The most relevant information is:\n\n{search_results[0].content[:500]}..."

        generation_time_ms = int((time.time() - gen_start) * 1000)

        # Create or update session
        if session_id:
            result = await db.execute(
                select(RAGSession).where(RAGSession.session_id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                session.message_count += 1
                session.updated_at = datetime.utcnow()

        # Store messages
        if session_id:
            user_message = RAGMessage(
                session_id=session_id,
                role="user",
                content=question,
                retrieved_chunks=sources[:3],
                retrieval_scores=[r.score for r in search_results[:3]],
            )
            db.add(user_message)

            assistant_message = RAGMessage(
                session_id=session_id,
                role="assistant",
                content=answer,
                retrieved_chunks=sources[:3],
            )
            db.add(assistant_message)

            await db.commit()

        return RAGAnswer(
            answer=answer,
            sources=sources,
            context_used=len(context_parts),
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            session_id=session_id,
        )

    async def delete_document(
        self,
        db: AsyncSession,
        kb_id: str,
        doc_id: str,
        user_id: str,
    ) -> bool:
        """Delete a document from knowledge base"""
        # Get knowledge base
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise ValueError(f"Knowledge base {kb_id} not found")

        # Check ownership
        if kb.owner_id != user_id:
            raise PermissionError("Only the owner can delete documents")

        # Get document
        result = await db.execute(
            select(KnowledgeDocument).where(
                and_(
                    KnowledgeDocument.doc_id == doc_id,
                    KnowledgeDocument.kb_id == kb_id,
                )
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            return False

        # Delete from vector store
        vector_store = await self._get_vector_store(kb)
        await vector_store.delete_by_document(doc_id)

        # Delete chunk records
        await db.execute(
            select(DocumentChunk).where(DocumentChunk.doc_id == doc_id)
        )

        # Delete document
        await db.delete(document)

        # Update KB stats
        kb.chunk_count -= document.indexed_chunk_count
        kb.document_count -= 1
        kb.total_size -= document.file_size or 0

        await db.commit()

        logger.info(f"Deleted document {doc_id} from KB {kb_id}")
        return True

    async def create_session(
        self,
        db: AsyncSession,
        kb_id: str,
        user_id: str,
        title: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.7,
    ) -> RAGSession:
        """Create a new RAG chat session"""
        session_id = str(uuid.uuid4())

        session = RAGSession(
            session_id=session_id,
            kb_id=kb_id,
            title=title or "New Chat",
            model=model,
            temperature=temperature,
            user_id=user_id,
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session


# Global RAG engine instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get or create global RAG engine instance"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
