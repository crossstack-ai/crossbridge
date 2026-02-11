"""
Log analysis utilities for CrossBridge.

Provides advanced analysis capabilities for test execution logs including:
- Failure deduplication and clustering
- Root cause analysis
- Pattern detection
- Severity impact scoring
"""

from .clustering import (
    fingerprint_error,
    cluster_failures,
    FailureCluster,
    ClusteredFailure,
    FailureSeverity,
    get_cluster_summary,
    SEVERITY_RULES
)

__all__ = [
    "fingerprint_error",
    "cluster_failures",
    "FailureCluster",
    "ClusteredFailure",
    "FailureSeverity",
    "get_cluster_summary",
    "SEVERITY_RULES"
]
