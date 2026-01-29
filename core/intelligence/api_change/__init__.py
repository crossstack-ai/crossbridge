"""
API Change Intelligence Module

Detects OpenAPI/Swagger spec changes and provides:
- Incremental documentation
- Risk analysis
- Test impact mapping
- Selective test execution
- Alert notifications
"""

from .orchestrator import APIChangeOrchestrator
from .models.api_change import APIChangeEvent, DiffResult, ChangeType, EntityType, RiskLevel

__all__ = [
    "APIChangeOrchestrator",
    "APIChangeEvent",
    "DiffResult",
    "ChangeType",
    "EntityType",
    "RiskLevel",
]
