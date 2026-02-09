"""
Unit tests for failure clustering module.

Tests the ability to group similar failures to reduce AI analysis redundancy.
"""

import pytest
from core.execution.intelligence.failure_clustering import (
    FailureClusterer,
    FailureCluster,
    cluster_similar_failures
)
from core.execution.intelligence.models import FailureSignal, SignalType


class TestFailureClusterer:
    """Test FailureClusterer class"""
    
    def test_initialization(self):
        """Test clusterer initialization"""
        clusterer = FailureClusterer(similarity_threshold=0.8)
        assert clusterer.similarity_threshold == 0.8
    
    def test_empty_signals(self):
        """Test clustering with no signals"""
        clusterer = FailureClusterer()
        clusters = clusterer.cluster([])
        assert clusters == []
    
    def test_single_signal(self):
        """Test clustering with single signal"""
        clusterer = FailureClusterer()
        signal = FailureSignal(
            signal_type=SignalType.HTTP_ERROR,
            message="HTTP 500 Internal Server Error"
        )
        
        clusters = clusterer.cluster([signal])
        
        assert len(clusters) == 1
        assert clusters[0].count == 1
        assert clusters[0].representative_signal == signal
    
    def test_identical_signals_cluster_together(self):
        """Test that identical errors cluster together"""
        clusterer = FailureClusterer()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.HTTP_ERROR,
                message="HTTP 400 Bad Request"
            ),
            FailureSignal(
                signal_type=SignalType.HTTP_ERROR,
                message="HTTP 400 Bad Request"
            ),
            FailureSignal(
                signal_type=SignalType.HTTP_ERROR,
                message="HTTP 400 Bad Request"
            )
        ]
        
        clusters = clusterer.cluster(signals)
        
        assert len(clusters) == 1
        assert clusters[0].count == 3
    
    def test_similar_signals_with_different_numbers_cluster(self):
        """Test that similar errors with different numeric values cluster together"""
        clusterer = FailureClusterer()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.ASSERTION_ERROR,
                message="Expected 200 but got 400"
            ),
            FailureSignal(
                signal_type=SignalType.ASSERTION_ERROR,
                message="Expected 201 but got 500"
            ),
            FailureSignal(
                signal_type=SignalType.ASSERTION_ERROR,
                message="Expected 204 but got 404"
            )
        ]
        
        clusters = clusterer.cluster(signals)
        
        # All should cluster together (same pattern: "expected {NUM} but got {NUM}")
        assert len(clusters) == 1
        assert clusters[0].count == 3
    
    def test_different_error_types_separate_clusters(self):
        """Test that different error types form separate clusters"""
        clusterer = FailureClusterer()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.HTTP_ERROR,
                message="HTTP 500 Internal Server Error"
            ),
            FailureSignal(
                signal_type=SignalType.TIMEOUT,
                message="Connection timeout after 30 seconds"
            ),
            FailureSignal(
                signal_type=SignalType.ASSERTION_ERROR,
                message="Expected true but got false"
            )
        ]
        
        clusters = clusterer.cluster(signals)
        
        assert len(clusters) == 3
        assert all(c.count == 1 for c in clusters)
    
    def test_pattern_extraction_numbers(self):
        """Test pattern extraction replaces numbers correctly"""
        clusterer = FailureClusterer()
        
        pattern = clusterer._extract_pattern("Error on line 42")
        assert pattern == "error on line {num}"
    
    def test_pattern_extraction_paths(self):
        """Test pattern extraction replaces file paths"""
        clusterer = FailureClusterer()
        
        pattern = clusterer._extract_pattern("File not found: /home/user/test.py")
        assert "{path}" in pattern.lower()
    
    def test_pattern_extraction_urls(self):
        """Test pattern extraction replaces URLs"""
        clusterer = FailureClusterer()
        
        pattern = clusterer._extract_pattern("Failed to fetch https://api.example.com/data")
        assert "{url}" in pattern.lower()
    
    def test_pattern_extraction_uuids(self):
        """Test pattern extraction replaces UUIDs"""
        clusterer = FailureClusterer()
        
        pattern = clusterer._extract_pattern(
            "Resource a1b2c3d4-e5f6-7890-abcd-1234567890ab not found"
        )
        assert "{uuid}" in pattern.lower()
    
    def test_severity_inference_high(self):
        """Test high severity inference"""
        clusterer = FailureClusterer()
        
        signal = FailureSignal(
            signal_type=SignalType.HTTP_ERROR,
            message="HTTP 500 Internal Server Error - data loss detected"
        )
        
        severity = clusterer._infer_severity(signal)
        assert severity == "High"
    
    def test_severity_inference_medium(self):
        """Test medium severity inference"""
        clusterer = FailureClusterer()
        
        signal = FailureSignal(
            signal_type=SignalType.TIMEOUT,
            message="Request timeout after 30 seconds"
        )
        
        severity = clusterer._infer_severity(signal)
        assert severity == "Medium"
    
    def test_severity_inference_low(self):
        """Test low severity inference"""
        clusterer = FailureClusterer()
        
        signal = FailureSignal(
            signal_type=SignalType.VALIDATION_ERROR,
            message="Invalid email format"
        )
        
        severity = clusterer._infer_severity(signal)
        assert severity == "Low"
    
    def test_cluster_sorting_by_count(self):
        """Test that clusters are sorted by count (most common first)"""
        clusterer = FailureClusterer()
        
        signals = [
            # 5 of type A
            *[FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error") for _ in range(5)],
            # 2 of type B
            *[FailureSignal(SignalType.TIMEOUT, "Timeout occurred") for _ in range(2)],
            # 8 of type C
            *[FailureSignal(SignalType.ASSERTION_ERROR, "Assertion failed") for _ in range(8)],
        ]
        
        clusters = clusterer.cluster(signals)
        
        assert len(clusters) == 3
        assert clusters[0].count == 8  # Most common first
        assert clusters[1].count == 5
        assert clusters[2].count == 2
    
    def test_cluster_to_dict(self):
        """Test cluster serialization to dict"""
        signal = FailureSignal(
            signal_type=SignalType.HTTP_ERROR,
            message="HTTP 400 Bad Request"
        )
        
        cluster = FailureCluster(
            representative_signal=signal,
            cluster_signals=[signal, signal],
            count=2,
            pattern="http {num} bad request",
            severity="Medium"
        )
        
        result = cluster.to_dict()
        
        assert result["count"] == 2
        assert result["pattern"] == "http {num} bad request"
        assert result["severity"] == "Medium"
        assert result["signal_type"] == SignalType.HTTP_ERROR.value
        assert "HTTP 400" in result["representative_message"]
    
    def test_reduction_percentage_calculation(self):
        """Test that clustering achieves expected reduction"""
        clusterer = FailureClusterer()
        
        # Create 100 signals with only 5 unique patterns
        signals = []
        patterns = [
            "HTTP 400 error",
            "Timeout after seconds",
            "Expected value got value",
            "Connection refused",
            "Resource not found"
        ]
        
        for i in range(100):
            pattern = patterns[i % 5]
            signals.append(
                FailureSignal(
                    SignalType.HTTP_ERROR,
                    f"{pattern} {i}"  # Add number to make them slightly different
                )
            )
        
        clusters = clusterer.cluster(signals)
        
        # Should cluster into ~5 groups
        assert len(clusters) <= 10  # Some tolerance for pattern matching
        reduction = (1 - len(clusters) / len(signals)) * 100
        assert reduction >= 80  # At least 80% reduction


class TestConvenienceFunction:
    """Test cluster_similar_failures convenience function"""
    
    def test_convenience_function(self):
        """Test the convenience function works"""
        signals = [
            FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error"),
            FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error"),
        ]
        
        clusters = cluster_similar_failures(signals)
        
        assert len(clusters) == 1
        assert clusters[0].count == 2
    
    def test_convenience_function_with_threshold(self):
        """Test convenience function with custom threshold"""
        signals = [
            FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error")
        ]
        
        clusters = cluster_similar_failures(signals, threshold=0.9)
        
        assert len(clusters) == 1
    
    def test_convenience_function_semantic_mode(self):
        """Test convenience function with semantic mode"""
        signals = [
            FailureSignal(SignalType.HTTP_ERROR, "HTTP 500 Error"),
            FailureSignal(SignalType.HTTP_ERROR, "Internal Server Error"),
        ]
        
        # Should work even if semantic libraries not available (falls back to rules)
        clusters = cluster_similar_failures(signals, use_semantic=True)
        
        assert len(clusters) >= 1


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_none_message_handling(self):
        """Test handling of None messages"""
        clusterer = FailureClusterer()
        
        signal = FailureSignal(
            signal_type=SignalType.UNKNOWN,
            message=None
        )
        
        # Should not crash
        pattern = clusterer._extract_pattern(signal.message or "")
        assert isinstance(pattern, str)
    
    def test_very_long_message(self):
        """Test handling of very long error messages"""
        clusterer = FailureClusterer()
        
        signal = FailureSignal(
            signal_type=SignalType.STACK_TRACE,
            message="Error: " + "A" * 10000  # Very long message
        )
        
        clusters = clusterer.cluster([signal])
        
        assert len(clusters) == 1
    
    def test_special_characters_in_message(self):
        """Test handling of special characters"""
        clusterer = FailureClusterer()
        
        signal = FailureSignal(
            signal_type=SignalType.VALIDATION_ERROR,
            message="Invalid JSON: {\"key\": \"value\", 'other': null}"
        )
        
        pattern = clusterer._extract_pattern(signal.message)
        
        # Should handle special characters without crashing
        assert isinstance(pattern, str)
    
    def test_empty_message(self):
        """Test handling of empty messages"""
        clusterer = FailureClusterer()
        
        signal = FailureSignal(
            signal_type=SignalType.UNKNOWN,
            message=""
        )
        
        clusters = clusterer.cluster([signal])
        
        assert len(clusters) == 1
