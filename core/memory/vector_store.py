"""
Vector store abstraction for CrossBridge Memory system.

This module provides pluggable storage backends for memory embeddings,
supporting both PostgreSQL (pgvector) and local FAISS indexes.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.logging import get_logger, LogCategory
from core.memory.models import MemoryRecord, MemoryType

logger = get_logger(__name__, category=LogCategory.AI)


class VectorStore(ABC):
    """
    Abstract base class for vector storage backends.
    
    This allows CrossBridge to support multiple vector databases
    without locking into a specific vendor.
    """

    @abstractmethod
    def upsert(self, records: List[MemoryRecord]) -> int:
        """
        Insert or update memory records.
        
        Args:
            records: List of MemoryRecord objects with embeddings
            
        Returns:
            Number of records successfully stored
        """
        pass

    @abstractmethod
    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query for similar vectors.
        
        Args:
            vector: Query vector
            top_k: Maximum number of results to return
            filters: Optional filters (type, framework, etc.)
            
        Returns:
            List of results with records and similarity scores
        """
        pass

    @abstractmethod
    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """
        Retrieve a specific record by ID.
        
        Args:
            record_id: Unique record identifier
            
        Returns:
            MemoryRecord if found, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, record_ids: List[str]) -> int:
        """
        Delete records by ID.
        
        Args:
            record_ids: List of record IDs to delete
            
        Returns:
            Number of records deleted
        """
        pass

    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching filters.
        
        Args:
            filters: Optional filters
            
        Returns:
            Number of matching records
        """
        pass


class PgVectorStore(VectorStore):
    """
    PostgreSQL vector store using pgvector extension.
    
    Requires PostgreSQL with pgvector extension installed.
    """

    def __init__(self, connection_string: str, dimension: int = 1536):
        """
        Initialize PostgreSQL vector store.
        
        Args:
            connection_string: PostgreSQL connection string
            dimension: Vector dimension (must match embedding provider)
        """
        self.connection_string = connection_string
        self.dimension = dimension

        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker
        except ImportError:
            raise ImportError(
                "sqlalchemy not installed. Install with: pip install sqlalchemy psycopg2-binary"
            )

        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)

        # Initialize schema
        self._init_schema()

        logger.info(
            f"Initialized PgVectorStore with dimension {dimension}"
        )

    def _init_schema(self):
        """Create tables and pgvector extension if they don't exist."""
        from sqlalchemy import text

        with self.engine.connect() as conn:
            # Enable pgvector extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

            # Create memory_embeddings table
            conn.execute(
                text(
                    f"""
                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    metadata JSONB,
                    embedding VECTOR({self.dimension}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )

            # Create indexes for performance
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_memory_type 
                ON memory_embeddings(type)
            """
                )
            )

            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_memory_metadata 
                ON memory_embeddings USING GIN(metadata)
            """
                )
            )

            # Vector similarity index (HNSW for fast approximate search)
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_memory_embedding 
                ON memory_embeddings USING hnsw (embedding vector_cosine_ops)
            """
                )
            )

            conn.commit()

        logger.info("Database schema initialized successfully")

    def upsert(self, records: List[MemoryRecord]) -> int:
        """Insert or update memory records in PostgreSQL."""
        from sqlalchemy import text

        if not records:
            return 0

        inserted = 0
        with self.Session() as session:
            for record in records:
                if not record.embedding:
                    logger.warning(
                        f"Skipping record {record.id} without embedding"
                    )
                    continue

                # Convert embedding to pgvector format
                embedding_str = "[" + ",".join(map(str, record.embedding)) + "]"

                session.execute(
                    text(
                        """
                    INSERT INTO memory_embeddings (id, type, text, metadata, embedding, created_at, updated_at)
                    VALUES (:id, :type, :text, :metadata::jsonb, :embedding::vector, :created_at, :updated_at)
                    ON CONFLICT (id) DO UPDATE SET
                        type = EXCLUDED.type,
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding,
                        updated_at = EXCLUDED.updated_at
                """
                    ),
                    {
                        "id": record.id,
                        "type": record.type.value,
                        "text": record.text,
                        "metadata": json.dumps(record.metadata),
                        "embedding": embedding_str,
                        "created_at": record.created_at,
                        "updated_at": record.updated_at,
                    },
                )
                inserted += 1

            session.commit()

        logger.info(f"Upserted {inserted} records to PostgreSQL")
        return inserted

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query for similar vectors using cosine similarity."""
        from sqlalchemy import text

        # Build query with optional filters
        embedding_str = "[" + ",".join(map(str, vector)) + "]"

        where_clauses = []
        params = {"embedding": embedding_str, "top_k": top_k}

        if filters:
            if "type" in filters:
                types = filters["type"] if isinstance(filters["type"], list) else [filters["type"]]
                where_clauses.append("type = ANY(:types)")
                params["types"] = types

            if "framework" in filters:
                where_clauses.append("metadata->>'framework' = :framework")
                params["framework"] = filters["framework"]

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query_sql = f"""
            SELECT 
                id, type, text, metadata, embedding,
                created_at, updated_at,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM memory_embeddings
            {where_sql}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """

        with self.Session() as session:
            result = session.execute(text(query_sql), params)
            rows = result.fetchall()

        results = []
        for row in rows:
            record = MemoryRecord(
                id=row.id,
                type=MemoryType(row.type),
                text=row.text,
                metadata=row.metadata,
                embedding=None,  # Don't return full embedding in results
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            results.append({"record": record, "score": float(row.similarity)})

        logger.info(f"Found {len(results)} similar records")
        return results

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """Retrieve a specific record by ID."""
        from sqlalchemy import text

        with self.Session() as session:
            result = session.execute(
                text(
                    """
                SELECT id, type, text, metadata, created_at, updated_at
                FROM memory_embeddings
                WHERE id = :id
            """
                ),
                {"id": record_id},
            )
            row = result.fetchone()

        if not row:
            return None

        return MemoryRecord(
            id=row.id,
            type=MemoryType(row.type),
            text=row.text,
            metadata=row.metadata,
            embedding=None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def delete(self, record_ids: List[str]) -> int:
        """Delete records by ID."""
        from sqlalchemy import text

        if not record_ids:
            return 0

        with self.Session() as session:
            result = session.execute(
                text("DELETE FROM memory_embeddings WHERE id = ANY(:ids)"),
                {"ids": record_ids},
            )
            session.commit()
            deleted = result.rowcount

        logger.info(f"Deleted {deleted} records")
        return deleted

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records matching filters."""
        from sqlalchemy import text

        where_clauses = []
        params = {}

        if filters:
            if "type" in filters:
                types = filters["type"] if isinstance(filters["type"], list) else [filters["type"]]
                where_clauses.append("type = ANY(:types)")
                params["types"] = types

            if "framework" in filters:
                where_clauses.append("metadata->>'framework' = :framework")
                params["framework"] = filters["framework"]

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        with self.Session() as session:
            result = session.execute(
                text(f"SELECT COUNT(*) FROM memory_embeddings {where_sql}"),
                params,
            )
            count = result.scalar()

        return count


