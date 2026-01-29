"""
PostgreSQL Vector Store (pgvector)

Production-ready vector store using PostgreSQL with pgvector extension.

Advantages:
- Single database (no separate vector DB)
- ACID transactions
- Mature ops tooling
- Good enough until 5-10M embeddings
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.logging import get_logger, LogCategory
from core.config.loader import ConfigLoader
from core.ai.embeddings.vector_store import VectorStore, SimilarityResult
from core.ai.embeddings.text_builder import EmbeddableEntity
from cli.errors import CrossBridgeError

logger = get_logger(__name__, category=LogCategory.AI)


class VectorStoreError(CrossBridgeError):
    """Vector store operation error"""
    pass


class PgVectorStore(VectorStore):
    """
    PostgreSQL vector store implementation
    
    Uses pgvector extension for similarity search.
    
    Table schema:
        CREATE TABLE semantic_embeddings (
            id TEXT PRIMARY KEY,
            entity_type TEXT,
            embedding VECTOR(dimensions),
            embedding_text TEXT,
            model TEXT,
            version TEXT,
            metadata JSONB,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
        
        CREATE INDEX ON semantic_embeddings USING ivfflat (embedding vector_cosine_ops);
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        table_name: str = "semantic_embeddings",
        dimensions: int = 1536,
        config_loader: Optional[ConfigLoader] = None
    ):
        """
        Initialize pgvector store
        
        Args:
            connection_string: PostgreSQL connection string (overrides config)
            table_name: Table name for embeddings
            dimensions: Embedding vector dimensions
            config_loader: Optional config loader
        """
        # Load config
        if config_loader is None:
            config_loader = ConfigLoader()
        config = config_loader.load()
        
        self.connection_string = connection_string or config.database.connection_string
        self.table_name = table_name
        self.dimensions = dimensions
        
        # Lazy import
        try:
            import psycopg2
            from psycopg2.extras import Json, RealDictCursor
            self.psycopg2 = psycopg2
            self.Json = Json
            self.RealDictCursor = RealDictCursor
        except ImportError:
            raise VectorStoreError(
                "psycopg2 not installed",
                suggestion="Install with: pip install psycopg2-binary"
            )
        
        # Test connection and ensure table exists
        self._ensure_table()
        
        logger.info(
            "Initialized pgvector store",
            table=self.table_name,
            dimensions=self.dimensions
        )
    
    def _get_connection(self):
        """Get database connection"""
        try:
            return self.psycopg2.connect(self.connection_string)
        except Exception as e:
            logger.error(f"Failed to connect to database", error=str(e))
            raise VectorStoreError(f"Database connection failed: {e}")
    
    def _ensure_table(self) -> None:
        """Ensure table and extension exist"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Create table if not exists
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        entity_type TEXT NOT NULL,
                        embedding VECTOR({self.dimensions}),
                        embedding_text TEXT NOT NULL,
                        model TEXT NOT NULL,
                        version TEXT NOT NULL,
                        metadata JSONB DEFAULT '{{}}'::jsonb,
                        created_at TIMESTAMP DEFAULT now(),
                        updated_at TIMESTAMP DEFAULT now()
                    );
                """)
                
                # Create index for similarity search
                # Note: ivfflat index is created manually after data load for better performance
                # For now, use brute force (exact) search which works for < 1M vectors
                
                conn.commit()
                logger.debug(f"Ensured table exists: {self.table_name}")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to ensure table", error=str(e))
            raise VectorStoreError(f"Table creation failed: {e}")
        finally:
            conn.close()
    
    def upsert(
        self,
        entity: EmbeddableEntity,
        embedding: List[float],
        model: str,
        version: str
    ) -> None:
        """Insert or update entity embedding"""
        if len(embedding) != self.dimensions:
            raise VectorStoreError(
                f"Embedding dimension mismatch: expected {self.dimensions}, got {len(embedding)}"
            )
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Convert embedding to string format for pgvector
                embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
                
                cur.execute(f"""
                    INSERT INTO {self.table_name} 
                        (id, entity_type, embedding, embedding_text, model, version, metadata, created_at, updated_at)
                    VALUES 
                        (%s, %s, %s::vector, %s, %s, %s, %s, now(), now())
                    ON CONFLICT (id) 
                    DO UPDATE SET
                        entity_type = EXCLUDED.entity_type,
                        embedding = EXCLUDED.embedding,
                        embedding_text = EXCLUDED.embedding_text,
                        model = EXCLUDED.model,
                        version = EXCLUDED.version,
                        metadata = EXCLUDED.metadata,
                        updated_at = now();
                """, (
                    entity.id,
                    entity.entity_type,
                    embedding_str,
                    entity.text,
                    model,
                    version,
                    self.Json(entity.metadata)
                ))
                
                conn.commit()
                logger.debug(f"Upserted entity", entity_id=entity.id, entity_type=entity.entity_type)
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to upsert entity", entity_id=entity.id, error=str(e))
            raise VectorStoreError(f"Upsert failed: {e}")
        finally:
            conn.close()
    
    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[SimilarityResult]:
        """Find similar entities using cosine similarity"""
        if len(query_embedding) != self.dimensions:
            raise VectorStoreError(
                f"Query embedding dimension mismatch: expected {self.dimensions}, got {len(query_embedding)}"
            )
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=self.RealDictCursor) as cur:
                # Convert query embedding to string
                query_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
                
                # Build WHERE clause
                where_clauses = []
                params = [query_str, top_k]
                
                if entity_type:
                    where_clauses.append("entity_type = %s")
                    params.append(entity_type)
                
                if filters:
                    for key, value in filters.items():
                        where_clauses.append(f"metadata->>%s = %s")
                        params.extend([key, str(value)])
                
                where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""
                
                # Cosine similarity: 1 - cosine_distance
                # <-> is cosine distance operator
                query = f"""
                    SELECT 
                        id,
                        entity_type,
                        embedding_text,
                        metadata,
                        model,
                        version,
                        1 - (embedding <-> %s::vector) AS score
                    FROM {self.table_name}
                    WHERE 1=1 {where_sql}
                    ORDER BY embedding <-> %s::vector
                    LIMIT %s;
                """
                
                # Adjust params order for query
                params_ordered = [query_str] + params[2:] + [query_str, top_k]
                
                cur.execute(query, params_ordered)
                rows = cur.fetchall()
                
                # Convert to SimilarityResult objects
                results = []
                for row in rows:
                    score = float(row['score'])
                    if score >= min_score:
                        results.append(SimilarityResult(
                            id=row['id'],
                            entity_type=row['entity_type'],
                            score=score,
                            text=row['embedding_text'],
                            metadata=row['metadata'] or {}
                        ))
                
                logger.debug(
                    f"Similarity search completed",
                    results=len(results),
                    entity_type=entity_type
                )
                
                return results
                
        except Exception as e:
            logger.error(f"Similarity search failed", error=str(e))
            raise VectorStoreError(f"Similarity search failed: {e}")
        finally:
            conn.close()
    
    def get(self, entity_id: str) -> Optional[SimilarityResult]:
        """Retrieve entity by ID"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=self.RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT id, entity_type, embedding_text, metadata
                    FROM {self.table_name}
                    WHERE id = %s;
                """, (entity_id,))
                
                row = cur.fetchone()
                if row:
                    return SimilarityResult(
                        id=row['id'],
                        entity_type=row['entity_type'],
                        score=1.0,  # Perfect match
                        text=row['embedding_text'],
                        metadata=row['metadata'] or {}
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get entity", entity_id=entity_id, error=str(e))
            raise VectorStoreError(f"Get failed: {e}")
        finally:
            conn.close()
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    DELETE FROM {self.table_name}
                    WHERE id = %s;
                """, (entity_id,))
                
                deleted = cur.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.debug(f"Deleted entity", entity_id=entity_id)
                
                return deleted
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete entity", entity_id=entity_id, error=str(e))
            raise VectorStoreError(f"Delete failed: {e}")
        finally:
            conn.close()
    
    def count(
        self,
        entity_type: Optional[str] = None,
        version: Optional[str] = None
    ) -> int:
        """Count entities in store"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                where_clauses = []
                params = []
                
                if entity_type:
                    where_clauses.append("entity_type = %s")
                    params.append(entity_type)
                
                if version:
                    where_clauses.append("version = %s")
                    params.append(version)
                
                where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
                
                cur.execute(f"""
                    SELECT COUNT(*) as count
                    FROM {self.table_name}
                    {where_sql};
                """, params)
                
                row = cur.fetchone()
                return row[0] if row else 0
                
        except Exception as e:
            logger.error(f"Failed to count entities", error=str(e))
            raise VectorStoreError(f"Count failed: {e}")
        finally:
            conn.close()
    
    def list_versions(self) -> List[str]:
        """List all embedding versions"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT DISTINCT version
                    FROM {self.table_name}
                    ORDER BY version;
                """)
                
                rows = cur.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list versions", error=str(e))
            raise VectorStoreError(f"List versions failed: {e}")
        finally:
            conn.close()
    
    def upsert_batch(
        self,
        entities: List[EmbeddableEntity],
        embeddings: List[List[float]],
        model: str,
        version: str
    ) -> None:
        """Batch upsert (optimized)"""
        if len(entities) != len(embeddings):
            raise ValueError("entities and embeddings must have same length")
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Use COPY or batch INSERT for better performance
                for entity, embedding in zip(entities, embeddings):
                    if len(embedding) != self.dimensions:
                        logger.warning(
                            f"Skipping entity with wrong dimensions",
                            entity_id=entity.id,
                            expected=self.dimensions,
                            got=len(embedding)
                        )
                        continue
                    
                    embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
                    
                    cur.execute(f"""
                        INSERT INTO {self.table_name} 
                            (id, entity_type, embedding, embedding_text, model, version, metadata, created_at, updated_at)
                        VALUES 
                            (%s, %s, %s::vector, %s, %s, %s, %s, now(), now())
                        ON CONFLICT (id) 
                        DO UPDATE SET
                            entity_type = EXCLUDED.entity_type,
                            embedding = EXCLUDED.embedding,
                            embedding_text = EXCLUDED.embedding_text,
                            model = EXCLUDED.model,
                            version = EXCLUDED.version,
                            metadata = EXCLUDED.metadata,
                            updated_at = now();
                    """, (
                        entity.id,
                        entity.entity_type,
                        embedding_str,
                        entity.text,
                        model,
                        version,
                        self.Json(entity.metadata)
                    ))
                
                conn.commit()
                logger.info(f"Batch upserted {len(entities)} entities")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Batch upsert failed", error=str(e))
            raise VectorStoreError(f"Batch upsert failed: {e}")
        finally:
            conn.close()
    
    def create_index(self, lists: int = 100) -> None:
        """
        Create IVFFlat index for faster similarity search
        
        Note: Only create after inserting data. Index creation is expensive.
        
        Args:
            lists: Number of inverted lists (rule of thumb: sqrt(rows))
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                index_name = f"{self.table_name}_embedding_idx"
                
                logger.info(f"Creating IVFFlat index (this may take a while)...")
                
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {self.table_name}
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = {lists});
                """)
                
                conn.commit()
                logger.info(f"IVFFlat index created: {index_name}")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Index creation failed", error=str(e))
            raise VectorStoreError(f"Index creation failed: {e}")
        finally:
            conn.close()
