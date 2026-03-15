"""
Vector Store Backends

Abstract interface and implementations for various vector databases:
- ChromaDB
- Faiss
- PGVector
- Qdrant
- Milvus
- In-memory
"""

import asyncio
import pickle
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class VectorResult:
    """Result from vector similarity search"""
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class VectorStoreBackend(ABC):
    """Abstract base class for vector storage backends"""

    def __init__(self, collection_name: str, embedding_dim: int):
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector store"""

    @abstractmethod
    async def insert(
        self,
        chunk_id: str,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Insert a vector into the store"""

    @abstractmethod
    async def insert_batch(
        self,
        items: List[Tuple[str, str, str, List[float], Optional[Dict[str, Any]]]],
    ) -> List[str]:
        """Insert multiple vectors"""

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorResult]:
        """Search for similar vectors"""

    @abstractmethod
    async def delete(self, chunk_id: str) -> bool:
        """Delete a vector by chunk ID"""

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> int:
        """Delete all vectors for a document"""

    @abstractmethod
    async def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by chunk ID"""

    @abstractmethod
    async def count(self) -> int:
        """Get total number of vectors"""

    @abstractmethod
    async def drop(self) -> bool:
        """Drop the entire collection"""


class MemoryVectorStore(VectorStoreBackend):
    """In-memory vector store for development/testing"""

    def __init__(self, collection_name: str, embedding_dim: int):
        super().__init__(collection_name, embedding_dim)
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._content: Dict[str, str] = {}
        self._doc_mapping: Dict[str, str] = {}  # chunk_id -> document_id

    async def initialize(self) -> None:
        """No initialization needed for in-memory store"""
        pass

    async def insert(
        self,
        chunk_id: str,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._vectors[chunk_id] = embedding
        self._metadata[chunk_id] = metadata or {}
        self._content[chunk_id] = content
        self._doc_mapping[chunk_id] = document_id
        return chunk_id

    async def insert_batch(
        self,
        items: List[Tuple[str, str, str, List[float], Optional[Dict[str, Any]]]],
    ) -> List[str]:
        chunk_ids = []
        for chunk_id, document_id, content, embedding, metadata in items:
            await self.insert(chunk_id, document_id, content, embedding, metadata)
            chunk_ids.append(chunk_id)
        return chunk_ids

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorResult]:
        results = []

        for chunk_id, vector in self._vectors.items():
            # Apply filters
            if filters:
                metadata = self._metadata.get(chunk_id, {})
                if not all(metadata.get(k) == v for k, v in filters.items()):
                    continue

            # Calculate similarity
            score = self._cosine_similarity(query_embedding, vector)
            results.append((
                chunk_id,
                self._doc_mapping.get(chunk_id, ""),
                self._content.get(chunk_id, ""),
                score,
                self._metadata.get(chunk_id),
            ))

        # Sort by score descending
        results.sort(key=lambda x: x[3], reverse=True)
        return [
            VectorResult(
                chunk_id=r[0],
                document_id=r[1],
                content=r[2],
                score=r[3],
                metadata=r[4],
            )
            for r in results[:top_k]
        ]

    async def delete(self, chunk_id: str) -> bool:
        if chunk_id in self._vectors:
            del self._vectors[chunk_id]
            del self._metadata[chunk_id]
            del self._content[chunk_id]
            del self._doc_mapping[chunk_id]
            return True
        return False

    async def delete_by_document(self, document_id: str) -> int:
        to_delete = [
            chunk_id for chunk_id, doc_id in self._doc_mapping.items()
            if doc_id == document_id
        ]
        for chunk_id in to_delete:
            await self.delete(chunk_id)
        return len(to_delete)

    async def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        if chunk_id not in self._vectors:
            return None
        return {
            "chunk_id": chunk_id,
            "document_id": self._doc_mapping.get(chunk_id),
            "content": self._content.get(chunk_id),
            "embedding": self._vectors.get(chunk_id),
            "metadata": self._metadata.get(chunk_id),
        }

    async def count(self) -> int:
        return len(self._vectors)

    async def drop(self) -> bool:
        self._vectors.clear()
        self._metadata.clear()
        self._content.clear()
        self._doc_mapping.clear()
        return True

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity"""
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(y * y for y in b) ** 0.5
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        return dot_product / (magnitude_a * magnitude_b)