class FAISSVectorStore(VectorStore):
    """
    Local FAISS vector store for development and testing.
    
    Stores data in memory and optionally persists to disk.
    """

    def __init__(self, dimension: int = 1536, index_path: Optional[str] = None):
        """
        Initialize FAISS vector store.
        
        Args:
            dimension: Vector dimension
            index_path: Optional path to save/load index from disk
        """
        try:
            import faiss
            import numpy as np
        except ImportError:
            raise ImportError(
                "faiss-cpu not installed. Install with: pip install faiss-cpu numpy"
            )

        self.dimension = dimension
        self.index_path = index_path
        self.faiss = faiss
        self.np = np

        # Create FAISS index (using cosine similarity via normalized vectors)
        self.index = faiss.IndexFlatIP(dimension)

        # Store metadata separately
        self.records: Dict[str, MemoryRecord] = {}
        self.id_to_idx: Dict[str, int] = {}
        self.idx_to_id: Dict[int, str] = {}

        # Load from disk if path provided
        if index_path:
            self._load()

        logger.info(f"Initialized FAISSVectorStore with dimension {dimension}")

    def upsert(self, records: List[MemoryRecord]) -> int:
        """Insert or update memory records in FAISS index."""
        if not records:
            return 0

        inserted = 0
        for record in records:
            if not record.embedding:
                logger.warning(f"Skipping record {record.id} without embedding")
                continue

            # Normalize embedding for cosine similarity
            embedding = self.np.array([record.embedding], dtype="float32")
            self.faiss.normalize_L2(embedding)

            # Remove old entry if exists
            if record.id in self.id_to_idx:
                # FAISS doesn't support deletion, so we rebuild if needed
                # For now, just update metadata
                self.records[record.id] = record
            else:
                # Add new entry
                idx = self.index.ntotal
                self.index.add(embedding)
                self.id_to_idx[record.id] = idx
                self.idx_to_id[idx] = record.id
                self.records[record.id] = record

            inserted += 1

        # Save to disk if path provided
        if self.index_path:
            self._save()

        logger.info(f"Upserted {inserted} records to FAISS")
        return inserted

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query for similar vectors in FAISS index."""
        if self.index.ntotal == 0:
            return []

        # Normalize query vector
        query_vector = self.np.array([vector], dtype="float32")
        self.faiss.normalize_L2(query_vector)

        # Search FAISS index
        scores, indices = self.index.search(query_vector, min(top_k * 2, self.index.ntotal))

        # Apply filters and collect results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for padding
                continue

            record_id = self.idx_to_id.get(idx)
            if not record_id:
                continue

            record = self.records.get(record_id)
            if not record:
                continue

            # Apply filters
            if filters:
                if "type" in filters:
                    types = filters["type"] if isinstance(filters["type"], list) else [filters["type"]]
                    if record.type.value not in types:
                        continue

                if "framework" in filters:
                    if record.metadata.get("framework") != filters["framework"]:
                        continue

            results.append({"record": record, "score": float(score)})

            if len(results) >= top_k:
                break

        logger.info(f"Found {len(results)} similar records in FAISS")
        return results

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """Retrieve a specific record by ID."""
        return self.records.get(record_id)

    def delete(self, record_ids: List[str]) -> int:
        """Delete records by ID (marks as deleted, requires rebuild for actual removal)."""
        deleted = 0
        for record_id in record_ids:
            if record_id in self.records:
                del self.records[record_id]
                if record_id in self.id_to_idx:
                    idx = self.id_to_idx[record_id]
                    del self.id_to_idx[record_id]
                    del self.idx_to_id[idx]
                deleted += 1

        logger.info(f"Deleted {deleted} records from FAISS")
        return deleted

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records matching filters."""
        if not filters:
            return len(self.records)

        count = 0
        for record in self.records.values():
            if "type" in filters:
                types = filters["type"] if isinstance(filters["type"], list) else [filters["type"]]
                if record.type.value not in types:
                    continue

            if "framework" in filters:
                if record.metadata.get("framework") != filters["framework"]:
                    continue

            count += 1

        return count

    def _save(self):
        """Save FAISS index and metadata to disk."""
        import pickle

        if not self.index_path:
            return

        try:
            # Save FAISS index
            self.faiss.write_index(self.index, f"{self.index_path}.index")

            # Save metadata
            with open(f"{self.index_path}.metadata", "wb") as f:
                pickle.dump(
                    {
                        "records": self.records,
                        "id_to_idx": self.id_to_idx,
                        "idx_to_id": self.idx_to_id,
                    },
                    f,
                )

            logger.info(f"Saved FAISS index to {self.index_path}")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    def _load(self):
        """Load FAISS index and metadata from disk."""
        import pickle
        import os

        if not self.index_path or not os.path.exists(f"{self.index_path}.index"):
            return

        try:
            # Load FAISS index
            self.index = self.faiss.read_index(f"{self.index_path}.index")

            # Load metadata
            with open(f"{self.index_path}.metadata", "rb") as f:
                data = pickle.load(f)
                self.records = data["records"]
                self.id_to_idx = data["id_to_idx"]
                self.idx_to_id = data["idx_to_id"]

            logger.info(
                f"Loaded FAISS index with {self.index.ntotal} vectors from {self.index_path}"
            )
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")


def create_vector_store(
    store_type: str = "pgvector", **kwargs
) -> VectorStore:
    """
    Factory function to create vector stores.
    
    Args:
        store_type: Type of store ('pgvector', 'faiss')
        **kwargs: Store-specific configuration
        
    Returns:
        Configured VectorStore instance
        
    Example:
        >>> store = create_vector_store('pgvector', connection_string='postgresql://...', dimension=1536)
        >>> store.upsert(records)
    """
    stores = {
        "pgvector": PgVectorStore,
        "faiss": FAISSVectorStore,
    }

    if store_type not in stores:
        raise ValueError(
            f"Unknown store type: {store_type}. Available: {list(stores.keys())}"
        )

    return stores[store_type](**kwargs)
