"""
Embedding Service

Supports multiple embedding providers:
- OpenAI (text-embedding-3-small/large)
- Cohere (embed-v3)
- HuggingFace (sentence-transformers)
- BGE (BAAI General Embedding)
- Custom endpoints
"""

import asyncio
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.core.config import settings


@dataclass
class EmbeddingResult:
    """Result from embedding generation"""
    embedding: List[float]
    model: str
    dimension: int
    tokens_used: Optional[int] = None


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""

    def __init__(self, model: str, embedding_dim: int):
        self.model = model
        self.embedding_dim = embedding_dim
        self._cache: Dict[str, List[float]] = {}

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""

    @abstractmethod
    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text"""

    async def embed_with_cache(
        self,
        texts: List[str],
        use_cache: bool = True,
        cache_ttl: int = 3600,
    ) -> List[List[float]]:
        """Generate embeddings with caching support"""
        results = []
        texts_to_embed = []
        indices_to_embed = []

        if use_cache:
            # Check cache
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    results.append((i, self._cache[cache_key]))
                else:
                    texts_to_embed.append(text)
                    indices_to_embed.append(i)
        else:
            texts_to_embed = texts
            indices_to_embed = list(range(len(texts)))

        # Generate embeddings for uncached texts
        if texts_to_embed:
            new_embeddings = await self.embed(texts_to_embed)

            for idx, embedding in zip(indices_to_embed, new_embeddings):
                results.append((idx, embedding))
                if use_cache:
                    cache_key = self._get_cache_key(texts[indices_to_embed.index(idx)])
                    self._cache[cache_key] = embedding

        # Sort results by original index
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results]

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return f"{self.model}:{hashlib.md5(text.encode()).hexdigest()}"

    def clear_cache(self) -> None:
        """Clear the embedding cache"""
        self._cache.clear()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        embedding_dim = 1536 if model == "text-embedding-3-small" else 3072
        super().__init__(model, embedding_dim)
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_BASE_URL

    async def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai not installed")

        client = openai.AsyncAI(api_key=self.api_key, base_url=self.base_url)

        # OpenAI supports batch embedding
        response = await client.embeddings.create(
            input=texts,
            model=self.model,
        )

        return [item.embedding for item in response.data]

    async def embed_single(self, text: str) -> List[float]:
        embeddings = await self.embed([text])
        return embeddings[0]


class CohereEmbeddingProvider(EmbeddingProvider):
    """Cohere embedding provider"""

    def __init__(
        self,
        model: str = "embed-english-v3.0",
        api_key: Optional[str] = None,
    ):
        embedding_dim = 1024
        super().__init__(model, embedding_dim)
        self.api_key = api_key

    async def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            import cohere
        except ImportError:
            raise RuntimeError("cohere not installed")

        client = cohere.AsyncClient(api_key=self.api_key)

        # Cohere supports batch embedding
        response = await client.embed(
            texts=texts,
            model=self.model,
            input_type="search_document",
        )

        return response.embeddings

    async def embed_single(self, text: str) -> List[float]:
        embeddings = await self.embed([text])
        return embeddings[0]


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """HuggingFace sentence-transformers provider"""

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
    ):
        # Common dimensions for popular models
        model_dims = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
        }
        embedding_dim = model_dims.get(model, 768)
        super().__init__(model, embedding_dim)
        self.device = device
        self._model = None
        self._tokenizer = None

    async def _load_model(self):
        """Lazy load model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise RuntimeError("sentence-transformers not installed")

            self._model = SentenceTransformer(self.model, device=self.device)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        await self._load_model()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self._model.encode,
            texts,
        )

        return embeddings.tolist()

    async def embed_single(self, text: str) -> List[float]:
        embeddings = await self.embed([text])
        return embeddings[0]


