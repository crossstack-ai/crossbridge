# RestAssured OAuth/JWT Authentication Support

## Overview

The RestAssured adapter now includes comprehensive support for detecting and extracting OAuth and JWT authentication patterns from your API tests. This enables better test analysis, transformation, and migration capabilities.

## Supported Authentication Types

### 1. Basic Authentication

```java
import io.restassured.RestAssured;
import static io.restassured.RestAssured.given;
import org.testng.annotations.Test;

public class BasicAuthTest {
    @Test
    public void testBasicAuth() {
        given()
            .auth().basic("username", "password")
        .when()
            .get("/api/protected")
        .then()
            .statusCode(200);
    }
}
```

**Detected Metadata:**
- `authentication.type`: `"basic"`
- `authentication.username`: `"username"`
- `authentication.password`: `"password"`

### 2. OAuth 2.0 Token

```java
import io.restassured.RestAssured;
import static io.restassured.RestAssured.given;
import org.junit.jupiter.api.Test;

public class OAuth2Test {
    @Test
    public void testOAuth2() {
        String token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0";
        
        given()
            .auth().oauth2(token)
        .when()
            .get("/api/user")
        .then()
            .statusCode(200);
    }
}
```

**Detected Metadata:**
- `authentication.type`: `"oauth2"`
- `authentication.token`: `"eyJhbGci..."`
- `has_oauth`: `true`

### 3. Bearer Token (JWT)

```java
import io.restassured.RestAssured;
import static io.restassured.RestAssured.given;
import org.testng.annotations.Test;

public class JwtTest {
    private String jwtToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature";
    
    @Test
    public void testBearerAuth() {
        given()
            .header("Authorization", "Bearer " + jwtToken)
        .when()
            .get("/api/protected")
        .then()
            .statusCode(200);
    }
}
```

**Detected Metadata:**
- `authentication.type`: `"bearer"`
- `authentication.token`: `"eyJhbGci..."`
- `has_jwt`: `true`

### 4. OAuth Client Credentials

```java
import io.restassured.RestAssured;
import static io.restassured.RestAssured.given;
import org.junit.jupiter.api.Test;

public class ClientCredsTest {
    private String clientId = "my-client-app-123";
    private String clientSecret = "secret-key-456";
    
    @Test
    public void testClientCredentials() {
        given()
            .formParam("client_id", clientId)
            .formParam("client_secret", clientSecret)
            .formParam("grant_type", "client_credentials")
        .when()
            .post("/oauth/token")
        .then()
            .statusCode(200);
    }
}
```

**Detected Metadata:**
- `authentication.client_id`: `"my-client-app-123"`
- `has_oauth`: `true`

## Using Authentication Detection

### Extract Authentication Info

```python
from adapters.restassured_java.extractor import RestAssuredExtractor
from adapters.restassured_java.config import RestAssuredConfig

# Create extractor
config = RestAssuredConfig(project_root="path/to/project")
extractor = RestAssuredExtractor(config)

# Extract test metadata
tests = extractor.extract_tests("path/to/test/file.java")

# Access authentication info
for test in tests:
    if test.metadata.get('authentication'):
        auth = test.metadata['authentication']
        print(f"Test: {test.test_name}")
        print(f"  Auth Type: {auth['type']}")
        
        if auth['type'] == 'basic':
            print(f"  Username: {auth['username']}")
        elif auth['type'] in ['oauth2', 'bearer']:
            print(f"  Token: {auth['token'][:20]}...")
        
        print(f"  Has OAuth: {test.metadata['has_oauth']}")
        print(f"  Has JWT: {test.metadata['has_jwt']}")
```

### Filter Tests by Authentication

```python
# Find all tests using OAuth
oauth_tests = [
    test for test in tests 
    if test.metadata.get('has_oauth', False)
]

# Find all tests using JWT
jwt_tests = [
    test for test in tests 
    if test.metadata.get('has_jwt', False)
]

# Find all tests using basic auth
basic_auth_tests = [
    test for test in tests 
    if test.metadata.get('authentication', {}).get('type') == 'basic'
]
```

