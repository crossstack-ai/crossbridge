"""
RestAssured to Robot Framework + Python requests - Complete Example

This example demonstrates the full translation of RestAssured Java API tests
to Robot Framework using RequestsLibrary (Python requests wrapper).

Usage:
    python examples/restassured_to_robot_example.py
"""

from pathlib import Path
from core.translation.pipeline import TranslationPipeline, TranslationConfig


def example_simple_get():
    """Example: Simple GET request translation."""
    print("=" * 80)
    print("Example 1: Simple GET Request")
    print("=" * 80)
    
    restassured_code = """
    import io.restassured.RestAssured;
    import org.testng.annotations.Test;
    
    public class UserApiTest {
        @Test
        public void testGetAllUsers() {
            given()
            .when()
                .get("/api/users")
            .then()
                .statusCode(200);
        }
    }
    """
    
    config = TranslationConfig(
        source_framework="restassured",
        target_framework="robot"
    )
    
    pipeline = TranslationPipeline(config)
    result = pipeline.translate(
        source_code=restassured_code,
        source_framework="restassured",
        target_framework="robot"
    )
    
    print("\n Input (RestAssured Java):")
    print(restassured_code)
    
    print("\n Output (Robot Framework):")
    print(result.target_code)
    
    print(f"\n Translation Success: {result.success}")
    print(f" Confidence: {result.confidence:.2%}")
    print()


def example_post_with_json():
    """Example: POST request with JSON body."""
    print("=" * 80)
    print("Example 2: POST with JSON Body")
    print("=" * 80)
    
    restassured_code = """
    @Test
    public void testCreateUser() {
        given()
            .contentType("application/json")
            .body("{\\"name\\": \\"John Doe\\", \\"email\\": \\"john@test.com\\", \\"age\\": 30}")
        .when()
            .post("/api/users")
        .then()
            .statusCode(201)
            .body("id", notNullValue())
            .body("name", equalTo("John Doe"));
    }
    """
    
    config = TranslationConfig(
        source_framework="restassured",
        target_framework="robot"
    )
    
    pipeline = TranslationPipeline(config)
    result = pipeline.translate(
        source_code=restassured_code,
        source_framework="restassured",
        target_framework="robot"
    )
    
    print("\n Input (RestAssured Java):")
    print(restassured_code)
    
    print("\n Output (Robot Framework):")
    print(result.target_code)
    
    print(f"\n Translation Success: {result.success}")
    print(f" Confidence: {result.confidence:.2%}")
    print()


def example_crud_operations():
    """Example: Complete CRUD operations."""
    print("=" * 80)
    print("Example 3: Complete CRUD Operations")
    print("=" * 80)
    
    restassured_code = """
    import io.restassured.RestAssured;
    import static io.restassured.RestAssured.*;
    import static org.hamcrest.Matchers.*;
    import org.testng.annotations.Test;
    
    public class CrudApiTest {
        @Test
        public void testCrudOperations() {
            // CREATE - POST
            given()
                .contentType("application/json")
                .body("{\\"name\\": \\"Test Item\\", \\"price\\": 99.99}")
            .when()
                .post("/api/items")
            .then()
                .statusCode(201);
            
            // READ - GET
            given()
            .when()
                .get("/api/items/1")
            .then()
                .statusCode(200)
                .body("name", equalTo("Test Item"));
            
            // UPDATE - PUT
            given()
                .contentType("application/json")
                .body("{\\"name\\": \\"Updated Item\\", \\"price\\": 149.99}")
            .when()
                .put("/api/items/1")
            .then()
                .statusCode(200);
            
            // DELETE
            given()
            .when()
                .delete("/api/items/1")
            .then()
                .statusCode(204);
        }
    }
    """
    
    config = TranslationConfig(
        source_framework="restassured",
        target_framework="robot"
    )
    
    pipeline = TranslationPipeline(config)
    result = pipeline.translate(
        source_code=restassured_code,
        source_framework="restassured",
        target_framework="robot"
    )
    
    print("\n Input (RestAssured Java):")
    print(restassured_code)
    
    print("\n Output (Robot Framework):")
    print(result.target_code)
    
    print(f"\n Translation Success: {result.success}")
    print(f" Confidence: {result.confidence:.2%}")
    print()


