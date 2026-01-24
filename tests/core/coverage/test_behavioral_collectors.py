"""
Unit tests for behavioral coverage collectors.
"""

import pytest
import uuid
from datetime import datetime

from core.coverage.behavioral_collectors import (
    ApiEndpointCollector,
    UiComponentCollector,
    NetworkCaptureCollector,
    ContractCoverageCollector
)


class TestApiEndpointCollector:
    """Tests for ApiEndpointCollector class."""
    
    def test_record_api_call(self):
        """Test recording an API call."""
        collector = ApiEndpointCollector()
        test_id = uuid.uuid4()
        
        coverage = collector.record_api_call(
            test_case_id=test_id,
            endpoint_path="/api/v1/users/123",
            http_method="GET",
            status_code=200,
            execution_time_ms=45.2
        )
        
        assert coverage.test_case_id == test_id
        assert coverage.endpoint_path == "/api/v1/users/{id}"  # Normalized
        assert coverage.http_method == "GET"
        assert coverage.status_code == 200
        assert coverage.execution_time_ms == 45.2
    
    def test_normalize_endpoint_numeric_ids(self):
        """Test endpoint normalization with numeric IDs."""
        collector = ApiEndpointCollector()
        test_id = uuid.uuid4()
        
        # Numeric ID
        coverage1 = collector.record_api_call(
            test_case_id=test_id,
            endpoint_path="/api/users/12345/orders",
            http_method="GET",
            status_code=200
        )
        assert coverage1.endpoint_path == "/api/users/{id}/orders"
        
        # Multiple IDs
        coverage2 = collector.record_api_call(
            test_case_id=test_id,
            endpoint_path="/api/users/123/orders/456",
            http_method="GET",
            status_code=200
        )
        assert coverage2.endpoint_path == "/api/users/{id}/orders/{id}"
    
    def test_normalize_endpoint_uuid(self):
        """Test endpoint normalization with UUIDs."""
        collector = ApiEndpointCollector()
        test_id = uuid.uuid4()
        
        # Use a mixed-case UUID to test case-insensitive matching
        coverage = collector.record_api_call(
            test_case_id=test_id,
            endpoint_path="/api/orders/550e8400-E29B-41D4-a716-446655440000",
            http_method="PUT",
            status_code=200
        )
        
        assert coverage.endpoint_path == "/api/orders/{id}"
    
    def test_record_with_request_response(self):
        """Test recording with request/response data."""
        collector = ApiEndpointCollector()
        test_id = uuid.uuid4()
        
        request_body = {"userId": 123, "name": "John"}
        response_body = {"id": 123, "name": "John", "email": "john@example.com"}
        
        coverage = collector.record_api_call(
            test_case_id=test_id,
            endpoint_path="/api/users",
            http_method="POST",
            status_code=201,
            request_body=request_body,
            response_body=response_body
        )
        
        assert coverage.request_schema is not None
        assert "userId" in coverage.request_schema
        assert coverage.response_schema is not None
        assert "email" in coverage.response_schema
    
    def test_get_covered_endpoints(self):
        """Test getting all covered endpoints."""
        collector = ApiEndpointCollector()
        test_id = uuid.uuid4()
        
        collector.record_api_call(test_id, "/api/users", "GET", 200)
        collector.record_api_call(test_id, "/api/orders", "POST", 201)
        
        endpoints = collector.get_covered_endpoints()
        
        assert len(endpoints) == 2
        paths = [e.endpoint_path for e in endpoints]
        assert "/api/users" in paths
        assert "/api/orders" in paths
    
    def test_get_coverage_summary(self):
        """Test getting coverage summary."""
        collector = ApiEndpointCollector()
        test_id = uuid.uuid4()
        
        collector.record_api_call(test_id, "/api/users", "GET", 200)
        collector.record_api_call(test_id, "/api/users/1", "PUT", 200)
        collector.record_api_call(test_id, "/api/orders", "POST", 201)
        
        summary = collector.get_coverage_summary()
        
        assert summary['total_endpoints'] == 3
        assert summary['unique_paths'] == 3
        assert "GET" in summary['http_methods']
        assert "POST" in summary['http_methods']
        assert "PUT" in summary['http_methods']
        assert 200 in summary['status_codes']
        assert 201 in summary['status_codes']


