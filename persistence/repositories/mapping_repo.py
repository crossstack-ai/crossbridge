"""
Repository for test_page_mapping table operations.

Handles CRUD operations for test-to-page-object mappings (append-only).
"""

import uuid
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

from ..models import TestPageMapping

logger = logging.getLogger(__name__)


def insert_mapping(
    session: Session,
    test_case_id: uuid.UUID,
    page_object_id: uuid.UUID,
    source: str,
    discovery_run_id: uuid.UUID,
    confidence: float = 1.0,
    metadata: Optional[dict] = None
) -> uuid.UUID:
    """
    Insert a new test-to-page-object mapping (append-only).
    
    This operation is append-only - we never overwrite mappings.
    Each discovery can add new mappings, building a history.
    
    Args:
        session: Database session
        test_case_id: Test case UUID
        page_object_id: Page object UUID
        source: Source of mapping (static_ast, coverage, ai, manual)
        discovery_run_id: Discovery run UUID
        confidence: Confidence score (0.0 to 1.0)
        metadata: Optional metadata as JSON
        
    Returns:
        UUID of created mapping
        
    Example:
        >>> mapping_id = insert_mapping(
        ...     session,
        ...     test_id,
        ...     page_id,
        ...     "static_ast",
        ...     run_id,
        ...     confidence=0.95
        ... )
    """
    try:
        mapping_id = uuid.uuid4()
        
        session.execute(
            text("""
            INSERT INTO test_page_mapping
            (id, test_case_id, page_object_id, source, confidence, discovery_run_id, metadata)
            VALUES (:id, :test_id, :page_id, :source, :confidence, :run_id, :metadata::jsonb)
            """),
            {
                "id": mapping_id,
                "test_id": test_case_id,
                "page_id": page_object_id,
                "source": source,
                "confidence": confidence,
                "run_id": discovery_run_id,
                "metadata": metadata or {}
            }
        )
        
        logger.debug(f"Created mapping {mapping_id}: test {test_case_id} -> page {page_object_id}")
        return mapping_id
    
    except Exception as e:
        logger.error(f"Failed to insert mapping: {e}")
        raise


def get_mapping(session: Session, mapping_id: uuid.UUID) -> Optional[TestPageMapping]:
    """
    Get a mapping by ID.
    
    Args:
        session: Database session
        mapping_id: Mapping UUID
        
    Returns:
        TestPageMapping or None if not found
    """
    try:
        result = session.execute(
            text("""
            SELECT id, test_case_id, page_object_id, source, confidence, 
                   discovery_run_id, created_at, metadata
            FROM test_page_mapping
            WHERE id = :id
            """),
            {"id": mapping_id}
        ).fetchone()
        
        if result:
            return TestPageMapping(
                id=result[0],
                test_case_id=result[1],
                page_object_id=result[2],
                source=result[3],
                confidence=result[4],
                discovery_run_id=result[5],
                created_at=result[6],
                metadata=result[7]
            )
        
        return None
    
    except Exception as e:
        logger.error(f"Failed to get mapping {mapping_id}: {e}")
        return None


def get_mappings_for_test(
    session: Session,
    test_case_id: uuid.UUID,
    source: Optional[str] = None
) -> List[TestPageMapping]:
    """
    Get all page object mappings for a test.
    
    Args:
        session: Database session
        test_case_id: Test case UUID
        source: Optional source filter
        
    Returns:
        List of TestPageMapping objects
    """
    try:
        if source:
            query = text("""
            SELECT id, test_case_id, page_object_id, source, confidence, 
                   discovery_run_id, created_at, metadata
            FROM test_page_mapping
            WHERE test_case_id = :test_id AND source = :source
            ORDER BY confidence DESC, created_at DESC
            """)
            result = session.execute(query, {"test_id": test_case_id, "source": source})
        else:
            query = text("""
            SELECT id, test_case_id, page_object_id, source, confidence, 
                   discovery_run_id, created_at, metadata
            FROM test_page_mapping
            WHERE test_case_id = :test_id
            ORDER BY confidence DESC, created_at DESC
            """)
            result = session.execute(query, {"test_id": test_case_id})
        
        mappings = []
        for row in result:
            mappings.append(TestPageMapping(
                id=row[0],
                test_case_id=row[1],
                page_object_id=row[2],
                source=row[3],
                confidence=row[4],
                discovery_run_id=row[5],
                created_at=row[6],
                metadata=row[7]
            ))
        
        return mappings
    
    except Exception as e:
        logger.error(f"Failed to get mappings for test {test_case_id}: {e}")
        return []


