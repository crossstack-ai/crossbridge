"""
JavaParser integration for AST-based Java test parsing.

This module provides a Python wrapper around JavaParser (Java library)
to extract test metadata with high accuracy.
"""

from pathlib import Path
from typing import List, Optional
import subprocess
import json
import tempfile
import shutil

from .model import JavaTestClass, JavaTestMethod, JavaAnnotation, JavaTestFramework


class JavaParserClient:
    """
    Client for interacting with JavaParser.
    
    Uses a Java utility that leverages JavaParser to extract AST metadata
    and returns it as JSON for Python consumption.
    """
    
    def __init__(self, java_parser_jar: Optional[str] = None):
        """
        Initialize JavaParser client.
        
        Args:
            java_parser_jar: Path to the JavaParser utility JAR.
                           If None, looks in adapters/java/parser/target/
        """
        self.java_parser_jar = java_parser_jar or self._find_parser_jar()
    
    def _find_parser_jar(self) -> Optional[str]:
        """Locate the JavaParser utility JAR."""
        # Look for JAR in expected locations
        possible_paths = [
            Path(__file__).parent / "parser" / "target" / "java-test-parser-1.0.jar",
            Path(__file__).parent / "parser" / "java-test-parser.jar",
        ]
        
        for jar_path in possible_paths:
            if jar_path.exists():
                return str(jar_path)
        
        return None
    
    def parse_test_file(self, file_path: str) -> Optional[JavaTestClass]:
        """
        Parse a Java test file and extract metadata using JavaParser.
        
        Args:
            file_path: Path to Java source file.
            
        Returns:
            JavaTestClass with extracted metadata, or None if parsing fails.
        """
        if not self.java_parser_jar:
            # Fall back to regex-based parsing if JAR not available
            return None
        
        try:
            # Run JavaParser utility
            result = subprocess.run(
                ["java", "-jar", self.java_parser_jar, file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return None
            
            # Parse JSON output
            data = json.loads(result.stdout)
            
            return self._json_to_test_class(data, file_path)
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            return None
    
    def _json_to_test_class(self, data: dict, file_path: str) -> JavaTestClass:
        """Convert JSON data to JavaTestClass."""
        # Detect framework from imports
        imports = data.get("imports", [])
        framework = self._detect_framework(imports)
        
        # Parse annotations
        class_annotations = [
            JavaAnnotation(name=ann["name"], attributes=ann.get("attributes", {}))
            for ann in data.get("annotations", [])
        ]
        
        # Extract class-level tags
        class_tags = self._extract_tags_from_annotations(class_annotations)
        
        # Parse test methods
        test_methods = []
        for method_data in data.get("testMethods", []):
            method_annotations = [
                JavaAnnotation(name=ann["name"], attributes=ann.get("attributes", {}))
                for ann in method_data.get("annotations", [])
            ]
            
            method_tags = self._extract_tags_from_annotations(method_annotations)
            
            test_methods.append(JavaTestMethod(
                method_name=method_data["name"],
                annotations=method_annotations,
                tags=method_tags,
                line_number=method_data.get("lineNumber"),
                is_parameterized=self._is_parameterized(method_annotations, framework),
                is_disabled=self._is_disabled(method_annotations, framework)
            ))
        
        return JavaTestClass(
            class_name=data["className"],
            package=data.get("package", ""),
            file_path=file_path,
            framework=framework,
            test_methods=test_methods,
            annotations=class_annotations,
            tags=class_tags,
            imports=imports
        )
    
    def _detect_framework(self, imports: List[str]) -> JavaTestFramework:
        """Detect test framework from imports."""
        import_str = " ".join(imports)
        
        if "org.junit.jupiter" in import_str:
            return JavaTestFramework.JUNIT5
        elif "org.junit.Test" in import_str or "org.junit" in import_str:
            return JavaTestFramework.JUNIT4
        elif "org.testng" in import_str:
            return JavaTestFramework.TESTNG
        
        return JavaTestFramework.UNKNOWN
    
    def _extract_tags_from_annotations(self, annotations: List[JavaAnnotation]) -> List[str]:
        """Extract tags from annotations."""
        tags = []
        
        for ann in annotations:
            # JUnit 5 @Tag
            if ann.name == "Tag":
                if "value" in ann.attributes:
                    tags.append(ann.attributes["value"].strip('"'))
            
            # JUnit 4 @Category
            elif ann.name == "Category":
                if "value" in ann.attributes:
                    # Extract class name from Category
                    category = ann.attributes["value"]
                    if ".class" in category:
                        category = category.replace(".class", "").split(".")[-1]
                    tags.append(category)
            
            # TestNG @Test(groups={...})
            elif ann.name == "Test" and "groups" in ann.attributes:
                groups = ann.attributes["groups"]
                # Parse groups array
                if groups.startswith("{") and groups.endswith("}"):
                    groups = groups[1:-1]
                for group in groups.split(","):
                    tags.append(group.strip().strip('"'))
        
        return tags
    
    def _is_parameterized(self, annotations: List[JavaAnnotation], framework: JavaTestFramework) -> bool:
        """Check if test is parameterized."""
        if framework == JavaTestFramework.JUNIT5:
            return any(ann.name == "ParameterizedTest" for ann in annotations)
        elif framework == JavaTestFramework.TESTNG:
            return any(ann.name == "DataProvider" for ann in annotations) or \
                   any("dataProvider" in ann.attributes for ann in annotations if ann.name == "Test")
        return False
    
    def _is_disabled(self, annotations: List[JavaAnnotation], framework: JavaTestFramework) -> bool:
        """Check if test is disabled."""
        disabled_annotations = {
            JavaTestFramework.JUNIT4: ["Ignore"],
            JavaTestFramework.JUNIT5: ["Disabled"],
            JavaTestFramework.TESTNG: []  # TestNG uses enabled=false attribute
        }
        
        disabled_names = disabled_annotations.get(framework, [])
        if any(ann.name in disabled_names for ann in annotations):
            return True
        
        # Check TestNG enabled=false
        if framework == JavaTestFramework.TESTNG:
            for ann in annotations:
                if ann.name == "Test" and "enabled" in ann.attributes:
                    if ann.attributes["enabled"] == "false":
                        return True
        
        return False


def parse_java_test_file(file_path: str) -> Optional[JavaTestClass]:
    """
    Convenience function to parse a Java test file.
    
    Args:
        file_path: Path to Java source file.
        
    Returns:
        JavaTestClass or None if parsing fails.
    """
    parser = JavaParserClient()
    return parser.parse_test_file(file_path)
