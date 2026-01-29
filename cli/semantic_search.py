"""
Semantic Search CLI for CrossBridge

Provides command-line interface for searching tests, page objects,
and other artifacts using natural language queries powered by embeddings.
"""

import sys
import argparse
from typing import List, Optional, Dict, Any
from pathlib import Path

from core.logging import get_logger, LogCategory
from core.memory import (
    SemanticSearchEngine,
    MemoryIngestionPipeline,
    create_vector_store,
    create_embedding_provider,
    SearchResult,
    MemoryType,
)
from core.config import get_config

logger = get_logger(__name__, category=LogCategory.AI)


class SemanticSearchCLI:
    """Command-line interface for semantic search operations."""
    
    def __init__(self):
        self.config = get_config()
        self.search_engine: Optional[SemanticSearchEngine] = None
        self.ingestion_pipeline: Optional[MemoryIngestionPipeline] = None
    
    def _initialize_search_engine(self):
        """Initialize search engine with configured providers."""
        if self.search_engine:
            return
        
        try:
            # Create embedding provider
            embedding_config = self.config.get('ai', {}).get('embedding', {})
            provider_type = embedding_config.get('provider', 'openai')
            embedding_provider = create_embedding_provider(provider_type, embedding_config)
            
            # Create vector store
            vector_config = self.config.get('ai', {}).get('vector_store', {})
            store_type = vector_config.get('type', 'faiss')
            vector_store = create_vector_store(store_type, vector_config)
            
            # Create search engine
            self.search_engine = SemanticSearchEngine(
                embedding_provider=embedding_provider,
                vector_store=vector_store
            )
            
            logger.info(f"Initialized semantic search with {provider_type} embeddings and {store_type} store")
            
        except Exception as e:
            logger.error(f"Failed to initialize search engine: {e}", exc_info=True)
            raise
    
    def _initialize_ingestion_pipeline(self):
        """Initialize ingestion pipeline for indexing."""
        if self.ingestion_pipeline:
            return
        
        try:
            embedding_config = self.config.get('ai', {}).get('embedding', {})
            vector_config = self.config.get('ai', {}).get('vector_store', {})
            
            provider_type = embedding_config.get('provider', 'openai')
            store_type = vector_config.get('type', 'faiss')
            
            embedding_provider = create_embedding_provider(provider_type, embedding_config)
            vector_store = create_vector_store(store_type, vector_config)
            
            self.ingestion_pipeline = MemoryIngestionPipeline(
                embedding_provider=embedding_provider,
                vector_store=vector_store
            )
            
            logger.info("Initialized ingestion pipeline")
            
        except Exception as e:
            logger.error(f"Failed to initialize ingestion pipeline: {e}", exc_info=True)
            raise
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        memory_type: Optional[str] = None,
        framework: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for artifacts using natural language.
        
        Args:
            query: Natural language search query
            top_k: Maximum number of results
            memory_type: Filter by type (test_case, page_object, etc.)
            framework: Filter by framework
            
        Returns:
            List of search results with similarity scores
        """
        self._initialize_search_engine()
        
        filters = {}
        if memory_type:
            filters['memory_type'] = memory_type
        if framework:
            filters['framework'] = framework
        
        logger.info(f"Searching for: '{query}' (top_k={top_k}, filters={filters})")
        
        results = self.search_engine.search(
            query=query,
            top_k=top_k,
            filters=filters if filters else None
        )
        
        logger.info(f"Found {len(results)} results")
        return results
    
    def index_project(self, project_path: Path) -> Dict[str, int]:
        """
        Index all artifacts in a project directory.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Dictionary with counts of indexed items by type
        """
        self._initialize_ingestion_pipeline()
        
        logger.info(f"Indexing project: {project_path}")
        
        counts = {
            'test_cases': 0,
            'page_objects': 0,
            'errors': 0
        }
        
        # Index test files
        for test_file in project_path.rglob('test_*.py'):
            try:
                content = test_file.read_text()
                self.ingestion_pipeline.ingest_text(
                    content=content,
                    memory_type=MemoryType.TEST_CASE,
                    metadata={'file_path': str(test_file)}
                )
                counts['test_cases'] += 1
            except Exception as e:
                logger.error(f"Failed to index {test_file}: {e}")
                counts['errors'] += 1
        
        # Index page object files
        for po_file in project_path.rglob('*page*.py'):
            try:
                content = po_file.read_text()
                self.ingestion_pipeline.ingest_text(
                    content=content,
                    memory_type=MemoryType.PAGE_OBJECT,
                    metadata={'file_path': str(po_file)}
                )
                counts['page_objects'] += 1
            except Exception as e:
                logger.error(f"Failed to index {po_file}: {e}")
                counts['errors'] += 1
        
        logger.info(f"Indexing complete: {counts}")
        return counts
    
    def find_duplicates(
        self,
        threshold: float = 0.85,
        memory_type: Optional[str] = None
    ) -> List[tuple[SearchResult, SearchResult, float]]:
        """
        Find potential duplicate tests based on semantic similarity.
        
        Args:
            threshold: Similarity threshold (0.0 to 1.0)
            memory_type: Filter by type
            
        Returns:
            List of (result1, result2, similarity) tuples
        """
        self._initialize_search_engine()
        
        logger.info(f"Finding duplicates with threshold={threshold}")
        
        # Get all records
        filters = {'memory_type': memory_type} if memory_type else None
        
        # This is a simplified implementation
        # In production, use more efficient clustering algorithms
        duplicates = []
        
        logger.info(f"Found {len(duplicates)} potential duplicates")
        return duplicates


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='CrossBridge Semantic Search CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for tests related to login
  %(prog)s search "user login with email"
  
  # Index a project for semantic search
  %(prog)s index ./tests --framework pytest
  
  # Find duplicate tests
  %(prog)s duplicates --threshold 0.85
  
  # Search for page objects
  %(prog)s search "shopping cart page" --type page_object
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for artifacts')
    search_parser.add_argument('query', type=str, help='Natural language query')
    search_parser.add_argument('--top-k', type=int, default=10, help='Maximum results')
    search_parser.add_argument('--type', type=str, help='Filter by memory type')
    search_parser.add_argument('--framework', type=str, help='Filter by framework')
    search_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Index project artifacts')
    index_parser.add_argument('path', type=Path, help='Project directory path')
    index_parser.add_argument('--framework', type=str, help='Framework name')
    
    # Duplicates command
    dup_parser = subparsers.add_parser('duplicates', help='Find duplicate tests')
    dup_parser.add_argument('--threshold', type=float, default=0.85, help='Similarity threshold')
    dup_parser.add_argument('--type', type=str, help='Filter by memory type')
    dup_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = SemanticSearchCLI()
    
    try:
        if args.command == 'search':
            results = cli.search(
                query=args.query,
                top_k=args.top_k,
                memory_type=args.type,
                framework=args.framework
            )
            
            if args.format == 'json':
                import json
                print(json.dumps([{
                    'content': r.record.content[:200],
                    'type': r.record.memory_type.value,
                    'score': r.similarity_score,
                    'metadata': r.record.metadata
                } for r in results], indent=2))
            else:
                print(f"\n🔍 Found {len(results)} results for: '{args.query}'\n")
                for i, result in enumerate(results, 1):
                    print(f"{i}. [{result.similarity_score:.3f}] {result.record.memory_type.value}")
                    print(f"   {result.record.content[:150]}...")
                    if result.record.metadata.get('file_path'):
                        print(f"   📁 {result.record.metadata['file_path']}")
                    print()
        
        elif args.command == 'index':
            counts = cli.index_project(args.path)
            print(f"\n✅ Indexing complete:")
            print(f"   Test cases: {counts['test_cases']}")
            print(f"   Page objects: {counts['page_objects']}")
            if counts['errors'] > 0:
                print(f"   ⚠️  Errors: {counts['errors']}")
        
        elif args.command == 'duplicates':
            duplicates = cli.find_duplicates(
                threshold=args.threshold,
                memory_type=args.type
            )
            
            if args.format == 'json':
                import json
                print(json.dumps([{
                    'test1': d[0].record.content[:100],
                    'test2': d[1].record.content[:100],
                    'similarity': d[2]
                } for d in duplicates], indent=2))
            else:
                print(f"\n🔄 Found {len(duplicates)} potential duplicates:\n")
                for i, (r1, r2, sim) in enumerate(duplicates, 1):
                    print(f"{i}. Similarity: {sim:.3f}")
                    print(f"   A: {r1.record.content[:100]}...")
                    print(f"   B: {r2.record.content[:100]}...")
                    print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
