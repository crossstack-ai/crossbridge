"""
RestAssured Java Parser.

Extracts TestIntent from RestAssured Java API test code.
"""

import re
from typing import List, Optional

from core.translation.intent_model import (
    ActionIntent,
    ActionType,
    AssertionIntent,
    AssertionType,
    IntentType,
    TestIntent,
)
from core.translation.pipeline import SourceParser


class RestAssuredParser(SourceParser):
    """Parser for RestAssured Java API tests."""
    
    def __init__(self, framework: str = "restassured"):
        """Initialize RestAssured parser."""
        super().__init__(framework)
    
    def can_parse(self, source_code: str) -> bool:
        """Check if this is RestAssured code."""
        indicators = [
            "import io.restassured",
            "RestAssured",
            "given()",
            ".when().",
            ".then().",
        ]
        return any(indicator in source_code for indicator in indicators)
    
    def parse(self, source_code: str, source_file: str = "") -> TestIntent:
        """
        Parse RestAssured Java code into TestIntent.
        
        Extracts:
        - Test methods
        - HTTP requests (GET, POST, PUT, DELETE)
        - Authentication
        - Headers, body, query params
        - Status code assertions
        - Response body assertions
        """
        # Extract test method
        test_name = self._extract_test_name(source_code)
        
        # Create test intent
        intent = TestIntent(
            test_type=IntentType.API,
            name=test_name or "test_api_translated",
            source_framework=self.framework,
            source_file=source_file,
        )
        
        # Parse BDD-style RestAssured chains (given/when/then)
        self._parse_bdd_chain(source_code, intent)
        
        return intent
    
    def _extract_test_name(self, source_code: str) -> Optional[str]:
        """Extract test method name."""
        test_pattern = r'@Test[^\n]*\s+public\s+void\s+(\w+)\s*\('
        match = re.search(test_pattern, source_code)
        if match:
            return match.group(1)
        return None
    
    def _parse_bdd_chain(self, source_code: str, intent: TestIntent):
        """Parse RestAssured given/when/then chain."""
        lines = source_code.split('\n')
        
        # Track state
        current_request = {
            'method': None,
            'endpoint': None,
            'auth': None,
            'headers': {},
            'body': None,
            'query_params': {},
        }
        
        in_given = False
        in_when = False
        in_then = False
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            if not line or line.startswith('//'):
                continue
            
            # Detect given/when/then boundaries
            if 'given()' in line:
                in_given = True
                in_when = False
                in_then = False
                continue
            elif '.when()' in line:
                in_given = False
                in_when = True
                in_then = False
                continue
            elif '.then()' in line:
                in_given = False
                in_when = False
                in_then = True
                continue
            
            # Parse given() section (setup)
            if in_given:
                # Authentication
                if '.auth()' in line or '.basic(' in line:
                    auth_match = re.search(r'\.basic\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)', line)
                    if auth_match:
                        current_request['auth'] = ('basic', auth_match.group(1), auth_match.group(2))
                        intent.add_step(ActionIntent(
                            action_type=ActionType.AUTH,
                            target="basic_auth",
                            value=f"{auth_match.group(1)}:{auth_match.group(2)}",
                            description="Set basic authentication",
                            line_number=line_num,
                        ))
                
                # Headers
                if '.header(' in line:
                    header_match = re.search(r'\.header\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)', line)
                    if header_match:
                        current_request['headers'][header_match.group(1)] = header_match.group(2)
                
                # Body
                if '.body(' in line:
                    body = self._extract_body(line)
                    if body:
                        current_request['body'] = body
                
                # Content-Type
                if '.contentType(' in line:
                    content_match = re.search(r'\.contentType\(\s*"([^"]+)"\s*\)', line)
                    if content_match:
                        current_request['headers']['Content-Type'] = content_match.group(1)
            
            # Parse when() section (action)
            if in_when:
                # HTTP methods
                if '.get(' in line:
                    current_request['method'] = 'GET'
                    current_request['endpoint'] = self._extract_endpoint(line, 'get')
                    self._add_request_action(intent, current_request, line_num)
                elif '.post(' in line:
                    current_request['method'] = 'POST'
                    current_request['endpoint'] = self._extract_endpoint(line, 'post')
                    self._add_request_action(intent, current_request, line_num)
                elif '.put(' in line:
                    current_request['method'] = 'PUT'
                    current_request['endpoint'] = self._extract_endpoint(line, 'put')
                    self._add_request_action(intent, current_request, line_num)
                elif '.delete(' in line:
                    current_request['method'] = 'DELETE'
                    current_request['endpoint'] = self._extract_endpoint(line, 'delete')
                    self._add_request_action(intent, current_request, line_num)
            
            # Parse then() section (assertions)
            if in_then:
                # Status code
                if '.statusCode(' in line:
                    status_match = re.search(r'\.statusCode\(\s*(\d+)\s*\)', line)
                    if status_match:
                        intent.add_assertion(AssertionIntent(
                            assertion_type=AssertionType.STATUS_CODE,
                            target="response",
                            expected=int(status_match.group(1)),
                            description=f"Assert status code is {status_match.group(1)}",
                            line_number=line_num,
                        ))
                
                # Body assertions
                if '.body(' in line and 'equalTo' in line:
                    body_match = re.search(r'\.body\(\s*"([^"]+)"\s*,\s*equalTo\(\s*"?([^"]+)"?\s*\)\)', line)
                    if body_match:
                        json_path = body_match.group(1)
                        expected = body_match.group(2).strip('"')
                        intent.add_assertion(AssertionIntent(
                            assertion_type=AssertionType.RESPONSE_BODY,
                            target=json_path,
                            expected=expected,
                            description=f"Assert {json_path} equals {expected}",
                            line_number=line_num,
                        ))
    
    def _extract_endpoint(self, line: str, method: str) -> Optional[str]:
        """Extract endpoint URL from method call."""
        pattern = rf'\.{method}\(\s*"([^"]+)"\s*\)'
        match = re.search(pattern, line)
        if match:
            return match.group(1)
        return None
    
    def _extract_body(self, line: str) -> Optional[str]:
        """Extract request body."""
        # JSON string
        if '"{' in line:
            body_match = re.search(r'\.body\(\s*"(\{[^}]+\})"\s*\)', line)
            if body_match:
                return body_match.group(1)
        
        # Object
        body_match = re.search(r'\.body\(\s*(\w+)\s*\)', line)
        if body_match:
            return f"${{{body_match.group(1)}}}"  # Variable placeholder
        
        return None
    
    def _add_request_action(self, intent: TestIntent, request: dict, line_num: int):
        """Add HTTP request action to intent."""
        method = request['method']
        endpoint = request['endpoint']
        
        # Skip if endpoint is None (parsing error)
        if not endpoint:
            return
        
        # Build semantics
        semantics = {
            'method': method,
            'endpoint': endpoint,
            'headers': request['headers'],
            'auth': request['auth'],
        }
        
        if request['body']:
            semantics['body'] = request['body']
        
        intent.add_step(ActionIntent(
            action_type=ActionType.REQUEST,
            target=f"{method}_{endpoint.replace('/', '_')}",
            value=endpoint,
            semantics=semantics,
            description=f"{method} request to {endpoint}",
            line_number=line_num,
        ))
