"""
Repository for discovery_run table operations.

Handles CRUD operations for discovery runs.
"""

import uuid
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..models import DiscoveryRun

logger = logging.getLogger(__name__)


def create_discovery_run(
    session: Session,
    project_name: str,
    git_commit: Optional[str] = None,
    git_branch: Optional[str] = None,
    triggered_by: str = "cli",
    metadata: Optional[dict] = None
) -> uuid.UUID:
    """
    Create a new discovery run.
    
    Args:
        session: Database session
        project_name: Name of the project
        git_commit: Git commit hash
        git_branch: Git branch name
        triggered_by: Source of trigger (cli, ci, jira, manual)
        metadata: Additional metadata as JSON
        
    Returns:
        UUID of created discovery run
        
    Example:
        >>> run_id = create_discovery_run(
        ...     session,
        ...     "crossbridge-ai",
        ...     "abc123",
        ...     "main",
        ...     "cli"
        ... )
    """
    run_id = uuid.uuid4()
    
    try:
        session.execute(
            text("""
            INSERT INTO discovery_run
            (id, project_name, git_commit, git_branch, triggered_by, metadata)
            VALUES (:id, :project, :commit, :branch, :triggered_by, :metadata::jsonb)
            """),
            {
                "id": run_id,
                "project": project_name,
                "commit": git_commit,
                "branch": git_branch,
                "triggered_by": triggered_by,
                "metadata": metadata or {}
            }
        )
        
        logger.info(f"Created discovery run: {run_id} for {project_name}")
        return run_id
    
    except Exception as e:
        logger.error(f"Failed to create discovery run: {e}")
        raise


def get_discovery_run(session: Session, run_id: uuid.UUID) -> Optional[DiscoveryRun]:
    """
    Get a discovery run by ID.
    
    Args:
        session: Database session
        run_id: Discovery run UUID
        
    Returns:
        DiscoveryRun or None if not found
    """
    try:
        result = session.execute(
            text("""
            SELECT id, project_name, git_commit, git_branch, triggered_by, created_at, metadata
            FROM discovery_run
            WHERE id = :id
            """),
            {"id": run_id}
        ).fetchone()
        
        if result:
            return DiscoveryRun(
                id=result[0],
                project_name=result[1],
                git_commit=result[2],
                git_branch=result[3],
                triggered_by=result[4],
                created_at=result[5],
                metadata=result[6]
            )
        
        return None
    
    except Exception as e:
        logger.error(f"Failed to get discovery run {run_id}: {e}")
        return None


def get_latest_discovery_run(session: Session, project_name: str) -> Optional[DiscoveryRun]:
    """
    Get the latest discovery run for a project.
    
    Args:
        session: Database session
        project_name: Name of the project
        
    Returns:
        Latest DiscoveryRun or None if not found
    """
    try:
        result = session.execute(
            text("""
            SELECT id, project_name, git_commit, git_branch, triggered_by, created_at, metadata
            FROM discovery_run
            WHERE project_name = :project
            ORDER BY created_at DESC
            LIMIT 1
            """),
            {"project": project_name}
        ).fetchone()
        
        if result:
            return DiscoveryRun(
                id=result[0],
                project_name=result[1],
                git_commit=result[2],
                git_branch=result[3],
                triggered_by=result[4],
                created_at=result[5],
                metadata=result[6]
            )
        
        return None
    
    except Exception as e:
        logger.error(f"Failed to get latest discovery run for {project_name}: {e}")
        return None


def list_discovery_runs(
    session: Session,
    project_name: Optional[str] = None,
    limit: int = 10
) -> list[DiscoveryRun]:
    """
    List discovery runs, optionally filtered by project.
    
    Args:
        session: Database session
        project_name: Optional project name filter
        limit: Maximum number of results
        
    Returns:
        List of DiscoveryRun objects
    """
    try:
        if project_name:
            query = text("""
            SELECT id, project_name, git_commit, git_branch, triggered_by, created_at, metadata
            FROM discovery_run
            WHERE project_name = :project
            ORDER BY created_at DESC
            LIMIT :limit
            """)
            result = session.execute(query, {"project": project_name, "limit": limit})
        else:
            query = text("""
            SELECT id, project_name, git_commit, git_branch, triggered_by, created_at, metadata
            FROM discovery_run
            ORDER BY created_at DESC
            LIMIT :limit
            """)
            result = session.execute(query, {"limit": limit})
        
        runs = []
        for row in result:
            runs.append(DiscoveryRun(
                id=row[0],
                project_name=row[1],
                git_commit=row[2],
                git_branch=row[3],
                triggered_by=row[4],
                created_at=row[5],
                metadata=row[6]
            ))
        
        return runs
    
    except Exception as e:
        logger.error(f"Failed to list discovery runs: {e}")
        return []


def get_discovery_stats(session: Session, run_id: uuid.UUID) -> dict:
    """
    Get statistics for a discovery run.
    
    Args:
        session: Database session
        run_id: Discovery run UUID
        
    Returns:
        Dictionary with stats (test_count, page_object_count, mapping_count)
    """
    try:
        result = session.execute(
            text("""
            SELECT 
                COUNT(DISTINCT dtc.test_case_id) as test_count,
                COUNT(DISTINCT tpm.page_object_id) as page_object_count,
                COUNT(DISTINCT tpm.id) as mapping_count
            FROM discovery_run dr
            LEFT JOIN discovery_test_case dtc ON dr.id = dtc.discovery_run_id
            LEFT JOIN test_page_mapping tpm ON dr.id = tpm.discovery_run_id
            WHERE dr.id = :id
            GROUP BY dr.id
            """),
            {"id": run_id}
        ).fetchone()
        
        if result:
            return {
                "test_count": result[0] or 0,
                "page_object_count": result[1] or 0,
                "mapping_count": result[2] or 0
            }
        
        return {
            "test_count": 0,
            "page_object_count": 0,
            "mapping_count": 0
        }
    
    except Exception as e:
        logger.error(f"Failed to get discovery stats for {run_id}: {e}")
        return {
            "test_count": 0,
            "page_object_count": 0,
            "mapping_count": 0
        }