class TestUiComponentCollector:
    """Tests for UiComponentCollector class."""
    
    def test_record_interaction(self):
        """Test recording a UI interaction."""
        collector = UiComponentCollector()
        test_id = uuid.uuid4()
        
        coverage = collector.record_interaction(
            test_case_id=test_id,
            component_name="login_button",
            component_type="button",
            interaction_type="click",
            selector="#login-btn",
            page_url="https://app.example.com/login"
        )
        
        assert coverage.test_case_id == test_id
        assert coverage.component_name == "login_button"
        assert coverage.component_type == "button"
        assert coverage.interaction_type == "click"
        assert coverage.selector == "#login-btn"
        assert coverage.page_url == "https://app.example.com/login"
    
    def test_record_multiple_interactions(self):
        """Test recording multiple interactions."""
        collector = UiComponentCollector()
        test_id = uuid.uuid4()
        
        collector.record_interaction(test_id, "username_input", "input", "type")
        collector.record_interaction(test_id, "password_input", "input", "type")
        collector.record_interaction(test_id, "login_button", "button", "click")
        
        components = collector.get_covered_components()
        
        assert len(components) == 3
        component_names = [c.component_name for c in components]
        assert "username_input" in component_names
        assert "password_input" in component_names
        assert "login_button" in component_names
    
    def test_get_coverage_summary(self):
        """Test getting UI coverage summary."""
        collector = UiComponentCollector()
        test_id = uuid.uuid4()
        
        collector.record_interaction(
            test_id, "submit_btn", "button", "click",
            page_url="https://app.example.com/form"
        )
        collector.record_interaction(
            test_id, "email_input", "input", "type",
            page_url="https://app.example.com/form"
        )
        collector.record_interaction(
            test_id, "profile_menu", "dropdown", "click",
            page_url="https://app.example.com/dashboard"
        )
        
        summary = collector.get_coverage_summary()
        
        assert summary['total_interactions'] == 3
        assert summary['unique_components'] == 3
        assert "button" in summary['component_types']
        assert "input" in summary['component_types']
        assert "dropdown" in summary['component_types']
        assert len(summary['pages_covered']) == 2


class TestNetworkCaptureCollector:
    """Tests for NetworkCaptureCollector class."""
    
    def test_record_request(self):
        """Test recording a network request."""
        collector = NetworkCaptureCollector()
        test_id = uuid.uuid4()
        
        capture = collector.record_request(
            test_case_id=test_id,
            request_url="https://api.example.com/users",
            request_method="GET",
            request_headers={"Authorization": "Bearer token123"},
            response_status=200,
            response_body='{"id": 1, "name": "John"}',
            duration_ms=150.5
        )
        
        assert capture.test_case_id == test_id
        assert capture.request_url == "https://api.example.com/users"
        assert capture.request_method == "GET"
        assert capture.response_status == 200
        assert capture.duration_ms == 150.5
    
    def test_record_multiple_requests(self):
        """Test recording multiple requests."""
        collector = NetworkCaptureCollector()
        test_id = uuid.uuid4()
        
        collector.record_request(test_id, "https://api.example.com/users", "GET", response_status=200)
        collector.record_request(test_id, "https://api.example.com/orders", "POST", response_status=201)
        collector.record_request(test_id, "https://api.example.com/products", "GET", response_status=200)
        
        captures = collector.get_captures()
        
        assert len(captures) == 3
    
    def test_to_api_endpoint_coverage(self):
        """Test converting network captures to API endpoint coverage."""
        collector = NetworkCaptureCollector()
        test_id = uuid.uuid4()
        
        collector.record_request(
            test_id,
            "https://api.example.com/v1/users/123",
            "GET",
            response_status=200,
            duration_ms=45.0
        )
        collector.record_request(
            test_id,
            "https://api.example.com/v1/orders",
            "POST",
            response_status=201,
            duration_ms=120.5
        )
        
        api_coverage = collector.to_api_endpoint_coverage()
        
        assert len(api_coverage) == 2
        paths = [e.endpoint_path for e in api_coverage]
        assert "/v1/users/{id}" in paths
        assert "/v1/orders" in paths


