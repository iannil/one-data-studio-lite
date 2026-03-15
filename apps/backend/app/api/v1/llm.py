"""
LLM API Endpoints

REST API for LLM chat, knowledge base, and inference management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.llm import (
    llm_chat_service,
    rag_service,
    ChatRole,
    MessageStatus,
    ChunkStrategy,
)

router = APIRouter(prefix="/llm", tags=["llm"])

# Request/Response Models


class CreateSessionRequest(BaseModel):
    """Request to create a chat session"""

    model: str = Field(..., description="Model to use for chat")
    system_prompt: Optional[str] = Field(
        None, description="System prompt for the session"
    )
    parameters: Optional[dict] = Field(
        None, description="Chat parameters (temperature, max_tokens, etc.)"
    )


class ChatRequest(BaseModel):
    """Request to send a chat message"""

    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    stream: bool = Field(False, description="Stream the response")
    parameters: Optional[dict] = Field(None, description="Override parameters")


class ChatResponse(BaseModel):
    """Chat message response"""

    id: str
    role: str
    content: str
    status: str
    created_at: str
    completed_at: Optional[str]
    token_count: int


class CreateKnowledgeBaseRequest(BaseModel):
    """Request to create a knowledge base"""

    name: str = Field(..., min_length=1, max_length=256, description="KB name")
    description: Optional[str] = Field(None, description="KB description")
    embedding_model: str = Field("bge-large-zh", description="Embedding model")
    chunk_size: int = Field(500, ge=100, le=2000, description="Chunk size")
    chunk_overlap: int = Field(50, ge=0, le=500, description="Chunk overlap")
    retrieval_top_k: int = Field(5, ge=1, le=20, description="Top K retrieval")


class AddDocumentRequest(BaseModel):
    """Request to add a document to knowledge base"""

    title: str = Field(..., min_length=1, max_length=512, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    source_uri: Optional[str] = Field(None, description="Source URI")
    source_type: str = Field("upload", description="Source type")
    mime_type: Optional[str] = Field(None, description="MIME type")
    chunk_strategy: str = Field("fixed_size", description="Chunking strategy")


class SearchRequest(BaseModel):
    """Request to search knowledge base"""

    query: str = Field(..., min_length=1, description="Search query")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of results")
    document_id: Optional[str] = Field(None, description="Filter by document")


class RAGQuestionRequest(BaseModel):
    """Request to ask a question with RAG"""

    question: str = Field(..., min_length=1, description="Question")
    session_id: Optional[str] = Field(None, description="Chat session ID")


# Chat Endpoints


@router.post("/chat/sessions")
async def create_chat_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a new chat session"""
    session = llm_chat_service.create_session(
        user_id=current_user.id,
        model=request.model,
        system_prompt=request.system_prompt,
        parameters=request.parameters,
    )
    return session.to_dict()


