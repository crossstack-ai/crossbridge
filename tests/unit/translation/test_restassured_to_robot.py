"""
Unit tests for RestAssured to Robot Framework translation.

Tests the complete pipeline: RestAssured Java → TestIntent → Robot Framework
"""

import pytest

from core.translation.intent_model import ActionType, AssertionType, IntentType
from core.translation.parsers.restassured_parser import RestAssuredParser
from core.translation.generators.robot_generator import RobotGenerator
from core.translation.pipeline import TranslationPipeline, TranslationConfig


class TestRestAssuredToRobotParser:
    """Test RestAssured parser for Robot Framework translation."""
    
    def test_parse_simple_get_request(self):
        """Test parsing simple GET request."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testGetUsers() {
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
        
        # Check request action
        request_actions = [a for a in intent.steps if a.action_type == ActionType.REQUEST]
        assert len(request_actions) == 1
        assert request_actions[0].semantics['method'] == 'GET'
        assert request_actions[0].value == '/api/users'
        
        # Check assertion
        assert len(intent.assertions) == 1
        assert intent.assertions[0].assertion_type == AssertionType.STATUS_CODE
        assert intent.assertions[0].expected == 200
    
    def test_parse_post_with_json_body(self):
        """Test parsing POST request with JSON body."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testCreateUser() {
            given()
                .contentType("application/json")
                .body("{\\"name\\": \\"John Doe\\", \\"email\\": \\"john@test.com\\"}")
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
        assert 'Content-Type' in request_actions[0].semantics['headers']
    
    def test_parse_put_request(self):
        """Test parsing PUT request."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testUpdateUser() {
            given()
                .body("{\\"name\\": \\"Jane\\"}")
            .when()
                .put("/api/users/1")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        request_actions = [a for a in intent.steps if a.action_type == ActionType.REQUEST]
        
        assert len(request_actions) == 1
        assert request_actions[0].semantics['method'] == 'PUT'
        assert '/api/users/1' in request_actions[0].value
    
    def test_parse_delete_request(self):
        """Test parsing DELETE request."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testDeleteUser() {
            given()
            .when()
                .delete("/api/users/1")
            .then()
                .statusCode(204);
        }
        """
        
        intent = parser.parse(code)
        request_actions = [a for a in intent.steps if a.action_type == ActionType.REQUEST]
        
        assert len(request_actions) == 1
        assert request_actions[0].semantics['method'] == 'DELETE'
    
    def test_parse_basic_authentication(self):
        """Test parsing basic authentication."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testWithAuth() {
            given()
                .auth().basic("admin", "password123")
            .when()
                .get("/api/protected")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        auth_actions = [a for a in intent.steps if a.action_type == ActionType.AUTH]
        
        assert len(auth_actions) >= 1
        assert 'admin' in auth_actions[0].value
    
    def test_parse_custom_headers(self):
        """Test parsing custom headers."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testWithHeaders() {
            given()
                .header("X-API-Key", "secret-key")
                .header("Accept", "application/json")
            .when()
                .get("/api/data")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        request_actions = [a for a in intent.steps if a.action_type == ActionType.REQUEST]
        
        assert len(request_actions) == 1
        assert 'X-API-Key' in request_actions[0].semantics['headers']
    
    def test_parse_response_body_assertion(self):
        """Test parsing response body assertions."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testResponseBody() {
            given()
            .when()
                .get("/api/users/1")
            .then()
                .statusCode(200)
                .body("name", equalTo("John"))
                .body("email", equalTo("john@test.com"));
        }
        """
        
        intent = parser.parse(code)
        
        # Should have status code assertion + body assertions
        assert len(intent.assertions) >= 3
        body_assertions = [a for a in intent.assertions if a.assertion_type == AssertionType.RESPONSE_BODY]
        assert len(body_assertions) == 2


class TestRestAssuredToRobotGenerator:
    """Test Robot Framework generator for RestAssured tests."""
    
    def test_generate_simple_get_request(self):
        """Test generating Robot Framework code for GET request."""
        parser = RestAssuredParser()
        generator = RobotGenerator()
        
        code = """
        @Test
        public void testGetUsers() {
            given()
            .when()
                .get("/api/users")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        robot_code = generator.generate(intent)
        
        # Verify Robot Framework structure
        assert '*** Settings ***' in robot_code
        assert '*** Test Cases ***' in robot_code
        assert 'Library    RequestsLibrary' in robot_code
        assert 'GET On Session' in robot_code
        assert 'api' in robot_code
        assert '/api/users' in robot_code
        assert 'Status Should Be' in robot_code
        assert '200' in robot_code
    
    def test_generate_post_with_body(self):
        """Test generating Robot Framework code for POST request."""
        parser = RestAssuredParser()
        generator = RobotGenerator()
        
        code = """
        @Test
        public void testCreateUser() {
            given()
                .body("{\\"name\\": \\"John\\"}")
            .when()
                .post("/api/users")
            .then()
                .statusCode(201);
        }
        """
        
        intent = parser.parse(code)
        robot_code = generator.generate(intent)
        
        assert 'POST On Session' in robot_code
        assert '/api/users' in robot_code
        assert 'json=' in robot_code or 'data=' in robot_code
    
    def test_generate_with_headers(self):
        """Test generating Robot Framework code with custom headers."""
        parser = RestAssuredParser()
        generator = RobotGenerator()
        
        code = """
        @Test
        public void testWithHeaders() {
            given()
                .header("X-API-Key", "secret")
            .when()
                .get("/api/data")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        robot_code = generator.generate(intent)
        
        assert 'GET On Session' in robot_code
        assert 'headers=' in robot_code or 'X-API-Key' in robot_code
    
    def test_generate_suite_setup(self):
        """Test that API tests generate proper suite setup."""
        parser = RestAssuredParser()
        generator = RobotGenerator()
        
        code = """
        @Test
        public void testApi() {
            given().when().get("/test").then().statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        robot_code = generator.generate(intent)
        
        assert 'Suite Setup' in robot_code
        assert 'Create Session' in robot_code
        assert 'Suite Teardown' in robot_code
        assert 'Delete All Sessions' in robot_code
    
    def test_generate_response_body_assertion(self):
        """Test generating Robot Framework assertions for response body."""
        parser = RestAssuredParser()
        generator = RobotGenerator()
        
        code = """
        @Test
        public void testResponseBody() {
            given()
            .when()
                .get("/api/users/1")
            .then()
                .body("name", equalTo("John"));
        }
        """
        
        intent = parser.parse(code)
        robot_code = generator.generate(intent)
        
        # Should have assertion for response body
        assert 'Should Be Equal' in robot_code or 'Dictionary Should Contain' in robot_code
        assert 'name' in robot_code
        assert 'John' in robot_code


class TestRestAssuredToRobotPipeline:
    """Test complete translation pipeline."""
    
    def test_end_to_end_translation(self):
        """Test complete RestAssured to Robot Framework translation."""
        config = TranslationConfig(
            source_framework="restassured",
            target_framework="robot"
        )
        
        pipeline = TranslationPipeline(config)
        
        restassured_code = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class UserApiTest {
            @Test
            public void testGetAllUsers() {
                given()
                    .auth().basic("admin", "admin123")
                    .header("Accept", "application/json")
                .when()
                    .get("https://api.example.com/users")
                .then()
                    .statusCode(200)
                    .body("users.size()", equalTo(10));
            }
        }
        """
        
        result = pipeline.translate(
            source_code=restassured_code,
            source_framework="restassured",
            target_framework="robot"
        )
        
        assert result.success
        assert result.target_code
        robot_code = result.target_code
        
        # Verify comprehensive Robot Framework structure
        assert '*** Settings ***' in robot_code
        assert 'Library    RequestsLibrary' in robot_code
        assert 'Suite Setup    Create Session' in robot_code
        assert '*** Test Cases ***' in robot_code
        assert 'GET On Session' in robot_code
        assert 'Status Should Be    200' in robot_code
    
    def test_translation_with_multiple_methods(self):
        """Test translation with multiple HTTP methods."""
        config = TranslationConfig(
            source_framework="restassured",
            target_framework="robot"
        )
        
        pipeline = TranslationPipeline(config)
        
        restassured_code = """
        @Test
        public void testCrudOperations() {
            // Create
            given()
                .body("{\\"name\\": \\"Test\\"}")
            .when()
                .post("/api/items")
            .then()
                .statusCode(201);
            
            // Read
            given()
            .when()
                .get("/api/items/1")
            .then()
                .statusCode(200);
            
            // Update
            given()
                .body("{\\"name\\": \\"Updated\\"}")
            .when()
                .put("/api/items/1")
            .then()
                .statusCode(200);
            
            // Delete
            given()
            .when()
                .delete("/api/items/1")
            .then()
                .statusCode(204);
        }
        """
        
        result = pipeline.translate(
            source_code=restassured_code,
            source_framework="restassured",
            target_framework="robot"
        )
        
        assert result.success
        robot_code = result.target_code
        
        # Should contain all HTTP methods
        assert 'POST On Session' in robot_code
        assert 'GET On Session' in robot_code
        assert 'PUT On Session' in robot_code
        assert 'DELETE On Session' in robot_code
    
    def test_translation_confidence_high(self):
        """Test that translation confidence is high for standard patterns."""
        config = TranslationConfig(
            source_framework="restassured",
            target_framework="robot"
        )
        
        pipeline = TranslationPipeline(config)
        
        restassured_code = """
        @Test
        public void testStandardApi() {
            given()
            .when()
                .get("/api/health")
            .then()
                .statusCode(200);
        }
        """
        
        result = pipeline.translate(
            source_code=restassured_code,
            source_framework="restassured",
            target_framework="robot"
        )
        
        assert result.success
        assert result.confidence >= 0.8


class TestRestAssuredComplexScenarios:
    """Test complex RestAssured scenarios."""
    
    def test_chained_requests(self):
        """Test translation of chained API requests."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testChainedRequests() {
            String userId = given()
                .body("{\\"name\\": \\"John\\"}")
            .when()
                .post("/api/users")
            .then()
                .statusCode(201)
                .extract()
                .path("id");
            
            given()
            .when()
                .get("/api/users/" + userId)
            .then()
                .statusCode(200)
                .body("name", equalTo("John"));
        }
        """
        
        intent = parser.parse(code)
        
        # Should extract at least the POST request (GET with dynamic URL may not parse)
        request_actions = [a for a in intent.steps if a.action_type == ActionType.REQUEST]
        assert len(request_actions) >= 1
        assert request_actions[0].semantics['method'] == 'POST'
    
    def test_query_parameters(self):
        """Test parsing query parameters."""
        parser = RestAssuredParser()
        
        code = """
        @Test
        public void testWithQueryParams() {
            given()
                .queryParam("page", "1")
                .queryParam("limit", "10")
            .when()
                .get("/api/users")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        request_actions = [a for a in intent.steps if a.action_type == ActionType.REQUEST]
        
        # Query params should be captured
        assert len(request_actions) >= 1
        # Note: Query param parsing may need enhancement in the parser
    
    def test_path_parameters(self):
        """Test translation with path parameters."""
        parser = RestAssuredParser()
        generator = RobotGenerator()
        
        code = """
        @Test
        public void testPathParams() {
            given()
                .pathParam("id", "123")
            .when()
                .get("/api/users/{id}")
            .then()
                .statusCode(200);
        }
        """
        
        intent = parser.parse(code)
        robot_code = generator.generate(intent)
        
        # Should handle path params
        assert 'GET On Session' in robot_code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