def get_mappings_for_page(
    session: Session,
    page_object_id: uuid.UUID,
    source: Optional[str] = None
) -> List[TestPageMapping]:
    """
    Get all test mappings for a page object.
    
    Args:
        session: Database session
        page_object_id: Page object UUID
        source: Optional source filter
        
    Returns:
        List of TestPageMapping objects
    """
    try:
        if source:
            query = text("""
            SELECT id, test_case_id, page_object_id, source, confidence, 
                   discovery_run_id, created_at, metadata
            FROM test_page_mapping
            WHERE page_object_id = :page_id AND source = :source
            ORDER BY confidence DESC, created_at DESC
            """)
            result = session.execute(query, {"page_id": page_object_id, "source": source})
        else:
            query = text("""
            SELECT id, test_case_id, page_object_id, source, confidence, 
                   discovery_run_id, created_at, metadata
            FROM test_page_mapping
            WHERE page_object_id = :page_id
            ORDER BY confidence DESC, created_at DESC
            """)
            result = session.execute(query, {"page_id": page_object_id})
        
        mappings = []
        for row in result:
            mappings.append(TestPageMapping(
                id=row[0],
                test_case_id=row[1],
                page_object_id=row[2],
                source=row[3],
                confidence=row[4],
                discovery_run_id=row[5],
                created_at=row[6],
                metadata=row[7]
            ))
        
        return mappings
    
    except Exception as e:
        logger.error(f"Failed to get mappings for page {page_object_id}: {e}")
        return []


def get_impacted_tests(
    session: Session,
    page_object_id: uuid.UUID,
    min_confidence: float = 0.5
) -> List[uuid.UUID]:
    """
    Get tests impacted by a page object change.
    
    Args:
        session: Database session
        page_object_id: Page object UUID
        min_confidence: Minimum confidence threshold
        
    Returns:
        List of test case UUIDs
        
    Example:
        >>> # LoginPage changed, find all impacted tests
        >>> impacted = get_impacted_tests(session, login_page_id, min_confidence=0.7)
    """
    try:
        result = session.execute(
            text("""
            SELECT DISTINCT test_case_id
            FROM test_page_mapping
            WHERE page_object_id = :page_id
              AND confidence >= :min_confidence
            """),
            {
                "page_id": page_object_id,
                "min_confidence": min_confidence
            }
        )
        
        return [row[0] for row in result]
    
    except Exception as e:
        logger.error(f"Failed to get impacted tests for page {page_object_id}: {e}")
        return []


def get_mapping_sources(session: Session, discovery_run_id: uuid.UUID) -> dict:
    """
    Get statistics on mapping sources for a discovery run.
    
    Args:
        session: Database session
        discovery_run_id: Discovery run UUID
        
    Returns:
        Dictionary with counts per source
    """
    try:
        result = session.execute(
            text("""
            SELECT source, COUNT(*) as count
            FROM test_page_mapping
            WHERE discovery_run_id = :run_id
            GROUP BY source
            """),
            {"run_id": discovery_run_id}
        )
        
        sources = {}
        for row in result:
            sources[row[0]] = row[1]
        
        return sources
    
    except Exception as e:
        logger.error(f"Failed to get mapping sources for run {discovery_run_id}: {e}")
        return {}


def get_latest_mappings_for_test(
    session: Session,
    test_case_id: uuid.UUID,
    source: Optional[str] = None
) -> List[tuple]:
    """
    Get latest (most recent discovery) mappings for a test with page object details.
    
    Args:
        session: Database session
        test_case_id: Test case UUID
        source: Optional source filter
        
    Returns:
        List of tuples (page_object_name, confidence, source, created_at)
    """
    try:
        if source:
            query = text("""
            SELECT DISTINCT ON (tpm.page_object_id)
                po.name, tpm.confidence, tpm.source, tpm.created_at
            FROM test_page_mapping tpm
            INNER JOIN page_object po ON tpm.page_object_id = po.id
            WHERE tpm.test_case_id = :test_id AND tpm.source = :source
            ORDER BY tpm.page_object_id, tpm.created_at DESC
            """)
            result = session.execute(query, {"test_id": test_case_id, "source": source})
        else:
            query = text("""
            SELECT DISTINCT ON (tpm.page_object_id)
                po.name, tpm.confidence, tpm.source, tpm.created_at
            FROM test_page_mapping tpm
            INNER JOIN page_object po ON tpm.page_object_id = po.id
            WHERE tpm.test_case_id = :test_id
            ORDER BY tpm.page_object_id, tpm.created_at DESC
            """)
            result = session.execute(query, {"test_id": test_case_id})
        
        return [(row[0], row[1], row[2], row[3]) for row in result]
    
    except Exception as e:
        logger.error(f"Failed to get latest mappings for test {test_case_id}: {e}")
        return []
