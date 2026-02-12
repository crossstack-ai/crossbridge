"""
Repository for page_object table operations.

Handles CRUD operations for page objects with idempotent upserts.
"""

import uuid
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.logging import get_logger, LogCategory
from ..models import PageObject

logger = get_logger(__name__, category=LogCategory.PERSISTENCE)


def upsert_page_object(session: Session, page_object: PageObject) -> uuid.UUID:
    """
    Insert or update a page object (idempotent).
    
    Uses unique constraint (name, file_path) to avoid duplicates.
    Updates framework and package if page object already exists.
    
    Args:
        session: Database session
        page_object: PageObject to upsert
        
    Returns:
        UUID of the page object (existing or new)
        
    Example:
        >>> po = PageObject(
        ...     name="LoginPage",
        ...     file_path="src/main/java/pages/LoginPage.java",
        ...     framework="selenium",
        ...     package="com.example.pages"
        ... )
        >>> page_id = upsert_page_object(session, po)
    """
    try:
        result = session.execute(
            text("""
            INSERT INTO page_object
            (id, name, file_path, framework, package)
            VALUES (:id, :name, :file_path, :framework, :package)
            ON CONFLICT (name, file_path)
            DO UPDATE SET 
                framework = EXCLUDED.framework,
                package = EXCLUDED.package,
                updated_at = now()
            RETURNING id
            """),
            {
                "id": page_object.id,
                "name": page_object.name,
                "file_path": page_object.file_path,
                "framework": page_object.framework,
                "package": page_object.package
            }
        )
        
        page_id = result.scalar()
        logger.debug(f"Upserted page object: {page_object.name}")
        return page_id
    
    except Exception as e:
        logger.error(f"Failed to upsert page object {page_object.name}: {e}")
        raise


def get_page_object(session: Session, page_id: uuid.UUID) -> Optional[PageObject]:
    """
    Get a page object by ID.
    
    Args:
        session: Database session
        page_id: Page object UUID
        
    Returns:
        PageObject or None if not found
    """
    try:
        result = session.execute(
            text("""
            SELECT id, name, file_path, framework, package, created_at, updated_at
            FROM page_object
            WHERE id = :id
            """),
            {"id": page_id}
        ).fetchone()
        
        if result:
            return PageObject(
                id=result[0],
                name=result[1],
                file_path=result[2],
                framework=result[3],
                package=result[4],
                created_at=result[5],
                updated_at=result[6]
            )
        
        return None
    
    except Exception as e:
        logger.error(f"Failed to get page object {page_id}: {e}")
        return None


def find_page_object(
    session: Session,
    name: str,
    file_path: str
) -> Optional[uuid.UUID]:
    """
    Find a page object by its unique attributes.
    
    Args:
        session: Database session
        name: Page object name
        file_path: File path
        
    Returns:
        UUID if found, None otherwise
    """
    try:
        result = session.execute(
            text("""
            SELECT id
            FROM page_object
            WHERE name = :name AND file_path = :file_path
            """),
            {
                "name": name,
                "file_path": file_path
            }
        ).fetchone()
        
        return result[0] if result else None
    
    except Exception as e:
        logger.error(f"Failed to find page object: {e}")
        return None


def list_page_objects(
    session: Session,
    framework: Optional[str] = None,
    name_pattern: Optional[str] = None,
    limit: int = 100
) -> List[PageObject]:
    """
    List page objects with optional filters.
    
    Args:
        session: Database session
        framework: Optional framework filter
        name_pattern: Optional name pattern (SQL LIKE pattern)
        limit: Maximum number of results
        
    Returns:
        List of PageObject objects
    """
    try:
        # Build dynamic query
        conditions = []
        params = {"limit": limit}
        
        if framework:
            conditions.append("framework = :framework")
            params["framework"] = framework
        
        if name_pattern:
            conditions.append("name LIKE :pattern")
            params["pattern"] = name_pattern
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = text(f"""
            SELECT id, name, file_path, framework, package, created_at, updated_at
            FROM page_object
            WHERE {where_clause}
            ORDER BY name
            LIMIT :limit
        """)
        
        result = session.execute(query, params)
        
        pages = []
        for row in result:
            pages.append(PageObject(
                id=row[0],
                name=row[1],
                file_path=row[2],
                framework=row[3],
                package=row[4],
                created_at=row[5],
                updated_at=row[6]
            ))
        
        return pages
    
    except Exception as e:
        logger.error(f"Failed to list page objects: {e}")
        return []


def get_page_object_usage(session: Session, page_id: uuid.UUID) -> dict:
    """
    Get usage statistics for a page object.
    
    Args:
        session: Database session
        page_id: Page object UUID
        
    Returns:
        Dictionary with usage stats (test_count, discovery_count)
    """
    try:
        result = session.execute(
            text("""
            SELECT 
                COUNT(DISTINCT tpm.test_case_id) as test_count,
                COUNT(DISTINCT tpm.discovery_run_id) as discovery_count,
                ARRAY_AGG(DISTINCT tpm.source) as sources
            FROM test_page_mapping tpm
            WHERE tpm.page_object_id = :page_id
            """),
            {"page_id": page_id}
        ).fetchone()
        
        if result:
            return {
                "test_count": result[0] or 0,
                "discovery_count": result[1] or 0,
                "sources": result[2] or []
            }
        
        return {
            "test_count": 0,
            "discovery_count": 0,
            "sources": []
        }
    
    except Exception as e:
        logger.error(f"Failed to get page object usage for {page_id}: {e}")
        return {
            "test_count": 0,
            "discovery_count": 0,
            "sources": []
        }


def get_most_used_page_objects(session: Session, limit: int = 10) -> List[tuple]:
    """
    Get page objects ranked by usage (most tests).
    
    Args:
        session: Database session
        limit: Maximum number of results
        
    Returns:
        List of tuples (PageObject, test_count)
    """
    try:
        result = session.execute(
            text("""
            SELECT po.id, po.name, po.file_path, po.framework, po.package, 
                   po.created_at, po.updated_at, COUNT(DISTINCT tpm.test_case_id) as test_count
            FROM page_object po
            LEFT JOIN test_page_mapping tpm ON po.id = tpm.page_object_id
            GROUP BY po.id, po.name, po.file_path, po.framework, po.package, po.created_at, po.updated_at
            HAVING COUNT(DISTINCT tpm.test_case_id) > 0
            ORDER BY test_count DESC
            LIMIT :limit
            """),
            {"limit": limit}
        )
        
        ranked = []
        for row in result:
            page_obj = PageObject(
                id=row[0],
                name=row[1],
                file_path=row[2],
                framework=row[3],
                package=row[4],
                created_at=row[5],
                updated_at=row[6]
            )
            ranked.append((page_obj, row[7]))
        
        return ranked
    
    except Exception as e:
        logger.error(f"Failed to get most used page objects: {e}")
        return []
