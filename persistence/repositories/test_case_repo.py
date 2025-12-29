"""
Repository for test_case table operations.

Handles CRUD operations for test cases with idempotent upserts.
"""

import uuid
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

from ..models import TestCase

logger = logging.getLogger(__name__)


def upsert_test_case(session: Session, test_case: TestCase) -> uuid.UUID:
    """
    Insert or update a test case (idempotent).
    
    Uses unique constraint (framework, package, class_name, method_name) to avoid duplicates.
    Updates file_path and tags if test already exists.
    
    Args:
        session: Database session
        test_case: TestCase to upsert
        
    Returns:
        UUID of the test case (existing or new)
        
    Example:
        >>> tc = TestCase(
        ...     framework="junit5",
        ...     package="com.example",
        ...     class_name="LoginTest",
        ...     method_name="testValidLogin",
        ...     file_path="src/test/java/LoginTest.java",
        ...     tags=["smoke"]
        ... )
        >>> test_id = upsert_test_case(session, tc)
    """
    try:
        result = session.execute(
            text("""
            INSERT INTO test_case
            (id, framework, package, class_name, method_name, file_path, tags)
            VALUES (:id, :framework, :package, :class_name, :method_name, :file_path, :tags)
            ON CONFLICT (framework, package, class_name, method_name)
            DO UPDATE SET 
                file_path = EXCLUDED.file_path,
                tags = EXCLUDED.tags,
                updated_at = now()
            RETURNING id
            """),
            {
                "id": test_case.id,
                "framework": test_case.framework,
                "package": test_case.package,
                "class_name": test_case.class_name,
                "method_name": test_case.method_name,
                "file_path": test_case.file_path,
                "tags": test_case.tags
            }
        )
        
        test_id = result.scalar()
        logger.debug(f"Upserted test case: {test_case.full_name}")
        return test_id
    
    except Exception as e:
        logger.error(f"Failed to upsert test case {test_case.full_name}: {e}")
        raise


def get_test_case(session: Session, test_id: uuid.UUID) -> Optional[TestCase]:
    """
    Get a test case by ID.
    
    Args:
        session: Database session
        test_id: Test case UUID
        
    Returns:
        TestCase or None if not found
    """
    try:
        result = session.execute(
            text("""
            SELECT id, framework, package, class_name, method_name, file_path, tags, created_at, updated_at
            FROM test_case
            WHERE id = :id
            """),
            {"id": test_id}
        ).fetchone()
        
        if result:
            return TestCase(
                id=result[0],
                framework=result[1],
                package=result[2],
                class_name=result[3],
                method_name=result[4],
                file_path=result[5],
                tags=result[6] or [],
                created_at=result[7],
                updated_at=result[8]
            )
        
        return None
    
    except Exception as e:
        logger.error(f"Failed to get test case {test_id}: {e}")
        return None


def find_test_case(
    session: Session,
    framework: str,
    package: Optional[str],
    class_name: Optional[str],
    method_name: str
) -> Optional[uuid.UUID]:
    """
    Find a test case by its unique attributes.
    
    Args:
        session: Database session
        framework: Test framework
        package: Package name (can be None)
        class_name: Class name (can be None)
        method_name: Method name
        
    Returns:
        UUID if found, None otherwise
    """
    try:
        result = session.execute(
            text("""
            SELECT id
            FROM test_case
            WHERE framework = :framework
              AND package IS NOT DISTINCT FROM :package
              AND class_name IS NOT DISTINCT FROM :class_name
              AND method_name = :method_name
            """),
            {
                "framework": framework,
                "package": package,
                "class_name": class_name,
                "method_name": method_name
            }
        ).fetchone()
        
        return result[0] if result else None
    
    except Exception as e:
        logger.error(f"Failed to find test case: {e}")
        return None


def list_test_cases(
    session: Session,
    framework: Optional[str] = None,
    file_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 100
) -> List[TestCase]:
    """
    List test cases with optional filters.
    
    Args:
        session: Database session
        framework: Optional framework filter
        file_path: Optional file path filter (exact match)
        tags: Optional tag filter (any match)
        limit: Maximum number of results
        
    Returns:
        List of TestCase objects
    """
    try:
        # Build dynamic query
        conditions = []
        params = {"limit": limit}
        
        if framework:
            conditions.append("framework = :framework")
            params["framework"] = framework
        
        if file_path:
            conditions.append("file_path = :file_path")
            params["file_path"] = file_path
        
        if tags:
            conditions.append("tags && :tags")
            params["tags"] = tags
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = text(f"""
            SELECT id, framework, package, class_name, method_name, file_path, tags, created_at, updated_at
            FROM test_case
            WHERE {where_clause}
            ORDER BY framework, class_name, method_name
            LIMIT :limit
        """)
        
        result = session.execute(query, params)
        
        tests = []
        for row in result:
            tests.append(TestCase(
                id=row[0],
                framework=row[1],
                package=row[2],
                class_name=row[3],
                method_name=row[4],
                file_path=row[5],
                tags=row[6] or [],
                created_at=row[7],
                updated_at=row[8]
            ))
        
        return tests
    
    except Exception as e:
        logger.error(f"Failed to list test cases: {e}")
        return []


def link_test_to_discovery(session: Session, discovery_run_id: uuid.UUID, test_case_id: uuid.UUID):
    """
    Link a test case to a discovery run.
    
    Args:
        session: Database session
        discovery_run_id: Discovery run UUID
        test_case_id: Test case UUID
        
    Example:
        >>> link_test_to_discovery(session, run_id, test_id)
    """
    try:
        session.execute(
            text("""
            INSERT INTO discovery_test_case
            (discovery_run_id, test_case_id)
            VALUES (:run_id, :test_id)
            ON CONFLICT (discovery_run_id, test_case_id) DO NOTHING
            """),
            {
                "run_id": discovery_run_id,
                "test_id": test_case_id
            }
        )
        
        logger.debug(f"Linked test {test_case_id} to discovery run {discovery_run_id}")
    
    except Exception as e:
        logger.error(f"Failed to link test to discovery: {e}")
        raise


def get_tests_in_discovery(session: Session, discovery_run_id: uuid.UUID) -> List[TestCase]:
    """
    Get all test cases discovered in a specific run.
    
    Args:
        session: Database session
        discovery_run_id: Discovery run UUID
        
    Returns:
        List of TestCase objects
    """
    try:
        result = session.execute(
            text("""
            SELECT tc.id, tc.framework, tc.package, tc.class_name, tc.method_name, 
                   tc.file_path, tc.tags, tc.created_at, tc.updated_at
            FROM test_case tc
            INNER JOIN discovery_test_case dtc ON tc.id = dtc.test_case_id
            WHERE dtc.discovery_run_id = :run_id
            ORDER BY tc.framework, tc.class_name, tc.method_name
            """),
            {"run_id": discovery_run_id}
        )
        
        tests = []
        for row in result:
            tests.append(TestCase(
                id=row[0],
                framework=row[1],
                package=row[2],
                class_name=row[3],
                method_name=row[4],
                file_path=row[5],
                tags=row[6] or [],
                created_at=row[7],
                updated_at=row[8]
            ))
        
        return tests
    
    except Exception as e:
        logger.error(f"Failed to get tests in discovery {discovery_run_id}: {e}")
        return []
