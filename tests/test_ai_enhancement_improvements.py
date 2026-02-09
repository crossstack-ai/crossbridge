"""
Unit tests for enhanced AI enhancement module.

Tests structured prompts, LLM output sanitization, severity scoring,
and multi-provider consensus features.
"""

import pytest
from unittest.mock import Mock, patch
from core.execution.intelligence.ai_enhancement import (
    AIEnhancer,
    MultiProviderAggregator
)
from core.execution.intelligence.models import (
    FailureClassification,
    FailureSignal,
    ExecutionEvent,
    FailureType,
    SignalType,
    LogLevel
)


class TestAIEnhancer:
    """Test AIEnhancer class"""
    
    def test_initialization_default(self):
        """Test default initialization"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        assert enhancer.ai_provider == provider
        assert enhancer.enable_clustering is True
        assert enhancer.cluster_threshold == 0.8
    
    def test_initialization_custom(self):
        """Test custom initialization"""
        provider = Mock()
        enhancer = AIEnhancer(
            provider,
            enable_clustering=False,
            cluster_threshold=0.9
        )
        
        assert enhancer.enable_clustering is False
        assert enhancer.cluster_threshold == 0.9
    
    def test_enhance_without_clustering(self):
        """Test enhancement without clustering"""
        provider = Mock()
        provider.complete = Mock(return_value='{"findings": [], "overallSeverity": "Medium", "confidenceAdjustment": 0.0, "reasoning": "Test"}')
        
        enhancer = AIEnhancer(provider, enable_clustering=False)
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.8,
            reason="API returned 500"
        )
        
        signals = [
            FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error")
        ]
        
        events = []
        context = {}
        
        result = enhancer.enhance(classification, signals, events, context)
        
        assert result.ai_enhanced is True
        assert result.failure_type == FailureType.PRODUCT_DEFECT  # Never changes
    
    def test_enhance_with_clustering(self):
        """Test enhancement with clustering enabled"""
        provider = Mock()
        provider.complete = Mock(return_value='{"findings": [], "overallSeverity": "High", "confidenceAdjustment": 0.05, "reasoning": "Critical error"}')
        
        enhancer = AIEnhancer(provider, enable_clustering=True)
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.7,
            reason="Multiple failures"
        )
        
        # Multiple similar signals
        signals = [
            FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error"),
            FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error"),
            FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error"),
        ]
        
        result = enhancer.enhance(classification, signals, [], {})
        
        # Should have called provider
        assert provider.complete.called
        assert result.ai_enhanced is True
        assert result.confidence == 0.75  # 0.7 + 0.05
    
    def test_enhance_failure_returns_original(self):
        """Test that enhancement failure returns original classification"""
        provider = Mock()
        provider.complete = Mock(side_effect=Exception("Provider failed"))
        
        enhancer = AIEnhancer(provider)
        
        classification = FailureClassification(
            failure_type=FailureType.AUTOMATION_DEFECT,
            confidence=0.9,
            reason="Test error"
        )
        
        result = enhancer.enhance(classification, [], [], {})
        
        # Should return original on error
        assert result == classification
    
    def test_extract_json_from_pure_json(self):
        """Test extracting JSON from pure JSON response"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        response = '{"findings": [], "overallSeverity": "Medium", "confidenceAdjustment": 0.0}'
        result = enhancer._extract_json_from_response(response)
        
        assert result["overallSeverity"] == "Medium"
        assert "findings" in result
    
    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code block"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        response = """Here's the analysis:
```json
{
  "findings": [],
  "overallSeverity": "High",
  "confidenceAdjustment": 0.1
}
```
"""
        result = enhancer._extract_json_from_response(response)
        
        assert result["overallSeverity"] == "High"
        assert result["confidenceAdjustment"] == 0.1
    
    def test_extract_json_from_mixed_content(self):
        """Test extracting JSON from response with extra text"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        response = """I'll analyze this failure.
        
The JSON response is: {"findings": [], "overallSeverity": "Low", "confidenceAdjustment": -0.05}

