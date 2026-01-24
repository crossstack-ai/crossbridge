"""
Tests for RestAssured OAuth/JWT authentication detection.
"""

import pytest
from pathlib import Path

from adapters.restassured_java.extractor import RestAssuredExtractor
from adapters.restassured_java.config import RestAssuredConfig


class TestRestAssuredAuthentication:
    """Test authentication detection in RestAssured tests."""
    
    def test_basic_auth_detection(self):
        """Test detection of basic authentication."""
        code = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            @Test
            public void testBasicAuth() {
                given()
                    .auth().basic("admin", "password123")
                .when()
                    .get("/api/protected")
                .then()
                    .statusCode(200);
            }
        }
        """
        
        extractor = RestAssuredExtractor()
        auth_info = extractor.extract_authentication_info(code)
        
        assert auth_info['type'] == 'basic'
        assert auth_info['username'] == 'admin'
        assert auth_info['password'] == 'password123'
        assert not auth_info['has_oauth']
        assert not auth_info['has_jwt']
    
    def test_oauth2_detection(self):
        """Test detection of OAuth2 authentication."""
        code = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            @Test
            public void testOAuth2() {
                given()
                    .auth().oauth2("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
                .when()
                    .get("/api/user")
                .then()
                    .statusCode(200);
            }
        }
        """
        
        extractor = RestAssuredExtractor()
        auth_info = extractor.extract_authentication_info(code)
        
        assert auth_info['type'] == 'oauth2'
        assert auth_info['token'] == 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
        assert auth_info['has_oauth']
        assert not auth_info['has_jwt']  # OAuth2 but not marked as JWT specifically
    
    def test_bearer_token_detection(self):
        """Test detection of Bearer token (JWT)."""
        code = """
        import io.restassured.RestAssured;
        import org.junit.jupiter.api.Test;
        
        public class ApiTest {
            @Test
            public void testBearerAuth() {
                given()
                    .header("Authorization", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0")
                .when()
                    .get("/api/protected")
                .then()
                    .statusCode(200);
            }
        }
        """
        
        extractor = RestAssuredExtractor()
        auth_info = extractor.extract_authentication_info(code)
        
        assert auth_info['type'] == 'bearer'
        assert 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' in auth_info['token']
        assert not auth_info['has_oauth']
        assert auth_info['has_jwt']
    
    def test_jwt_variable_detection(self):
        """Test detection of JWT token in variable."""
        code = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            String authToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload";
            
            @Test
            public void testWithToken() {
                given()
                    .header("Authorization", "Bearer " + authToken)
                .when()
                    .get("/api/user")
                .then()
                    .statusCode(200);
            }
        }
        """
        
        extractor = RestAssuredExtractor()
        auth_info = extractor.extract_authentication_info(code)
        
        assert auth_info['has_jwt']
        assert 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' in auth_info['token']
    
    def test_oauth_client_credentials_detection(self):
        """Test detection of OAuth client credentials."""
        code = """
        import io.restassured.RestAssured;
        import org.junit.jupiter.api.Test;
        
        public class ApiTest {
            private String clientId = "my-client-app-123";
            private String apiKey = "secret-api-key-456";
            
            @Test
            public void testClientCreds() {
                given()
                    .formParam("client_id", clientId)
                    .formParam("client_secret", "secret")
                .when()
                    .post("/oauth/token")
                .then()
                    .statusCode(200);
            }
        }
        """
        
        extractor = RestAssuredExtractor()
        auth_info = extractor.extract_authentication_info(code)
        
        assert auth_info['has_oauth']
        assert auth_info['client_id'] in ['my-client-app-123', 'secret-api-key-456']
    
    def test_no_authentication(self):
        """Test when no authentication is present."""
        code = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            @Test
            public void testPublicEndpoint() {
                given()
                .when()
                    .get("/api/public")
                .then()
                    .statusCode(200);
            }
        }
        """
        
        extractor = RestAssuredExtractor()
        auth_info = extractor.extract_authentication_info(code)
        
        assert auth_info['type'] is None
        assert not auth_info['has_oauth']
        assert not auth_info['has_jwt']
    
    def test_multiple_auth_types(self):
        """Test file with multiple authentication types."""
        code = """
        import io.restassured.RestAssured;
        import org.testng.annotations.Test;
        
        public class ApiTest {
            String jwtToken = "eyJhbGciOiJIUzI1NiJ9.payload";
            
            @Test(groups = "basic")
            public void testBasic() {
                given()
                    .auth().basic("user", "pass")
                .when().get("/api/v1").then().statusCode(200);
            }
            
            @Test(groups = "oauth")
            public void testOAuth() {
                given()
                    .auth().oauth2(jwtToken)
                .when().get("/api/v2").then().statusCode(200);
            }
            
            @Test(groups = "bearer")
            public void testBearer() {
                given()
                    .header("Authorization", "Bearer " + jwtToken)
                .when().get("/api/v3").then().statusCode(200);
            }
        }
        """
        
        extractor = RestAssuredExtractor()
        auth_info = extractor.extract_authentication_info(code)
        
        # Should detect multiple auth types
        assert auth_info['type'] in ['basic', 'oauth2', 'bearer']
        assert auth_info['has_oauth'] or auth_info['has_jwt']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