def example_authentication():
    """Example: API with authentication."""
    print("=" * 80)
    print("Example 4: API with Basic Authentication")
    print("=" * 80)
    
    restassured_code = """
    @Test
    public void testProtectedEndpoint() {
        given()
            .auth().basic("admin", "admin123")
            .header("Accept", "application/json")
            .header("X-API-Key", "secret-key-12345")
        .when()
            .get("/api/protected/data")
        .then()
            .statusCode(200)
            .body("status", equalTo("authorized"))
            .body("data", notNullValue());
    }
    """
    
    config = TranslationConfig(
        source_framework="restassured",
        target_framework="robot"
    )
    
    pipeline = TranslationPipeline(config)
    result = pipeline.translate(
        source_code=restassured_code,
        source_framework="restassured",
        target_framework="robot"
    )
    
    print("\n Input (RestAssured Java):")
    print(restassured_code)
    
    print("\n Output (Robot Framework):")
    print(result.target_code)
    
    print(f"\n Translation Success: {result.success}")
    print(f" Confidence: {result.confidence:.2%}")
    print()


def example_complex_assertions():
    """Example: Complex response validations."""
    print("=" * 80)
    print("Example 5: Complex Response Validations")
    print("=" * 80)
    
    restassured_code = """
    @Test
    public void testComplexValidations() {
        given()
            .contentType("application/json")
        .when()
            .get("/api/users")
        .then()
            .statusCode(200)
            .body("users.size()", greaterThan(0))
            .body("users[0].name", equalTo("Alice"))
            .body("users[0].email", containsString("@"))
            .body("users[0].active", equalTo(true))
            .header("Content-Type", containsString("application/json"));
    }
    """
    
    config = TranslationConfig(
        source_framework="restassured",
        target_framework="robot"
    )
    
    pipeline = TranslationPipeline(config)
    result = pipeline.translate(
        source_code=restassured_code,
        source_framework="restassured",
        target_framework="robot"
    )
    
    print("\n Input (RestAssured Java):")
    print(restassured_code)
    
    print("\n Output (Robot Framework):")
    print(result.target_code)
    
    print(f"\n Translation Success: {result.success}")
    print(f" Confidence: {result.confidence:.2%}")
    print()


def save_translated_example():
    """Save a complete translated example to file."""
    print("=" * 80)
    print("Saving Complete Translation Example")
    print("=" * 80)
    
    restassured_code = """
    import io.restassured.RestAssured;
    import static io.restassured.RestAssured.*;
    import static org.hamcrest.Matchers.*;
    import org.testng.annotations.Test;
    import org.testng.annotations.BeforeClass;
    
    public class UserManagementApiTest {
        
        @BeforeClass
        public void setup() {
            RestAssured.baseURI = "https://api.example.com";
        }
        
        @Test
        public void testGetUserById() {
            given()
                .pathParam("id", "123")
            .when()
                .get("/api/users/{id}")
            .then()
                .statusCode(200)
                .body("id", equalTo("123"))
                .body("username", notNullValue());
        }
        
        @Test
        public void testCreateNewUser() {
            String newUser = "{\\"username\\": \\"johndoe\\", " +
                           "\\"email\\": \\"john@example.com\\", " +
                           "\\"firstName\\": \\"John\\", " +
                           "\\"lastName\\": \\"Doe\\"}";
            
            given()
                .contentType("application/json")
                .body(newUser)
            .when()
                .post("/api/users")
            .then()
                .statusCode(201)
                .body("id", notNullValue())
                .body("username", equalTo("johndoe"));
        }
        
        @Test
        public void testUpdateUser() {
            given()
                .contentType("application/json")
                .pathParam("id", "123")
                .body("{\\"email\\": \\"newemail@example.com\\"}")
            .when()
                .put("/api/users/{id}")
            .then()
                .statusCode(200)
                .body("email", equalTo("newemail@example.com"));
        }
        
        @Test
        public void testDeleteUser() {
            given()
                .pathParam("id", "123")
            .when()
                .delete("/api/users/{id}")
            .then()
                .statusCode(204);
        }
        
        @Test
        public void testSearchUsers() {
            given()
                .queryParam("name", "John")
                .queryParam("limit", "10")
            .when()
                .get("/api/users/search")
            .then()
                .statusCode(200)
                .body("results.size()", lessThanOrEqualTo(10));
        }
    }
    """
    
    config = TranslationConfig(
        source_framework="restassured",
        target_framework="robot"
    )
    
    pipeline = TranslationPipeline(config)
    result = pipeline.translate(
        source_code=restassured_code,
        source_framework="restassured",
        target_framework="robot"
    )
    
    # Save to file
    output_file = Path("examples/output/user_management_api_test.robot")
    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(result.target_code)
    
    print(f"\n Saved translated test to: {output_file}")
    print(f" Translation confidence: {result.confidence:.2%}")
    print(f" Source lines: {len(restassured_code.splitlines())}")
    print(f" Target lines: {len(result.target_code.splitlines())}")
    print()


