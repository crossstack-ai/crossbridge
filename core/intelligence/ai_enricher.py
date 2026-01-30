"""
AI Enrichment Layer for Test Intelligence.

This module provides OPTIONAL AI-powered insights that:
- NEVER change deterministic classifications
- Add context, explanations, and recommendations
- Fail gracefully without impacting correctness
- Are advisory only

AI enrichment is SECONDARY to deterministic classification.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
import time

from .deterministic_classifier import DeterministicResult, SignalData, ClassificationLabel

logger = logging.getLogger(__name__)


@dataclass
class AIResult:
    """
    AI enrichment output (ADVISORY ONLY).
    
    This does NOT contain classification labels.
    It ONLY adds insights and recommendations.
    """
    insights: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    similarity_refs: List[str] = field(default_factory=list)
    root_cause_hints: List[str] = field(default_factory=list)
    
    # AI metadata
    confidence: float = 0.0  # AI's confidence in its enrichment
    model_used: Optional[str] = None
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "insights": self.insights,
            "suggested_actions": self.suggested_actions,
            "similarity_refs": self.similarity_refs,
            "root_cause_hints": self.root_cause_hints,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "processing_time_ms": self.processing_time_ms,
        }


@dataclass
class FinalResult:
    """
    Combined deterministic + AI result.
    
    Structure:
    - label: ALWAYS from deterministic classifier
    - deterministic_confidence: ALWAYS from deterministic classifier
    - ai_enrichment: OPTIONAL, can be None
    """
    # Deterministic (MANDATORY)
    label: str  # From deterministic classifier
    deterministic_confidence: float
    deterministic_reasons: List[str]
    
    # AI enrichment (OPTIONAL)
    ai_enrichment: Optional[AIResult] = None
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    test_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "label": self.label,
            "deterministic_confidence": self.deterministic_confidence,
            "deterministic_reasons": self.deterministic_reasons,
            "timestamp": self.timestamp,
            "test_name": self.test_name,
        }
        
        if self.ai_enrichment:
            result["ai_enrichment"] = self.ai_enrichment.to_dict()
        else:
            result["ai_enrichment"] = None
        
        return result


class AIEnricherConfig:
    """Configuration for AI enrichment behavior."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        # Feature flags
        self.enabled = config.get('enabled', True)
        self.enrichment_enabled = config.get('enrichment', True)
        
        # Timeouts and limits
        self.timeout_ms = config.get('timeout_ms', 2000)
        self.min_confidence = config.get('min_confidence', 0.5)
        
        # Failure handling
        self.fail_open = config.get('fail_open', True)  # Return deterministic on failure
        
        # Model selection
        self.model = config.get('model', 'gpt-4o-mini')
        self.temperature = config.get('temperature', 0.3)
        
    def is_enrichment_enabled(self) -> bool:
        """Check if AI enrichment should be attempted."""
        return self.enabled and self.enrichment_enabled