Hope this helps!"""
        
        result = enhancer._extract_json_from_response(response)
        
        assert result["overallSeverity"] == "Low"
    
    def test_extract_json_failure_returns_fallback(self):
        """Test that failed JSON extraction returns fallback"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        response = "This is not JSON at all"
        result = enhancer._extract_json_from_response(response)
        
        # Should return valid fallback structure
        assert "findings" in result
        assert "overallSeverity" in result
        assert result["findings"] == []
    
    def test_sanitize_apology_phrases(self):
        """Test sanitization removes apology phrases"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        response = {
            "findings": [],
            "reasoning": "I'm sorry, as an AI model I cannot access real-time data. However, the error suggests a problem."
        }
        
        sanitized = enhancer._sanitize_llm_output(response)
        
        # Should remove apology
        assert "I'm sorry" not in sanitized["reasoning"]
        assert "cannot access" not in sanitized["reasoning"]
        assert "suggests a problem" in sanitized["reasoning"]
    
    def test_sanitize_llm_disclaimers(self):
        """Test sanitization removes LLM disclaimers"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        response = {
            "findings": [{
                "rootCause": "As a large language model, I believe this is a timeout issue.",
                "recommendedAction": "Please note that you should increase timeout."
            }]
        }
        
        sanitized = enhancer._sanitize_llm_output(response)
        
        finding = sanitized["findings"][0]
        assert "large language model" not in finding["rootCause"]
        assert "timeout issue" in finding["rootCause"]
        assert "Please note that" not in finding["recommendedAction"]
    
    def test_confidence_adjustment_clamped(self):
        """Test that confidence adjustments are clamped to ±0.1"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.5,
            reason="Test"
        )
        
        # Try large positive adjustment
        ai_response = {
            "findings": [],
            "confidenceAdjustment": 0.5,  # Too large
            "overallSeverity": "High"
        }
        
        result = enhancer._parse_ai_response(classification, ai_response, [])
        
        # Should be clamped to 0.5 + 0.1 = 0.6
        assert result.confidence == 0.6
    
    def test_confidence_clamped_to_range(self):
        """Test that final confidence stays in [0, 1] range"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        classification = FailureClassification(
            failure_type=FailureType.AUTOMATION_DEFECT,
            confidence=0.95,
            reason="Test"
        )
        
        ai_response = {
            "findings": [],
            "confidenceAdjustment": 0.1,  # Would push to 1.05
            "overallSeverity": "High"
        }
        
        result = enhancer._parse_ai_response(classification, ai_response, [])
        
        # Should be clamped to 1.0
        assert result.confidence == 1.0
    
    def test_parse_ai_response_with_findings(self):
        """Test parsing AI response with multiple findings"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.7,
            reason="Original reason"
        )
        
        ai_response = {
            "findings": [
                {
                    "rootCause": "Database connection timeout",
                    "recommendedAction": "Increase connection pool size",
                    "severity": "High",
                    "confidenceScore": 0.92,
                    "evidence": [{"text": "Connection refused", "logIndex": 10}]
                },
                {
                    "rootCause": "Missing configuration",
                    "recommendedAction": "Add DB_HOST env variable",
                    "severity": "Medium",
                    "confidenceScore": 0.78
                }
            ],
            "overallSeverity": "High",
            "confidenceAdjustment": 0.05,
            "reasoning": "Multiple database issues detected"
        }
        
        result = enhancer._parse_ai_response(classification, ai_response, [])
        
        # Should include AI findings in reason
        assert "Database connection timeout" in result.reason
        assert "Increase connection pool size" in result.reason
        assert result.confidence == 0.75
        assert result.ai_reasoning == "Multiple database issues detected"
    
    def test_failure_type_never_changes(self):
        """Test that AI never changes the failure type"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        original_type = FailureType.AUTOMATION_DEFECT
        classification = FailureClassification(
            failure_type=original_type,
            confidence=0.6,
            reason="Test error"
        )
        
        # Even if AI suggests different severity/confidence
        ai_response = {
            "findings": [],
            "overallSeverity": "High",
            "confidenceAdjustment": 0.3
        }
        
        result = enhancer._parse_ai_response(classification, ai_response, [])
        
        # Failure type must remain unchanged
        assert result.failure_type == original_type