def print_migration_guide():
    """Print migration guide."""
    print("\n" + "=" * 80)
    print("RestAssured → Robot Framework + Python Requests Migration Guide")
    print("=" * 80)
    
    guide = """
    
 MIGRATION PATTERNS:

1. RestAssured given() → Robot Framework Session Setup
   
   RestAssured:
       given().auth().basic("user", "pass")
   
   Robot:
       Suite Setup    Create Session    api    ${BASE_URL}    auth=(user, pass)

2. RestAssured when() → Robot Framework Request Keywords
   
   RestAssured:
       .when().get("/api/users")
   
   Robot:
       ${response}=    GET On Session    api    /api/users

3. RestAssured then() → Robot Framework Assertions
   
   RestAssured:
       .then().statusCode(200)
   
   Robot:
       Status Should Be    200    ${response}

4. Request Body (JSON)
   
   RestAssured:
       .body("{\\"name\\": \\"John\\"}")
   
   Robot:
       ${response}=    POST On Session    api    /api/users    json={"name": "John"}

5. Response Body Assertions
   
   RestAssured:
       .body("name", equalTo("John"))
   
   Robot:
       ${value}=    Get Value From Json    ${response.json()}    $.name
       Should Be Equal As Strings    ${value}    John

6. Custom Headers
   
   RestAssured:
       .header("X-API-Key", "secret")
   
   Robot:
       ${headers}=    Create Dictionary    X-API-Key=secret
       ${response}=    GET On Session    api    /api/data    headers=${headers}

 REQUIRED LIBRARIES:

In Robot Framework, you need:
    pip install robotframework
    pip install robotframework-requests
    pip install robotframework-jsonlibrary (optional, for complex JSON)

 ROBOT FRAMEWORK STRUCTURE:

    *** Settings ***
    Library    RequestsLibrary
    Library    Collections
    Suite Setup    Create Session    api    ${BASE_URL}
    Suite Teardown    Delete All Sessions
    
    *** Variables ***
    ${BASE_URL}    https://api.example.com
    
    *** Test Cases ***
    Test Get Users
        ${response}=    GET On Session    api    /api/users
        Status Should Be    200    ${response}
        ${users}=    Get From Dictionary    ${response.json()}    users
        Length Should Be    ${users}    10

 BEST PRACTICES:

1. Use session management for base URLs
2. Store credentials in variables or Robot Framework vault
3. Use ${response} variable to capture and validate responses
4. Leverage Collections library for JSON manipulation
5. Add proper error handling with Run Keyword And Return Status
6. Use test templates for data-driven API tests

 RESOURCES:

- RequestsLibrary: https://marketsquare.github.io/robotframework-requests/
- Robot Framework: https://robotframework.org/
- Python requests: https://requests.readthedocs.io/
"""
    
    print(guide)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("RestAssured to Robot Framework Migration Examples")
    print("CrossBridge Framework - API Test Translation")
    print("=" * 80 + "\n")
    
    # Run examples
    example_simple_get()
    example_post_with_json()
    example_crud_operations()
    example_authentication()
    example_complex_assertions()
    
    # Save example
    save_translated_example()
    
    # Print guide
    print_migration_guide()
    
    print("\n All examples completed successfully!\n")


if __name__ == "__main__":
    main()