class TestContractCoverageCollector:
    """Tests for ContractCoverageCollector class."""
    
    def test_record_contract_usage(self):
        """Test recording contract usage."""
        collector = ContractCoverageCollector()
        test_id = uuid.uuid4()
        
        coverage = collector.record_contract_usage(
            test_case_id=test_id,
            contract_name="UserAPI.getUser",
            contract_version="v2",
            request_fields={"userId", "includeProfile"},
            response_fields={"id", "name", "email", "profile"},
            validation_passed=True
        )
        
        assert coverage.test_case_id == test_id
        assert coverage.contract_name == "UserAPI.getUser"
        assert coverage.contract_version == "v2"
        assert len(coverage.request_fields_covered) == 2
        assert len(coverage.response_fields_covered) == 4
        assert coverage.validation_passed is True
    
    def test_record_validation_failure(self):
        """Test recording contract validation failure."""
        collector = ContractCoverageCollector()
        test_id = uuid.uuid4()
        
        coverage = collector.record_contract_usage(
            test_case_id=test_id,
            contract_name="OrderAPI.createOrder",
            contract_version="v1",
            request_fields={"productId"},
            response_fields=set(),
            validation_passed=False,
            validation_errors=["Missing required field: quantity", "Invalid productId"]
        )
        
        assert coverage.validation_passed is False
        assert len(coverage.validation_errors) == 2
        assert "Missing required field: quantity" in coverage.validation_errors
    
    def test_get_coverage_summary(self):
        """Test getting contract coverage summary."""
        collector = ContractCoverageCollector()
        test_id1 = uuid.uuid4()
        test_id2 = uuid.uuid4()
        
        # Successful validation
        collector.record_contract_usage(
            test_id1,
            "UserAPI.getUser",
            "v1",
            {"userId"},
            {"id", "name"},
            validation_passed=True
        )
        
        # Failed validation
        collector.record_contract_usage(
            test_id2,
            "OrderAPI.createOrder",
            "v1",
            {"productId", "quantity"},
            set(),
            validation_passed=False
        )
        
        summary = collector.get_coverage_summary()
        
        assert summary['total_contracts'] == 2
        assert summary['total_request_fields'] == 3
        assert summary['total_response_fields'] == 2
        assert summary['validation_passed'] == 1
        assert summary['validation_failed'] == 1
        assert len(summary['contracts']) == 2


class TestEndToEnd:
    """End-to-end behavioral coverage tests."""
    
    def test_full_test_execution_coverage(self):
        """Test capturing full behavioral coverage during a test."""
        test_id = uuid.uuid4()
        
        # Setup collectors
        api_collector = ApiEndpointCollector()
        ui_collector = UiComponentCollector()
        contract_collector = ContractCoverageCollector()
        
        # Simulate test execution
        
        # 1. UI interactions
        ui_collector.record_interaction(test_id, "username_input", "input", "type")
        ui_collector.record_interaction(test_id, "password_input", "input", "type")
        ui_collector.record_interaction(test_id, "login_button", "button", "click")
        
        # 2. API calls
        api_collector.record_api_call(test_id, "/api/auth/login", "POST", 200)
        api_collector.record_api_call(test_id, "/api/users/me", "GET", 200)
        
        # 3. Contract validation
        contract_collector.record_contract_usage(
            test_id,
            "AuthAPI.login",
            "v1",
            {"username", "password"},
            {"token", "userId"},
            validation_passed=True
        )
        
        # Verify coverage
        assert len(ui_collector.get_covered_components()) == 3
        assert len(api_collector.get_covered_endpoints()) == 2
        assert len(contract_collector.get_contract_coverage()) == 1
        
        # Verify summaries
        ui_summary = ui_collector.get_coverage_summary()
        assert ui_summary['total_interactions'] == 3
        
        api_summary = api_collector.get_coverage_summary()
        assert api_summary['total_endpoints'] == 2
        
        contract_summary = contract_collector.get_coverage_summary()
        assert contract_summary['validation_passed'] == 1