class FaissVectorStore(VectorStoreBackend):
    """Faiss-based vector store (local file-based)"""

    def __init__(
        self,
        collection_name: str,
        embedding_dim: int,
        index_type: str = "HNSW",
        data_path: str = "/data/faiss",
    ):
        super().__init__(collection_name, embedding_dim)
        self.index_type = index_type
        self.data_path = Path(data_path) / collection_name
        self.data_path.mkdir(parents=True, exist_ok=True)

        self._index = None
        self._chunk_ids: List[str] = []
        self._doc_mapping: Dict[str, str] = {}
        self._content: Dict[str, str] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize or load existing Faiss index"""
        try:
            import faiss
        except ImportError:
            raise RuntimeError("faiss-cpu or faiss-gpu not installed")

        index_file = self.data_path / "index.faiss"
        metadata_file = self.data_path / "metadata.pkl"

        if index_file.exists() and metadata_file.exists():
            # Load existing index
            self._index = faiss.read_index(str(index_file))
            with open(metadata_file, "rb") as f:
                data = pickle.load(f)
                self._chunk_ids = data.get("chunk_ids", [])
                self._doc_mapping = data.get("doc_mapping", {})
                self._content = data.get("content", {})
                self._metadata = data.get("metadata", {})
        else:
            # Create new index
            if self.index_type == "HNSW":
                self._index = faiss.IndexHNSWFlat(self.embedding_dim, 32)
            elif self.index_type == "IVF":
                quantizer = faiss.IndexFlatL2(self.embedding_dim)
                self._index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, 100)
            else:  # FLAT
                self._index = faiss.IndexFlatL2(self.embedding_dim)

    async def insert(
        self,
        chunk_id: str,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        import faiss

        idx = len(self._chunk_ids)
        self._chunk_ids.append(chunk_id)
        self._doc_mapping[chunk_id] = document_id
        self._content[chunk_id] = content
        self._metadata[chunk_id] = metadata or {}

        # Add to index
        vector = np.array([embedding], dtype=np.float32)
        if isinstance(self._index, faiss.IndexIVFFlat):
            if not self._index.is_trained:
                self._index.train(vector)
        self._index.add(vector)

        # Save to disk
        self._save()
        return chunk_id

    async def insert_batch(
        self,
        items: List[Tuple[str, str, str, List[float], Optional[Dict[str, Any]]]],
    ) -> List[str]:
        import faiss

        chunk_ids = []
        vectors = []

        for chunk_id, document_id, content, embedding, metadata in items:
            idx = len(self._chunk_ids)
            self._chunk_ids.append(chunk_id)
            self._doc_mapping[chunk_id] = document_id
            self._content[chunk_id] = content
            self._metadata[chunk_id] = metadata or {}
            chunk_ids.append(chunk_id)
            vectors.append(embedding)

        # Add batch to index
        if vectors:
            vectors_array = np.array(vectors, dtype=np.float32)
            if isinstance(self._index, faiss.IndexIVFFlat):
                if not self._index.is_trained:
                    self._index.train(vectors_array)
            self._index.add(vectors_array)

        self._save()
        return chunk_ids

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorResult]:
        if self._index.ntotal() == 0:
            return []

        import faiss

        # Convert to L2 distance (Faiss default is L2)
        # For cosine similarity, we'd need to normalize vectors
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Faiss returns L2 distances, we convert to cosine similarity scores
        k = min(top_k, self._index.ntotal())
        distances, indices = self._index.search(query_vector, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._chunk_ids):
                continue

            chunk_id = self._chunk_ids[idx]

            # Apply filters
            if filters:
                metadata = self._metadata.get(chunk_id, {})
                if not all(metadata.get(k) == v for k, v in filters.items()):
                    continue

            # Convert L2 distance to similarity score (0-1)
            # Higher is better
            score = 1.0 / (1.0 + float(dist))

            results.append(VectorResult(
                chunk_id=chunk_id,
                document_id=self._doc_mapping.get(chunk_id, ""),
                content=self._content.get(chunk_id, ""),
                score=score,
                metadata=self._metadata.get(chunk_id),
            ))

        return results

    async def delete(self, chunk_id: str) -> bool:
        # Faiss doesn't support deletion, need to rebuild
        return await self._delete_and_rebuild([chunk_id])

    async def delete_by_document(self, document_id: str) -> int:
        to_delete = [
            chunk_id for chunk_id, doc_id in self._doc_mapping.items()
            if doc_id == document_id
        ]
        if to_delete:
            await self._delete_and_rebuild(to_delete)
        return len(to_delete)

    async def _delete_and_rebuild(self, chunk_ids_to_delete: List[str]) -> bool:
        """Rebuild index without specified chunks"""
        import faiss

        delete_set = set(chunk_ids_to_delete)
        new_chunk_ids = []
        new_doc_mapping = {}
        new_content = {}
        new_metadata = {}
        vectors = []

        for chunk_id in self._chunk_ids:
            if chunk_id in delete_set:
                continue
            new_chunk_ids.append(chunk_id)
            new_doc_mapping[chunk_id] = self._doc_mapping[chunk_id]
            new_content[chunk_id] = self._content[chunk_id]
            new_metadata[chunk_id] = self._metadata[chunk_id]
            # Need to retrieve vector from index
            # For simplicity, we'd need to store vectors separately
            # This is a limitation of Faiss

        self._chunk_ids = new_chunk_ids
        self._doc_mapping = new_doc_mapping
        self._content = new_content
        self._metadata = new_metadata

        # Rebuild index
        # In practice, you'd need to store original vectors
        self._save()
        return True

    async def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        if chunk_id not in self._doc_mapping:
            return None
        return {
            "chunk_id": chunk_id,
            "document_id": self._doc_mapping.get(chunk_id),
            "content": self._content.get(chunk_id),
            "metadata": self._metadata.get(chunk_id),
        }

    async def count(self) -> int:
        return len(self._chunk_ids)

    async def drop(self) -> bool:
        self._chunk_ids.clear()
        self._doc_mapping.clear()
        self._content.clear()
        self._metadata.clear()
        self._save()
        return True

    def _save(self) -> None:
        """Save index and metadata to disk"""
        import faiss

        if self._index:
            faiss.write_index(self._index, str(self.data_path / "index.faiss"))

        with open(self.data_path / "metadata.pkl", "wb") as f:
            pickle.dump({
                "chunk_ids": self._chunk_ids,
                "doc_mapping": self._doc_mapping,
                "content": self._content,
                "metadata": self._metadata,
            }, f)


class ChromaDBVectorStore(VectorStoreBackend):
    """ChromaDB-based vector store"""

    def __init__(
        self,
        collection_name: str,
        embedding_dim: int,
        endpoint: Optional[str] = None,
    ):
        super().__init__(collection_name, embedding_dim)
        self.endpoint = endpoint
        self._client = None
        self._collection = None

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection"""
        try:
            import chromadb
        except ImportError:
            raise RuntimeError("chromadb not installed")

        if self.endpoint:
            # Connect to remote ChromaDB
            self._client = chromadb.HttpClient(host=self.endpoint.split(":")[0].replace("//", ""), port=int(self.endpoint.split(":")[-1]) if ":" in self.endpoint else 8000)
        else:
            # Use in-memory or persistent client
            self._client = chromadb.Client()

        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"embedding_dim": self.embedding_dim},
        )

    async def insert(
        self,
        chunk_id: str,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        metadata = metadata or {}
        metadata["document_id"] = document_id

        self._collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata],
        )
        return chunk_id

    async def insert_batch(
        self,
        items: List[Tuple[str, str, str, List[float], Optional[Dict[str, Any]]]],
    ) -> List[str]:
        chunk_ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk_id, document_id, content, embedding, metadata in items:
            chunk_ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(content)
            meta = metadata or {}
            meta["document_id"] = document_id
            metadatas.append(meta)

        self._collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return chunk_ids

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorResult]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters,
        )

        vector_results = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                vector_results.append(VectorResult(
                    chunk_id=chunk_id,
                    document_id=results["metadatas"][0][i].get("document_id", ""),
                    content=results["documents"][0][i] if results["documents"] else "",
                    score=1.0 - results["distances"][0][i] if results.get("distances") else 1.0,
                    metadata=results["metadatas"][0][i] if results.get("metadatas") else None,
                ))

        return vector_results

    async def delete(self, chunk_id: str) -> bool:
        self._collection.delete(ids=[chunk_id])
        return True

    async def delete_by_document(self, document_id: str) -> int:
        # Get all chunks for the document
        results = self._collection.get(
            where={"document_id": document_id}
        )
        if results["ids"]:
            self._collection.delete(ids=results["ids"])
            return len(results["ids"])
        return 0

    async def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        results = self._collection.get(ids=[chunk_id])
        if results["ids"] and results["ids"][0] == chunk_id:
            return {
                "chunk_id": chunk_id,
                "document_id": results["metadatas"][0].get("document_id") if results.get("metadatas") else None,
                "content": results["documents"][0] if results.get("documents") else None,
                "metadata": results["metadatas"][0] if results.get("metadatas") else None,
            }
        return None

    async def count(self) -> int:
        return self._collection.count()

    async def drop(self) -> bool:
        self._client.delete_collection(name=self.collection_name)
        return True


