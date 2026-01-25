"""
Semantic search engine for CrossBridge Memory system.

This module provides natural language search over test-related entities,
enabling AI-powered test discovery and intelligent recommendations.
"""

from typing import Any, Dict, List, Optional

from core.logging import get_logger, LogCategory
from core.memory.embedding_provider import EmbeddingProvider
from core.memory.models import MemoryRecord, MemoryType, SearchResult
from core.memory.vector_store import VectorStore

logger = get_logger(__name__, category=LogCategory.AI)


class SemanticSearchEngine:
    """
    Semantic search engine for test-related knowledge.
    
    This enables natural language queries like:
    - "Tests related to login failures"
    - "Scenarios covering payment edge cases"
    - "Flaky tests touching authentication"
    - "Tests similar to this one"
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        """
        Initialize semantic search engine.
        
        Args:
            embedding_provider: Provider for generating query embeddings
            vector_store: Storage backend containing memory records
        """
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

        logger.info("Initialized SemanticSearchEngine")

    def search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        framework: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Perform semantic search over memory records.
        
        Args:
            query: Natural language search query
            entity_types: Filter by entity types (test, scenario, step, etc.)
            framework: Filter by framework (pytest, cypress, etc.)
            top_k: Maximum number of results to return
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of SearchResult objects ordered by relevance
            
        Example:
            >>> engine.search("tests covering login timeout", entity_types=["test"], top_k=5)
        """
        if not query:
            logger.warning("Empty search query provided")
            return []

        try:
            # Generate embedding for query
            query_vector = self.embedding_provider.embed([query])[0]

            # Build filters
            filters = {}
            if entity_types:
                filters["type"] = entity_types
            if framework:
                filters["framework"] = framework

            # Query vector store
            raw_results = self.vector_store.query(
                vector=query_vector,
                top_k=top_k,
                filters=filters if filters else None,
            )

            # Convert to SearchResult objects
            results = []
            for rank, item in enumerate(raw_results, start=1):
                score = item["score"]
                if score >= min_score:
                    results.append(
                        SearchResult(
                            record=item["record"],
                            score=score,
                            rank=rank,
                        )
                    )

            logger.info(
                f"Search returned {len(results)} results for query: '{query[:50]}...'"
            )
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def find_similar(
        self,
        record_id: str,
        entity_types: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        Find records similar to a given record.
        
        Useful for:
        - Detecting duplicate tests
        - Finding redundant coverage
        - Suggesting related tests
        
        Args:
            record_id: ID of the reference record
            entity_types: Filter by entity types
            top_k: Maximum number of results (excluding the reference record)
            
        Returns:
            List of similar SearchResult objects
            
        Example:
            >>> engine.find_similar("test_login_valid", top_k=5)
        """
        # Retrieve the reference record
        record = self.vector_store.get(record_id)
        if not record or not record.embedding:
            logger.warning(f"Record {record_id} not found or has no embedding")
            return []

        try:
            # Build filters
            filters = {}
            if entity_types:
                filters["type"] = entity_types

            # Query using the record's embedding
            raw_results = self.vector_store.query(
                vector=record.embedding,
                top_k=top_k + 1,  # +1 to exclude self
                filters=filters if filters else None,
            )

            # Convert to SearchResult objects (excluding self)
            results = []
            rank = 0
            for item in raw_results:
                if item["record"].id == record_id:
                    continue  # Skip the reference record itself

                rank += 1
                results.append(
                    SearchResult(
                        record=item["record"],
                        score=item["score"],
                        rank=rank,
                    )
                )

                if rank >= top_k:
                    break

            logger.info(f"Found {len(results)} similar records to {record_id}")
            return results

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def search_by_example(
        self,
        example_text: str,
        entity_types: Optional[List[str]] = None,
        framework: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Search using example text instead of a natural language query.
        
        Useful for:
        - Finding tests matching a code snippet
        - Finding scenarios matching a description
        - Finding failures similar to an error message
        
        Args:
            example_text: Example text to search for
            entity_types: Filter by entity types
            framework: Filter by framework
            top_k: Maximum number of results
            
        Returns:
            List of SearchResult objects
            
        Example:
            >>> engine.search_by_example("TimeoutException: element not found", entity_types=["failure"])
        """
        return self.search(
            query=example_text,
            entity_types=entity_types,
            framework=framework,
            top_k=top_k,
        )

    def multi_query_search(
        self,
        queries: List[str],
        entity_types: Optional[List[str]] = None,
        framework: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Search using multiple queries and combine results.
        
        This performs multiple searches and aggregates results by
        averaging similarity scores.
        
        Args:
            queries: List of search queries
            entity_types: Filter by entity types
            framework: Filter by framework
            top_k: Maximum number of results
            
        Returns:
            List of SearchResult objects with aggregated scores
            
        Example:
            >>> engine.multi_query_search(
            ...     ["login tests", "authentication scenarios"],
            ...     entity_types=["test", "scenario"]
            ... )
        """
        if not queries:
            return []

        # Perform searches for all queries
        all_results: Dict[str, List[float]] = {}  # record_id -> [scores]

        for query in queries:
            results = self.search(
                query=query,
                entity_types=entity_types,
                framework=framework,
                top_k=top_k * 2,  # Get more results for aggregation
            )

            for result in results:
                if result.record.id not in all_results:
                    all_results[result.record.id] = []
                all_results[result.record.id].append(result.score)

        # Aggregate scores (average)
        aggregated = []
        for record_id, scores in all_results.items():
            record = self.vector_store.get(record_id)
            if record:
                avg_score = sum(scores) / len(scores)
                aggregated.append((record, avg_score))

        # Sort by aggregated score
        aggregated.sort(key=lambda x: x[1], reverse=True)

        # Convert to SearchResult objects
        results = [
            SearchResult(record=record, score=score, rank=rank)
            for rank, (record, score) in enumerate(aggregated[:top_k], start=1)
        ]

        logger.info(
            f"Multi-query search returned {len(results)} results from {len(queries)} queries"
        )
        return results

    def search_with_context(
        self,
        query: str,
        context: Dict[str, Any],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Search with additional context for better results.
        
        Context can include:
        - Current file being edited
        - Recent test failures
        - Code changes in current branch
        - Related feature/story information
        
        Args:
            query: Natural language search query
            context: Additional context dictionary
            top_k: Maximum number of results
            
        Returns:
            List of SearchResult objects
            
        Example:
            >>> engine.search_with_context(
            ...     "timeout tests",
            ...     context={"file": "login_tests.py", "framework": "pytest"}
            ... )
        """
        # Enhance query with context
        enhanced_query = query

        if file_name := context.get("file"):
            enhanced_query += f" in {file_name}"

        if feature := context.get("feature"):
            enhanced_query += f" related to {feature}"

        # Extract filters from context
        entity_types = context.get("entity_types")
        framework = context.get("framework")

        return self.search(
            query=enhanced_query,
            entity_types=entity_types,
            framework=framework,
            top_k=top_k,
        )

    def get_recommendations(
        self,
        record_id: str,
        recommendation_type: str = "similar",
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        Get recommendations based on a record.
        
        Recommendation types:
        - "similar": Find similar tests/scenarios
        - "complement": Find complementary tests (different but related)
        - "duplicate": Find potential duplicates (very similar)
        
        Args:
            record_id: ID of the reference record
            recommendation_type: Type of recommendation
            top_k: Maximum number of recommendations
            
        Returns:
            List of recommended SearchResult objects
        """
        if recommendation_type == "duplicate":
            # Very high similarity threshold for duplicates
            results = self.find_similar(record_id, top_k=top_k)
            return [r for r in results if r.score > 0.9]

        elif recommendation_type == "similar":
            # Standard similarity search
            return self.find_similar(record_id, top_k=top_k)

        elif recommendation_type == "complement":
            # Find related but different tests (medium similarity)
            results = self.find_similar(record_id, top_k=top_k * 2)
            return [r for r in results if 0.5 < r.score < 0.8][:top_k]

        else:
            logger.warning(f"Unknown recommendation type: {recommendation_type}")
            return []

    def explain_search(
        self,
        query: str,
        result: SearchResult,
    ) -> str:
        """
        Explain why a result was returned for a query.
        
        This generates a human-readable explanation of the match.
        
        Args:
            query: The search query
            result: A search result
            
        Returns:
            Explanation string
        """
        explanation_parts = [
            f"This {result.record.type.value} matched your query with {result.score:.2%} similarity.",
        ]

        # Extract key terms from query and result
        query_lower = query.lower()
        text_lower = result.record.text.lower()

        # Find common words (simple approach)
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        common_words = query_words & text_words

        if common_words:
            explanation_parts.append(
                f"Common terms: {', '.join(sorted(common_words)[:5])}"
            )

        # Add metadata info
        if framework := result.record.metadata.get("framework"):
            explanation_parts.append(f"Framework: {framework}")

        if tags := result.record.metadata.get("tags"):
            explanation_parts.append(f"Tags: {', '.join(tags[:3])}")

        return " ".join(explanation_parts)
