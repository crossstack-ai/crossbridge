"""
Unit tests for RestAssured to Pytest translation.
"""

import pytest

from core.translation.intent_model import ActionType, AssertionType, IntentType
from core.translation.parsers.restassured_parser import RestAssuredParser
from core.translation.generators.pytest_generator import PytestGenerator
from core.translation.pipeline import TranslationPipeline


class TestRestAssuredParser:
    """Test RestAssured parser."""
    
    def test_can_parse_restassured_code(self):
        """Test detection of RestAssured code."""
        parser = RestAssuredParser()
        
        restassured_code = """
        import io.restassured.RestAssured;
        
        @Test
        public void testGetUser() {
            given()
                .auth().basic("user", "pass")
            .when()
                .get("/api/users/1")
            .then()
                .statusCode(200);
        }
        """
        
        assert parser.can_parse(restassured_code)
    
    def test_parse_get_request(self):
        """Test parsing GET request."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testGet() {
            given()
            .when()
                .get("/api/users")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        assert intent.test_type == IntentType.API
        assert len(intent.steps) >= 1
        request_actions = [a for a in intent.steps if a.action_type == ActionType.REQUEST]
        assert len(request_actions) == 1
        assert request_actions[0].semantics['method'] == 'GET'
        assert request_actions[0].value == '/api/users'
    
    def test_parse_post_with_body(self):
        """Test parsing POST request with body."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testPost() {
            given()
                .body("{\\"name\\": \\"John\\"}")
            .when()
                .post("/api/users")
            .then()
                .statusCode(201);
        }
        """
        
        intent = parser.parse(code)
        request_actions = [a for a in intent.steps if a.action_type == ActionType.REQUEST]
        assert len(request_actions) == 1
        assert request_actions[0].semantics['method'] == 'POST'
        assert 'body' in request_actions[0].semantics
    
    def test_parse_authentication(self):
        """Test parsing basic authentication."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testAuth() {
            given()
                .auth().basic("admin", "secret")
            .when()
                .get("/api/protected")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        auth_actions = [a for a in intent.steps if a.action_type == ActionType.AUTH]
        assert len(auth_actions) == 1
        assert 'admin:secret' in auth_actions[0].value
    
    def test_parse_status_code_assertion(self):
        """Test parsing status code assertion."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testStatus() {
            given()
            .when()
                .get("/api/health")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        assert len(intent.assertions) == 1
        assert intent.assertions[0].assertion_type == AssertionType.STATUS_CODE
        assert intent.assertions[0].expected == 200
    
    def test_parse_body_assertion(self):
        """Test parsing response body assertion."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testBody() {
            given()
            .when()
                .get("/api/users/1")
            .then()
                .body("name", equalTo("John"));
        }
        """
        
        intent = parser.parse(code)
        body_assertions = [a for a in intent.assertions if a.assertion_type == AssertionType.RESPONSE_BODY]
        assert len(body_assertions) == 1
        assert body_assertions[0].target == 'name'
        assert body_assertions[0].expected == 'John'


class TestPytestGenerator:
    """Test pytest generator."""
    
    def test_can_generate_api_test(self):
        """Test capability check for API tests."""
        generator = PytestGenerator()
        
        from core.translation.intent_model import TestIntent
        intent = TestIntent(test_type=IntentType.API, name="test_api")
        
        assert generator.can_generate(intent)
    
    def test_generate_get_request(self):
        """Test generation of GET request."""
        generator = PytestGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.API, name="test_get")
        intent.add_step(ActionIntent(
            action_type=ActionType.REQUEST,
            target="GET_/api/users",
            value="/api/users",
            semantics={'method': 'GET', 'endpoint': '/api/users', 'headers': {}, 'auth': None},
        ))
        
        code = generator.generate(intent)
        assert "requests.get('/api/users')" in code
    
    def test_generate_post_with_auth(self):
        """Test generation of POST with authentication."""
        generator = PytestGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.API, name="test_post_auth")
        intent.add_step(ActionIntent(
            action_type=ActionType.REQUEST,
            target="POST_/api/users",
            value="/api/users",
            semantics={
                'method': 'POST',
                'endpoint': '/api/users',
                'headers': {},
                'auth': ('basic', 'user', 'pass'),
                'body': '{"name": "John"}',
            },
        ))
        
        code = generator.generate(intent)
        assert "requests.post" in code
        assert "auth=('user', 'pass')" in code
        assert "json=" in code
    
    def test_generate_status_assertion(self):
        """Test generation of status code assertion."""
        generator = PytestGenerator()
        
        from core.translation.intent_model import TestIntent, AssertionIntent
        intent = TestIntent(test_type=IntentType.API, name="test_status")
        intent.add_assertion(AssertionIntent(
            assertion_type=AssertionType.STATUS_CODE,
            target="response",
            expected=200,
        ))
        
        code = generator.generate(intent)
        assert "assert response.status_code == 200" in code
    
    def test_generate_body_assertion(self):
        """Test generation of response body assertion."""
        generator = PytestGenerator()
        
        from core.translation.intent_model import TestIntent, AssertionIntent
        intent = TestIntent(test_type=IntentType.API, name="test_body")
        intent.add_assertion(AssertionIntent(
            assertion_type=AssertionType.RESPONSE_BODY,
            target="name",
            expected="John",
        ))
        
        code = generator.generate(intent)
        assert "response.json()" in code
        assert "== 'John'" in code


class TestRestAssuredToPytestPipeline:
    """Test end-to-end RestAssured to pytest translation."""
    
    def test_complete_api_test_translation(self):
        """Test translating a complete API test."""
        restassured_code = """
        import io.restassured.RestAssured;
        
        @Test
        public void testUserApi() {
            given()
                .auth().basic("admin", "password")
                .header("Content-Type", "application/json")
                .body("{\\"name\\": \\"John\\"}")
            .when()
                .post("/api/users")
            .then()
                .statusCode(201)
                .body("name", equalTo("John"));
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=restassured_code,
            source_framework="restassured",
            target_framework="pytest",
        )
        
        assert result.success
        assert result.target_code
        assert "requests.post" in result.target_code
        assert "auth=('admin', 'password')" in result.target_code
        assert "assert response.status_code == 201" in result.target_code
    
    def test_get_request_translation(self):
        """Test simple GET request translation."""
        restassured_code = """
        @Test
        public void testGet() {
            given()
            .when()
                .get("/api/users/1")
            .then()
                .statusCode(200);
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=restassured_code,
            source_framework="restassured",
            target_framework="pytest",
        )
        
        assert result.success
        assert "requests.get('/api/users/1')" in result.target_code
        assert "def test_get():" in result.target_code
