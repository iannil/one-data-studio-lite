"""
LLM Chat Service

Provides intelligent dialogue capabilities with context management,
model routing, and streaming support.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Union,
)
from enum import Enum

from app.core.config import settings


class ChatRole(str, Enum):
    """Chat message roles"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class MessageStatus(str, Enum):
    """Message processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatMessage:
    """Chat message representation"""

    def __init__(
        self,
        role: ChatRole,
        content: str,
        status: MessageStatus = MessageStatus.COMPLETED,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.role = role
        self.content = content
        self.status = status
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.token_count: int = 0
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "role": self.value,
            "content": self.content,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "token_count": self.token_count,
            "error": self.error,
            "metadata": self.metadata,
        }

    def to_openai_format(self) -> Dict[str, str]:
        """Convert to OpenAI chat format"""
        return {"role": self.value, "content": self.content}


class ChatSession:
    """Chat session with context management"""

    def __init__(
        self,
        user_id: int,
        model: str,
        system_prompt: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.model = model
        self.system_prompt = system_prompt
        self.parameters = parameters or {}
        self.messages: List[ChatMessage] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.title: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

        # Add system message if provided
        if system_prompt:
            self.messages.append(
                ChatMessage(
                    role=ChatRole.SYSTEM,
                    content=system_prompt,
                    status=MessageStatus.COMPLETED,
                )
            )

    def add_message(
        self,
        role: ChatRole,
        content: str,
        status: MessageStatus = MessageStatus.COMPLETED,
    ) -> ChatMessage:
        """Add a message to the session"""
        message = ChatMessage(role=role, content=content, status=status)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

        # Auto-generate title from first user message
        if (
            role == ChatRole.USER
            and len(self.messages) <= 2
            and not self.title
        ):
            self.title = content[:50] + "..." if len(content) > 50 else content

        return message

    def get_messages(
        self,
        include_system: bool = True,
        max_messages: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Get messages in OpenAI format"""
        messages = self.messages

        if not include_system:
            messages = [m for m in messages if m.role != ChatRole.SYSTEM]

        if max_messages:
            messages = messages[-max_messages:]

        return [m.to_openai_format() for m in messages]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "parameters": self.parameters,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
        }


class ChatParameters:
    """Default chat parameters for different models"""

    # Default parameters
    DEFAULT = {
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stream": False,
    }

    # Creative mode (higher temperature, more randomness)
    CREATIVE = {
        "temperature": 0.9,
        "max_tokens": 2048,
        "top_p": 0.95,
        "frequency_penalty": 0.5,
        "presence_penalty": 0.5,
    }

    # Precise mode (lower temperature, more focused)
    PRECISE = {
        "temperature": 0.2,
        "max_tokens": 4096,
        "top_p": 0.8,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }

    # Code generation mode
    CODE = {
        "temperature": 0.1,
        "max_tokens": 4096,
        "top_p": 0.95,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }

    # Fast mode (shorter responses)
    FAST = {
        "temperature": 0.7,
        "max_tokens": 512,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }


class LLMRouter:
    """
    Routes requests to appropriate LLM backends.
    Supports multiple inference engines:
    - vLLM (for fast local inference)
    - OpenAI API
    - Azure OpenAI
    - Custom endpoints
    """

    def __init__(self):
        self.backends: Dict[str, Dict[str, Any]] = {
            "chatglm3-6b": {
                "type": "vllm",
                "endpoint": f"{settings.LLM_INFERENCE_URL}/v1/chatglm3-6b",
                "supports_streaming": True,
                "supports_function_calling": False,
                "context_window": 8192,
            },
            "qwen-14b": {
                "type": "vllm",
                "endpoint": f"{settings.LLM_INFERENCE_URL}/v1/qwen-14b",
                "supports_streaming": True,
                "supports_function_calling": True,
                "context_window": 32768,
            },
            "llama3-8b": {
                "type": "vllm",
                "endpoint": f"{settings.LLM_INFERENCE_URL}/v1/llama3-8b",
                "supports_streaming": True,
                "supports_function_calling": True,
                "context_window": 8192,
            },
            "gpt-4": {
                "type": "openai",
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "supports_streaming": True,
                "supports_function_calling": True,
                "context_window": 8192,
            },
            "gpt-3.5-turbo": {
                "type": "openai",
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "supports_streaming": True,
                "supports_function_calling": True,
                "context_window": 16385,
            },
        }

    def get_backend(self, model: str) -> Optional[Dict[str, Any]]:
        """Get backend configuration for a model"""
        return self.backends.get(model)

    def list_models(
        self,
        category: Optional[str] = None,
        supports_streaming: Optional[bool] = None,
    ) -> List[Dict[str, str]]:
        """List available models"""
        models = []

        for model_id, config in self.backends.items():
            if supports_streaming and not config.get("supports_streaming"):
                continue

            models.append(
                {
                    "id": model_id,
                    "type": config["type"],
                    "context_window": config["context_window"],
                    "supports_streaming": config.get("supports_streaming", False),
                    "supports_function_calling": config.get("supports_function_calling", False),
                }
            )

        return models


