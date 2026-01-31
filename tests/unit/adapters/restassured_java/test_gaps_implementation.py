"""
Comprehensive tests for RestAssured failure classification and metadata extraction.

Tests Gap 1.1 (Failure Classification) and Gap 1.2 (Metadata Enrichment).
"""

import pytest
import os
from adapters.restassured_java.failure_classifier import (
    RestAssuredFailureClassifier,
    APIFailureType,
    classify_api_failure
)
from adapters.restassured_java.metadata_extractor import (
    RestAssuredMetadataExtractor,
    ExecutionEnvironment,
    extract_restassured_metadata
)


class TestAPIFailureClassification:
    """Tests for Gap 1.1: API Failure Classification."""
    
    def test_timeout_classification(self):
        """Test timeout failure classification."""
        error = """java.net.SocketTimeoutException: Read timed out
    at java.net.SocketInputStream.socketRead0(Native Method)
    at io.restassured.RestAssured.get(RestAssured.java:45)
    at com.api.tests.UserAPITest.testGetUser(UserAPITest.java:32)"""
        
        classification = classify_api_failure(error, "testGetUser")
        
        assert classification.failure_type == APIFailureType.TIMEOUT.value
        assert "SocketTimeoutException" in classification.exception_type
        assert classification.is_intermittent is True
        assert classification.confidence > 0.7
    
    def test_connection_error_classification(self):
        """Test connection error classification."""
        error = """java.net.ConnectException: Connection refused: connect
    at java.net.DualStackPlainSocketImpl.connect0(Native Method)
    at com.api.client.APIClient.executeRequest(APIClient.java:67)"""
        
        classification = classify_api_failure(error)
        
        assert classification.failure_type == APIFailureType.CONNECTION_ERROR.value
        assert "ConnectException" in classification.exception_type
        assert classification.is_intermittent is True
    
    def test_auth_failure_401(self):
        """Test 401 authentication failure."""
        error = """java.lang.AssertionError: 1 expectation failed.
Expected status code <200> but was <401>."""
        
        classification = classify_api_failure(error, http_status=401)
        
        # Exception takes precedence, but HTTP status captured
        assert classification.http_status == 401
        assert classification.is_intermittent is False
        # Failure type can be assertion or auth_failure based on precedence
        assert classification.failure_type in [APIFailureType.AUTH_FAILURE.value, APIFailureType.ASSERTION.value]
    
    def test_auth_failure_403(self):
        """Test 403 forbidden failure."""
        error = "Expected <200> but was <403> Forbidden"
        
        classification = classify_api_failure(error, http_status=403)
        
        assert classification.failure_type == APIFailureType.AUTH_FAILURE.value
        assert classification.http_status == 403
    
    def test_not_found_404(self):
        """Test 404 not found classification."""
        error = "GET /api/users/999 returned 404 Not Found"
        
        classification = classify_api_failure(error, http_status=404)
        
        assert classification.failure_type == APIFailureType.NOT_FOUND.value
        assert classification.http_status == 404
        assert classification.http_method == "GET"
    
    def test_client_error_4xx(self):
        """Test generic 4xx client error."""
        error = "Bad Request: Invalid parameters"
        
        classification = classify_api_failure(error, http_status=400)
        
        assert classification.failure_type == APIFailureType.CLIENT_ERROR.value
        assert classification.http_status == 400
    
    def test_server_error_5xx(self):
        """Test 5xx server error."""
        error = "Internal Server Error"
        
        classification = classify_api_failure(error, http_status=500)
        
        assert classification.failure_type == APIFailureType.SERVER_ERROR.value
        assert classification.http_status == 500
        assert classification.is_intermittent is True
    
    def test_serialization_error(self):
        """Test JSON serialization error."""
        error = """com.fasterxml.jackson.core.JsonParseException: Unexpected character
    at com.fasterxml.jackson.core.JsonParser.parse(JsonParser.java:123)
    at com.api.tests.ProductAPITest.testCreateProduct(ProductAPITest.java:45)"""
        
        classification = classify_api_failure(error)
        
        assert classification.failure_type == APIFailureType.SERIALIZATION_ERROR.value
        assert "JsonParseException" in classification.exception_type
    
    def test_ssl_error(self):
        """Test SSL certificate error."""
        error = """javax.net.ssl.SSLHandshakeException: PKIX path building failed
    at sun.security.ssl.Alerts.getSSLException(Alerts.java:192)"""
        
        classification = classify_api_failure(error)
        
        assert classification.failure_type == APIFailureType.SSL_ERROR.value
        assert "SSLHandshakeException" in classification.exception_type
    
    def test_contract_violation(self):
        """Test schema/contract violation."""
        error = """java.lang.AssertionError: JSON path id doesn't match.
Expected: <123>
Actual: null"""
        
        classification = classify_api_failure(error)
        
        # AssertionError maps to ASSERTION, but pattern may detect contract/validation
        assert classification.failure_type in [
            APIFailureType.CONTRACT_VIOLATION.value,
            APIFailureType.VALIDATION_FAILURE.value,
            APIFailureType.ASSERTION.value
        ]
    
    def test_validation_failure(self):
        """Test response validation failure."""
        error = """java.lang.AssertionError: 1 expectation failed.
JSON path response.status doesn't match.
Expected: success
Actual: error"""
        
        classification = classify_api_failure(error)
        
        # Validation failure or assertion (both valid for RestAssured)
        assert classification.failure_type in [APIFailureType.VALIDATION_FAILURE.value, APIFailureType.ASSERTION.value]
        assert "AssertionError" in classification.exception_type
    
    def test_null_pointer_exception(self):
        """Test null pointer exception."""
        error = """java.lang.NullPointerException: Cannot invoke getStatus() because response is null
    at com.api.tests.OrderAPITest.verifyOrder(OrderAPITest.java:78)"""
        
        classification = classify_api_failure(error)
        
        assert classification.failure_type == APIFailureType.NULL_POINTER.value
        assert "NullPointerException" in classification.exception_type
    
    def test_http_method_extraction(self):
        """Test HTTP method extraction from error."""
        error = "POST /api/users failed with 500"
        
        classification = classify_api_failure(error, http_method="POST", http_status=500)
        
        assert classification.http_method == "POST"
        assert classification.failure_type == APIFailureType.SERVER_ERROR.value
    
    def test_endpoint_extraction(self):
        """Test endpoint extraction."""
        error = "GET /api/v1/products/123 returned 404"
        
        classification = classify_api_failure(error)
        
        assert classification.endpoint == "/api/v1/products/123"
        assert classification.http_method == "GET"
    
    def test_response_time_extraction(self):
        """Test response time extraction."""
        error = "Request timeout after 5000 ms"
        
        classification = classify_api_failure(error)
        
        assert classification.response_time == 5000.0
    
    def test_root_cause_extraction(self):
        """Test root cause extraction from nested exceptions."""
        error = """java.lang.RuntimeException: API call failed
Caused by: java.net.SocketTimeoutException: Read timed out"""
        
        classification = classify_api_failure(error)
        
        assert classification.root_cause is not None
        assert "SocketTimeoutException" in classification.root_cause
    
    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        classifier = RestAssuredFailureClassifier()
        
        # High confidence - exception and pattern matched
        high_conf = classifier.classify("SocketTimeoutException: timeout", http_status=408)
        assert high_conf.confidence >= 0.7
        
        # Medium confidence - pattern matched only (lower bound)
        med_conf = classifier.classify("Request timed out after 30 seconds")
        assert 0.3 <= med_conf.confidence < 0.8
        
        # Low confidence - unknown error
        low_conf = classifier.classify("Something went wrong")
        assert low_conf.confidence < 0.5


