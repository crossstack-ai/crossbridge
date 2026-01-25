"""
OpenAPI/Swagger contract validation for RestAssured tests.

Handles API contract validation and schema generation.
"""

import re
import json
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class APIContract:
    """Represents an API contract definition."""
    path: str
    method: str
    request_schema: Optional[Dict]
    response_schema: Optional[Dict]
    status_code: int
    test_name: str


class RestAssuredContractValidator:
    """Extract and validate API contracts from RestAssured tests."""
    
    def __init__(self):
        # RestAssured request patterns
        self.request_pattern = re.compile(
            r'given\(\).*?\.when\(\).*?\.(get|post|put|delete|patch)\("([^"]+)"',
            re.DOTALL | re.IGNORECASE
        )
        
        # Response status code pattern
        self.status_pattern = re.compile(
            r'\.statusCode\((\d+)\)',
            re.IGNORECASE
        )
        
        # Body validation pattern
        self.body_validation = re.compile(
            r'\.body\("([^"]+)",\s*(?:is|equalTo|hasItems?)\(([^)]+)\)\)',
            re.DOTALL
        )
        
        # Schema validation pattern
        self.schema_validation = re.compile(
            r'\.body\(matchesJsonSchema(?:InClasspath)?\("([^"]+)"\)\)',
            re.IGNORECASE
        )
    
    def extract_contracts_from_test(
        self,
        java_file: Path
    ) -> List[APIContract]:
        """
        Extract API contracts from RestAssured test file.
        
        Args:
            java_file: Path to Java test file
            
        Returns:
            List of APIContract objects
        """
        if not java_file.exists():
            return []
        
        content = java_file.read_text(encoding='utf-8')
        contracts = []
        
        # Find test methods
        test_methods = self._extract_test_methods(content)
        
        for test_name, test_body in test_methods.items():
            # Extract API endpoint and method
            request_match = self.request_pattern.search(test_body)
            if not request_match:
                continue
            
            http_method = request_match.group(1).upper()
            endpoint = request_match.group(2)
            
            # Extract expected status code
            status_match = self.status_pattern.search(test_body)
            status_code = int(status_match.group(1)) if status_match else 200
            
            # Extract request schema (if body is sent)
            request_schema = self._extract_request_schema(test_body)
            
            # Extract response validation
            response_schema = self._extract_response_schema(test_body)
            
            contracts.append(APIContract(
                path=endpoint,
                method=http_method,
                request_schema=request_schema,
                response_schema=response_schema,
                status_code=status_code,
                test_name=test_name
            ))
        
        return contracts
    
    def _extract_test_methods(self, content: str) -> Dict[str, str]:
        """Extract test methods and their bodies."""
        test_methods = {}
        
        method_pattern = re.compile(
            r'@Test\s+(?:public\s+)?void\s+(\w+)\s*\([^)]*\)\s*\{',
            re.MULTILINE
        )
        
        for match in method_pattern.finditer(content):
            method_name = match.group(1)
            method_start = match.end()
            
            # Extract method body
            method_body = self._extract_method_body(content, method_start)
            test_methods[method_name] = method_body
        
        return test_methods
    
    def _extract_method_body(self, content: str, start_pos: int) -> str:
        """Extract method body from start position."""
        brace_count = 1
        end_pos = start_pos
        
        for i in range(start_pos, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break
        
        return content[start_pos:end_pos]
    
    def _extract_request_schema(self, test_body: str) -> Optional[Dict]:
        """Extract request body schema from test."""
        # Look for .body() calls with JSON/object
        body_pattern = re.compile(
            r'\.body\(([^)]+)\)',
            re.IGNORECASE
        )
        
        match = body_pattern.search(test_body)
        if not match:
            return None
        
        body_content = match.group(1)
        
        # Try to parse as JSON string
        if '"' in body_content or "'" in body_content:
            # It's a string body
            return {'type': 'string', 'example': body_content[:100]}
        else:
            # It's an object reference
            return {'type': 'object', 'ref': body_content}
    
    def _extract_response_schema(self, test_body: str) -> Optional[Dict]:
        """Extract response validation schema."""
        schema = {'validations': []}
        
        # Check for schema validation
        schema_match = self.schema_validation.search(test_body)
        if schema_match:
            schema_file = schema_match.group(1)
            schema['schema_file'] = schema_file
            return schema
        
        # Extract body validations
        for match in self.body_validation.finditer(test_body):
            json_path = match.group(1)
            expected_value = match.group(2)
            
            schema['validations'].append({
                'path': json_path,
                'expected': expected_value.strip()
            })
        
        return schema if schema['validations'] or 'schema_file' in schema else None
    
    def generate_openapi_spec(
        self,
        contracts: List[APIContract],
        title: str = "API Specification",
        version: str = "1.0.0"
    ) -> Dict:
        """
        Generate OpenAPI 3.0 specification from contracts.
        
        Args:
            contracts: List of APIContract objects
            title: API title
            version: API version
            
        Returns:
            OpenAPI specification dictionary
        """
        spec = {
            'openapi': '3.0.0',
            'info': {
                'title': title,
                'version': version,
                'description': 'Generated from RestAssured tests'
            },
            'paths': {}
        }
        
        # Group contracts by path
        for contract in contracts:
            if contract.path not in spec['paths']:
                spec['paths'][contract.path] = {}
            
            # Add operation
            operation = {
                'summary': contract.test_name.replace('_', ' ').title(),
                'responses': {
                    str(contract.status_code): {
                        'description': f'Response from {contract.test_name}'
                    }
                }
            }
            
            # Add request body if present
            if contract.request_schema:
                operation['requestBody'] = {
                    'content': {
                        'application/json': {
                            'schema': contract.request_schema
                        }
                    }
                }
            
            # Add response schema if present
            if contract.response_schema:
                response_content = {
                    'application/json': {
                        'schema': contract.response_schema
                    }
                }
                operation['responses'][str(contract.status_code)]['content'] = response_content
            
            spec['paths'][contract.path][contract.method.lower()] = operation
        
        return spec
    
    def export_openapi_yaml(
        self,
        contracts: List[APIContract],
        output_file: Path
    ):
        """
        Export contracts as OpenAPI YAML file.
        
        Args:
            contracts: List of APIContract objects
            output_file: Path to output YAML file
        """
        spec = self.generate_openapi_spec(contracts)
        
        try:
            import yaml
            with open(output_file, 'w') as f:
                yaml.dump(spec, f, default_flow_style=False)
        except ImportError:
            # Fallback to JSON if PyYAML not available
            json_file = output_file.with_suffix('.json')
            with open(json_file, 'w') as f:
                json.dump(spec, f, indent=2)
    
    def validate_contract_coverage(
        self,
        contracts: List[APIContract],
        openapi_spec: Dict
    ) -> Dict[str, Any]:
        """
        Validate test coverage against OpenAPI specification.
        
        Args:
            contracts: List of extracted contracts from tests
            openapi_spec: OpenAPI specification dictionary
            
        Returns:
            Coverage report
        """
        report = {
            'total_endpoints': 0,
            'covered_endpoints': 0,
            'uncovered_endpoints': [],
            'coverage_percentage': 0.0
        }
        
        # Extract endpoints from spec
        spec_endpoints = set()
        for path, operations in openapi_spec.get('paths', {}).items():
            for method in operations.keys():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    spec_endpoints.add(f"{method.upper()} {path}")
        
        # Extract endpoints from contracts
        test_endpoints = set()
        for contract in contracts:
            test_endpoints.add(f"{contract.method} {contract.path}")
        
        # Calculate coverage
        report['total_endpoints'] = len(spec_endpoints)
        report['covered_endpoints'] = len(spec_endpoints & test_endpoints)
        report['uncovered_endpoints'] = list(spec_endpoints - test_endpoints)
        
        if report['total_endpoints'] > 0:
            report['coverage_percentage'] = (
                report['covered_endpoints'] / report['total_endpoints']
            ) * 100
        
        return report
    
    def has_contract_validation(self, java_file: Path) -> bool:
        """Check if test file uses schema validation."""
        if not java_file.exists():
            return False
        
        content = java_file.read_text(encoding='utf-8')
        return bool(self.schema_validation.search(content))
