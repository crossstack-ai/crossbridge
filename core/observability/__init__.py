"""
CrossBridge Observability & Continuous Intelligence

Post-Migration System Components:
- Lifecycle Management (migration → observer → optimization)
- Observer Service (event processing, non-blocking)
- Framework Hooks (pytest, Robot, Playwright)
- Drift Detection (new tests, behavior changes, flakiness)
- Coverage Intelligence (graph-based test-to-feature mapping)
- AI Intelligence (Phase 3: flaky prediction, coverage gaps, refactor suggestions)

Sidecar Resilience Components (Phase 3):
- Circuit Breaker: Failure isolation and recovery
- Performance Monitor: Overhead tracking (<5% target)
- Failure Isolation: Prevent observer crashes from affecting tests
- Async Processor: Non-blocking event processing
- Health Monitor: Kubernetes/Docker liveness/readiness probes

Design Contract:
- CrossBridge NEVER owns test execution
- CrossBridge NEVER regenerates tests post-migration
- CrossBridge operates as pure observer via hooks
- NEW tests auto-register on first run (NO remigration)
"""

from .events import CrossBridgeEvent, EventType
from .hook_sdk import CrossBridgeHookSDK
from .hook_integrator import HookIntegrator
from .event_persistence import EventPersistence
from .lifecycle import CrossBridgeMode, LifecycleManager
from .observer_service import CrossBridgeObserverService
from .drift_detector import DriftDetector, DriftSignal
from .coverage_intelligence import CoverageIntelligence, CoverageNode, CoverageEdge
from .ai_intelligence import (
    AIIntelligence,
    FlakyPrediction,
    CoverageGap,
    RefactorRecommendation,
    RiskScore,
    TestGenerationSuggestion
)

# Sidecar Resilience (Phase 3)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    circuit_breaker_registry
)
from .performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    SamplingStrategy,
    performance_monitor,
    sampling_strategy
)
from .failure_isolation import (
    IsolatedExecutor,
    ObserverFailureHandler,
    FailureRecord,
    failure_handler,
    safe_observer_call,
    isolated_observer_operation
)
from .async_processor import (
    AsyncProcessor,
    ObserverEvent,
    EventPriority,
    async_processor
)
from .health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheck,
    health_monitor,
    setup_default_health_checks
)

__all__ = [
    # Core Observability
    'CrossBridgeEvent',
    'EventType',
    'CrossBridgeHookSDK',
    'HookIntegrator',
    'EventPersistence',
    'CrossBridgeMode',
    'LifecycleManager',
    'CrossBridgeObserverService',
    'DriftDetector',
    'DriftSignal',
    'CoverageIntelligence',
    'CoverageNode',
    'CoverageEdge',
    'AIIntelligence',
    'FlakyPrediction',
    'CoverageGap',
    'RefactorRecommendation',
    'RiskScore',
    'TestGenerationSuggestion',
    
    # Sidecar Resilience (Phase 3)
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitState',
    'circuit_breaker_registry',
    'PerformanceMonitor',
    'PerformanceMetrics',
    'SamplingStrategy',
    'performance_monitor',
    'sampling_strategy',
    'IsolatedExecutor',
    'ObserverFailureHandler',
    'FailureRecord',
    'failure_handler',
    'safe_observer_call',
    'isolated_observer_operation',
    'AsyncProcessor',
    'ObserverEvent',
    'EventPriority',
    'async_processor',
    'HealthMonitor',
    'HealthStatus',
    'HealthCheck',
    'health_monitor',
    'setup_default_health_checks',
]