## Transformation Benefits

Authentication detection enables:

1. **Smart Credential Management**: Automatically identify tests requiring credentials
2. **Security Analysis**: Find hardcoded credentials or tokens
3. **Test Categorization**: Group tests by authentication method
4. **Migration Planning**: Understand authentication complexity before transformation
5. **Target Framework Mapping**: Map RestAssured auth to equivalent methods in Playwright, Pytest, etc.

## Pattern Detection Details

The adapter uses regular expressions to detect:

- `.auth().basic(username, password)` calls
- `.auth().oauth2(token)` calls
- `.auth().oauth()` calls (OAuth 1.0)
- `.header("Authorization", "Bearer token")` patterns
- JWT tokens in string variables (recognizes common token variable names)
- OAuth client credentials (clientId, client_id, apiKey, api_key)

## Example: Security Audit

```python
from pathlib import Path
from adapters.restassured_java.extractor import RestAssuredExtractor
from adapters.restassured_java.config import RestAssuredConfig

def audit_authentication(project_root: str):
    """Audit authentication usage across all tests."""
    config = RestAssuredConfig(project_root=project_root)
    extractor = RestAssuredExtractor(config)
    
    # Find all Java test files
    test_files = Path(project_root).rglob("*Test.java")
    
    auth_summary = {
        'basic': 0,
        'oauth2': 0,
        'bearer': 0,
        'none': 0,
        'hardcoded_creds': []
    }
    
    for test_file in test_files:
        tests = extractor.extract_tests(str(test_file))
        
        for test in tests:
            auth = test.metadata.get('authentication')
            
            if not auth or not auth.get('type'):
                auth_summary['none'] += 1
                continue
            
            auth_type = auth['type']
            auth_summary[auth_type] = auth_summary.get(auth_type, 0) + 1
            
            # Check for hardcoded credentials
            if auth_type == 'basic' and auth.get('password'):
                if not auth['password'].startswith('$') and \
                   not auth['password'].startswith('System.'):
                    auth_summary['hardcoded_creds'].append({
                        'file': str(test_file),
                        'test': test.test_name,
                        'username': auth['username']
                    })
    
    return auth_summary

# Run audit
results = audit_authentication("path/to/project")
print(f"Authentication Summary:")
print(f"  Basic Auth: {results['basic']}")
print(f"  OAuth 2.0: {results['oauth2']}")
print(f"  Bearer/JWT: {results['bearer']}")
print(f"  No Auth: {results['none']}")
print(f"\nSecurity Issues:")
print(f"  Hardcoded Credentials: {len(results['hardcoded_creds'])}")
```

## Integration with Crossbridge CLI

The authentication detection is automatically used when running:

```bash
# Discover tests with authentication info
crossbridge discover --adapter restassured

# Transform tests (authentication patterns preserved)
crossbridge transform --source restassured --target pytest

# Analyze authentication complexity
crossbridge analyze --adapter restassured --report auth-summary
```

## Testing

Run the authentication detection tests:

```bash
pytest tests/unit/adapters/test_restassured_auth.py -v
```

All 7 authentication detection tests should pass:
- ✅ Basic authentication detection
- ✅ OAuth 2.0 detection
- ✅ Bearer token (JWT) detection
- ✅ JWT variable detection
- ✅ OAuth client credentials detection
- ✅ No authentication detection
- ✅ Multiple authentication types

## Future Enhancements

Planned improvements:
- OAuth 1.0 signature detection
- API key authentication patterns
- AWS Signature v4 detection
- Custom authentication header patterns
- Environment variable credential extraction
- Vault/secrets manager integration hints

## See Also

- [RestAssured Adapter Documentation](../README.md)
- [Authentication Patterns Reference](patterns.py)
- [Test Extractor Implementation](extractor.py)
- [API Testing Best Practices](../docs/api-testing-guide.md)