class BGEEmbeddingProvider(EmbeddingProvider):
    """BGE (BAAI General Embedding) provider"""

    def __init__(
        self,
        model: str = "BAAI/bge-large-zh-v1.5",
        device: str = "cpu",
    ):
        # BGE model dimensions
        model_dims = {
            "BAAI/bge-small-en-v1.5": 384,
            "BAAI/bge-base-en-v1.5": 768,
            "BAAI/bge-large-en-v1.5": 1024,
            "BAAI/bge-large-zh-v1.5": 1024,
        }
        embedding_dim = model_dims.get(model, 1024)
        super().__init__(model, embedding_dim)
        self.device = device
        self._model = None

    async def _load_model(self):
        """Lazy load model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise RuntimeError("sentence-transformers not installed")

            self._model = SentenceTransformer(self.model, device=self.device)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        await self._load_model()

        # Add instruction for BGE models
        instruction = "为这个句子生成表示以用于检索相关文章："

        # Prepend instruction for Chinese model
        if "zh" in self.model:
            texts = [instruction + text for text in texts]

        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self._model.encode,
            texts,
        )

        return embeddings.tolist()

    async def embed_single(self, text: str) -> List[float]:
        embeddings = await self.embed([text])
        return embeddings[0]


class CustomEmbeddingProvider(EmbeddingProvider):
    """Custom HTTP endpoint embedding provider"""

    def __init__(
        self,
        endpoint: str,
        embedding_dim: int = 1024,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__("custom", embedding_dim)
        self.endpoint = endpoint
        self.headers = headers or {}

    async def embed(self, texts: List[str]) -> List[List[float]]:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.endpoint,
                json={"texts": texts},
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("embeddings", [])

    async def embed_single(self, text: str) -> List[float]:
        embeddings = await self.embed([text])
        return embeddings[0]


class EmbeddingService:
    """Unified embedding service with provider management"""

    def __init__(self):
        self._providers: Dict[str, EmbeddingProvider] = {}
        self._default_provider: Optional[str] = None

    def register_provider(
        self,
        name: str,
        provider: EmbeddingProvider,
        set_as_default: bool = False,
    ) -> None:
        """Register an embedding provider"""
        self._providers[name] = provider
        if set_as_default or self._default_provider is None:
            self._default_provider = name

    def get_provider(self, name: Optional[str] = None) -> EmbeddingProvider:
        """Get a registered provider"""
        provider_name = name or self._default_provider
        if provider_name not in self._providers:
            raise ValueError(f"Provider {provider_name} not found. Available: {list(self._providers.keys())}")
        return self._providers[provider_name]

    async def embed(
        self,
        texts: List[str],
        provider: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[List[float]]:
        """Generate embeddings for texts"""
        embedding_provider = self.get_provider(provider)
        return await embedding_provider.embed_with_cache(texts, use_cache)

    async def embed_single(
        self,
        text: str,
        provider: Optional[str] = None,
    ) -> List[float]:
        """Generate embedding for a single text"""
        embedding_provider = self.get_provider(provider)
        return await embedding_provider.embed_single(text)

    def list_providers(self) -> List[str]:
        """List registered providers"""
        return list(self._providers.keys())


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create global embedding service instance"""
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()

        # Register default providers based on configuration
        from app.core.config import settings

        # Register OpenAI if API key is available
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            _embedding_service.register_provider(
                "openai",
                OpenAIEmbeddingProvider(
                    model=getattr(settings, 'EMBEDDING_MODEL', 'text-embedding-3-small'),
                ),
                set_as_default=True,
            )

        # Register BGE as default if OpenAI is not available
        if not _embedding_service.list_providers():
            _embedding_service.register_provider(
                "bge",
                BGEEmbeddingProvider(
                    model=getattr(settings, 'EMBEDDING_MODEL', 'BAAI/bge-large-zh-v1.5'),
                ),
                set_as_default=True,
            )

    return _embedding_service


async def embed_texts(texts: List[str], provider: Optional[str] = None) -> List[List[float]]:
    """Convenience function to embed texts"""
    service = get_embedding_service()
    return await service.embed(texts, provider)


async def embed_text(text: str, provider: Optional[str] = None) -> List[float]:
    """Convenience function to embed a single text"""
    service = get_embedding_service()
    return await service.embed_single(text, provider)