class TestMultiProviderAggregator:
    """Test MultiProviderAggregator for consensus analysis"""
    
    def test_initialization(self):
        """Test aggregator initialization"""
        providers = {
            "openai": Mock(),
            "anthropic": Mock()
        }
        
        aggregator = MultiProviderAggregator(providers)
        
        assert len(aggregator.providers) == 2
        assert len(aggregator.enhancers) == 2
    
    def test_consensus_with_single_provider(self):
        """Test consensus with single provider"""
        provider = Mock()
        provider.complete = Mock(return_value='{"findings": [], "overallSeverity": "Medium", "confidenceAdjustment": 0.0, "reasoning": "Test"}')
        
        aggregator = MultiProviderAggregator({"test": provider})
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.8,
            reason="Test"
        )
        
        result = aggregator.enhance_with_consensus(classification, [], [], {})
        
        assert "consensus" in result
        assert "provider_reports" in result
        assert "agreement_score" in result
        assert result["agreement_score"] == 1.0  # Single provider = perfect agreement
    
    def test_consensus_with_multiple_providers(self):
        """Test consensus averaging multiple providers"""
        provider1 = Mock()
        provider1.complete = Mock(return_value='{"findings": [], "overallSeverity": "High", "confidenceAdjustment": 0.1, "reasoning": "Critical"}')
        
        provider2 = Mock()
        provider2.complete = Mock(return_value='{"findings": [], "overallSeverity": "Medium", "confidenceAdjustment": 0.0, "reasoning": "Moderate"}')
        
        aggregator = MultiProviderAggregator({
            "provider1": provider1,
            "provider2": provider2
        })
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.7,
            reason="Test"
        )
        
        result = aggregator.enhance_with_consensus(classification, [], [], {})
        
        consensus = result["consensus"]
        
        # Consensus confidence should be average: (0.8 + 0.7) / 2 = 0.75
        assert 0.7 <= consensus.confidence <= 0.8
        assert consensus.ai_enhanced is True
    
    def test_provider_failure_handled_gracefully(self):
        """Test that provider failures don't crash aggregation"""
        good_provider = Mock()
        good_provider.complete = Mock(return_value='{"findings": [], "overallSeverity": "Medium", "confidenceAdjustment": 0.0, "reasoning": "Good"}')
        
        bad_provider = Mock()
        bad_provider.complete = Mock(side_effect=Exception("Provider crashed"))
        
        aggregator = MultiProviderAggregator({
            "good": good_provider,
            "bad": bad_provider
        })
        
        classification = FailureClassification(
            failure_type=FailureType.AUTOMATION_DEFECT,
            confidence=0.6,
            reason="Test"
        )
        
        result = aggregator.enhance_with_consensus(classification, [], [], {})
        
        # Should still return consensus from good provider
        assert "consensus" in result
        assert "good" in result["provider_reports"]
        assert "bad" in result["provider_reports"]
        assert "error" in result["provider_reports"]["bad"]
    
    def test_agreement_score_high_when_similar(self):
        """Test agreement score is high when providers agree"""
        provider1 = Mock()
        provider1.complete = Mock(return_value='{"findings": [], "overallSeverity": "High", "confidenceAdjustment": 0.05, "reasoning": "Test"}')
        
        provider2 = Mock()
        provider2.complete = Mock(return_value='{"findings": [], "overallSeverity": "High", "confidenceAdjustment": 0.04, "reasoning": "Test"}')
        
        aggregator = MultiProviderAggregator({
            "p1": provider1,
            "p2": provider2
        })
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.7,
            reason="Test"
        )
        
        result = aggregator.enhance_with_consensus(classification, [], [], {})
        
        # Similar confidences should yield high agreement
        assert result["agreement_score"] > 0.9
    
    def test_all_providers_fail_returns_original(self):
        """Test that if all providers fail, original classification is returned"""
        bad_provider1 = Mock()
        bad_provider1.complete = Mock(side_effect=Exception("Failed"))
        
        bad_provider2 = Mock()
        bad_provider2.complete = Mock(side_effect=Exception("Failed"))
        
        aggregator = MultiProviderAggregator({
            "bad1": bad_provider1,
            "bad2": bad_provider2
        })
        
        classification = FailureClassification(
            failure_type=FailureType.ENVIRONMENT_ISSUE,
            confidence=0.5,
            reason="Original"
        )
        
        result = aggregator.enhance_with_consensus(classification, [], [], {})
        
        # Should return original classification
        consensus = result["consensus"]
        assert consensus.failure_type == FailureType.ENVIRONMENT_ISSUE
        assert consensus.confidence == 0.5
        assert result["agreement_score"] == 0.0


class TestStructuredPrompt:
    """Test structured prompt generation"""
    
    def test_structured_prompt_includes_constraints(self):
        """Test that structured prompt includes strict constraints"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.8,
            reason="API error"
        )
        
        prompt = enhancer._build_structured_prompt(classification, [], [], {})
        
        # Should include strict instructions
        assert "DO NOT OVERRIDE" in prompt
        assert "MANDATORY FORMAT" in prompt
        assert "ONLY with valid JSON" in prompt
        assert "No extra text" in prompt
        assert "no apologies" in prompt
    
    def test_structured_prompt_shows_failure_type(self):
        """Test that prompt clearly shows determined failure type"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        classification = FailureClassification(
            failure_type=FailureType.AUTOMATION_DEFECT,
            confidence=0.9,
            reason="Locator error"
        )
        
        prompt = enhancer._build_structured_prompt(classification, [], [], {})
        
        assert "AUTOMATION_DEFECT" in prompt
        assert "0.90" in prompt or "0.9" in prompt


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_signals_list(self):
        """Test enhancement with empty signals list"""
        provider = Mock()
        provider.complete = Mock(return_value='{"findings": [], "overallSeverity": "Low", "confidenceAdjustment": 0.0}')
        
        enhancer = AIEnhancer(provider)
        
        classification = FailureClassification(
            failure_type=FailureType.UNKNOWN,
            confidence=0.5,
            reason="Unknown error"
        )
        
        result = enhancer.enhance(classification, [], [], {})
        
        assert result.ai_enhanced is True
    
    def test_invalid_json_in_findings(self):
        """Test handling of malformed findings"""
        provider = Mock()
        enhancer = AIEnhancer(provider)
        
        # Missing required fields
        ai_response = {
            "findings": [
                {"severity": "High"}  # Missing rootCause, recommendedAction
            ],
            "overallSeverity": "High",
            "confidenceAdjustment": 0.0
        }
        
        classification = FailureClassification(
            failure_type=FailureType.PRODUCT_DEFECT,
            confidence=0.7,
            reason="Test"
        )
        
        # Should not crash
        result = enhancer._parse_ai_response(classification, ai_response, [])
        
        assert result.confidence == 0.7
