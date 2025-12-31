"""
Batch Processing Orchestration for CrossStack-AI CrossBridge.

Provides unified batch orchestration, cross-feature coordination, result aggregation,
and distributed processing capabilities.
"""

from .models import (
    BatchJob,
    BatchTask,
    BatchResult,
    BatchConfig,
    TaskStatus,
    JobPriority,
    FeatureType,
    ExecutionMode,
    TaskDependency,
    WorkerInfo
)

from .orchestrator import BatchOrchestrator

from .coordinator import FeatureCoordinator

from .aggregator import BatchResultAggregator

from .distributed import (
    DistributedExecutor,
    LoadBalancer,
    WorkerPool
)


__all__ = [
    # Models
    'BatchJob',
    'BatchTask',
    'BatchResult',
    'BatchConfig',
    'TaskStatus',
    'JobPriority',
    'FeatureType',
    'ExecutionMode',
    'TaskDependency',
    'WorkerInfo',
    
    # Orchestrator
    'BatchOrchestrator',
    
    # Coordinator
    'FeatureCoordinator',
    
    # Aggregator
    'BatchResultAggregator',
    
    # Distributed
    'DistributedExecutor',
    'LoadBalancer',
    'WorkerPool',
]