@router.get("/chat/sessions")
async def list_chat_sessions(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """List chat sessions for current user"""
    sessions = llm_chat_service.list_sessions(current_user.id, limit)
    return [s.to_dict() for s in sessions]


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get chat session details"""
    session = llm_chat_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return session.to_dict()


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a chat session"""
    success = llm_chat_service.delete_session(session_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return {"deleted": True}


@router.post("/chat/sessions/{session_id}/clear")
async def clear_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Clear message history for a session"""
    success = llm_chat_service.clear_history(session_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return {"cleared": True}


@router.post("/chat/sessions/{session_id}/message")
async def send_chat_message(
    session_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Send a message and get a response"""
    result = await llm_chat_service.chat(
        session_id=session_id,
        user_message=request.message,
        user_id=current_user.id,
        stream=request.stream,
        parameters=request.parameters,
    )

    if isinstance(result, str):
        # Streaming would be handled via Server-Sent Events
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Streaming not yet implemented via REST"
        )

    return ChatResponse(**result.to_dict())


@router.put("/chat/sessions/{session_id}/model")
async def switch_session_model(
    session_id: str,
    new_model: str = Query(..., description="New model to use"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Switch the model for a session"""
    try:
        session = llm_chat_service.switch_model(session_id, new_model, current_user.id)
        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/chat/sessions/{session_id}/parameters")
async def update_session_parameters(
    session_id: str,
    parameters: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update session parameters"""
    session = llm_chat_service.update_parameters(
        session_id, parameters, current_user.id
    )
    return session.to_dict()


@router.get("/chat/models")
async def list_available_models(
    supports_streaming: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """List available LLM models"""
    models = llm_chat_service.router.list_models(
        supports_streaming=supports_streaming
    )
    return models


# Knowledge Base Endpoints


@router.post("/knowledge-bases")
async def create_knowledge_base(
    request: CreateKnowledgeBaseRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a new knowledge base"""
    kb = rag_service.create_knowledge_base(
        name=request.name,
        description=request.description,
        user_id=current_user.id,
        embedding_model=request.embedding_model,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        retrieval_top_k=request.retrieval_top_k,
    )
    return kb.to_dict()


@router.get("/knowledge-bases")
async def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """List knowledge bases for current user"""
    kbs = rag_service.list_knowledge_bases(current_user.id)
    return [kb.to_dict() for kb in kbs]


@router.get("/knowledge-bases/{kb_id}")
async def get_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get knowledge base details"""
    kb = rag_service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found"
        )
    return kb.to_dict()


@router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a knowledge base"""
    success = rag_service.delete_knowledge_base(kb_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found"
        )
    return {"deleted": True}


@router.post("/knowledge-bases/{kb_id}/documents")
async def add_document(
    kb_id: str,
    request: AddDocumentRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Add a document to a knowledge base"""
    try:
        document = await rag_service.add_document(
            kb_id=kb_id,
            title=request.title,
            content=request.content,
            source_uri=request.source_uri,
            source_type=request.source_type,
            mime_type=request.mime_type,
            chunk_strategy=ChunkStrategy(request.chunk_strategy),
        )
        return {
            "id": document.id,
            "kb_id": document.kb_id,
            "title": document.title,
            "chunk_count": len(document.chunks),
            "status": document.status.value,
            "created_at": document.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/knowledge-bases/{kb_id}/search")
async def search_knowledge_base(
    kb_id: str,
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """Search a knowledge base"""
    try:
        results = await rag_service.search(
            kb_id=kb_id,
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
        )
        return results
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/knowledge-bases/{kb_id}/answer")
async def ask_question(
    kb_id: str,
    request: RAGQuestionRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Ask a question using RAG"""
    try:
        result = await rag_service.answer(
            kb_id=kb_id,
            question=request.question,
            llm_service=llm_chat_service,
            session_id=request.session_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/knowledge-bases/{kb_id}/documents/{document_id}")
async def delete_document(
    kb_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a document from knowledge base"""
    success = rag_service.delete_document(kb_id, document_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return {"deleted": True}


# Inference Service Endpoints


@router.post("/inference/completions")
async def create_completion(
    model: str = Query(..., description="Model to use"),
    prompt: str = Query(..., description="Prompt text"),
    max_tokens: int = Query(512, ge=1, le=4096, description="Max tokens"),
    temperature: float = Query(0.7, ge=0, le=2, description="Temperature"),
    stream: bool = Query(False, description="Stream response"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a text completion (OpenAI-compatible).

    This endpoint provides OpenAI-compatible completion API.
    """
    # In production, call actual inference service
    return {
        "id": "cmpl-" + str(hash(prompt) % 1000000),
        "object": "text_completion",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [
            {
                "text": f"Completion for: {prompt[:50]}...",
                "index": 0,
                "logprobs": None,
                "finish_reason": "length",
            }
        ],
        "usage": {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": 20,
            "total_tokens": len(prompt.split()) + 20,
        },
    }


@router.post("/inference/chat/completions")
async def create_chat_completion(
    request: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a chat completion (OpenAI-compatible).

    This endpoint provides OpenAI-compatible chat API.
    """
    model = request.get("model", "gpt-3.5-turbo")
    messages = request.get("messages", [])
    temperature = request.get("temperature", 0.7)
    max_tokens = request.get("max_tokens", 2048)
    stream = request.get("stream", False)

    # Extract last user message
    user_message = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_message = msg.get("content", "")

    # In production, call actual inference service
    response_text = f"This is a simulated response to: {user_message[:100]}"

    return {
        "id": "chatcmpl-" + str(hash(user_message) % 1000000),
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
            "completion_tokens": len(response_text.split()),
            "total_tokens": sum(len(m.get("content", "").split()) for m in messages) + len(response_text.split()),
        },
    }


@router.get("/inference/endpoints")
async def list_inference_endpoints(
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """List available inference endpoints"""
    # Return deployed models from AIHub
    return [
        {
            "id": "chatglm3-6b",
            "name": "ChatGLM3-6B",
            "type": "llm",
            "endpoint": "/v1/chatglm3-6b",
            "status": "running",
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "qwen-14b",
            "name": "Qwen-14B",
            "type": "llm",
            "endpoint": "/v1/qwen-14b",
            "status": "running",
            "created_at": "2024-01-01T00:00:00Z",
        },
    ]


@router.get("/inference/endpoints/{endpoint_id}/metrics")
async def get_endpoint_metrics(
    endpoint_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get metrics for an inference endpoint"""
    return {
        "endpoint_id": endpoint_id,
        "requests_per_second": 5.2,
        "average_latency_ms": 150,
        "p95_latency_ms": 300,
        "p99_latency_ms": 500,
        "error_rate": 0.001,
        "token_throughput": 1250,
        "gpu_utilization": 0.75,
    }


from datetime import datetime
