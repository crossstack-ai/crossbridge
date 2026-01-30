"""
AI Enhancement Layer (OPTIONAL)

Provides optional AI-powered enhancements to deterministic classification.

CRITICAL: AI never overrides deterministic classification.
AI only enhances by:
- Adjusting confidence based on historical patterns
- Providing more detailed explanations
- Suggesting potential fixes
- Correlating with similar past failures

System works perfectly WITHOUT AI - this is purely additive.
"""

from typing import List, Dict, Any, Optional
import logging

from core.execution.intelligence.models import (
    FailureClassification,
    FailureSignal,
    ExecutionEvent,
    FailureType,
)
from core.logging import get_logger

logger = get_logger(__name__)


class AIEnhancer:
    """
    AI enhancement layer for failure classification.
    
    Works as an OPTIONAL plugin - system functions fully without it.
    """
    
    def __init__(self, ai_provider: Any):
        """
        Initialize AI enhancer.
        
        Args:
            ai_provider: AI provider instance (e.g., OpenAI, Anthropic)
        """
        self.ai_provider = ai_provider
    
    def enhance(
        self,
        classification: FailureClassification,
        signals: List[FailureSignal],
        events: List[ExecutionEvent],
        context: Dict[str, Any]
    ) -> FailureClassification:
        """
        Enhance classification with AI reasoning.
        
        Args:
            classification: Original deterministic classification
            signals: Extracted failure signals
            events: Execution events
            context: Additional context
            
        Returns:
            Enhanced classification (never overrides failure_type)
        """
        try:
            # Build AI prompt
            prompt = self._build_prompt(classification, signals, events, context)
            
            # Query AI
            ai_response = self._query_ai(prompt)
            
            # Parse AI response
            enhanced_classification = self._parse_ai_response(
                classification, ai_response
            )
            
            # Mark as AI-enhanced
            enhanced_classification.ai_enhanced = True
            enhanced_classification.ai_reasoning = ai_response.get('reasoning', '')
            
            logger.info(
                f"AI enhancement applied: confidence {classification.confidence:.2f} -> "
                f"{enhanced_classification.confidence:.2f}"
            )
            
            return enhanced_classification
        
        except Exception as e:
            logger.error(f"AI enhancement failed: {str(e)}")
            # Return original classification on error
            return classification
    
    def _build_prompt(
        self,
        classification: FailureClassification,
        signals: List[FailureSignal],
        events: List[ExecutionEvent],
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for AI"""
        signal_summary = '\n'.join([
            f"- {s.signal_type.value}: {s.message[:100]}"
            for s in signals[:5]
        ])
        
        prompt = f"""You are an expert test automation failure analyzer.

DETERMINISTIC CLASSIFICATION (DO NOT OVERRIDE):
- Failure Type: {classification.failure_type.value}
- Confidence: {classification.confidence:.2f}
- Rule Matched: {classification.rule_matched}
- Reason: {classification.reason}

FAILURE SIGNALS:
{signal_summary}

TASK:
Enhance this classification by:
1. Adjusting confidence (if historical patterns suggest)
2. Providing more detailed explanation
3. Suggesting potential root cause
4. Recommending fix (if applicable)

CONSTRAINTS:
- Do NOT change the failure type ({classification.failure_type.value})
- Confidence adjustments must be small (±0.1 max)
- Be concise and actionable

Respond in JSON format:
{{
    "confidence_adjustment": 0.0,  // -0.1 to +0.1
    "reasoning": "Detailed explanation...",
    "root_cause": "Likely root cause...",
    "suggested_fix": "Potential fix..."
}}
"""
        return prompt
    
    def _query_ai(self, prompt: str) -> Dict[str, Any]:
        """Query AI provider"""
        # This is a placeholder - actual implementation depends on AI provider
        # Could use OpenAI, Anthropic, local LLM, etc.
        
        if hasattr(self.ai_provider, 'complete'):
            response = self.ai_provider.complete(prompt)
        elif hasattr(self.ai_provider, 'chat'):
            response = self.ai_provider.chat([{"role": "user", "content": prompt}])
        else:
            raise ValueError("AI provider does not support completion or chat")
        
        # Parse JSON response
        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback - extract JSON from markdown code blocks
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
                return json.loads(json_str)
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
                return json.loads(json_str)
            else:
                return {"reasoning": response}
    
    def _parse_ai_response(
        self,
        classification: FailureClassification,
        ai_response: Dict[str, Any]
    ) -> FailureClassification:
        """Parse AI response and enhance classification"""
        # Adjust confidence (small adjustments only)
        confidence_adj = ai_response.get('confidence_adjustment', 0.0)
        confidence_adj = max(-0.1, min(0.1, confidence_adj))  # Clamp to ±0.1
        
        new_confidence = classification.confidence + confidence_adj
        new_confidence = max(0.0, min(1.0, new_confidence))  # Clamp to [0, 1]
        
        # Enhance reason if AI provides better explanation
        reason = classification.reason
        if ai_response.get('root_cause'):
            reason = f"{reason}\n\nAI Analysis: {ai_response['root_cause']}"
        
        # Add suggested fix to reason
        if ai_response.get('suggested_fix'):
            reason = f"{reason}\n\nSuggested Fix: {ai_response['suggested_fix']}"
        
        # Create enhanced classification
        return FailureClassification(
            failure_type=classification.failure_type,  # NEVER change this
            confidence=new_confidence,
            reason=reason,
            evidence=classification.evidence,
            code_reference=classification.code_reference,
            rule_matched=classification.rule_matched,
            ai_enhanced=True,
            ai_reasoning=ai_response.get('reasoning', ''),
            similar_failures_count=classification.similar_failures_count,
            last_seen=classification.last_seen,
        )


class HistoricalCorrelation:
    """
    Correlates current failure with historical failures.
    
    This can help identify:
    - Flaky tests (intermittent failures)
    - Known issues (recurring patterns)
    - Recent regressions (new failure patterns)
    """
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize historical correlation.
        
        Args:
            database_path: Path to historical failure database
        """
        self.database_path = database_path
    
    def correlate(
        self,
        classification: FailureClassification,
        test_name: str,
        lookback_days: int = 30
    ) -> FailureClassification:
        """
        Correlate with historical failures.
        
        Args:
            classification: Current classification
            test_name: Test name
            lookback_days: Days to look back
            
        Returns:
            Enhanced classification with historical context
        """
        # TODO: Implement database query
        # This would query a historical failure database and:
        # 1. Count similar failures
        # 2. Find last occurrence
        # 3. Identify if this is a new pattern
        # 4. Check if this is a known flaky test
        
        # For now, return as-is
        return classification
