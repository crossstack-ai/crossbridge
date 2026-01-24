"""
Memory ingestion pipeline for CrossBridge.

This module orchestrates the process of extracting test-related entities,
generating embeddings, and storing them in the vector database.
"""

import logging
from typing import Any, Dict, List, Optional

from core.memory.embedding_provider import EmbeddingProvider
from core.memory.models import (
    MemoryRecord,
    MemoryType,
    test_to_text,
    scenario_to_text,
    step_to_text,
    page_to_text,
    failure_to_text,
)
from core.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MemoryIngestionPipeline:
    """
    Pipeline for ingesting test-related entities into memory system.
    
    This orchestrates:
    1. Entity extraction from test code
    2. Text generation for embedding
    3. Embedding generation
    4. Storage in vector database
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        batch_size: int = 100,
    ):
        """
        Initialize ingestion pipeline.
        
        Args:
            embedding_provider: Provider for generating embeddings
            vector_store: Storage backend for memory records
            batch_size: Number of records to process in one batch
        """
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.batch_size = batch_size

        logger.info(
            f"Initialized MemoryIngestionPipeline with batch_size={batch_size}"
        )

    def ingest(self, records: List[MemoryRecord]) -> int:
        """
        Ingest memory records into the system.
        
        This is the main entry point for adding new memory records.
        Records should have text but no embeddings (will be generated).
        
        Args:
            records: List of MemoryRecord objects (without embeddings)
            
        Returns:
            Number of records successfully ingested
            
        Example:
            >>> pipeline = MemoryIngestionPipeline(provider, store)
            >>> records = [MemoryRecord(id='test_1', type=MemoryType.TEST, text='...', metadata={})]
            >>> pipeline.ingest(records)
        """
        if not records:
            logger.warning("No records provided for ingestion")
            return 0

        logger.info(f"Starting ingestion of {len(records)} records")

        total_ingested = 0

        # Process in batches
        for i in range(0, len(records), self.batch_size):
            batch = records[i : i + self.batch_size]

            try:
                # Generate embeddings for batch
                texts = [r.text for r in batch]
                embeddings = self.embedding_provider.embed(texts)

                # Attach embeddings to records
                for record, embedding in zip(batch, embeddings):
                    record.embedding = embedding

                # Store in vector database
                stored = self.vector_store.upsert(batch)
                total_ingested += stored

                logger.info(
                    f"Ingested batch {i // self.batch_size + 1}: {stored} records"
                )

            except Exception as e:
                logger.error(f"Failed to ingest batch: {e}")
                # Continue with next batch instead of failing completely

        logger.info(f"Ingestion complete: {total_ingested} records stored")
        return total_ingested

    def ingest_from_tests(self, test_data: List[Dict[str, Any]]) -> int:
        """
        Ingest test cases into memory system.
        
        Args:
            test_data: List of test metadata dictionaries
            
        Returns:
            Number of records ingested
            
        Example:
            >>> test_data = [{'name': 'test_login', 'framework': 'pytest', 'steps': [...]}]
            >>> pipeline.ingest_from_tests(test_data)
        """
        records = []

        for test in test_data:
            try:
                record = MemoryRecord(
                    id=test.get("id") or test.get("name", "unknown"),
                    type=MemoryType.TEST,
                    text=test_to_text(test),
                    metadata={
                        "framework": test.get("framework"),
                        "file": test.get("file"),
                        "tags": test.get("tags", []),
                        "intent": test.get("intent"),
                    },
                )
                records.append(record)

            except Exception as e:
                logger.error(f"Failed to create record from test: {e}")

        return self.ingest(records)

    def ingest_from_scenarios(self, scenario_data: List[Dict[str, Any]]) -> int:
        """
        Ingest BDD scenarios into memory system.
        
        Args:
            scenario_data: List of scenario metadata dictionaries
            
        Returns:
            Number of records ingested
        """
        records = []

        for scenario in scenario_data:
            try:
                record = MemoryRecord(
                    id=scenario.get("id")
                    or f"{scenario.get('feature')}_{scenario.get('name')}",
                    type=MemoryType.SCENARIO,
                    text=scenario_to_text(scenario),
                    metadata={
                        "framework": scenario.get("framework"),
                        "feature": scenario.get("feature"),
                        "file": scenario.get("file"),
                        "tags": scenario.get("tags", []),
                    },
                )
                records.append(record)

            except Exception as e:
                logger.error(f"Failed to create record from scenario: {e}")

        return self.ingest(records)

    def ingest_from_steps(self, step_data: List[Dict[str, Any]]) -> int:
        """
        Ingest test steps into memory system.
        
        Args:
            step_data: List of step metadata dictionaries
            
        Returns:
            Number of records ingested
        """
        records = []

        for step in step_data:
            try:
                record = MemoryRecord(
                    id=step.get("id") or step.get("text", "unknown"),
                    type=MemoryType.STEP,
                    text=step_to_text(step),
                    metadata={
                        "framework": step.get("framework"),
                        "file": step.get("file"),
                        "keyword": step.get("keyword"),
                        "parent": step.get("parent"),
                    },
                )
                records.append(record)

            except Exception as e:
                logger.error(f"Failed to create record from step: {e}")

        return self.ingest(records)

    def ingest_from_pages(self, page_data: List[Dict[str, Any]]) -> int:
        """
        Ingest page objects into memory system.
        
        Args:
            page_data: List of page object metadata dictionaries
            
        Returns:
            Number of records ingested
        """
        records = []

        for page in page_data:
            try:
                record = MemoryRecord(
                    id=page.get("id") or page.get("name", "unknown"),
                    type=MemoryType.PAGE,
                    text=page_to_text(page),
                    metadata={
                        "framework": page.get("framework"),
                        "file": page.get("file"),
                        "url": page.get("url"),
                    },
                )
                records.append(record)

            except Exception as e:
                logger.error(f"Failed to create record from page: {e}")

        return self.ingest(records)

    def ingest_from_failures(self, failure_data: List[Dict[str, Any]]) -> int:
        """
        Ingest test failures into memory system.
        
        Args:
            failure_data: List of failure metadata dictionaries
            
        Returns:
            Number of records ingested
        """
        records = []

        for failure in failure_data:
            try:
                record = MemoryRecord(
                    id=failure.get("id")
                    or f"{failure.get('test_name')}_{failure.get('timestamp')}",
                    type=MemoryType.FAILURE,
                    text=failure_to_text(failure),
                    metadata={
                        "framework": failure.get("framework"),
                        "test_name": failure.get("test_name"),
                        "error_type": failure.get("error_type"),
                        "timestamp": failure.get("timestamp"),
                    },
                )
                records.append(record)

            except Exception as e:
                logger.error(f"Failed to create record from failure: {e}")

        return self.ingest(records)

    def update_records(self, records: List[MemoryRecord]) -> int:
        """
        Update existing memory records.
        
        This regenerates embeddings for updated records.
        
        Args:
            records: List of MemoryRecord objects to update
            
        Returns:
            Number of records updated
        """
        return self.ingest(records)

    def delete_records(self, record_ids: List[str]) -> int:
        """
        Delete memory records.
        
        Args:
            record_ids: List of record IDs to delete
            
        Returns:
            Number of records deleted
        """
        try:
            deleted = self.vector_store.delete(record_ids)
            logger.info(f"Deleted {deleted} memory records")
            return deleted

        except Exception as e:
            logger.error(f"Failed to delete records: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory system.
        
        Returns:
            Dictionary with counts by type and other metrics
        """
        stats = {"total": self.vector_store.count()}

        # Count by type
        for memory_type in MemoryType:
            count = self.vector_store.count(filters={"type": [memory_type.value]})
            stats[f"{memory_type.value}_count"] = count

        return stats


