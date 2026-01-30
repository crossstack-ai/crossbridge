"""
Intelligence Engine - Main Orchestration Module.

This module orchestrates the Deterministic + AI behavior system:
1. Deterministic classification (ALWAYS)
2. AI enrichment (OPTIONAL)
3. Metrics tracking
4. Graceful fallback handling

CRITICAL PRINCIPLES:
- Deterministic path NEVER fails
- AI failures NEVER block results
- Configuration controls all behavior
"""

from typing import List, Optional, Dict, Any
import time
import logging

from .deterministic_classifier import (
    DeterministicClassifier,
    SignalData,
    DeterministicResult,
    ClassificationLabel
)
from .ai_enricher import (
    AIEnricher,
    AIEnricherConfig,
    AIResult,
    FinalResult,
    safe_ai_enrich,
    merge_results
)
from .intelligence_config import IntelligenceConfig, get_config
from .intelligence_metrics import MetricsTracker, get_metrics_tracker

logger = logging.getLogger(__name__)


class IntelligenceEngine:
    """
    Main intelligence engine coordinating deterministic + AI behavior.
    
    This is the primary interface for test classification.
    
    Usage:
        engine = IntelligenceEngine()
        result = engine.classify(test_signal)
        
    The result ALWAYS contains deterministic classification.
    AI enrichment is added if available and successful.
    """
    
    def __init__(
        self,
        config: Optional[IntelligenceConfig] = None,
        metrics: Optional[MetricsTracker] = None,
        ai_analyzer=None
    ):
        """
        Initialize intelligence engine.
        
        Args:
            config: Optional configuration (uses global config if None)
            metrics: Optional metrics tracker (uses global if None)
            ai_analyzer: Optional AI analyzer instance
        """
        self.config = config or get_config()
        self.metrics = metrics or get_metrics_tracker()
        
        # Initialize deterministic classifier (REQUIRED)
        self.deterministic_classifier = DeterministicClassifier(
            config=self.config.deterministic.to_dict()
        )
        
        # Initialize AI enricher (OPTIONAL)
        ai_config = AIEnricherConfig(self.config.ai.to_dict())
        self.ai_enricher = AIEnricher(config=ai_config, ai_analyzer=ai_analyzer)
        
        logger.info(
            "IntelligenceEngine initialized (AI enabled: %s)",
            self.config.ai.enabled
        )
    
    def classify(
        self,
        signal: SignalData,
        context: Optional[Dict[str, Any]] = None
    ) -> FinalResult:
        """
        Classify a test using deterministic + optional AI enrichment.
        
        Flow:
        1. Run deterministic classification (ALWAYS succeeds)
        2. Optionally enrich with AI (may fail gracefully)
        3. Merge results
        4. Track metrics
        
        Args:
            signal: Test execution signals
            context: Optional additional context for AI enrichment
            
        Returns:
            FinalResult with deterministic classification + optional AI enrichment
        """
        start_time = time.time()
        
        # Step 1: Deterministic classification (MANDATORY)
        det_start = time.time()
        try:
            deterministic_result = self.deterministic_classifier.classify(signal)
            det_duration = (time.time() - det_start) * 1000
            
            self.metrics.track_deterministic_classification(
                label=deterministic_result.label.value,
                confidence=deterministic_result.confidence,
                duration_ms=det_duration
            )
            
            logger.debug(
                "Deterministic classification: %s (confidence=%.2f) in %.1fms",
                deterministic_result.label.value,
                deterministic_result.confidence,
                det_duration
            )
            
        except Exception as e:
            # This should NEVER happen (deterministic classifier has internal fallbacks)
            # But if it does, we still need to return something
            logger.error("Deterministic classification failed: %s", str(e), exc_info=True)
            deterministic_result = DeterministicResult(
                label=ClassificationLabel.UNKNOWN,
                confidence=0.0,
                reasons=["Classification system error"],
                applied_rules=["error_fallback"]
            )
        
        # Step 2: AI enrichment (OPTIONAL, can fail gracefully)
        ai_result = None
        if self.config.ai.enabled and self.config.ai.enrichment:
            ai_start = time.time()
            
            ai_result = safe_ai_enrich(
                deterministic_result=deterministic_result,
                signal=signal,
                ai_enricher=self.ai_enricher,
                context=context
            )
            
            ai_duration = (time.time() - ai_start) * 1000
            
            if ai_result:
                self.metrics.track_ai_enrichment_success(
                    duration_ms=ai_duration,
                    confidence=ai_result.confidence
                )
                logger.debug("AI enrichment succeeded in %.1fms", ai_duration)
            else:
                self.metrics.track_ai_enrichment_failure(reason="general_failure")
                logger.debug("AI enrichment failed or skipped")
        
        # Step 3: Merge results
        final_result = merge_results(
            deterministic_result=deterministic_result,
            signal=signal,
            ai_result=ai_result
        )
        
        # Step 4: Track overall metrics
        total_duration = (time.time() - start_time) * 1000
        self.metrics.track_final_result(
            has_ai_enrichment=(ai_result is not None),
            total_duration_ms=total_duration
        )
        
        logger.info(
            "Classification complete: %s (total=%.1fms, AI=%s)",
            final_result.label,
            total_duration,
            "yes" if ai_result else "no"
        )
        
        return final_result
    
    def batch_classify(
        self,
        signals: List[SignalData],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FinalResult]:
        """
        Classify multiple tests efficiently.
        
        Args:
            signals: List of test signals
            context: Optional shared context
            
        Returns:
            List of FinalResult (same order as input)
        """
        results = []
        
        for signal in signals:
            try:
                result = self.classify(signal, context)
                results.append(result)
            except Exception as e:
                # Should never happen, but handle defensively
                logger.error("Batch classification failed for %s: %s", signal.test_name, e)
                
                # Return minimal result
                results.append(FinalResult(
                    label=ClassificationLabel.UNKNOWN.value,
                    deterministic_confidence=0.0,
                    deterministic_reasons=["Classification error"],
                    test_name=signal.test_name
                ))
        
        return results
    
    def get_health(self) -> Dict[str, Any]:
        """
        Get health status of intelligence engine.
        
        Returns:
            Health status including metrics and configuration
        """
        metrics_summary = self.metrics.get_summary()
        
        # Calculate AI success rate
        ai_attempted = metrics_summary['ai_enrichment']['attempted']
        ai_success_rate = metrics_summary['ai_enrichment']['success_rate_pct']
        
        # Determine health status
        if ai_attempted == 0:
            ai_health = "no_data"
        elif ai_success_rate >= 90:
            ai_health = "healthy"
        elif ai_success_rate >= 70:
            ai_health = "degraded"
        else:
            ai_health = "unhealthy"
        
        return {
            'status': 'operational',  # Deterministic path always works
            'deterministic': {
                'status': 'healthy',
                'total_classifications': metrics_summary['total_classifications']
            },
            'ai_enrichment': {
                'status': ai_health,
                'enabled': self.config.ai.enabled,
                'success_rate_pct': ai_success_rate,
                'stats': metrics_summary['ai_enrichment']
            },
            'latency': metrics_summary['latency'],
            'config': {
                'ai_timeout_ms': self.config.ai.timeout_ms,
                'ai_min_confidence': self.config.ai.min_confidence,
                'fail_open': self.config.ai.fail_open
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics."""
        return self.metrics.get_summary()


# Convenience functions for simple usage


def classify_test(
    test_name: str,
    test_status: str,
    retry_count: int = 0,
    historical_failure_rate: float = 0.0,
    total_runs: int = 0,
    **kwargs
) -> FinalResult:
    """
    Classify a single test (convenience function).
    
    Args:
        test_name: Name of the test
        test_status: Status (pass/fail/skip/error)
        retry_count: Number of retries
        historical_failure_rate: Historical failure rate (0.0 - 1.0)
        total_runs: Total historical runs
        **kwargs: Additional TestSignal fields
        
    Returns:
        FinalResult with classification
    """
    signal = SignalData(
        test_name=test_name,
        test_status=test_status,
        retry_count=retry_count,
        historical_failure_rate=historical_failure_rate,
        total_runs=total_runs,
        **kwargs
    )
    
    engine = IntelligenceEngine()
    return engine.classify(signal)


def classify_tests_batch(signals: List[SignalData]) -> List[FinalResult]:
    """
    Classify multiple tests (convenience function).
    
    Args:
        signals: List of test signals
        
    Returns:
        List of FinalResult
    """
    engine = IntelligenceEngine()
    return engine.batch_classify(signals)
