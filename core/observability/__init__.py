"""
CrossBridge Observability & Continuous Intelligence

Post-Migration System Components:
- Lifecycle Management (migration → observer → optimization)
- Observer Service (event processing, non-blocking)
- Framework Hooks (pytest, Robot, Playwright)
- Drift Detection (new tests, behavior changes, flakiness)
- Coverage Intelligence (graph-based test-to-feature mapping)
- AI Intelligence (Phase 3: flaky prediction, coverage gaps, refactor suggestions)

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

__all__ = [
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
]