# Helper function for incremental ingestion


def ingest_from_discovery(
    discovery_results: Dict[str, Any],
    pipeline: MemoryIngestionPipeline,
) -> Dict[str, int]:
    """
    Ingest results from test discovery into memory system.
    
    This is the main integration point with CrossBridge's discovery system.
    
    Args:
        discovery_results: Output from test discovery
        pipeline: Configured ingestion pipeline
        
    Returns:
        Dictionary with counts of ingested records by type
        
    Example:
        >>> results = crossbridge.discover_tests(...)
        >>> counts = ingest_from_discovery(results, pipeline)
        >>> print(f"Ingested {counts['tests']} tests, {counts['scenarios']} scenarios")
    """
    counts = {}

    # Ingest tests
    if tests := discovery_results.get("tests"):
        counts["tests"] = pipeline.ingest_from_tests(tests)

    # Ingest scenarios
    if scenarios := discovery_results.get("scenarios"):
        counts["scenarios"] = pipeline.ingest_from_scenarios(scenarios)

    # Ingest steps
    if steps := discovery_results.get("steps"):
        counts["steps"] = pipeline.ingest_from_steps(steps)

    # Ingest pages
    if pages := discovery_results.get("pages"):
        counts["pages"] = pipeline.ingest_from_pages(pages)

    logger.info(f"Ingestion summary: {counts}")
    return counts
