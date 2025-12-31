"""
RestAssured + Java test patterns and constants.

Supports both TestNG and JUnit 5 annotations and patterns.
"""

import re

# TestNG annotations
TESTNG_ANNOTATIONS = {
    '@Test',
    '@BeforeMethod',
    '@AfterMethod',
    '@BeforeClass',
    '@AfterClass',
    '@BeforeSuite',
    '@AfterSuite',
    '@BeforeTest',
    '@AfterTest',
    '@BeforeGroups',
    '@AfterGroups',
    '@DataProvider',
    '@Factory',
    '@Listeners',
    '@Parameters',
}

# JUnit 5 annotations
JUNIT5_ANNOTATIONS = {
    '@Test',
    '@DisplayName',
    '@Tag',
    '@Tags',
    '@Disabled',
    '@BeforeEach',
    '@AfterEach',
    '@BeforeAll',
    '@AfterAll',
    '@ParameterizedTest',
    '@RepeatedTest',
    '@TestFactory',
    '@Nested',
}

# RestAssured specific patterns
RESTASSURED_IMPORTS = [
    'io.restassured.RestAssured',
    'io.restassured.response.Response',
    'io.restassured.specification.RequestSpecification',
    'io.restassured.http.ContentType',
    'io.restassured.matcher.ResponseAwareMatcher',
    'static io.restassured.RestAssured.*',
    'static io.restassured.matcher.RestAssuredMatchers.*',
    'static org.hamcrest.Matchers.*',
]

# RestAssured method calls (for detection)
RESTASSURED_METHODS = [
    'given()',
    'when()',
    'then()',
    'get(',
    'post(',
    'put(',
    'delete(',
    'patch(',
    'head(',
    'options(',
    'baseURI',
    'basePath',
    'port',
    'authentication',
    'oauth',
    'oauth2',
    'basic',
    'digest',
    'form',
    'preemptive',
]

# Regex patterns
CLASS_PATTERN = re.compile(
    r'(?:public\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*\{',
    re.MULTILINE
)

TEST_METHOD_PATTERN = re.compile(
    r'(?:public\s+)?void\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{',
    re.MULTILINE
)

# TestNG groups pattern (handles groups anywhere in @Test annotation)
GROUPS_PATTERN = re.compile(
    r'groups\s*=\s*\{([^}]+)\}',
    re.MULTILINE
)

# TestNG single group pattern
SINGLE_GROUP_PATTERN = re.compile(
    r'groups\s*=\s*"([^"]+)"',
    re.MULTILINE
)

# Priority pattern
PRIORITY_PATTERN = re.compile(
    r'@Test\s*\([^)]*priority\s*=\s*(\d+)',
    re.MULTILINE
)

# Enabled/Disabled pattern
ENABLED_PATTERN = re.compile(
    r'@Test\s*\([^)]*enabled\s*=\s*(true|false)',
    re.MULTILINE
)

# Description pattern (TestNG)
DESCRIPTION_PATTERN = re.compile(
    r'@Test\s*\([^)]*description\s*=\s*"([^"]+)"',
    re.MULTILINE
)

# DisplayName pattern (JUnit 5)
DISPLAY_NAME_PATTERN = re.compile(
    r'@DisplayName\s*\(\s*"([^"]+)"',
    re.MULTILINE
)

# Tag pattern (JUnit 5)
JUNIT_TAG_PATTERN = re.compile(
    r'@Tag\s*\(\s*"([^"]+)"',
    re.MULTILINE
)

# Tags pattern (JUnit 5 multiple tags)
JUNIT_TAGS_PATTERN = re.compile(
    r'@Tags\s*\(\s*\{([^}]+)\}',
    re.MULTILINE
)

# Disabled pattern (JUnit 5)
DISABLED_PATTERN = re.compile(
    r'@Disabled',
    re.MULTILINE
)

# DependsOnMethods pattern
DEPENDS_ON_METHODS_PATTERN = re.compile(
    r'dependsOnMethods\s*=\s*\{([^}]+)\}',
    re.MULTILINE
)

# Package pattern
PACKAGE_PATTERN = re.compile(
    r'package\s+([\w.]+);',
    re.MULTILINE
)

# Import patterns
RESTASSURED_IMPORT_PATTERN = re.compile(
    r'import\s+(?:static\s+)?io\.restassured\.',
    re.MULTILINE
)

TESTNG_IMPORT_PATTERN = re.compile(
    r'import\s+org\.testng\.annotations\.',
    re.MULTILINE
)

JUNIT5_IMPORT_PATTERN = re.compile(
    r'import\s+org\.junit\.jupiter\.api\.',
    re.MULTILINE
)

# For backward compatibility
IMPORT_PATTERN = RESTASSURED_IMPORT_PATTERN
