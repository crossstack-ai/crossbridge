"""
Annotation patterns for parsing Selenium-Java test code (TestNG + JUnit).
"""

TEST_ANNOTATIONS = [
    r"@Test\b",              # TestNG + JUnit
]

TAG_ANNOTATIONS = [
    r"@Tag\(\"(.*?)\"\)",    # JUnit 5
    r"@Tags?\(\{?(.*?)\}?\)",# TestNG
]

METHOD_PATTERN = r"public\s+void\s+(\w+)\s*\("
CLASS_PATTERN = r"class\s+(\w+)"
