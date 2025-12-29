"""
Persistence orchestrator for discovery operations.

Coordinates saving discovery metadata to PostgreSQL.
Handles the full workflow: discovery run -> tests -> page objects -> mappings.
"""

import uuid
import subprocess
from typing import List, Optional
from pathlib import Path
import logging

from persistence import (
    DatabaseConfig,
    create_session,
    discovery_repo,
    test_case_repo,
    page_object_repo,
    mapping_repo,
    from_test_metadata,
    from_page_object_reference
)

logger = logging.getLogger(__name__)


def get_git_commit() -> Optional[str]:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return None


def get_git_branch() -> Optional[str]:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return None


def persist_discovery(
    discovered_tests: List,
    project_name: str,
    triggered_by: str = "cli",
    framework_hint: Optional[str] = None
) -> Optional[uuid.UUID]:
    """
    Persist discovery results to PostgreSQL.
    
    Args:
        discovered_tests: List of TestMetadata objects from extractors
        project_name: Name of the project
        triggered_by: Source of trigger (cli, ci, jira, manual)
        framework_hint: Optional framework name if not in metadata
        
    Returns:
        Discovery run UUID if successful, None if persistence disabled/failed
        
    Example:
        >>> from adapters.selenium_java.extractor import SeleniumJavaExtractor
        >>> tests = extractor.extract_tests()
        >>> run_id = persist_discovery(tests, "my-project", "cli", "junit5")
    """
    # Check if database is configured
    if not DatabaseConfig.is_configured():
        logger.info("Database not configured. Skipping persistence.")
        return None
    
    session = create_session()
    if session is None:
        logger.warning("Failed to create database session. Skipping persistence.")
        return None
    
    try:
        # Create discovery run
        run_id = discovery_repo.create_discovery_run(
            session,
            project_name=project_name,
            git_commit=get_git_commit(),
            git_branch=get_git_branch(),
            triggered_by=triggered_by,
            metadata={"framework_hint": framework_hint}
        )
        
        logger.info(f"Created discovery run: {run_id}")
        
        test_count = 0
        mapping_count = 0
        
        # Process each discovered test
        for test_metadata in discovered_tests:
            # Convert to persistence model
            test_case = from_test_metadata(test_metadata, framework_hint)
            
            # Upsert test case
            test_id = test_case_repo.upsert_test_case(session, test_case)
            
            # Link to discovery run
            test_case_repo.link_test_to_discovery(session, run_id, test_id)
            test_count += 1
            
            # Process page objects if available
            if hasattr(test_metadata, 'page_objects') and test_metadata.page_objects:
                for po_name in test_metadata.page_objects:
                    # Create page object
                    page_obj = from_page_object_reference(
                        name=po_name,
                        file_path=test_metadata.file_path,  # Reference from test file
                        framework=framework_hint
                    )
                    
                    # Upsert page object
                    page_id = page_object_repo.upsert_page_object(session, page_obj)
                    
                    # Create mapping
                    mapping_repo.insert_mapping(
                        session,
                        test_case_id=test_id,
                        page_object_id=page_id,
                        source="static_ast",
                        discovery_run_id=run_id,
                        confidence=0.8,  # Static AST detection confidence
                        metadata={"extractor": "ast_parser"}
                    )
                    mapping_count += 1
        
        # Commit all changes
        session.commit()
        
        logger.info(f"Persisted {test_count} tests and {mapping_count} mappings for run {run_id}")
        
        # Log stats
        stats = discovery_repo.get_discovery_stats(session, run_id)
        logger.info(f"Discovery stats: {stats}")
        
        return run_id
    
    except Exception as e:
        logger.error(f"Failed to persist discovery: {e}")
        session.rollback()
        return None
    
    finally:
        session.close()


def get_latest_discovery_stats(project_name: str) -> Optional[dict]:
    """
    Get statistics for the latest discovery run.
    
    Args:
        project_name: Name of the project
        
    Returns:
        Dictionary with stats or None if not available
    """
    if not DatabaseConfig.is_configured():
        return None
    
    session = create_session()
    if session is None:
        return None
    
    try:
        latest_run = discovery_repo.get_latest_discovery_run(session, project_name)
        if latest_run is None:
            return None
        
        stats = discovery_repo.get_discovery_stats(session, latest_run.id)
        stats.update({
            "run_id": str(latest_run.id),
            "git_commit": latest_run.git_commit,
            "git_branch": latest_run.git_branch,
            "created_at": latest_run.created_at.isoformat() if latest_run.created_at else None
        })
        
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get latest discovery stats: {e}")
        return None
    
    finally:
        session.close()


def compare_discoveries(
    run_id_1: uuid.UUID,
    run_id_2: uuid.UUID
) -> dict:
    """
    Compare two discovery runs.
    
    Args:
        run_id_1: First discovery run UUID
        run_id_2: Second discovery run UUID
        
    Returns:
        Dictionary with comparison results (added, removed, common tests)
    """
    if not DatabaseConfig.is_configured():
        return {}
    
    session = create_session()
    if session is None:
        return {}
    
    try:
        # Get tests from both runs
        tests_1 = test_case_repo.get_tests_in_discovery(session, run_id_1)
        tests_2 = test_case_repo.get_tests_in_discovery(session, run_id_2)
        
        # Convert to sets for comparison
        test_ids_1 = {t.id for t in tests_1}
        test_ids_2 = {t.id for t in tests_2}
        
        added = test_ids_2 - test_ids_1
        removed = test_ids_1 - test_ids_2
        common = test_ids_1 & test_ids_2
        
        return {
            "run_1_test_count": len(tests_1),
            "run_2_test_count": len(tests_2),
            "added_count": len(added),
            "removed_count": len(removed),
            "common_count": len(common),
            "added_tests": [str(tid) for tid in added],
            "removed_tests": [str(tid) for tid in removed]
        }
    
    except Exception as e:
        logger.error(f"Failed to compare discoveries: {e}")
        return {}
    
    finally:
        session.close()
