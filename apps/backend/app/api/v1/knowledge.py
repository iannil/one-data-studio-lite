"""
Knowledge Base API Endpoints

Provides REST API for knowledge base operations:
- Knowledge base CRUD
- Document upload and management
- Vector search
- RAG chat
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeDocument,
    DocumentChunk,
    VectorIndex,
    RAGSession,
    ChunkStrategy,
    DocumentStatus,
    VectorBackend,
)
from app.services.knowledge.rag import (
    RAGEngine,
    get_rag_engine,
    SearchResult,
    RAGAnswer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CreateKnowledgeBaseRequest(BaseModel):
    """Request to create a knowledge base"""
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    embedding_model: str = "bge-large-zh"
    chunk_size: int = Field(500, ge=100, le=2000)
    chunk_overlap: int = Field(50, ge=0, le=500)
    chunk_strategy: str = ChunkStrategy.FIXED_SIZE
    vector_backend: str = VectorBackend.MEMORY
    retrieval_top_k: int = Field(5, ge=1, le=100)
    is_public: bool = False
    tags: Optional[List[str]] = None


class UpdateKnowledgeBaseRequest(BaseModel):
    """Request to update a knowledge base"""
    name: Optional[str] = None
    description: Optional[str] = None
    retrieval_top_k: Optional[int] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None


class UploadDocumentRequest(BaseModel):
    """Request to upload a document"""
    title: str = Field(..., min_length=1, max_length=512)
    source_uri: Optional[str] = None
    source_type: str = "upload"
    chunk_strategy: Optional[str] = None


class SearchRequest(BaseModel):
    """Search request"""
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = None
    score_threshold: Optional[float] = None


class ChatRequest(BaseModel):
    """RAG chat request"""
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    model: str = "gpt-4"
    temperature: float = Field(0.7, ge=0, le=1)


class CreateSessionRequest(BaseModel):
    """Create chat session request"""
    kb_id: str
    title: Optional[str] = None
    model: str = "gpt-4"
    temperature: float = Field(0.7, ge=0, le=1)


# ============================================================================
# Knowledge Base Endpoints
# ============================================================================


@router.post("/bases", response_model=Dict[str, Any])
async def create_knowledge_base(
    request: CreateKnowledgeBaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new knowledge base"""
    try:
        rag_engine = get_rag_engine()

        kb = await rag_engine.create_knowledge_base(
            db=db,
            name=request.name,
            description=request.description,
            owner_id=str(current_user.id),
            tenant_id=current_user.tenant_id,
            embedding_model=request.embedding_model,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            vector_backend=request.vector_backend,
            is_public=request.is_public,
            tags=request.tags,
        )

        return {
            "kb_id": kb.kb_id,
            "name": kb.name,
            "description": kb.description,
            "embedding_model": kb.embedding_model,
            "chunk_size": kb.chunk_size,
            "vector_backend": kb.vector_backend,
            "is_public": kb.is_public,
            "tags": kb.tags,
            "document_count": kb.document_count,
            "chunk_count": kb.chunk_count,
            "created_at": kb.created_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to create knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/bases", response_model=List[Dict[str, Any]])
async def list_knowledge_bases(
    is_public: Optional[bool] = None,
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List knowledge bases"""
    try:
        from sqlalchemy import select

        query = select(KnowledgeBase)

        # Filter by user's own KBs or public ones
        query = query.where(
            (KnowledgeBase.owner_id == str(current_user.id)) | (KnowledgeBase.is_public == True)
        )

        if is_public is not None:
            query = query.where(KnowledgeBase.is_public == is_public)

        if tag:
            query = query.where(KnowledgeBase.tags.contains([tag]))

        query = query.order_by(KnowledgeBase.updated_at.desc())

        result = await db.execute(query)
        kbs = result.scalars().all()

        return [
            {
                "kb_id": kb.kb_id,
                "name": kb.name,
                "description": kb.description,
                "embedding_model": kb.embedding_model,
                "document_count": kb.document_count,
                "chunk_count": kb.chunk_count,
                "is_public": kb.is_public,
                "tags": kb.tags,
                "owner_id": kb.owner_id,
                "created_at": kb.created_at.isoformat(),
                "updated_at": kb.updated_at.isoformat(),
            }
            for kb in kbs
        ]

    except Exception as e:
        logger.error(f"Failed to list knowledge bases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/bases/{kb_id}", response_model=Dict[str, Any])
async def get_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge base details"""
    try:
        from sqlalchemy import select

        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base {kb_id} not found",
            )

        # Check permission
        if not kb.is_public and kb.owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return {
            "kb_id": kb.kb_id,
            "name": kb.name,
            "description": kb.description,
            "embedding_model": kb.embedding_model,
            "embedding_provider": kb.embedding_provider,
            "embedding_dim": kb.embedding_dim,
            "chunk_strategy": kb.chunk_strategy,
            "chunk_size": kb.chunk_size,
            "chunk_overlap": kb.chunk_overlap,
            "retrieval_top_k": kb.retrieval_top_k,
            "retrieval_score_threshold": kb.retrieval_score_threshold,
            "vector_backend": kb.vector_backend,
            "vector_collection": kb.vector_collection,
            "is_public": kb.is_public,
            "allowed_roles": kb.allowed_roles,
            "allowed_users": kb.allowed_users,
            "tags": kb.tags,
            "document_count": kb.document_count,
            "chunk_count": kb.chunk_count,
            "total_size": kb.total_size,
            "owner_id": kb.owner_id,
            "tenant_id": kb.tenant_id,
            "metadata": kb.metadata,
            "created_at": kb.created_at.isoformat(),
            "updated_at": kb.updated_at.isoformat(),
            "last_accessed_at": kb.last_accessed_at.isoformat() if kb.last_accessed_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/bases/{kb_id}", response_model=Dict[str, Any])
async def update_knowledge_base(
    kb_id: str,
    request: UpdateKnowledgeBaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update knowledge base"""
    try:
        from sqlalchemy import select

        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base {kb_id} not found",
            )

        # Check ownership
        if kb.owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can update knowledge base",
            )

        # Update fields
        if request.name is not None:
            kb.name = request.name
        if request.description is not None:
            kb.description = request.description
        if request.retrieval_top_k is not None:
            kb.retrieval_top_k = request.retrieval_top_k
        if request.is_public is not None:
            kb.is_public = request.is_public
        if request.tags is not None:
            kb.tags = request.tags

        kb.updated_at = datetime.utcnow()

        await db.commit()

        return {"message": "Knowledge base updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/bases/{kb_id}", response_model=Dict[str, Any])
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete knowledge base"""
    try:
        from sqlalchemy import select, delete

        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base {kb_id} not found",
            )

        # Check ownership
        if kb.owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can delete knowledge base",
            )

        # Delete related records
        await db.execute(delete(RAGSession).where(RAGSession.kb_id == kb_id))
        await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id))
        await db.execute(delete(DocumentChunk).where(DocumentChunk.kb_id == kb_id))
        await db.execute(delete(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id))

        await db.commit()

        return {"message": "Knowledge base deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Document Endpoints
# ============================================================================


@router.post("/bases/{kb_id}/documents", response_model=Dict[str, Any])
async def upload_document(
    kb_id: str,
    title: str = Form(...),
    content: str = Form(...),
    source_uri: Optional[str] = Form(None),
    source_type: str = Form("upload"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document to knowledge base.

    For large files, use file upload endpoint instead.
    """
    try:
        rag_engine = get_rag_engine()

        document = await rag_engine.add_document(
            db=db,
            kb_id=kb_id,
            title=title,
            content=content,
            source_uri=source_uri,
            source_type=source_type,
            uploader_id=str(current_user.id),
        )

        return {
            "doc_id": document.doc_id,
            "kb_id": document.kb_id,
            "title": document.title,
            "status": document.status,
            "chunk_count": document.chunk_count,
            "indexed_chunk_count": document.indexed_chunk_count,
            "created_at": document.created_at.isoformat(),
            "message": "Document uploaded successfully",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/bases/{kb_id}/documents", response_model=List[Dict[str, Any]])
async def list_documents(
    kb_id: str,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents in a knowledge base"""
    try:
        from sqlalchemy import select

        # Check KB access
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base {kb_id} not found",
            )

        if not kb.is_public and kb.owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Query documents
        query = select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id)

        if status:
            query = query.where(KnowledgeDocument.status == status)

        query = query.order_by(KnowledgeDocument.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        documents = result.scalars().all()

        return [
            {
                "doc_id": doc.doc_id,
                "kb_id": doc.kb_id,
                "title": doc.title,
                "source_uri": doc.source_uri,
                "source_type": doc.source_type,
                "mime_type": doc.mime_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "chunk_count": doc.chunk_count,
                "indexed_chunk_count": doc.indexed_chunk_count,
                "created_at": doc.created_at.isoformat(),
                "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
            }
            for doc in documents
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/bases/{kb_id}/documents/{doc_id}", response_model=Dict[str, Any])
async def get_document(
    kb_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document details"""
    try:
        from sqlalchemy import select

        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.doc_id == doc_id,
                KnowledgeDocument.kb_id == kb_id,
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        return {
            "doc_id": doc.doc_id,
            "kb_id": doc.kb_id,
            "title": doc.title,
            "content": doc.content,
            "source_uri": doc.source_uri,
            "source_type": doc.source_type,
            "mime_type": doc.mime_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "indexed_chunk_count": doc.indexed_chunk_count,
            "chunk_strategy": doc.chunk_strategy,
            "chunk_size": doc.chunk_size,
            "chunk_overlap": doc.chunk_overlap,
            "error_message": doc.error_message,
            "created_at": doc.created_at.isoformat(),
            "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/bases/{kb_id}/documents/{doc_id}", response_model=Dict[str, Any])
async def delete_document(
    kb_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document"""
    try:
        rag_engine = get_rag_engine()

        success = await rag_engine.delete_document(
            db=db,
            kb_id=kb_id,
            doc_id=doc_id,
            user_id=str(current_user.id),
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Search Endpoints
# ============================================================================


@router.post("/bases/{kb_id}/search", response_model=Dict[str, Any])
async def search_knowledge_base(
    kb_id: str,
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search knowledge base"""
    try:
        rag_engine = get_rag_engine()

        results, retrieval_time_ms = await rag_engine.search(
            db=db,
            kb_id=kb_id,
            query=request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            user_id=str(current_user.id),
        )

        return {
            "query": request.query,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "content": r.content,
                    "score": r.score,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "result_count": len(results),
            "retrieval_time_ms": retrieval_time_ms,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# RAG Chat Endpoints
# ============================================================================


@router.post("/bases/{kb_id}/chat", response_model=Dict[str, Any])
async def chat_with_knowledge_base(
    kb_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with knowledge base using RAG"""
    try:
        rag_engine = get_rag_engine()

        response: RAGAnswer = await rag_engine.ask(
            db=db,
            kb_id=kb_id,
            question=request.question,
            session_id=request.session_id,
            user_id=str(current_user.id),
            model=request.model,
            temperature=request.temperature,
        )

        return {
            "answer": response.answer,
            "sources": response.sources,
            "context_used": response.context_used,
            "retrieval_time_ms": response.retrieval_time_ms,
            "generation_time_ms": response.generation_time_ms,
            "session_id": response.session_id,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/sessions", response_model=Dict[str, Any])
async def create_chat_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new RAG chat session"""
    try:
        rag_engine = get_rag_engine()

        session = await rag_engine.create_session(
            db=db,
            kb_id=request.kb_id,
            user_id=str(current_user.id),
            title=request.title,
            model=request.model,
            temperature=request.temperature,
        )

        return {
            "session_id": session.session_id,
            "kb_id": session.kb_id,
            "title": session.title,
            "model": session.model,
            "temperature": session.temperature,
            "message_count": session.message_count,
            "created_at": session.created_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def list_chat_sessions(
    kb_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List chat sessions"""
    try:
        from sqlalchemy import select

        query = select(RAGSession).where(RAGSession.user_id == str(current_user.id))

        if kb_id:
            query = query.where(RAGSession.kb_id == kb_id)

        query = query.order_by(RAGSession.updated_at.desc()).limit(limit)

        result = await db.execute(query)
        sessions = result.scalars().all()

        return [
            {
                "session_id": s.session_id,
                "kb_id": s.kb_id,
                "title": s.title,
                "model": s.model,
                "message_count": s.message_count,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/sessions/{session_id}/messages", response_model=List[Dict[str, Any]])
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages in a chat session"""
    try:
        from sqlalchemy import select

        # Check session ownership
        result = await db.execute(
            select(RAGSession).where(
                RAGSession.session_id == session_id,
                RAGSession.user_id == str(current_user.id),
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Get messages
        result = await db.execute(
            select(RAGSession).where(RAGSession.session_id == session_id)
        )

        result = await db.execute(
            select(RAGMessage).where(
                RAGMessage.session_id == session_id
            ).order_by(RAGMessage.created_at)
        )
        messages = result.scalars().all()

        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "retrieved_chunks": msg.retrieved_chunks,
                "prompt_tokens": msg.prompt_tokens,
                "completion_tokens": msg.completion_tokens,
                "total_tokens": msg.total_tokens,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/sessions/{session_id}", response_model=Dict[str, Any])
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session"""
    try:
        from sqlalchemy import select, delete

        # Check ownership
        result = await db.execute(
            select(RAGSession).where(
                RAGSession.session_id == session_id,
                RAGSession.user_id == str(current_user.id),
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Delete messages and session
        await db.execute(delete(RAGMessage).where(RAGMessage.session_id == session_id))
        await db.execute(delete(RAGSession).where(RAGSession.session_id == session_id))

        await db.commit()

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Import Form for file upload
# from fastapi import Form  # Duplicate import
