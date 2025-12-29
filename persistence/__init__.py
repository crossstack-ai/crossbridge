"""
Persistence layer for CrossBridge discovery metadata.

Optional PostgreSQL persistence with append-only observational design.

Usage:
    # Check if DB configured
    if DatabaseConfig.is_configured():
        session = create_session()
        # ... use repositories
        session.commit()
        session.close()
    else:
        # Continue without persistence
        pass
"""

from .db import (
    DatabaseConfig,
    create_session,
    init_database,
    check_database_health
)

from .models import (
    DiscoveryRun,
    TestCase,
    PageObject,
    TestPageMapping,
    DiscoveryTestCase,
    from_test_metadata,
    from_page_object_reference
)

from .repositories import discovery_repo, test_case_repo, page_object_repo, mapping_repo

__all__ = [
    # Database
    "DatabaseConfig",
    "create_session",
    "init_database",
    "check_database_health",
    
    # Models
    "DiscoveryRun",
    "TestCase",
    "PageObject",
    "TestPageMapping",
    "DiscoveryTestCase",
    "from_test_metadata",
    "from_page_object_reference",
    
    # Repositories
    "discovery_repo",
    "test_case_repo",
    "page_object_repo",
    "mapping_repo",
]
