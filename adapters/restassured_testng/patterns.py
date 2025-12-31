"""
RestAssured + TestNG test patterns and constants.
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
    r'@Test\s*(?:\([^)]*\))?\s+(?:public\s+)?void\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{',
    re.MULTILINE
)

# TestNG groups pattern
GROUPS_PATTERN = re.compile(
    r'@Test\s*\(\s*groups\s*=\s*\{([^}]+)\}',
    re.MULTILINE
)

# TestNG single group pattern
SINGLE_GROUP_PATTERN = re.compile(
    r'@Test\s*\(\s*groups\s*=\s*"([^"]+)"',
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

# Description pattern
DESCRIPTION_PATTERN = re.compile(
    r'@Test\s*\([^)]*description\s*=\s*"([^"]+)"',
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

# Import pattern for RestAssured
IMPORT_PATTERN = re.compile(
    r'import\s+(?:static\s+)?io\.restassured\.',
    re.MULTILINE
)