class AIEnricher:
    """
    AI-powered enrichment for test intelligence.
    
    CRITICAL RULES:
    1. AI NEVER changes deterministic labels
    2. AI failures NEVER block results
    3. AI is ALWAYS optional
    4. Low confidence AI results are discarded
    """
    
    def __init__(self, config: Optional[AIEnricherConfig] = None, ai_analyzer=None):
        """
        Initialize AI enricher.
        
        Args:
            config: AI enrichment configuration
            ai_analyzer: Optional AI analyzer instance (from core.ai)
        """
        self.config = config or AIEnricherConfig()
        self.ai_analyzer = ai_analyzer
        
        # Metrics tracking
        self.metrics = {
            'attempted': 0,
            'success': 0,
            'failed': 0,
            'timeout': 0,
            'low_confidence': 0,
        }
        
        logger.info("AIEnricher initialized (enabled=%s)", self.config.enabled)
    
    def enrich(
        self,
        deterministic_result: DeterministicResult,
        signal: TestSignal,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[AIResult]:
        """
        Enrich deterministic result with AI insights.
        
        This method is SAFE - it will never throw exceptions that impact callers.
        
        Args:
            deterministic_result: The deterministic classification (immutable)
            signal: Test execution signals
            context: Optional additional context (similar tests, graph data, etc.)
            
        Returns:
            AIResult if successful and confident, None otherwise
        """
        if not self.config.is_enrichment_enabled():
            logger.debug("AI enrichment disabled")
            return None
        
        self.metrics['attempted'] += 1
        start_time = time.time()
        
        try:
            # Call AI enrichment with timeout protection
            ai_result = self._safe_ai_call(deterministic_result, signal, context)
            
            if ai_result is None:
                return None
            
            # Validate confidence threshold
            if ai_result.confidence < self.config.min_confidence:
                logger.info(
                    "AI enrichment confidence too low: %.2f < %.2f",
                    ai_result.confidence,
                    self.config.min_confidence
                )
                self.metrics['low_confidence'] += 1
                return None
            
            # Track processing time
            ai_result.processing_time_ms = (time.time() - start_time) * 1000
            self.metrics['success'] += 1
            
            return ai_result
            
        except Exception as e:
            logger.warning("AI enrichment failed: %s", str(e), exc_info=True)
            self.metrics['failed'] += 1
            return None
    
    def _safe_ai_call(
        self,
        deterministic_result: DeterministicResult,
        signal: TestSignal,
        context: Optional[Dict[str, Any]]
    ) -> Optional[AIResult]:
        """
        Call AI with timeout protection and error handling.
        
        Returns:
            AIResult or None on failure
        """
        if not self.ai_analyzer:
            logger.debug("No AI analyzer configured")
            return None
        
        # Build structured prompt
        prompt = self._build_enrichment_prompt(deterministic_result, signal, context)
        
        try:
            # Call AI with timeout
            response = self._call_ai_with_timeout(prompt)
            
            if not response:
                return None
            
            # Parse AI response into AIResult
            return self._parse_ai_response(response, deterministic_result.label)
            
        except TimeoutError:
            logger.warning("AI enrichment timeout after %dms", self.config.timeout_ms)
            self.metrics['timeout'] += 1
            return None
        except Exception as e:
            logger.error("AI call failed: %s", str(e))
            return None
    
    def _build_enrichment_prompt(
        self,
        deterministic_result: DeterministicResult,
        signal: TestSignal,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Build structured prompt for AI enrichment.
        
        IMPORTANT: Prompt is constrained and structured to prevent hallucination.
        """
        prompt_parts = [
            "You are analyzing a test classification result.",
            "",
            f"Classification: {deterministic_result.label.value}",
            f"Confidence: {deterministic_result.confidence:.0%}",
            f"Deterministic Reasons:",
        ]
        
        for reason in deterministic_result.reasons:
            prompt_parts.append(f"  - {reason}")
        
        prompt_parts.append("")
        prompt_parts.append("Signals:")
        for key, value in signal.summary().items():
            prompt_parts.append(f"  - {key}: {value}")
        
        # Add context if available
        if context:
            if context.get('similar_failures'):
                prompt_parts.append("")
                prompt_parts.append("Similar failures:")
                for failure in context['similar_failures'][:3]:
                    prompt_parts.append(f"  - {failure}")
            
            if context.get('graph_neighbors'):
                prompt_parts.append("")
                prompt_parts.append("Related tests:")
                for neighbor in context['graph_neighbors'][:3]:
                    prompt_parts.append(f"  - {neighbor}")
        
        prompt_parts.extend([
            "",
            "Provide:",
            "1. Brief explanation of possible root causes (2-3 sentences max)",
            "2. Risk level assessment (low/medium/high)",
            "3. Specific recommended actions (1-3 bullet points)",
            "",
            "Be concise and actionable. Do NOT change the classification."
        ])
        
        return "\n".join(prompt_parts)
    
    def _call_ai_with_timeout(self, prompt: str) -> Optional[str]:
        """
        Call AI analyzer with timeout protection.
        
        Args:
            prompt: The enrichment prompt
            
        Returns:
            AI response string or None
        """
        # TODO: Implement actual AI call with timeout
        # For now, return mock response for testing
        
        # In production, this would call:
        # return self.ai_analyzer.analyze(
        #     prompt,
        #     max_tokens=500,
        #     timeout_ms=self.config.timeout_ms
        # )
        
        return None
    
    def _parse_ai_response(
        self,
        response: str,
        classification: ClassificationLabel
    ) -> AIResult:
        """
        Parse AI response into structured AIResult.
        
        Args:
            response: Raw AI response text
            classification: The deterministic classification
            
        Returns:
            Parsed AIResult
        """
        # TODO: Implement actual parsing logic
        # This is a placeholder that shows the structure
        
        return AIResult(
            insights=[],
            suggested_actions=[],
            similarity_refs=[],
            root_cause_hints=[],
            confidence=0.7,
            model_used=self.config.model
        )
    
    def get_metrics(self) -> Dict[str, int]:
        """Get enrichment metrics for observability."""
        return self.metrics.copy()


def safe_ai_enrich(
    deterministic_result: DeterministicResult,
    signal: SignalData,
    ai_enricher: Optional[AIEnricher] = None,
    context: Optional[Dict[str, Any]] = None
) -> Optional[AIResult]:
    """
    Safe wrapper for AI enrichment.
    
    This function guarantees:
    - No exceptions propagate to caller
    - Metrics are always tracked
    - Failures are logged
    - None returned on any failure
    
    Args:
        deterministic_result: The deterministic classification
        signal: Test signals
        ai_enricher: AI enricher instance (optional)
        context: Additional context
        
    Returns:
        AIResult if successful, None otherwise
    """
    if not ai_enricher:
        return None
    
    try:
        return ai_enricher.enrich(deterministic_result, signal, context)
    except Exception as e:
        logger.error("AI enrichment wrapper failed: %s", str(e))
        return None


def merge_results(
    deterministic_result: DeterministicResult,
    signal: SignalData,
    ai_result: Optional[AIResult] = None
) -> FinalResult:
    """
    Merge deterministic and AI results into final output.
    
    CRITICAL: The deterministic result is the PRIMARY source.
    AI enrichment is ADDITIVE only.
    
    Args:
        deterministic_result: The deterministic classification (mandatory)
        signal: Original test signal
        ai_result: Optional AI enrichment
        
    Returns:
        FinalResult combining both sources
    """
    return FinalResult(
        label=deterministic_result.label.value,
        deterministic_confidence=deterministic_result.confidence,
        deterministic_reasons=deterministic_result.reasons,
        ai_enrichment=ai_result,
        test_name=signal.test_name
    )
