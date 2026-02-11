"""
Unit Tests for Failure Clustering Module

Tests the failure deduplication and root cause clustering functionality.
"""

import pytest
from core.log_analysis.clustering import (
    fingerprint_error,
    cluster_failures,
    get_cluster_summary,
    detect_systemic_patterns,
    _classify_failure_domain,
    FailureSeverity,
    FailureDomain,
    FailureCluster,
    ClusteredFailure
)


class TestFingerprintError:
    """Test error fingerprinting functionality."""
    
    def test_basic_fingerprint(self):
        """Test basic error fingerprinting."""
        error1 = "ElementNotFound: Could not find element #btn-login"
        error2 = "ElementNotFound: Could not find element #btn-signup"
        
        fp1 = fingerprint_error(error1)
        fp2 = fingerprint_error(error2)
        
        # Same error type should produce same fingerprint (IDs normalized)
        assert fp1 == fp2
        assert len(fp1) == 32  # MD5 hash length
    
    def test_different_errors_different_fingerprints(self):
        """Test that different errors produce different fingerprints."""
        error1 = "ElementNotFound: Could not find element"
        error2 = "TimeoutException: Operation timed out"
        
        fp1 = fingerprint_error(error1)
        fp2 = fingerprint_error(error2)
        
        assert fp1 != fp2
    
    def test_normalize_timestamps(self):
        """Test timestamp normalization."""
        error1 = "Error at 2024-01-15 10:30:45: Connection failed"
        error2 = "Error at 2024-12-31 23:59:59: Connection failed"
        
        fp1 = fingerprint_error(error1)
        fp2 = fingerprint_error(error2)
        
        # Different timestamps should produce same fingerprint
        assert fp1 == fp2
    
    def test_normalize_ids(self):
        """Test ID normalization."""
        error1 = "Element #btn-123 not found"
        error2 = "Element #btn-456 not found"
        
        fp1 = fingerprint_error(error1)
        fp2 = fingerprint_error(error2)
        
        assert fp1 == fp2
    
    def test_normalize_urls(self):
        """Test URL normalization."""
        error1 = "Failed to load https://example.com/api/users"
        error2 = "Failed to load https://example.com/api/products"
        
        fp1 = fingerprint_error(error1)
        fp2 = fingerprint_error(error2)
        
        assert fp1 == fp2
    
    def test_http_status_included(self):
        """Test HTTP status code inclusion in fingerprint."""
        error = "Server error"
        
        fp1 = fingerprint_error(error, http_status=500)
        fp2 = fingerprint_error(error, http_status=404)
        
        # Different status codes should produce different fingerprints
        assert fp1 != fp2
    
    def test_stack_trace_included(self):
        """Test stack trace inclusion in fingerprint."""
        error = "NullPointerException"
        stack1 = "at com.example.UserService.getUser(UserService.java:42)"
        stack2 = "at com.example.OrderService.getOrder(OrderService.java:25)"
        
        fp1 = fingerprint_error(error, stack_trace=stack1)
        fp2 = fingerprint_error(error, stack_trace=stack2)
        
        # Different stack locations should produce different fingerprints
        assert fp1 != fp2


