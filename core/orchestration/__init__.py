"""
Core orchestration layer for CrossBridge AI.

This layer contains the reusable business logic for migrations,
independent of the interaction layer (CLI, UI, API).
"""

from .models import (
    MigrationRequest,
    MigrationResponse,
    MigrationType,
    AuthType,
    AIMode,
    MigrationMode,
    MigrationStatus,
    RepositoryAuth,
    AIConfig,
    MigrationResult,
    TransformationMode,
    TransformationTier,
    OperationType
)
from .orchestrator import MigrationOrchestrator

__all__ = [
    "MigrationRequest",
    "MigrationResponse",
    "MigrationType",
    "AuthType",
    "AIMode",
    "MigrationMode",
    "MigrationStatus",
    "RepositoryAuth",
    "AIConfig",
    "MigrationResult",
    "MigrationOrchestrator",
    "TransformationMode",
    "TransformationTier",
    "OperationType"
]
