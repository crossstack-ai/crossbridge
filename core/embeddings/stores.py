"""
Unified Embedding Stores

Consolidates storage backends from Memory system and Execution Intelligence.
"""

from typing import List, Optional, Dict, Any
from collections import defaultdict

from core.embeddings.interface import IEmbeddingStore, Embedding
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


class InMemoryStore(IEmbeddingStore):
    """
    In-memory embedding store (ephemeral).
    
    Used by Execution Intelligence for runtime analysis.
    Fast, no external dependencies, but lost on restart.
    """
    
    def __init__(self):
        self._embeddings: Dict[str, Embedding] = {}
        self._type_index: Dict[str, List[str]] = defaultdict(list)
        logger.info("Initialized InMemory store")
    
    def add(self, embedding: Embedding) -> None:
        """Add embedding to store"""
        self._embeddings[embedding.entity_id] = embedding
        self._type_index[embedding.entity_type].append(embedding.entity_id)
    
    def add_batch(self, embeddings: List[Embedding]) -> None:
        """Add multiple embeddings"""
        for emb in embeddings:
            self.add(emb)
    
    def get(self, entity_id: str) -> Optional[Embedding]:
        """Get embedding by ID"""
        return self._embeddings.get(entity_id)
    
    def find_similar(
        self,
        query: Embedding,
        top_k: int = 10,
        entity_type: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[tuple[Embedding, float]]:
        """Find similar embeddings using cosine similarity"""
        candidates = self._embeddings.values()
        
        # Filter by type if specified
        if entity_type:
            entity_ids = self._type_index.get(entity_type, [])
            candidates = [self._embeddings[eid] for eid in entity_ids]
        
        # Calculate similarities
        similarities = []
        for candidate in candidates:
            if candidate.entity_id == query.entity_id:
                continue  # Skip self
            
            try:
                sim = query.cosine_similarity(candidate)
                if sim >= min_similarity:
                    similarities.append((candidate, sim))
            except ValueError:
                # Dimension mismatch, skip
                continue
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def delete(self, entity_id: str) -> bool:
        """Delete embedding by ID"""
        if entity_id in self._embeddings:
            emb = self._embeddings[entity_id]
            del self._embeddings[entity_id]
            
            # Remove from type index
            if emb.entity_type in self._type_index:
                self._type_index[emb.entity_type] = [
                    eid for eid in self._type_index[emb.entity_type]
                    if eid != entity_id
                ]
            
            return True
        return False
    
    def clear(self) -> None:
        """Clear all embeddings"""
        self._embeddings.clear()
        self._type_index.clear()
    
    def count(self) -> int:
        """Get total number of embeddings"""
        return len(self._embeddings)
    
    def stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        by_type = {
            entity_type: len(ids)
            for entity_type, ids in self._type_index.items()
        }
        
        return {
            'store_type': 'in_memory',
            'total_embeddings': len(self._embeddings),
            'by_type': by_type,
            'unique_types': len(self._type_index)
        }


class PgVectorStore(IEmbeddingStore):
    """
    PostgreSQL with pgvector extension (persistent).
    
    Used by Memory system for long-term semantic search.
    Requires database setup but provides persistence and scalability.
    """
    
    def __init__(
        self,
        connection_string: str,
        table_name: str = "embeddings",
        dimension: int = 384
    ):
        self.connection_string = connection_string
        self.table_name = table_name
        self.dimension = dimension
        
        try:
            import psycopg2
        except ImportError:
            raise ImportError(
                "psycopg2 required for PgVector. Install: pip install psycopg2-binary"
            )
        
        self.conn = psycopg2.connect(connection_string)
        self._ensure_table()
        
        logger.info(f"Initialized PgVector store: {table_name} ({dimension} dims)")
    
    def _ensure_table(self):
        """Create table if it doesn't exist"""
        with self.conn.cursor() as cur:
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create table
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    vector vector({self.dimension}),
                    metadata JSONB,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create indexes
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_type 
                ON {self.table_name}(entity_type)
            """)
            
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_vector 
                ON {self.table_name} 
                USING ivfflat (vector vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            self.conn.commit()
    
    def add(self, embedding: Embedding) -> None:
        """Add embedding to database"""
        import json
        
        with self.conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {self.table_name} 
                (entity_id, entity_type, text, vector, metadata, model)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (entity_id) DO UPDATE SET
                    entity_type = EXCLUDED.entity_type,
                    text = EXCLUDED.text,
                    vector = EXCLUDED.vector,
                    metadata = EXCLUDED.metadata,
                    model = EXCLUDED.model
            """, (
                embedding.entity_id,
                embedding.entity_type,
                embedding.text,
                embedding.vector,
                json.dumps(embedding.metadata),
                embedding.model
            ))
            self.conn.commit()
    
    def add_batch(self, embeddings: List[Embedding]) -> None:
        """Add multiple embeddings efficiently"""
        import json
        
        with self.conn.cursor() as cur:
            values = [
                (
                    emb.entity_id,
                    emb.entity_type,
                    emb.text,
                    emb.vector,
                    json.dumps(emb.metadata),
                    emb.model
                )
                for emb in embeddings
            ]
            
            from psycopg2.extras import execute_batch
            execute_batch(cur, f"""
                INSERT INTO {self.table_name}
                (entity_id, entity_type, text, vector, metadata, model)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (entity_id) DO UPDATE SET
                    entity_type = EXCLUDED.entity_type,
                    text = EXCLUDED.text,
                    vector = EXCLUDED.vector,
                    metadata = EXCLUDED.metadata,
                    model = EXCLUDED.model
            """, values)
            self.conn.commit()
    
    def get(self, entity_id: str) -> Optional[Embedding]:
        """Get embedding by ID"""
        import json
        
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT entity_id, entity_type, text, vector::text, metadata, model
                FROM {self.table_name}
                WHERE entity_id = %s
            """, (entity_id,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            vector_str = row[3].strip('[]')
            vector = [float(x) for x in vector_str.split(',')]
            
            return Embedding(
                entity_id=row[0],
                entity_type=row[1],
                text=row[2],
                vector=vector,
                metadata=json.loads(row[4]) if row[4] else {},
                model=row[5] or "unknown"
            )
    
    def find_similar(
        self,
        query: Embedding,
        top_k: int = 10,
        entity_type: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[tuple[Embedding, float]]:
        """Find similar embeddings using vector similarity search"""
        import json
        
        type_filter = ""
        params = [query.vector, top_k]
        
        if entity_type:
            type_filter = "AND entity_type = %s"
            params.append(entity_type)
        
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT 
                    entity_id, entity_type, text, vector::text, metadata, model,
                    1 - (vector <=> %s::vector) as similarity
                FROM {self.table_name}
                WHERE entity_id != %s {type_filter}
                    AND (1 - (vector <=> %s::vector)) >= %s
                ORDER BY vector <=> %s::vector
                LIMIT %s
            """, [
                query.vector,
                query.entity_id,
                *([entity_type] if entity_type else []),
                query.vector,
                min_similarity,
                query.vector,
                top_k
            ])
            
            results = []
            for row in cur.fetchall():
                vector_str = row[3].strip('[]')
                vector = [float(x) for x in vector_str.split(',')]
                
                emb = Embedding(
                    entity_id=row[0],
                    entity_type=row[1],
                    text=row[2],
                    vector=vector,
                    metadata=json.loads(row[4]) if row[4] else {},
                    model=row[5] or "unknown"
                )
                similarity = float(row[6])
                results.append((emb, similarity))
            
            return results
    
    def delete(self, entity_id: str) -> bool:
        """Delete embedding by ID"""
        with self.conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self.table_name} WHERE entity_id = %s", (entity_id,))
            self.conn.commit()
            return cur.rowcount > 0
    
    def clear(self) -> None:
        """Clear all embeddings"""
        with self.conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {self.table_name}")
            self.conn.commit()
    
    def count(self) -> int:
        """Get total number of embeddings"""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cur.fetchone()[0]
    
    def stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT entity_type, COUNT(*) 
                FROM {self.table_name}
                GROUP BY entity_type
            """)
            by_type = dict(cur.fetchall())
            
            return {
                'store_type': 'pgvector',
                'table_name': self.table_name,
                'dimension': self.dimension,
                'total_embeddings': self.count(),
                'by_type': by_type,
                'unique_types': len(by_type)
            }


def create_store(
    store_type: str = "memory",
    connection_string: Optional[str] = None,
    dimension: int = 384,
    **kwargs
) -> IEmbeddingStore:
    """
    Factory function to create embedding store.
    
    Args:
        store_type: Type of store (memory, pgvector)
        connection_string: Database connection (for pgvector)
        dimension: Embedding dimension
        **kwargs: Additional store-specific arguments
        
    Returns:
        IEmbeddingStore instance
    """
    store_type = store_type.lower()
    
    if store_type == "memory":
        return InMemoryStore()
    
    elif store_type == "pgvector":
        if not connection_string:
            raise ValueError("connection_string required for pgvector store")
        return PgVectorStore(connection_string, dimension=dimension, **kwargs)
    
    else:
        raise ValueError(
            f"Unknown store type: {store_type}. "
            f"Supported: memory, pgvector"
        )