class LLMChatService:
    """
    Main service for LLM chat functionality.
    """

    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.router = LLMRouter()
        self._default_system_prompt = (
            "You are a helpful AI assistant. "
            "Provide accurate, concise, and friendly responses."
        )

    def create_session(
        self,
        user_id: int,
        model: str,
        system_prompt: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            user_id=user_id,
            model=model,
            system_prompt=system_prompt or self._default_system_prompt,
            parameters=parameters or ChatParameters.DEFAULT.copy(),
        )
        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)

    def list_sessions(
        self, user_id: int, limit: int = 50
    ) -> List[ChatSession]:
        """List sessions for a user"""
        user_sessions = [
            s for s in self.sessions.values() if s.user_id == user_id
        ]
        return sorted(user_sessions, key=lambda x: x.updated_at, reverse=True)[
            :limit
        ]

    def delete_session(self, session_id: str, user_id: int) -> bool:
        """Delete a session"""
        session = self.sessions.get(session_id)
        if not session or session.user_id != user_id:
            return False
        del self.sessions[session_id]
        return True

    def clear_history(self, session_id: str, user_id: int) -> bool:
        """Clear message history but keep the session"""
        session = self.sessions.get(session_id)
        if not session or session.user_id != user_id:
            return False

        # Keep only system message
        system_message = None
        for msg in session.messages:
            if msg.role == ChatRole.SYSTEM:
                system_message = msg
                break

        session.messages = []
        if system_message:
            session.messages.append(system_message)

        session.updated_at = datetime.utcnow()
        return True

    async def chat(
        self,
        session_id: str,
        user_message: str,
        user_id: int,
        stream: bool = False,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Union[ChatMessage, AsyncIterator[str]]:
        """
        Send a chat message and get a response.

        Args:
            session_id: Session ID
            user_message: User message content
            user_id: User ID for authorization
            stream: Whether to stream the response
            parameters: Override parameters for this message

        Returns:
            ChatMessage or async iterator of chunks if streaming
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if session.user_id != user_id:
            raise PermissionError("Not authorized for this session")

        # Add user message
        user_msg = session.add_message(ChatRole.USER, user_message)

        # Merge parameters
        params = {**session.parameters, **(parameters or {})}

        if stream:
            return self._stream_chat(session, user_msg, params)
        else:
            return await self._complete_chat(session, user_msg, params)

    async def _complete_chat(
        self,
        session: ChatSession,
        user_message: ChatMessage,
        parameters: Dict[str, Any],
    ) -> ChatMessage:
        """Complete a non-streaming chat request"""
        backend = self.router.get_backend(session.model)
        if not backend:
            raise ValueError(f"Model {session.model} not available")

        # Prepare messages
        messages = session.get_messages(include_system=True, max_messages=50)

        # Simulate API call
        # In production, would call actual LLM backend
        await asyncio.sleep(0.5)

        # Generate response
        response_content = self._generate_response(
            user_message.content, session.system_prompt or ""
        )

        # Add assistant message
        assistant_msg = session.add_message(ChatRole.ASSISTANT, response_content)
        assistant_msg.completed_at = datetime.utcnow()

        return assistant_msg

    async def _stream_chat(
        self,
        session: ChatSession,
        user_message: ChatMessage,
        parameters: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """Stream a chat response"""
        backend = self.router.get_backend(session.model)
        if not backend or not backend.get("supports_streaming"):
            # Fallback to non-streaming
            result = await self._complete_chat(session, user_message, parameters)
            yield result.content
            return

        # Simulate streaming
        response = self._generate_response(
            user_message.content, session.system_prompt or ""
        )
        words = response.split()

        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)

        # Add complete message to session
        session.add_message(ChatRole.ASSISTANT, response)

    def _generate_response(self, user_message: str, system_prompt: str) -> str:
        """Generate a mock response (in production, call actual LLM)"""
        # Simple pattern matching for demo
        responses = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! What can I assist you with?",
            "code": "I'd be happy to help with coding. What language or problem are you working on?",
            "help": "I'm here to help! I can assist with various tasks including:\n- Answering questions\n- Writing code\n- Analyzing data\n- Creative writing\n- And much more!\n\nWhat do you need help with?",
            "thank": "You're welcome! Is there anything else I can help you with?",
            "bye": "Goodbye! Feel free to come back anytime you need assistance.",
        }

        user_lower = user_message.lower()
        for key, response in responses.items():
            if key in user_lower:
                return response

        return f"I understand you're asking about: {user_message}\n\nThis is a simulated response. In production, I would connect to an actual LLM backend to generate a contextual response."

    def switch_model(
        self, session_id: str, new_model: str, user_id: int
    ) -> ChatSession:
        """Switch the model for a session"""
        session = self.get_session(session_id)
        if not session or session.user_id != user_id:
            raise PermissionError("Not authorized for this session")

        # Verify new model exists
        backend = self.router.get_backend(new_model)
        if not backend:
            raise ValueError(f"Model {new_model} not available")

        session.model = new_model
        session.updated_at = datetime.utcnow()
        return session

    def update_parameters(
        self, session_id: str, parameters: Dict[str, Any], user_id: int
    ) -> ChatSession:
        """Update session parameters"""
        session = self.get_session(session_id)
        if not session or session.user_id != user_id:
            raise PermissionError("Not authorized for this session")

        session.parameters = {**session.parameters, **parameters}
        session.updated_at = datetime.utcnow()
        return session


# Global service instance
llm_chat_service = LLMChatService()
