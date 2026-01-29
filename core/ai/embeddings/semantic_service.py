"""
Semantic Search Service

High-level service for semantic similarity operations.
Coordinates embedding generation, vector storage, and search.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from core.logging import get_logger, LogCategory
from core.config.loader import ConfigLoader
from core.ai.embeddings.text_builder import EmbeddingTextBuilder, EmbeddableEntity
from core.ai.embeddings.provider import EmbeddingProvider, create_embedding_provider
from core.ai.embeddings.vector_store import VectorStore, SimilarityResult
from core.ai.embeddings.pgvector_store import PgVectorStore
from cli.errors import CrossBridgeError

logger = get_logger(__name__, category=LogCategory.AI)


# Embedding version - increment when text builder changes
EMBEDDING_VERSION = "v1-text-only"


class SemanticSearchError(CrossBridgeError):
    """Semantic search operation error"""
    pass


class SemanticSearchService:
    """
    Semantic search service
    
    Provides high-level APIs for:
    - Indexing tests/scenarios/failures
    - Searching by text query
    - Finding similar entities
    - Reindexing with new versions
    
    Configuration loaded from crossbridge.yml (runtime.semantic_search)
    """
    
    def __init__(
        self,
        provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
        text_builder: Optional[EmbeddingTextBuilder] = None,
        config_loader: Optional[ConfigLoader] = None
    ):
        """
        Initialize semantic search service
        
        Args:
            provider: Embedding provider (auto-created from config if None)
            vector_store: Vector store (auto-created from config if None)
            text_builder: Text builder (default if None)
            config_loader: Config loader (for testing)
        """
        # Load configuration
        if config_loader is None:
            config_loader = ConfigLoader()
        
        self.config = config_loader.load()
        self.semantic_config = self.config.semantic_search
        
        # Get effective config (migration mode overrides)
        self.effective_config = self.semantic_config.get_effective_config(self.config.mode)
        
        # Initialize components
        self.text_builder = text_builder or EmbeddingTextBuilder()
        
        # Create provider from config if not provided
        if provider is None:
            provider_type = self.semantic_config.provider_type
            provider_config = self._get_provider_config()
            self.provider = create_embedding_provider(provider_type, **provider_config)
        else:
            self.provider = provider
        
        # Create vector store from config if not provided
        if vector_store is None:
            self.vector_store = PgVectorStore(
                dimensions=self.provider.dimensions(),
                config_loader=config_loader
            )
        else:
            self.vector_store = vector_store
        
        self.version = EMBEDDING_VERSION
        
        mode_info = f" (migration mode)" if self.config.mode == "migration" else ""
        logger.info(
            f"SemanticSearchService initialized{mode_info}",
            provider=self.provider.model_name(),
            dimensions=self.provider.dimensions(),
            version=self.version,
            mode=self.config.mode
        )
    
    def _get_provider_config(self) -> Dict[str, Any]:
        """Get provider configuration from config"""
        config = {}
        
        provider_type = self.semantic_config.provider_type
        
        if provider_type == 'openai':
            config['api_key'] = self.semantic_config.openai_api_key
            config['model'] = self.semantic_config.openai_model
            config['timeout'] = self.semantic_config.api_timeout
        elif provider_type == 'anthropic':
            config['api_key'] = self.semantic_config.anthropic_api_key
            config['model'] = self.semantic_config.anthropic_model
            config['timeout'] = self.semantic_config.api_timeout
        elif provider_type == 'local':
            config['model'] = self.semantic_config.local_model
        
        return config
    
    def index_entity(
        self,
        entity_id: str,
        entity_type: str,
        **entity_data
    ) -> str:
        """
        Index a single entity
        
        Args:
            entity_id: Unique entity identifier
            entity_type: Entity type (test, scenario, failure)
            **entity_data: Entity-specific data (test_name, steps, etc.)
        
        Returns:
            Entity ID
        
        Raises:
            SemanticSearchError: If indexing fails
        
        Example:
            service.index_entity(
                entity_id="test_login",
                entity_type="test",
                test_name="test_user_login",
                description="Test login functionality",
                steps=["Navigate to login", "Enter credentials"],
                framework="pytest"
            )
        """
        try:
            # Build entity
            entity = self.text_builder.build_entity(
                entity_id=entity_id,
                entity_type=entity_type,
                **entity_data
            )
            
            # Check token limit
            if self.semantic_config.max_tokens:
                entity.text = self.text_builder.truncate_if_needed(
                    entity.text,
                    max_tokens=self.semantic_config.max_tokens
                )
            
            # Generate embedding
            embedding = self.provider.embed(entity.text)
            
            # Store in vector DB
            self.vector_store.upsert(
                entity=entity,
                embedding=embedding,
                model=self.provider.model_name(),
                version=self.version
            )
            
            logger.debug(
                f"Indexed entity",
                entity_id=entity_id,
                entity_type=entity_type,
                text_length=len(entity.text)
            )
            
            return entity_id
            
        except Exception as e:
            logger.error(f"Failed to index entity", entity_id=entity_id, error=str(e))
            raise SemanticSearchError(f"Indexing failed for {entity_id}: {e}")
    
    def index_batch(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Index multiple entities in batch
        
        Args:
            entities: List of entity dictionaries with id, type, and data
        
        Returns:
            List of indexed entity IDs
        
        Example:
            entities = [
                {"id": "test_1", "type": "test", "test_name": "test_login", ...},
                {"id": "test_2", "type": "test", "test_name": "test_logout", ...}
            ]
            service.index_batch(entities)
        """
        if not entities:
            return []
        
        try:
            # Build all entities
            embeddable_entities = []
            for entity_dict in entities:
                entity_id = entity_dict.pop('id')
                entity_type = entity_dict.pop('type')
                
                entity = self.text_builder.build_entity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    **entity_dict
                )
                
                if self.semantic_config.max_tokens:
                    entity.text = self.text_builder.truncate_if_needed(
                        entity.text,
                        max_tokens=self.semantic_config.max_tokens
                    )
                
                embeddable_entities.append(entity)
            
            # Generate embeddings in batch
            texts = [e.text for e in embeddable_entities]
            embeddings = self.provider.embed_batch(texts)
            
            # Store in vector DB (batch)
            self.vector_store.upsert_batch(
                entities=embeddable_entities,
                embeddings=embeddings,
                model=self.provider.model_name(),
                version=self.version
            )
            
            indexed_ids = [e.id for e in embeddable_entities]
            logger.info(f"Indexed batch", count=len(indexed_ids))
            
            return indexed_ids
            
        except Exception as e:
            logger.error(f"Batch indexing failed", count=len(entities), error=str(e))
            raise SemanticSearchError(f"Batch indexing failed: {e}")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None
    ) -> List[SimilarityResult]:
        """
        Search for similar entities by text query
        
        Args:
            query: Search query text
            top_k: Number of results to return
            entity_type: Filter by entity type
            filters: Additional metadata filters
            min_score: Minimum similarity score (uses config default if None)
        
        Returns:
            List of similarity results, sorted by score
        
        Example:
            results = service.search(
                query="login timeout issue",
                top_k=5,
                entity_type="failure"
            )
            
            for result in results:
                print(f"[{result.score:.2f}] {result.id}: {result.text[:100]}")
        """
        if not query or not query.strip():
            raise SemanticSearchError("Search query cannot be empty")
        
        try:
            # Generate query embedding
            query_embedding = self.provider.embed(query)
            
            # Search vector store
            min_score = min_score or self.semantic_config.min_similarity_score
            results = self.vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                entity_type=entity_type,
                filters=filters,
                min_score=min_score
            )
            
            logger.debug(
                f"Search completed",
                query=query[:50],
                results=len(results),
                entity_type=entity_type
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed", query=query[:50], error=str(e))
            raise SemanticSearchError(f"Search failed: {e}")
    
    def find_similar(
        self,
        entity_id: str,
        top_k: int = 10,
        entity_type: Optional[str] = None,
        min_score: Optional[float] = None
    ) -> List[SimilarityResult]:
        """
        Find similar entities to a given entity
        
        Args:
            entity_id: Entity ID to find similar entities for
            top_k: Number of results to return
            entity_type: Filter by entity type
            min_score: Minimum similarity score
        
        Returns:
            List of similarity results (excluding the query entity itself)
        
        Example:
            similar = service.find_similar("test_login_timeout", top_k=5)
        """
        try:
            # Get entity from store
            entity = self.vector_store.get(entity_id)
            if not entity:
                raise SemanticSearchError(
                    f"Entity not found: {entity_id}",
                    suggestion="Use 'crossbridge semantic list' to see available entities"
                )
            
            # Search by entity text
            results = self.search(
                query=entity.text,
                top_k=top_k + 1,  # +1 to exclude self
                entity_type=entity_type,
                min_score=min_score
            )
            
            # Filter out the entity itself
            similar = [r for r in results if r.id != entity_id][:top_k]
            
            logger.debug(f"Found similar entities", entity_id=entity_id, count=len(similar))
            
            return similar
            
        except Exception as e:
            logger.error(f"Find similar failed", entity_id=entity_id, error=str(e))
            if isinstance(e, SemanticSearchError):
                raise
            raise SemanticSearchError(f"Find similar failed: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get semantic search statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            total = self.vector_store.count()
            by_type = {
                'test': self.vector_store.count(entity_type='test'),
                'scenario': self.vector_store.count(entity_type='scenario'),
                'failure': self.vector_store.count(entity_type='failure')
            }
            versions = self.vector_store.list_versions()
            
            return {
                'total_entities': total,
                'by_entity_type': by_type,
                'embedding_versions': versions,
                'current_version': self.version,
                'provider': self.provider.model_name(),
                'dimensions': self.provider.dimensions()
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics", error=str(e))
            raise SemanticSearchError(f"Statistics failed: {e}")
    
    def reindex(
        self,
        entity_type: Optional[str] = None,
        new_version: Optional[str] = None
    ) -> int:
        """
        Reindex entities with new version
        
        Useful when:
        - Upgrading embedding model
        - Improving text builder logic
        - Changing dimensions
        
        Args:
            entity_type: Reindex specific entity type only
            new_version: New version string (defaults to EMBEDDING_VERSION)
        
        Returns:
            Number of entities reindexed
        
        Note: This requires access to original entity data
        """
        logger.warning(
            "Reindex requires original entity data - not yet implemented",
            entity_type=entity_type
        )
        raise NotImplementedError(
            "Reindexing requires integration with test discovery. "
            "Use CLI commands to index from source."
        )