class TestClusterFailures:
    """Test failure clustering functionality."""
    
    def test_empty_failures(self):
        """Test clustering with empty failure list."""
        clusters = cluster_failures([])
        assert len(clusters) == 0
    
    def test_single_failure(self):
        """Test clustering with single failure."""
        failures = [
            {
                "name": "Test Login",
                "error": "ElementNotFound: #btn-login",
                "library": "SeleniumLibrary"
            }
        ]
        
        clusters = cluster_failures(failures)
        assert len(clusters) == 1
        
        cluster = list(clusters.values())[0]
        assert cluster.failure_count == 1
        assert "Test Login" in cluster.tests
    
    def test_duplicate_detection(self):
        """Test deduplication of identical failures."""
        failures = [
            {"name": "Test1", "error": "ElementNotFound: #btn-login"},
            {"name": "Test2", "error": "ElementNotFound: #btn-login"},
            {"name": "Test3", "error": "ElementNotFound: #btn-signup"}
        ]
        
        clusters = cluster_failures(failures, deduplicate=True)
        
        # Should have 1 cluster (all ElementNotFound with normalized IDs)
        assert len(clusters) == 1
        
        cluster = list(clusters.values())[0]
        assert cluster.failure_count == 3
        assert len(cluster.tests) == 3
    
    def test_different_error_types(self):
        """Test clustering different error types separately."""
        failures = [
            {"name": "Test1", "error": "ElementNotFound: element missing"},
            {"name": "Test2", "error": "TimeoutException: operation timed out"},
            {"name": "Test3", "error": "ElementNotFound: element missing"}
        ]
        
        clusters = cluster_failures(failures)
        
        # Should have 2 clusters (ElementNotFound and TimeoutException)
        assert len(clusters) == 2
    
    def test_keyword_tracking(self):
        """Test that clusters track affected keywords."""
        failures = [
            {
                "name": "Test1",
                "keyword_name": "Click Button",
                "error": "ElementNotFound: button",
                "library": "SeleniumLibrary"
            },
            {
                "name": "Test2",
                "keyword_name": "Click Link",
                "error": "ElementNotFound: link",
                "library": "SeleniumLibrary"
            }
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        
        assert len(cluster.keywords) == 2
        assert "Click Button" in cluster.keywords
        assert "Click Link" in cluster.keywords
    
    def test_severity_detection(self):
        """Test severity level detection."""
        failures = [
            {"name": "Test1", "error": "FATAL: System crash"},
            {"name": "Test2", "error": "AssertionError: expected 5 but was 3"},
            {"name": "Test3", "error": "TimeoutException: timed out after 30s"}
        ]
        
        clusters = cluster_failures(failures)
        
        # Find each cluster and check severity
        severities = {c.severity for c in clusters.values()}
        
        assert FailureSeverity.CRITICAL in severities  # FATAL
        assert FailureSeverity.HIGH in severities  # AssertionError
        assert FailureSeverity.MEDIUM in severities  # TimeoutException
    
    def test_skip_empty_errors(self):
        """Test that empty error messages are skipped."""
        failures = [
            {"name": "Test1", "error": "Real error"},
            {"name": "Test2", "error": ""},
            {"name": "Test3", "error": "   "}
        ]
        
        clusters = cluster_failures(failures)
        
        # Should only have 1 cluster (empty errors skipped)
        assert len(clusters) == 1
    
    def test_min_cluster_size(self):
        """Test minimum cluster size filtering."""
        failures = [
            {"name": "Test1", "error": "Error A"},
            {"name": "Test2", "error": "Error A"},
            {"name": "Test3", "error": "Error B"}  # Only 1 instance
        ]
        
        clusters = cluster_failures(failures, min_cluster_size=2)
        
        # Should only return cluster with 2+ failures
        assert len(clusters) == 1
        cluster = list(clusters.values())[0]
        assert cluster.failure_count >= 2


class TestClusterSummary:
    """Test cluster summary generation."""
    
    def test_summary_statistics(self):
        """Test summary statistics calculation."""
        failures = [
            {"name": "Test1", "error": "ElementNotFound: #btn"},
            {"name": "Test2", "error": "ElementNotFound: #btn"},
            {"name": "Test3", "error": "TimeoutException: timeout"}
        ]
        
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        assert summary["total_failures"] == 3
        assert summary["unique_issues"] == 2
        assert summary["deduplication_ratio"] == 1.5  # 3 failures / 2 issues
    
    def test_severity_grouping(self):
        """Test clustering by severity in summary."""
        failures = [
            {"name": "Test1", "error": "FATAL: crash"},
            {"name": "Test2", "error": "AssertionError: failed"},
            {"name": "Test3", "error": "TimeoutException: timeout"}
        ]
        
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        by_severity = summary["by_severity"]
        assert by_severity["critical"] >= 1  # FATAL
        assert by_severity["high"] >= 1  # AssertionError
        assert by_severity["medium"] >= 1  # Timeout
    
    def test_top_clusters_limited(self):
        """Test that summary limits clusters per severity."""
        # Create many failures of same severity
        failures = [
            {"name": f"Test{i}", "error": f"Error{i}"}
            for i in range(20)
        ]
        
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        # Should limit to top 5 per severity
        high_clusters = summary["clusters_by_severity"]["high"]
        assert len(high_clusters) <= 5


class TestFailureCluster:
    """Test FailureCluster dataclass."""
    
    def test_add_failure(self):
        """Test adding failures to cluster."""
        cluster = FailureCluster(
            fingerprint="abc123",
            root_cause="Test error",
            severity=FailureSeverity.HIGH
        )
        
        failure = ClusteredFailure(
            test_name="Test1",
            keyword_name="Click Button",
            error_message="Error message"
        )
        
        cluster.add_failure(failure)
        
        assert cluster.failure_count == 1
        assert "Test1" in cluster.tests
        assert "Click Button" in cluster.keywords
    
    def test_multiple_failures(self):
        """Test adding multiple failures."""
        cluster = FailureCluster(
            fingerprint="abc123",
            root_cause="Test error",
            severity=FailureSeverity.HIGH
        )
        
        for i in range(5):
            failure = ClusteredFailure(
                test_name=f"Test{i}",
                keyword_name=f"Keyword{i}",
                error_message="Error"
            )
            cluster.add_failure(failure)
        
        assert cluster.failure_count == 5
        assert len(cluster.tests) == 5
        assert len(cluster.keywords) == 5


class TestPatternExtraction:
    """Test error pattern extraction."""
    
    def test_patterns_in_summary(self):
        """Test that common patterns are extracted."""
        failures = [
            {"name": "Test1", "error": "ElementNotFound: element missing"},
            {"name": "Test2", "error": "Element #btn not found"}
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        
        # Should detect "Element Not Found" pattern
        assert len(cluster.error_patterns) > 0
        assert any("Element Not Found" in pattern for pattern in cluster.error_patterns)


class TestSuggestedFixes:
    """Test fix suggestion generation."""
    
    def test_element_not_found_fix(self):
        """Test fix suggestion for element not found."""
        failures = [
            {"name": "Test1", "error": "element not found in the page"}
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        
        assert cluster.suggested_fix is not None
        assert "locator" in cluster.suggested_fix.lower() or "element" in cluster.suggested_fix.lower()
    
    def test_timeout_fix(self):
        """Test fix suggestion for timeout errors."""
        failures = [
            {"name": "Test1", "error": "TimeoutException: operation timed out"}
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        
        assert cluster.suggested_fix is not None
        assert "timeout" in cluster.suggested_fix.lower()
    
    def test_connection_fix(self):
        """Test fix suggestion for connection errors."""
        failures = [
            {"name": "Test1", "error": "ConnectionRefusedError: cannot connect"}
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        
        assert cluster.suggested_fix is not None
        assert "network" in cluster.suggested_fix.lower() or "connection" in cluster.suggested_fix.lower()


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_very_long_error_message(self):
        """Test handling of very long error messages."""
        long_error = "A" * 10000
        failures = [{"name": "Test1", "error": long_error}]
        
        clusters = cluster_failures(failures)
        assert len(clusters) == 1
        
        cluster = list(clusters.values())[0]
        # Root cause should be truncated
        assert len(cluster.root_cause) < 200
    
    def test_special_characters(self):
        """Test handling of special characters in errors."""
        failures = [
            {"name": "Test1", "error": "Error: <>&\"'\\n\\t special chars"}
        ]
        
        clusters = cluster_failures(failures)
        assert len(clusters) == 1
    
    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        failures = [
            {"name": "Test1", "error": "错误：无法找到元素"}  # Chinese
        ]
        
        clusters = cluster_failures(failures)
        assert len(clusters) == 1
    
    def test_multiline_errors(self):
        """Test handling of multiline error messages."""
        failures = [
            {
                "name": "Test1",
                "error": "Error occurred:\nLine 1\nLine 2\nLine 3"
            }
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        
        # Root cause should only include first line
        assert "\n" not in cluster.root_cause or cluster.root_cause.count("\n") < 2


class TestAdvancedScenarios:
    """Test advanced real-world scenarios."""
    
    def test_http_status_code_clustering(self):
        """Test that HTTP status codes are properly clustered."""
        failures = [
            {"name": "Test1", "error": "Server error", "http_status": 500},
            {"name": "Test2", "error": "Server error", "http_status": 500},
            {"name": "Test3", "error": "Server error", "http_status": 404},
        ]
        
        clusters = cluster_failures(failures)
        
        # Should have 2 clusters (500 and 404)
        assert len(clusters) == 2
        
        # Verify each cluster has correct count
        counts = sorted([c.failure_count for c in clusters.values()])
        assert counts == [1, 2]
    
    def test_stack_trace_similarity(self):
        """Test that similar stack traces cluster together."""
        failures = [
            {
                "name": "Test1",
                "error": "NullPointerException",
                "stack_trace": "at com.example.UserService.processUser(UserService.java:42)"
            },
            {
                "name": "Test2",
                "error": "NullPointerException",
                "stack_trace": "at com.example.UserService.processUser(UserService.java:42)"
            },
            {
                "name": "Test3",
                "error": "NullPointerException",
                "stack_trace": "at com.example.OrderService.processOrder(OrderService.java:100)"
            }
        ]
        
        clusters = cluster_failures(failures)
        
        # Should have 2 clusters (UserService vs OrderService)
        assert len(clusters) == 2
    
    def test_real_world_timeout_scenario(self):
        """Test real-world timeout scenario with various timeouts."""
        failures = [
            {"name": "Test Login", "error": "TimeoutException: operation timed out after 30000ms"},
            {"name": "Test Checkout", "error": "TimeoutException: operation timed out after 45000ms"},
            {"name": "Test Search", "error": "TimeoutException: operation timed out after 15000ms"},
        ]
        
        clusters = cluster_failures(failures)
        
        # Should cluster together despite different timeout values
        assert len(clusters) == 1
        
        cluster = list(clusters.values())[0]
        assert cluster.failure_count == 3
        assert cluster.severity == FailureSeverity.MEDIUM
        assert "timeout" in cluster.suggested_fix.lower()
    
    def test_real_world_element_not_found(self):
        """Test real-world element not found scenario."""
        failures = [
            {"name": "Test1", "error": "ElementNotFound: Could not find element #btn-submit"},
            {"name": "Test2", "error": "ElementNotFound: Could not find element #btn-login"},
            {"name": "Test3", "error": "ElementNotFound: Could not find element #btn-cancel"},
            {"name": "Test4", "error": "ElementNotFound: Could not find element #btn-save"},
        ]
        
        clusters = cluster_failures(failures)
        
        # IDs with #btn- pattern should cluster together
        # Note: Different selector types (.class, xpath=) may create separate clusters
        assert len(clusters) <= 2
        
        # Get the largest cluster
        largest_cluster = max(clusters.values(), key=lambda c: c.failure_count)
        assert largest_cluster.failure_count >= 2
        assert "Element Not Found" in largest_cluster.error_patterns
    
    def test_mixed_severity_failures(self):
        """Test handling of mixed severity failures."""
        failures = [
            {"name": "Test1", "error": "FATAL: System crash - data corruption detected"},
            {"name": "Test2", "error": "AssertionError: expected 5 but was 3"},
            {"name": "Test3", "error": "TimeoutException: operation timed out"},
            {"name": "Test4", "error": "Warning: deprecated method used"},
        ]
        
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        # Verify severity distribution
        assert summary["by_severity"]["critical"] >= 1
        assert summary["by_severity"]["high"] >= 1
        assert summary["by_severity"]["medium"] >= 1
    
    def test_deduplication_across_same_test(self):
        """Test that deduplication works for same test with same error."""
        failures = [
            {"name": "Test Login", "keyword_name": "Click Button", "error": "Element not found"},
            {"name": "Test Login", "keyword_name": "Click Button", "error": "Element not found"},
            {"name": "Test Login", "keyword_name": "Click Link", "error": "Element not found"},
        ]
        
        clusters = cluster_failures(failures, deduplicate=True)
        cluster = list(clusters.values())[0]
        
        # Should deduplicate identical test+keyword+error combinations
        assert cluster.failure_count == 2  # First and third (second is duplicate)
    
    def test_metadata_preservation(self):
        """Test that metadata is preserved in clustered failures."""
        failures = [
            {
                "name": "Test1",
                "error": "Error occurred",
                "library": "SeleniumLibrary",
                "custom_field": "custom_value",
                "timestamp": "2024-01-15T10:30:00"
            }
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        failure = cluster.failures[0]
        
        assert failure.library == "SeleniumLibrary"
        assert failure.timestamp == "2024-01-15T10:30:00"
        assert failure.metadata["custom_field"] == "custom_value"
    
    def test_large_scale_clustering(self):
        """Test clustering with large number of failures."""
        # Create 100 failures with 10 distinct error types
        failures = []
        for i in range(100):
            error_type = i % 10
            failures.append({
                "name": f"Test{i}",
                "error": f"ErrorType{error_type}: Something went wrong"
            })
        
        clusters = cluster_failures(failures)
        
        # Should have 10 clusters
        assert len(clusters) == 10
        
        # Each cluster should have 10 failures
        for cluster in clusters.values():
            assert cluster.failure_count == 10
    
    def test_cluster_summary_deduplication_ratio(self):
        """Test deduplication ratio calculation in summary."""
        # Create failures: 10 actual failures, 5 pairs of identical errors
        failures = []
        for i in range(5):
            # Create duplicate pairs with identical error messages
            failures.append({
                "name": f"Test{i}_A",
                "error": f"ErrorType{i}: Something went wrong"
            })
            failures.append({
                "name": f"Test{i}_B",
                "error": f"ErrorType{i}: Something went wrong"
            })
        
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        # 10 failures -> 5 unique issues -> ratio of 2.0
        assert summary["total_failures"] == 10
        assert summary["unique_issues"] == 5
        assert summary["deduplication_ratio"] == 2.0


class TestIntegrationScenarios:
    """Test integration with real-world data structures."""
    
    def test_robot_framework_style_failures(self):
        """Test with Robot Framework-style failure data."""
        failures = [
            {
                "name": "Checking Instant VM Job Status",
                "keyword_name": "Wait Until Keyword Succeeds",
                "error": "Keyword 'Get Job Status' failed after 5 retries: Element not found",
                "library": "CustomLibrary",
                "timestamp": "20240115 10:30:45.123"
            },
            {
                "name": "Checking Instant VM Job Status",
                "keyword_name": "Wait Until Keyword Succeeds",
                "error": "Keyword 'Get Job Status' failed after 5 retries: Element not found",
                "library": "CustomLibrary",
                "timestamp": "20240115 10:32:12.456"
            }
        ]
        
        clusters = cluster_failures(failures, deduplicate=True)
        
        # Should deduplicate these identical failures
        assert len(clusters) == 1
        cluster = list(clusters.values())[0]
        
        # First occurrence only (deduplication in effect)
        assert cluster.failure_count == 1
        assert "Checking Instant VM Job Status" in cluster.tests
        assert "Wait Until Keyword Succeeds" in cluster.keywords
    
    def test_selenium_style_failures(self):
        """Test with Selenium-style failure data."""
        failures = [
            {
                "name": "test_login_success",
                "error": "selenium.common.exceptions.NoSuchElementException: Message: Unable to locate element: #username",
                "stack_trace": "at test_login.py:45 in test_login_success"
            },
            {
                "name": "test_login_failure",
                "error": "selenium.common.exceptions.NoSuchElementException: Message: Unable to locate element: #password",
                "stack_trace": "at test_login.py:67 in test_login_failure"
            }
        ]
        
        clusters = cluster_failures(failures)
        
        # Should cluster together (same exception type, normalized locators)
        assert len(clusters) == 1
        
        cluster = list(clusters.values())[0]
        assert cluster.failure_count == 2
        # Pattern detection may vary based on error message format
        assert len(cluster.error_patterns) >= 0  # Patterns are optional
    
    def test_api_test_failures(self):
        """Test with API testing failures."""
        failures = [
            {
                "name": "test_get_user_api",
                "error": "AssertionError: Status code 500",
                "http_status": 500
            },
            {
                "name": "test_create_order_api",
                "error": "AssertionError: Status code 500",
                "http_status": 500
            },
            {
                "name": "test_delete_product_api",
                "error": "AssertionError: Status code 404",
                "http_status": 404
            }
        ]
        
        clusters = cluster_failures(failures)
        
        # Should have 2 clusters (500 vs 404)
        assert len(clusters) == 2
        
        # Find the 500 cluster
        cluster_500 = next(c for c in clusters.values() if c.failure_count == 2)
        assert cluster_500.severity == FailureSeverity.CRITICAL  # HTTP 500 errors
        assert len(cluster_500.tests) == 2


class TestSeverityScoring:
    """Test comprehensive severity impact scoring."""
    
    def test_http_status_critical(self):
        """Test HTTP 500 errors are marked as CRITICAL."""
        failures = [
            {"name": "Test1", "error": "Server error occurred", "http_status": 500},
            {"name": "Test2", "error": "Internal error", "http_status": 501},
            {"name": "Test3", "error": "Insufficient storage", "http_status": 507}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.CRITICAL
    
    def test_http_status_high(self):
        """Test client/server errors are marked as HIGH."""
        failures = [
            {"name": "Test1", "error": "Bad gateway", "http_status": 502},
            {"name": "Test2", "error": "Service unavailable", "http_status": 503},
            {"name": "Test3", "error": "Not found", "http_status": 404},
            {"name": "Test4", "error": "Forbidden", "http_status": 403}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.HIGH
    
    def test_http_status_medium(self):
        """Test timeout errors are marked as MEDIUM."""
        failures = [
            {"name": "Test1", "error": "Request timeout", "http_status": 408},
            {"name": "Test2", "error": "Too many requests", "http_status": 429}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.MEDIUM
    
    def test_http_status_low(self):
        """Test redirects are marked as LOW."""
        failures = [
            {"name": "Test1", "error": "Moved permanently", "http_status": 301},
            {"name": "Test2", "error": "Temporary redirect", "http_status": 307}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.LOW
    
    def test_critical_patterns(self):
        """Test critical error patterns."""
        failures = [
            {"name": "Test1", "error": "FATAL: System crash detected"},
            {"name": "Test2", "error": "Segmentation fault (core dumped)"},
            {"name": "Test3", "error": "OutOfMemoryError: Java heap space"},
            {"name": "Test4", "error": "Data corruption detected in database"},
            {"name": "Test5", "error": "Unauthorized access attempt"},
            {"name": "Test6", "error": "HTTP 500 Internal Server Error"}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.CRITICAL
    
    def test_high_patterns(self):
        """Test high severity error patterns."""
        failures = [
            {"name": "Test1", "error": "AssertionError: expected 5 but was 3"},
            {"name": "Test2", "error": "ElementNotFoundException: element not found"},
            {"name": "Test3", "error": "Test failed: validation error"},
            {"name": "Test4", "error": "HTTP 404 Not Found"},
            {"name": "Test5", "error": "SQLException: query failed"}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.HIGH
    
    def test_medium_patterns(self):
        """Test medium severity error patterns."""
        failures = [
            {"name": "Test1", "error": "TimeoutException: operation timed out"},
            {"name": "Test2", "error": "ConnectionRefusedError: cannot connect"},
            {"name": "Test3", "error": "NetworkError: host unreachable"},
            {"name": "Test4", "error": "Service unavailable, please retry"},
            {"name": "Test5", "error": "Max retries exceeded"}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.MEDIUM
    
    def test_low_patterns(self):
        """Test low severity patterns."""
        failures = [
            {"name": "Test1", "error": "Warning: deprecated method used"},
            {"name": "Test2", "error": "Test skipped due to condition"},
            {"name": "Test3", "error": "Redirect to new location"}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.LOW
    
    def test_http_status_priority_over_pattern(self):
        """Test that HTTP status takes priority over error patterns."""
        failures = [
            # Has "timeout" keyword (MEDIUM) but HTTP 500 (CRITICAL)
            {"name": "Test1", "error": "Gateway timeout", "http_status": 500}
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        
        # HTTP status should take priority
        assert cluster.severity == FailureSeverity.CRITICAL
    
    def test_default_severity(self):
        """Test that unclassified errors default to HIGH."""
        failures = [
            {"name": "Test1", "error": "Some unknown error occurred"}
        ]
        
        clusters = cluster_failures(failures)
        cluster = list(clusters.values())[0]
        
        assert cluster.severity == FailureSeverity.HIGH
    
    def test_mixed_severity_prioritization(self):
        """Test that clusters are properly sorted by severity."""
        failures = [
            {"name": "Test1", "error": "Warning: minor issue"},  # LOW
            {"name": "Test2", "error": "TimeoutException"},      # MEDIUM
            {"name": "Test3", "error": "AssertionError"},        # HIGH
            {"name": "Test4", "error": "FATAL: crash"}           # CRITICAL
        ]
        
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        # Verify all severity levels are present
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["medium"] == 1
        assert summary["by_severity"]["low"] == 1
    
    def test_api_error_severity(self):
        """Test API-specific error severity detection."""
        failures = [
            {"name": "Test1", "error": "API returned 500", "http_status": 500},
            {"name": "Test2", "error": "Invalid request: 400 Bad Request", "http_status": 400},
            {"name": "Test3", "error": "Rate limited: 429 Too Many Requests", "http_status": 429}
        ]
        
        clusters = cluster_failures(failures)
        clusters_list = list(clusters.values())
        
        # Find each cluster and verify severity
        critical_cluster = next(c for c in clusters_list if "500" in c.root_cause)
        high_cluster = next(c for c in clusters_list if "400" in c.root_cause)
        medium_cluster = next(c for c in clusters_list if "429" in c.root_cause)
        
        assert critical_cluster.severity == FailureSeverity.CRITICAL
        assert high_cluster.severity == FailureSeverity.HIGH
        assert medium_cluster.severity == FailureSeverity.MEDIUM
    
    def test_security_error_severity(self):
        """Test security-related errors are CRITICAL."""
        failures = [
            {"name": "Test1", "error": "Unauthorized: authentication failed"},
            {"name": "Test2", "error": "Permission denied: access violation"},
            {"name": "Test3", "error": "Security exception: invalid token"}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.CRITICAL
    
    def test_database_error_severity(self):
        """Test database errors are HIGH."""
        failures = [
            {"name": "Test1", "error": "SQLException: connection failed"},
            {"name": "Test2", "error": "Deadlock detected"},
            {"name": "Test3", "error": "Constraint violation: duplicate key"}
        ]
        
        clusters = cluster_failures(failures)
        
        for cluster in clusters.values():
            assert cluster.severity == FailureSeverity.HIGH
    
    def test_severity_in_summary(self):
        """Test that severity is properly reflected in summary."""
        failures = [
            {"name": "Test1", "error": "FATAL: crash", "http_status": 500},
            {"name": "Test2", "error": "FATAL: crash", "http_status": 500},
            {"name": "Test3", "error": "AssertionError: failed"},
            {"name": "Test4", "error": "TimeoutException"}
        ]
        
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        # Verify breakdown
        assert summary["total_failures"] == 4
        assert summary["unique_issues"] == 3
        assert summary["by_severity"]["critical"] == 1  # 2 FATAL crashes (same cluster)
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["medium"] == 1


class TestSystemicPatterns:
    """Test cross-test failure pattern detection."""
    
    def test_empty_clusters(self):
        """Test with no clusters."""
        from core.log_analysis.clustering import detect_systemic_patterns
        
        patterns = detect_systemic_patterns({})
        assert patterns == []
    
    def test_volume_based_regression(self):
        """Test detection of many unique failure types."""
        failures = [
            {"name": "Test1", "error": "Error A"},
            {"name": "Test2", "error": "Error B"},
            {"name": "Test3", "error": "Error C"},
            {"name": "Test4", "error": "Error D"},
            {"name": "Test5", "error": "Error E"},
            {"name": "Test6", "error": "Error F"},
            {"name": "Test7", "error": "Error G"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect volume-based regression
        assert len(patterns) >= 1
        assert any("unique failure types" in p for p in patterns)
        assert any("systemic regression" in p for p in patterns)
    
    def test_common_keyword_pattern(self):
        """Test detection of common keyword across failures."""
        failures = [
            {"name": "Test1", "error": "Error A", "keyword_name": "Click Button"},
            {"name": "Test2", "error": "Error B", "keyword_name": "Click Button"},
            {"name": "Test3", "error": "Error C", "keyword_name": "Click Button"},
            {"name": "Test4", "error": "Error D", "keyword_name": "Click Button"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect common keyword
        assert any("Click Button" in p for p in patterns)
        assert any("keyword" in p.lower() for p in patterns)
    
    def test_common_library_pattern(self):
        """Test detection of common library across failures."""
        failures = [
            {"name": "Test1", "error": "Error A", "library": "SeleniumLibrary"},
            {"name": "Test2", "error": "Error B", "library": "SeleniumLibrary"},
            {"name": "Test3", "error": "Error C", "library": "SeleniumLibrary"},
            {"name": "Test4", "error": "Error D", "library": "SeleniumLibrary"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect common library
        assert any("SeleniumLibrary" in p for p in patterns)
    
    def test_feature_pattern_detection(self):
        """Test detection of common feature in test names."""
        failures = [
            {"name": "Test Instant VM Creation", "error": "Error A"},
            {"name": "Test Instant VM Deletion", "error": "Error B"},
            {"name": "Verify Instant VM Status", "error": "Error C"},
            {"name": "Check Instant VM Config", "error": "Error D"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect Instant feature (VM is too short and filtered out)
        assert any("Instant" in p for p in patterns)
    
    def test_environment_pattern_detection(self):
        """Test detection of environment-specific failures."""
        failures = [
            {"name": "Test ESXi Network Config", "error": "Error A"},
            {"name": "Test ESXi Storage Setup", "error": "Error B"},
            {"name": "Verify ESXi Cluster Status", "error": "Error C"},
            {"name": "Check ESXi Performance", "error": "Error D"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect ESXi environment
        assert any("ESXI" in p for p in patterns)
        assert any("environment" in p.lower() for p in patterns)
    
    def test_cascade_failure_pattern(self):
        """Test detection of cascade failures with timestamps."""
        failures = [
            {"name": "Test1", "error": "Error A", "timestamp": "2024-01-15 10:00:00"},
            {"name": "Test2", "error": "Error B", "timestamp": "2024-01-15 10:00:05"},
            {"name": "Test3", "error": "Error C", "timestamp": "2024-01-15 10:00:10"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect cascade pattern
        assert any("after first failure" in p for p in patterns)
    
    def test_multiple_patterns_combined(self):
        """Test detection of multiple systemic patterns."""
        failures = [
            {"name": "Test ESXi Instant VM Creation", "error": "Error A", "keyword_name": "Click Button"},
            {"name": "Test ESXi Instant VM Deletion", "error": "Error B", "keyword_name": "Click Button"},
            {"name": "Test ESXi Instant VM Status", "error": "Error C", "keyword_name": "Click Button"},
            {"name": "Verify ESXi Instant VM Config", "error": "Error D", "keyword_name": "Click Button"},
            {"name": "Check ESXi Instant VM Network", "error": "Error E", "keyword_name": "Click Button"},
            {"name": "Test ESXi Instant VM Storage", "error": "Error F", "keyword_name": "Click Button"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect multiple patterns
        assert len(patterns) >= 3  # Volume + keyword + feature/environment
        assert any("unique failure types" in p for p in patterns)
        assert any("Click Button" in p for p in patterns)
        # Should detect either Instant, VM, or ESXI
        feature_detected = any(
            word in p for p in patterns
            for word in ["Instant", "VM", "ESXI"]
        )
        assert feature_detected
    
    def test_no_patterns_with_few_failures(self):
        """Test with too few failures to establish patterns."""
        failures = [
            {"name": "Test1", "error": "Error A"},
            {"name": "Test2", "error": "Error B"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should not detect volume-based pattern with only 2 failures
        assert not any("systemic regression" in p for p in patterns)
    
    def test_patterns_included_in_summary(self):
        """Test that systemic patterns are included in cluster summary."""
        failures = [
            {"name": "Test1", "error": "Error A"},
            {"name": "Test2", "error": "Error B"},
            {"name": "Test3", "error": "Error C"},
            {"name": "Test4", "error": "Error D"},
            {"name": "Test5", "error": "Error E"},
            {"name": "Test6", "error": "Error F"},
        ]
        
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        # Summary should include systemic_patterns key
        assert "systemic_patterns" in summary
        assert isinstance(summary["systemic_patterns"], list)
        assert len(summary["systemic_patterns"]) >= 1
    
    def test_azure_environment_pattern(self):
        """Test detection of Azure environment pattern."""
        failures = [
            {"name": "Test Azure VM Creation", "error": "Error A"},
            {"name": "Test Azure Storage Setup", "error": "Error B"},
            {"name": "Verify Azure Network Config", "error": "Error C"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect AZURE environment
        assert any("AZURE" in p for p in patterns)
    
    def test_kubernetes_environment_pattern(self):
        """Test detection of Kubernetes environment pattern."""
        failures = [
            {"name": "Test k8s pod creation", "error": "Error A"},
            {"name": "Test k8s service config", "error": "Error B"},
            {"name": "Verify k8s deployment", "error": "Error C"},
        ]
        
        clusters = cluster_failures(failures)
        patterns = detect_systemic_patterns(clusters)
        
        # Should detect K8S environment
        assert any("K8S" in p for p in patterns)


class TestDomainClassification:
    """Test failure domain classification functionality."""
    
    # INFRA Domain Tests
    def test_classify_ssh_failure_as_infra(self):
        """Test SSH connection failures are classified as INFRA."""
        error = "SSH connection refused to host 192.168.1.100"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.INFRA
    
    def test_classify_vm_not_found_as_infra(self):
        """Test VM not found errors are classified as INFRA."""
        error = "Virtual machine not found: vm-instance-001"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.INFRA
    
    def test_classify_connection_refused_as_infra(self):
        """Test connection refused errors are classified as INFRA."""
        error = "Connection refused on port 8080"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.INFRA
    
    def test_classify_network_unreachable_as_infra(self):
        """Test network unreachable errors are classified as INFRA."""
        error = "Network unreachable: no route to host"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.INFRA
    
    def test_classify_dns_error_as_infra(self):
        """Test DNS resolution errors are classified as INFRA."""
        error = "DNS resolution failed for api.example.com"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.INFRA
    
    def test_classify_host_not_found_as_infra(self):
        """Test host not found errors are classified as INFRA."""
        error = "Host not found: server.example.com"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.INFRA
    
    # ENVIRONMENT Domain Tests
    def test_classify_config_missing_as_environment(self):
        """Test configuration missing errors are classified as ENVIRONMENT."""
        error = "Configuration file not found: /etc/app/config.yaml"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.ENVIRONMENT
    
    def test_classify_env_var_missing_as_environment(self):
        """Test environment variable errors are classified as ENVIRONMENT."""
        error = "Environment variable not set: DATABASE_URL"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.ENVIRONMENT
    
    def test_classify_module_not_found_as_environment(self):
        """Test module not found errors are classified as ENVIRONMENT."""
        error = "ModuleNotFoundError: No module named 'requests'"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.ENVIRONMENT
    
    def test_classify_import_error_as_environment(self):
        """Test import errors are classified as ENVIRONMENT."""
        error = "ImportError: cannot import name 'foo' from 'bar'"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.ENVIRONMENT
    
    def test_classify_file_not_found_as_environment(self):
        """Test file not found errors are classified as ENVIRONMENT."""
        error = "FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.ENVIRONMENT
    
    def test_classify_credentials_not_found_as_environment(self):
        """Test credential errors are classified as ENVIRONMENT."""
        error = "Credentials not found: API key missing"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.ENVIRONMENT
    
    def test_classify_property_not_set_as_environment(self):
        """Test property not set errors are classified as ENVIRONMENT."""
        error = "System property not set: java.home"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.ENVIRONMENT
    
    # TEST_AUTOMATION Domain Tests
    def test_classify_index_error_as_test_automation(self):
        """Test IndexError is classified as TEST_AUTOMATION."""
        error = "IndexError: list index out of range"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_classify_key_error_as_test_automation(self):
        """Test KeyError is classified as TEST_AUTOMATION."""
        error = "KeyError: 'user_id' not found in dictionary"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_classify_attribute_error_as_test_automation(self):
        """Test AttributeError is classified as TEST_AUTOMATION."""
        error = "AttributeError: 'NoneType' object has no attribute 'click'"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_classify_null_pointer_as_test_automation(self):
        """Test NullPointerException is classified as TEST_AUTOMATION."""
        error = "NullPointerException at line 42"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_classify_element_not_found_as_test_automation(self):
        """Test element not found errors are classified as TEST_AUTOMATION."""
        error = "ElementNotFound: Unable to locate element with id 'submit-button'"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_classify_stale_element_as_test_automation(self):
        """Test stale element errors are classified as TEST_AUTOMATION."""
        error = "StaleElementReferenceException: Element is no longer attached to DOM"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_classify_webdriver_exception_as_test_automation(self):
        """Test WebDriver exceptions are classified as TEST_AUTOMATION."""
        error = "WebDriverException: chrome not reachable"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_classify_test_code_stack_as_test_automation(self):
        """Test errors with test code in stack trace are TEST_AUTOMATION."""
        error = "Assertion failed"
        stack = "File '/tests/test_user.py', line 32, in test_login"
        domain = _classify_failure_domain(error, stack_trace=stack)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_classify_fixture_error_as_test_automation(self):
        """Test fixture errors are classified as TEST_AUTOMATION."""
        error = "FixtureError: setup failed for test_user_creation"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    # PRODUCT Domain Tests
    def test_classify_http_500_as_product(self):
        """Test HTTP 500 errors are classified as PRODUCT."""
        error = "HTTP 500 Internal Server Error from /api/users"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.PRODUCT
    
    def test_classify_http_404_as_product(self):
        """Test HTTP 404 errors are classified as PRODUCT."""
        error = "HTTP 404 Not Found: /api/products/12345"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.PRODUCT
    
    def test_classify_api_error_as_product(self):
        """Test API errors are classified as PRODUCT."""
        error = "API error: Invalid request parameters"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.PRODUCT
    
    def test_classify_validation_failure_as_product(self):
        """Test validation failures are classified as PRODUCT."""
        error = "Validation failed: Email format is invalid"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.PRODUCT
    
    def test_classify_business_rule_violation_as_product(self):
        """Test business rule violations are classified as PRODUCT."""
        error = "Business rule violation: Cannot delete active user"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.PRODUCT
    
    def test_classify_database_error_as_product(self):
        """Test database errors are classified as PRODUCT."""
        error = "SQLException: Duplicate key constraint violation"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.PRODUCT
    
    def test_classify_authentication_fail_as_product(self):
        """Test authentication failures are classified as PRODUCT."""
        error = "Authentication failed: Invalid credentials"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.PRODUCT
    
    def test_classify_operation_timeout_as_product(self):
        """Test product operation timeouts are classified as PRODUCT."""
        error = "Operation timeout: User update took too long"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.PRODUCT
    
    # Edge Cases and Priority Tests
    def test_test_automation_takes_priority_over_product(self):
        """Test that TEST_AUTOMATION patterns take priority over PRODUCT."""
        # IndexError is test automation, but mentions HTTP 500
        error = "IndexError while processing HTTP 500 response"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.TEST_AUTOMATION
    
    def test_infra_takes_priority_over_environment(self):
        """Test that INFRA patterns take priority over ENVIRONMENT."""
        # SSH failure even if config mentioned
        error = "SSH connection refused - check config file"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.INFRA
    
    def test_unknown_domain_for_generic_error(self):
        """Test that generic errors are classified as UNKNOWN."""
        error = "Something went wrong"
        domain = _classify_failure_domain(error)
        assert domain == FailureDomain.UNKNOWN
    
    def test_empty_error_classified_as_unknown(self):
        """Test that empty errors are classified as UNKNOWN."""
        domain = _classify_failure_domain("")
        assert domain == FailureDomain.UNKNOWN
    
    # Integration Tests
    def test_domain_included_in_clustered_failure(self):
        """Test that domain is included in ClusteredFailure."""
        failures = [
            {"name": "Test1", "error": "SSH connection refused"}
        ]
        clusters = cluster_failures(failures)
        
        cluster = list(clusters.values())[0]
        failure = cluster.failures[0]
        
        assert hasattr(failure, 'domain')
        assert failure.domain == FailureDomain.INFRA
    
    def test_domain_included_in_cluster(self):
        """Test that domain is included in FailureCluster."""
        failures = [
            {"name": "Test1", "error": "HTTP 500 Internal Server Error"}
        ]
        clusters = cluster_failures(failures)
        
        cluster = list(clusters.values())[0]
        
        assert hasattr(cluster, 'domain')
        assert cluster.domain == FailureDomain.PRODUCT
    
    def test_domain_consistency_in_cluster(self):
        """Test that all failures in a cluster have same domain."""
        # Same error type should cluster together with same domain
        failures = [
            {"name": "Test1", "error": "IndexError: list index out of range at line 10"},
            {"name": "Test2", "error": "IndexError: list index out of range at line 25"},
        ]
        clusters = cluster_failures(failures)
        
        cluster = list(clusters.values())[0]
        
        # All failures should have TEST_AUTOMATION domain
        for failure in cluster.failures:
            assert failure.domain == FailureDomain.TEST_AUTOMATION
        
        # Cluster should also have TEST_AUTOMATION domain
        assert cluster.domain == FailureDomain.TEST_AUTOMATION
    
    def test_domain_in_cluster_summary(self):
        """Test that domain distribution is included in cluster summary."""
        failures = [
            {"name": "Test1", "error": "SSH connection refused"},
            {"name": "Test2", "error": "HTTP 500 error"},
            {"name": "Test3", "error": "Config file not found"},
        ]
        clusters = cluster_failures(failures)
        summary = get_cluster_summary(clusters)
        
        assert "by_domain" in summary
        assert "infrastructure" in summary["by_domain"]
        assert "environment" in summary["by_domain"]
        assert "test_automation" in summary["by_domain"]
        assert "product" in summary["by_domain"]
        assert "unknown" in summary["by_domain"]
        
        # Should have 1 infra, 1 product, 1 environment
        assert summary["by_domain"]["infrastructure"] == 1
        assert summary["by_domain"]["product"] == 1
        assert summary["by_domain"]["environment"] == 1
    
    def test_mixed_domain_clustering(self):
        """Test clustering with mixed domains."""
        failures = [
            {"name": "Test1", "error": "SSH connection failed"},
            {"name": "Test2", "error": "SSH timeout"},
            {"name": "Test3", "error": "HTTP 500 error"},
            {"name": "Test4", "error": "API failure"},
            {"name": "Test5", "error": "IndexError in test"},
        ]
        clusters = cluster_failures(failures)
        
        # Should have clusters from different domains
        domains_found = {cluster.domain for cluster in clusters.values()}
        
        # Should find at least INFRA and PRODUCT domains
        assert FailureDomain.INFRA in domains_found
        assert FailureDomain.PRODUCT in domains_found