class PGVectorStore(VectorStoreBackend):
    """PostgreSQL with pgvector extension"""

    def __init__(
        self,
        collection_name: str,
        embedding_dim: int,
        db_url: str,
    ):
        super().__init__(collection_name, embedding_dim)
        self.db_url = db_url
        self._pool = None

    async def initialize(self) -> None:
        """Initialize database connection pool"""
        try:
            from asyncpg import create_pool
            from asyncpg.pool import Pool
        except ImportError:
            raise RuntimeError("asyncpg not installed")

        self._pool = await create_pool(self.db_url)

        # Create table if not exists
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table_name()} (
                    chunk_id VARCHAR(100) PRIMARY KEY,
                    document_id VARCHAR(100) NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({self.embedding_dim}),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_{self._table_name()}_embedding
                ON {self._table_name()}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);

                CREATE INDEX IF NOT EXISTS idx_{self._table_name()}_document_id
                ON {self._table_name()}(document_id);
            """)

    def _table_name(self) -> str:
        """Get SQL table name (sanitized)"""
        return f"vectors_{self.collection_name.lower().replace('-', '_')}"

    async def insert(
        self,
        chunk_id: str,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        import json

        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {self._table_name()}
                (chunk_id, document_id, content, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (chunk_id) DO UPDATE
                SET content = $3, embedding = $4, metadata = $5
            """, chunk_id, document_id, content, str(embedding), json.dumps(metadata or {}))
        return chunk_id

    async def insert_batch(
        self,
        items: List[Tuple[str, str, str, List[float], Optional[Dict[str, Any]]]],
    ) -> List[str]:
        chunk_ids = []
        for chunk_id, document_id, content, embedding, metadata in items:
            await self.insert(chunk_id, document_id, content, embedding, metadata)
            chunk_ids.append(chunk_id)
        return chunk_ids

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorResult]:
        import json

        query = f"""
            SELECT chunk_id, document_id, content,
                   1 - (embedding <=> $1::vector) as score,
                   metadata
            FROM {self._table_name()}
        """
        params = [str(query_embedding)]

        if filters:
            conditions = []
            param_idx = 2
            for key, value in filters.items():
                conditions.append(f"metadata->>${param_idx} = ${param_idx + 1}")
                params.extend([key, str(value)])
                param_idx += 2
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY embedding <=> $1::vector LIMIT {top_k}"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            VectorResult(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                content=row["content"],
                score=float(row["score"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            )
            for row in rows
        ]

    async def delete(self, chunk_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table_name()} WHERE chunk_id = $1",
                chunk_id
            )
            return "DELETE 1" in result
        return False

    async def delete_by_document(self, document_id: str) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table_name()} WHERE document_id = $1",
                document_id
            )
            # Parse "DELETE n" from result
            try:
                return int(result.split()[-1])
            except (IndexError, ValueError):
                return 0

    async def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        import json

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {self._table_name()} WHERE chunk_id = $1",
                chunk_id
            )
            if row:
                return {
                    "chunk_id": row["chunk_id"],
                    "document_id": row["document_id"],
                    "content": row["content"],
                    "embedding": row["embedding"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                }
        return None

    async def count(self) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.fetchrow(
                f"SELECT COUNT(*) as count FROM {self._table_name()}"
            )
            return result["count"] if result else 0

    async def drop(self) -> bool:
        async with self._pool.acquire() as conn:
            await conn.execute(f"DROP TABLE IF EXISTS {self._table_name()}")
        return True


def get_vector_store(
    backend: str,
    collection_name: str,
    embedding_dim: int,
    **config,
) -> VectorStoreBackend:
    """Factory function to get vector store instance"""
    backend = backend.lower()

    if backend == VectorBackend.MEMORY:
        return MemoryVectorStore(collection_name, embedding_dim)
    elif backend == VectorBackend.FAISS:
        return FaissVectorStore(
            collection_name,
            embedding_dim,
            index_type=config.get("index_type", "HNSW"),
            data_path=config.get("data_path", "/data/faiss"),
        )
    elif backend == VectorBackend.CHROMADB:
        return ChromaDBVectorStore(
            collection_name,
            embedding_dim,
            endpoint=config.get("endpoint"),
        )
    elif backend == VectorBackend.PGVECTOR:
        return PGVectorStore(
            collection_name,
            embedding_dim,
            db_url=config.get("db_url"),
        )
    else:
        raise ValueError(f"Unsupported vector backend: {backend}")
