"""
Behavioral Coverage Collectors for CrossBridge.

Collects behavioral coverage for SaaS/black-box applications:
- API endpoint coverage (network capture)
- UI component coverage (element interaction)
- Contract/schema coverage

These are alternatives to instrumented code coverage when backend
instrumentation is not available (vendor SaaS, cloud consoles, etc.).
"""

from typing import List, Optional, Dict, Set
from dataclasses import dataclass
from datetime import datetime
import uuid
import re

from core.coverage.functional_models import (
    ApiEndpointCoverage,
    UiComponentCoverage,
    NetworkCapture,
    ContractCoverage
)


class ApiEndpointCollector:
    """
    Collects API endpoint coverage from network traffic.
    
    Can integrate with:
    - Browser DevTools Network tab
    - Selenium/Playwright network listeners
    - Proxy tools (mitmproxy, BrowserMob)
    - HAR file exports
    """
    
    def __init__(self):
        self.captured_endpoints: Dict[str, ApiEndpointCoverage] = {}
    
    def record_api_call(
        self,
        test_case_id: uuid.UUID,
        endpoint_path: str,
        http_method: str,
        status_code: int,
        request_body: Optional[Dict] = None,
        response_body: Optional[Dict] = None,
        execution_time_ms: Optional[float] = None
    ) -> ApiEndpointCoverage:
        """
        Record an API call made during test execution.
        
        Args:
            test_case_id: Test that made the call
            endpoint_path: API endpoint (e.g., /api/v1/users/123)
            http_method: HTTP method
            status_code: Response status code
            request_body: Request payload (optional)
            response_body: Response payload (optional)
            execution_time_ms: Request duration
            
        Returns:
            ApiEndpointCoverage object
        """
        # Normalize endpoint path (replace IDs with placeholders)
        normalized_path = self._normalize_endpoint(endpoint_path)
        
        # Extract schemas
        request_schema = self._extract_schema(request_body) if request_body else None
        response_schema = self._extract_schema(response_body) if response_body else None
        
        coverage = ApiEndpointCoverage(
            test_case_id=test_case_id,
            endpoint_path=normalized_path,
            http_method=http_method.upper(),
            status_code=status_code,
            request_schema=request_schema,
            response_schema=response_schema,
            execution_time_ms=execution_time_ms
        )
        
        # Cache by endpoint
        key = f"{http_method}:{normalized_path}"
        self.captured_endpoints[key] = coverage
        
        return coverage
    
    def get_covered_endpoints(self) -> List[ApiEndpointCoverage]:
        """Get all captured endpoint coverage."""
        return list(self.captured_endpoints.values())
    
    def get_coverage_summary(self) -> Dict:
        """
        Get summary of API coverage.
        
        Returns:
            Dict with endpoint counts, methods, status codes
        """
        endpoints = self.captured_endpoints.values()
        
        methods = set(e.http_method for e in endpoints)
        status_codes = set(e.status_code for e in endpoints)
        unique_paths = set(e.endpoint_path for e in endpoints)
        
        return {
            'total_endpoints': len(endpoints),
            'unique_paths': len(unique_paths),
            'http_methods': list(methods),
            'status_codes': list(status_codes),
            'endpoints': [
                {
                    'method': e.http_method,
                    'path': e.endpoint_path,
                    'status': e.status_code
                }
                for e in endpoints
            ]
        }
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path by replacing IDs with placeholders.
        
        Examples:
            /api/v1/users/12345 -> /api/v1/users/{id}
            /api/orders/abc-123/items -> /api/orders/{id}/items
        """
        # Replace UUIDs first (case insensitive) - must be before alphanumeric
        # Pattern matches standard UUID format: 8-4-4-4-12 hex digits
        import re
        uuid_pattern = re.compile(
            r'/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
            re.IGNORECASE
        )
        path = uuid_pattern.sub('/{id}', path)
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Replace alphanumeric IDs (e.g., abc123) - must be 10+ chars to avoid false positives
        path = re.sub(r'/[a-zA-Z0-9-_]{10,}', '/{id}', path)
        
        return path
    
    def _extract_schema(self, data: Dict) -> Dict:
        """
        Extract schema structure from JSON data.
        
        Returns dict with field names and types.
        """
        if not isinstance(data, dict):
            return {}
        
        schema = {}
        for key, value in data.items():
            schema[key] = type(value).__name__
        
        return schema


class UiComponentCollector:
    """
    Collects UI component/element coverage during test execution.
    
    Integrates with:
    - Selenium WebDriver
    - Playwright
    - Cypress
    - Robot Framework
    """
    
    def __init__(self):
        self.captured_components: List[UiComponentCoverage] = []
    
    def record_interaction(
        self,
        test_case_id: uuid.UUID,
        component_name: str,
        component_type: str,
        interaction_type: str = "click",
        selector: Optional[str] = None,
        page_url: Optional[str] = None
    ) -> UiComponentCoverage:
        """
        Record a UI component interaction.
        
        Args:
            test_case_id: Test performing interaction
            component_name: Name/ID of component
            component_type: Type (button, input, dropdown, etc.)
            interaction_type: Action (click, type, hover, etc.)
            selector: CSS selector or XPath
            page_url: Page where interaction occurred
            
        Returns:
            UiComponentCoverage object
        """
        coverage = UiComponentCoverage(
            test_case_id=test_case_id,
            component_name=component_name,
            component_type=component_type,
            selector=selector,
            page_url=page_url,
            interaction_type=interaction_type
        )
        
        self.captured_components.append(coverage)
        return coverage
    
    def get_covered_components(self) -> List[UiComponentCoverage]:
        """Get all captured component interactions."""
        return self.captured_components
    
    def get_coverage_summary(self) -> Dict:
        """
        Get summary of UI component coverage.
        
        Returns:
            Dict with component counts, types, pages
        """
        unique_components = set(c.component_name for c in self.captured_components)
        component_types = set(c.component_type for c in self.captured_components)
        pages = set(c.page_url for c in self.captured_components if c.page_url)
        
        return {
            'total_interactions': len(self.captured_components),
            'unique_components': len(unique_components),
            'component_types': list(component_types),
            'pages_covered': list(pages),
            'components': [
                {
                    'name': c.component_name,
                    'type': c.component_type,
                    'interaction': c.interaction_type,
                    'page': c.page_url
                }
                for c in self.captured_components
            ]
        }


class NetworkCaptureCollector:
    """
    Captures all network traffic during test execution.
    
    Provides raw network data for detailed analysis.
    Can be used to generate ApiEndpointCoverage.
    """
    
    def __init__(self):
        self.captures: List[NetworkCapture] = []
    
    def record_request(
        self,
        test_case_id: uuid.UUID,
        request_url: str,
        request_method: str,
        request_headers: Optional[Dict] = None,
        request_body: Optional[str] = None,
        response_status: Optional[int] = None,
        response_headers: Optional[Dict] = None,
        response_body: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> NetworkCapture:
        """
        Record a network request/response.
        
        Args:
            test_case_id: Test that made the request
            request_url: Full URL
            request_method: HTTP method
            request_headers: Request headers
            request_body: Request body (text)
            response_status: Response status code
            response_headers: Response headers
            response_body: Response body (text)
            duration_ms: Request duration
            
        Returns:
            NetworkCapture object
        """
        capture = NetworkCapture(
            test_case_id=test_case_id,
            request_url=request_url,
            request_method=request_method.upper(),
            request_headers=request_headers,
            request_body=request_body,
            response_status=response_status,
            response_headers=response_headers,
            response_body=response_body,
            duration_ms=duration_ms
        )
        
        self.captures.append(capture)
        return capture
    
    def get_captures(self) -> List[NetworkCapture]:
        """Get all network captures."""
        return self.captures
    
    def to_api_endpoint_coverage(self) -> List[ApiEndpointCoverage]:
        """
        Convert network captures to API endpoint coverage.
        
        Returns:
            List of ApiEndpointCoverage objects
        """
        endpoint_collector = ApiEndpointCollector()
        
        for capture in self.captures:
            # Parse URL to extract path
            from urllib.parse import urlparse
            parsed = urlparse(capture.request_url)
            
            endpoint_collector.record_api_call(
                test_case_id=capture.test_case_id,
                endpoint_path=parsed.path,
                http_method=capture.request_method,
                status_code=capture.response_status or 0,
                execution_time_ms=capture.duration_ms
            )
        
        return endpoint_collector.get_covered_endpoints()


class ContractCoverageCollector:
    """
    Collects API contract/schema coverage.
    
    Validates which request/response fields are exercised.
    Useful for OpenAPI/Swagger contract testing.
    """
    
    def __init__(self):
        self.contracts: List[ContractCoverage] = []
    
    def record_contract_usage(
        self,
        test_case_id: uuid.UUID,
        contract_name: str,
        contract_version: str,
        request_fields: Set[str],
        response_fields: Set[str],
        validation_passed: bool = True,
        validation_errors: Optional[List[str]] = None
    ) -> ContractCoverage:
        """
        Record contract/schema coverage.
        
        Args:
            test_case_id: Test using the contract
            contract_name: Contract/API name
            contract_version: Version
            request_fields: Fields used in request
            response_fields: Fields received in response
            validation_passed: Contract validation result
            validation_errors: Validation error messages
            
        Returns:
            ContractCoverage object
        """
        coverage = ContractCoverage(
            test_case_id=test_case_id,
            contract_name=contract_name,
            contract_version=contract_version,
            request_fields_covered=request_fields,
            response_fields_covered=response_fields,
            validation_passed=validation_passed,
            validation_errors=validation_errors
        )
        
        self.contracts.append(coverage)
        return coverage
    
    def get_contract_coverage(self) -> List[ContractCoverage]:
        """Get all contract coverage records."""
        return self.contracts
    
    def get_coverage_summary(self) -> Dict:
        """
        Get contract coverage summary.
        
        Returns:
            Dict with contract counts and field coverage
        """
        total_request_fields = sum(len(c.request_fields_covered) for c in self.contracts)
        total_response_fields = sum(len(c.response_fields_covered) for c in self.contracts)
        passed = sum(1 for c in self.contracts if c.validation_passed)
        
        return {
            'total_contracts': len(self.contracts),
            'total_request_fields': total_request_fields,
            'total_response_fields': total_response_fields,
            'validation_passed': passed,
            'validation_failed': len(self.contracts) - passed,
            'contracts': [
                {
                    'name': c.contract_name,
                    'version': c.contract_version,
                    'request_fields': len(c.request_fields_covered),
                    'response_fields': len(c.response_fields_covered),
                    'valid': c.validation_passed
                }
                for c in self.contracts
            ]
        }