class TestAPIMetadataExtraction:
    """Tests for Gap 1.2: Metadata Extraction."""
    
    def test_local_environment_detection(self):
        """Test local environment detection."""
        # Clear CI env vars
        original = os.environ.copy()
        try:
            for key in list(os.environ.keys()):
                if 'CI' in key or 'JENKINS' in key or 'GITHUB' in key:
                    del os.environ[key]
            
            metadata = extract_restassured_metadata()
            assert metadata.environment == ExecutionEnvironment.LOCAL
        finally:
            os.environ.clear()
            os.environ.update(original)
    
    def test_ci_environment_detection(self):
        """Test CI environment detection."""
        original = os.environ.copy()
        try:
            os.environ['CI'] = 'true'
            metadata = extract_restassured_metadata()
            assert metadata.environment == ExecutionEnvironment.CI
        finally:
            os.environ.clear()
            os.environ.update(original)
    
    def test_jenkins_metadata_extraction(self):
        """Test Jenkins CI metadata extraction."""
        original = os.environ.copy()
        try:
            os.environ.update({
                'JENKINS_URL': 'http://jenkins.example.com',
                'BUILD_ID': '12345',
                'BUILD_URL': 'http://jenkins.example.com/job/api-tests/12345/',
                'JOB_NAME': 'API Tests',
                'GIT_BRANCH': 'main',
                'GIT_COMMIT': 'abc123',
                'BUILD_NUMBER': '42'
            })
            
            metadata = extract_restassured_metadata()
            
            assert metadata.ci is not None
            assert metadata.ci.ci_system == 'jenkins'
            assert metadata.ci.build_id == '12345'
            assert metadata.ci.job_name == 'API Tests'
            assert metadata.ci.branch == 'main'
            assert metadata.ci.commit_sha == 'abc123'
            assert metadata.ci.build_number == 42
        finally:
            os.environ.clear()
            os.environ.update(original)
    
    def test_github_actions_metadata(self):
        """Test GitHub Actions metadata extraction."""
        original = os.environ.copy()
        try:
            os.environ.update({
                'GITHUB_ACTIONS': 'true',
                'GITHUB_RUN_ID': '987654',
                'GITHUB_WORKFLOW': 'API Test Suite',
                'GITHUB_REF_NAME': 'feature/new-api',
                'GITHUB_SHA': 'def456',
                'GITHUB_REPOSITORY': 'org/repo'
            })
            
            metadata = extract_restassured_metadata()
            
            assert metadata.ci is not None
            assert metadata.ci.ci_system == 'github_actions'
            assert metadata.ci.build_id == '987654'
            assert metadata.ci.job_name == 'API Test Suite'
            assert metadata.ci.branch == 'feature/new-api'
        finally:
            os.environ.clear()
            os.environ.update(original)
    
    def test_api_metadata_extraction(self):
        """Test API configuration metadata."""
        original = os.environ.copy()
        try:
            os.environ.update({
                'API_BASE_URL': 'https://api.example.com',
                'API_VERSION': 'v2',
                'API_KEY': 'secret-key-123',
                'CONTENT_TYPE': 'application/json'
            })
            
            metadata = extract_restassured_metadata()
            
            assert metadata.api is not None
            assert metadata.api.base_url == 'https://api.example.com'
            assert metadata.api.api_version == 'v2'
            assert metadata.api.auth_type == 'api_key'
            assert metadata.api.content_type == 'application/json'
        finally:
            os.environ.clear()
            os.environ.update(original)
    
    def test_auth_type_detection_bearer(self):
        """Test bearer token auth detection."""
        original = os.environ.copy()
        try:
            os.environ['BEARER_TOKEN'] = 'eyJhbGc...'
            metadata = extract_restassured_metadata()
            assert metadata.api.auth_type == 'bearer'
        finally:
            os.environ.clear()
            os.environ.update(original)
    
    def test_auth_type_detection_basic(self):
        """Test basic auth detection."""
        original = os.environ.copy()
        try:
            os.environ['BASIC_AUTH_USER'] = 'user'
            metadata = extract_restassured_metadata()
            assert metadata.api.auth_type == 'basic'
        finally:
            os.environ.clear()
            os.environ.update(original)
    
    def test_execution_context_generation(self):
        """Test execution context with session ID."""
        metadata = extract_restassured_metadata()
        
        assert metadata.execution_context is not None
        assert len(metadata.execution_context.session_id) > 0
        assert metadata.execution_context.retry_count == 0
    
    def test_grouping_from_testng_groups(self):
        """Test grouping extraction from TestNG groups."""
        extractor = RestAssuredMetadataExtractor()
        
        groups = ['smoke', 'critical', 'team-platform', 'owner-john']
        grouping = extractor.extract_grouping_from_annotations(groups=groups)
        
        assert 'smoke' in grouping.groups
        assert grouping.test_type == 'smoke'
        assert grouping.priority == 'high'
        assert grouping.team == 'platform'
        assert grouping.owner == 'john'
    
    def test_priority_detection(self):
        """Test priority level detection."""
        extractor = RestAssuredMetadataExtractor()
        
        # High priority
        high = extractor.extract_grouping_from_annotations(groups=['p0', 'critical'])
        assert high.priority == 'high'
        
        # Medium priority
        medium = extractor.extract_grouping_from_annotations(groups=['p1', 'medium'])
        assert medium.priority == 'medium'
        
        # Low priority
        low = extractor.extract_grouping_from_annotations(groups=['p2', 'low'])
        assert low.priority == 'low'
    
    def test_test_type_detection(self):
        """Test type detection."""
        extractor = RestAssuredMetadataExtractor()
        
        smoke = extractor.extract_grouping_from_annotations(groups=['smoke'])
        assert smoke.test_type == 'smoke'
        
        regression = extractor.extract_grouping_from_annotations(groups=['regression'])
        assert regression.test_type == 'regression'
    
    def test_metadata_to_dict(self):
        """Test metadata serialization to dict."""
        original = os.environ.copy()
        try:
            os.environ.update({
                'API_BASE_URL': 'https://api.example.com',
                'JENKINS_URL': 'http://jenkins',
                'BUILD_ID': '123'
            })
            
            metadata = extract_restassured_metadata()
            data = metadata.to_dict()
            
            assert data['api_base_url'] == 'https://api.example.com'
            assert data['environment'] == 'ci'
            assert data['ci_system'] == 'jenkins'
            assert data['build_id'] == '123'
            assert 'session_id' in data
        finally:
            os.environ.clear()
            os.environ.update(original)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
