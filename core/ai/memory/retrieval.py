"""
Context Retrieval System.

Retrieves relevant context (test history, failures, patterns) for AI tasks.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

from core.ai.memory.embeddings import EmbeddingEngine
from core.ai.memory.vector_store import VectorStore, SearchResult


@dataclass
class RetrievalConfig:
    """Configuration for context retrieval."""
    
    max_results: int = 10
    similarity_threshold: float = 0.7
    include_metadata: bool = True
    deduplicate: bool = True
    boost_recent: bool = True
    recency_weight: float = 0.2


class ContextRetriever:
    """
    Retrieve relevant context for AI tasks.
    
    Uses semantic search to find:
    - Similar test failures
    - Related test cases
    - Historical patterns
    - Code examples
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        config: Optional[RetrievalConfig] = None,
    ):
        """
        Initialize context retriever.
        
        Args:
            vector_store: Vector store for embeddings
            config: Retrieval configuration
        """
        self.store = vector_store or VectorStore()
        self.config = config or RetrievalConfig()
    
    def index_test_failures(
        self,
        failures: List[Dict[str, Any]],
    ):
        """
        Index test failures for future retrieval.
        
        Args:
            failures: List of test failure records
        """
        for failure in failures:
            content = self._format_failure(failure)
            metadata = {
                "type": "test_failure",
                "test_name": failure.get("test_name"),
                "timestamp": failure.get("timestamp"),
                "error_type": failure.get("error_type"),
            }
            
            self.store.add(content, metadata)
    
    def index_test_cases(
        self,
        test_cases: List[Dict[str, Any]],
    ):
        """
        Index test cases for similarity search.
        
        Args:
            test_cases: List of test case definitions
        """
        for test in test_cases:
            content = self._format_test_case(test)
            metadata = {
                "type": "test_case",
                "test_name": test.get("name"),
                "framework": test.get("framework"),
                "tags": test.get("tags", []),
            }
            
            self.store.add(content, metadata)
    
    def index_code_examples(
        self,
        examples: List[Dict[str, Any]],
    ):
        """
        Index code examples for reference.
        
        Args:
            examples: List of code examples
        """
        for example in examples:
            content = example.get("code", "")
            metadata = {
                "type": "code_example",
                "language": example.get("language"),
                "category": example.get("category"),
                "description": example.get("description"),
            }
            
            self.store.add(content, metadata)
    
    def retrieve_similar_failures(
        self,
        failure_description: str,
        max_results: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Retrieve similar test failures.
        
        Args:
            failure_description: Description of current failure
            max_results: Optional override for max results
        
        Returns:
            List of similar failures
        """
        return self.store.search(
            query=failure_description,
            top_k=max_results or self.config.max_results,
            threshold=self.config.similarity_threshold,
            filter_metadata={"type": "test_failure"},
        )
    
    def retrieve_related_tests(
        self,
        test_description: str,
        max_results: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Retrieve related test cases.
        
        Args:
            test_description: Description of test case
            max_results: Optional override for max results
        
        Returns:
            List of related test cases
        """
        return self.store.search(
            query=test_description,
            top_k=max_results or self.config.max_results,
            threshold=self.config.similarity_threshold,
            filter_metadata={"type": "test_case"},
        )
    
    def retrieve_code_examples(
        self,
        query: str,
        language: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Retrieve relevant code examples.
        
        Args:
            query: Search query
            language: Optional language filter
            max_results: Optional override for max results
        
        Returns:
            List of code examples
        """
        filters = {"type": "code_example"}
        if language:
            filters["language"] = language
        
        return self.store.search(
            query=query,
            top_k=max_results or self.config.max_results,
            threshold=self.config.similarity_threshold,
            filter_metadata=filters,
        )
    
    def retrieve_context(
        self,
        query: str,
        context_types: Optional[List[str]] = None,
        max_per_type: int = 5,
    ) -> Dict[str, List[SearchResult]]:
        """
        Retrieve mixed context from multiple sources.
        
        Args:
            query: Search query
            context_types: Types of context to retrieve
            max_per_type: Max results per type
        
        Returns:
            Dictionary mapping context type to results
        """
        if not context_types:
            context_types = ["test_failure", "test_case", "code_example"]
        
        results = {}
        
        for ctx_type in context_types:
            results[ctx_type] = self.store.search(
                query=query,
                top_k=max_per_type,
                threshold=self.config.similarity_threshold,
                filter_metadata={"type": ctx_type},
            )
        
        return results
    
    def _format_failure(self, failure: Dict[str, Any]) -> str:
        """Format failure for indexing."""
        parts = []
        
        if "test_name" in failure:
            parts.append(f"Test: {failure['test_name']}")
        
        if "error_message" in failure:
            parts.append(f"Error: {failure['error_message']}")
        
        if "stack_trace" in failure:
            # Include first few lines of stack trace
            trace_lines = failure['stack_trace'].split('\n')[:5]
            parts.append("Stack trace:\n" + '\n'.join(trace_lines))
        
        return '\n'.join(parts)
    
    def _format_test_case(self, test: Dict[str, Any]) -> str:
        """Format test case for indexing."""
        parts = []
        
        if "name" in test:
            parts.append(f"Test: {test['name']}")
        
        if "description" in test:
            parts.append(f"Description: {test['description']}")
        
        if "code" in test:
            parts.append(f"Code:\n{test['code']}")
        
        return '\n'.join(parts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        store_stats = self.store.get_statistics()
        
        # Count by type
        type_counts = {}
        for emb in self.store._embeddings.values():
            ctx_type = emb.metadata.get("type", "unknown")
            type_counts[ctx_type] = type_counts.get(ctx_type, 0) + 1
        
        return {
            **store_stats,
            "indexed_by_type": type_counts,
            "config": {
                "max_results": self.config.max_results,
                "similarity_threshold": self.config.similarity_threshold,
            },
        }
    
    def save(self, path: Optional[Path] = None):
        """Save indexed context to disk."""
        save_path = path or self.store.storage_path
        if save_path:
            self.store.storage_path = save_path
            self.store.save_embeddings()
    
    def load(self, path: Path):
        """Load indexed context from disk."""
        self.store.storage_path = path
        self.store._load_embeddings()
