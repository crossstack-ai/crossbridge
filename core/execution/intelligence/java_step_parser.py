"""
Java Step Definition Parser

Parses Java step definition files to map Cucumber steps to Java methods.

Uses JavaParser (javalang library) to extract:
- @Given / @When / @Then annotations
- Method signatures
- Class names
- File paths

This enables:
- Step → Method → File mapping
- Impact analysis
- Coverage mapping
- Root cause analysis
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import javalang
    JAVALANG_AVAILABLE = True
except ImportError:
    JAVALANG_AVAILABLE = False

from core.logging import get_logger
from core.execution.intelligence.models import StepBinding

logger = get_logger(__name__)


class JavaStepDefinitionParser:
    """
    Parses Java files to extract Cucumber step definitions.
    
    Requires: javalang library
    Install: pip install javalang
    """
    
    def __init__(self):
        if not JAVALANG_AVAILABLE:
            logger.warning("javalang not available. Install with: pip install javalang")
    
    def parse_file(self, java_file: str) -> List[StepBinding]:
        """
        Parse a Java file for step definitions.
        
        Args:
            java_file: Path to Java file
            
        Returns:
            List of StepBinding objects
        """
        if not JAVALANG_AVAILABLE:
            logger.error("javalang library not installed")
            return []
        
        try:
            with open(java_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.parse_content(content, java_file)
        except Exception as e:
            logger.error(f"Failed to parse Java file {java_file}: {e}")
            return []
    
    def parse_content(self, content: str, file_path: str = "") -> List[StepBinding]:
        """
        Parse Java source code for step definitions.
        
        Args:
            content: Java source code
            file_path: Optional file path for metadata
            
        Returns:
            List of StepBinding objects
        """
        if not JAVALANG_AVAILABLE:
            return []
        
        bindings = []
        
        try:
            # Parse Java source
            tree = javalang.parse.parse(content)
            
            # Get package name
            package_name = tree.package.name if tree.package else ""
            
            # Iterate through classes
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                class_name = node.name
                full_class_name = f"{package_name}.{class_name}" if package_name else class_name
                
                # Iterate through methods
                for method in node.methods:
                    # Check for step definition annotations
                    if method.annotations:
                        for annotation in method.annotations:
                            annotation_name = annotation.name
                            
                            # Check if it's a Cucumber step annotation
                            if annotation_name in ['Given', 'When', 'Then', 'And', 'But']:
                                # Extract step pattern from annotation
                                pattern = self._extract_pattern_from_annotation(annotation)
                                
                                if pattern:
                                    binding = StepBinding(
                                        step_pattern=pattern,
                                        annotation_type=annotation_name,
                                        class_name=full_class_name,
                                        method_name=method.name,
                                        file_path=file_path,
                                        parameters=[param.name for param in method.parameters] if method.parameters else [],
                                        line_number=method.position.line if method.position else None,
                                    )
                                    bindings.append(binding)
        
        except javalang.parser.JavaSyntaxError as e:
            logger.error(f"Java syntax error: {e}")
        except Exception as e:
            logger.error(f"Failed to parse Java content: {e}")
        
        return bindings
    
    def _extract_pattern_from_annotation(self, annotation) -> Optional[str]:
        """
        Extract regex pattern from Cucumber annotation.
        
        @Given("I have (\\d+) cukes in my belly")
        -> "I have (\\d+) cukes in my belly"
        """
        try:
            if annotation.element:
                # Single value annotation
                if isinstance(annotation.element, javalang.tree.Literal):
                    # Remove quotes
                    pattern = annotation.element.value.strip('"').strip("'")
                    return pattern
                elif isinstance(annotation.element, javalang.tree.MemberReference):
                    # Handle member references (less common)
                    return str(annotation.element.member)
            
            # Named parameters (rare for Cucumber)
            if annotation.element and hasattr(annotation.element, 'values'):
                for value in annotation.element.values:
                    if hasattr(value, 'value'):
                        return value.value.strip('"').strip("'")
        
        except Exception as e:
            logger.debug(f"Failed to extract pattern: {e}")
        
        return None
    
    def parse_directory(self, directory: str, recursive: bool = True) -> List[StepBinding]:
        """
        Parse all Java files in a directory for step definitions.
        
        Args:
            directory: Directory path
            recursive: Whether to search recursively
            
        Returns:
            List of StepBinding objects
        """
        bindings = []
        path = Path(directory)
        
        if not path.exists():
            logger.error(f"Directory not found: {directory}")
            return bindings
        
        # Find all Java files
        pattern = "**/*.java" if recursive else "*.java"
        for java_file in path.glob(pattern):
            file_bindings = self.parse_file(str(java_file))
            bindings.extend(file_bindings)
        
        logger.info(f"Found {len(bindings)} step definitions in {directory}")
        return bindings


class RegexStepDefinitionParser:
    """
    Fallback parser using regex for when javalang is not available.
    
    Less accurate but doesn't require external dependencies.
    """
    
    STEP_ANNOTATION_PATTERN = re.compile(
        r'@(Given|When|Then|And|But)\s*\(\s*["\']([^"\']+)["\']\s*\)',
        re.MULTILINE
    )
    
    METHOD_PATTERN = re.compile(
        r'public\s+\w+\s+(\w+)\s*\(',
        re.MULTILINE
    )
    
    CLASS_PATTERN = re.compile(
        r'class\s+(\w+)',
        re.MULTILINE
    )
    
    PACKAGE_PATTERN = re.compile(
        r'package\s+([\w.]+);',
        re.MULTILINE
    )
    
    def parse_file(self, java_file: str) -> List[StepBinding]:
        """Parse Java file using regex"""
        try:
            with open(java_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.parse_content(content, java_file)
        except Exception as e:
            logger.error(f"Failed to parse Java file {java_file}: {e}")
            return []
    
    def parse_content(self, content: str, file_path: str = "") -> List[StepBinding]:
        """Parse Java content using regex"""
        bindings = []
        
        # Extract package name
        package_match = self.PACKAGE_PATTERN.search(content)
        package_name = package_match.group(1) if package_match else ""
        
        # Extract class name
        class_match = self.CLASS_PATTERN.search(content)
        class_name = class_match.group(1) if class_match else "Unknown"
        full_class_name = f"{package_name}.{class_name}" if package_name else class_name
        
        # Find all step annotations
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Look for step annotation
            annotation_match = self.STEP_ANNOTATION_PATTERN.search(line)
            if annotation_match:
                annotation_type = annotation_match.group(1)
                pattern = annotation_match.group(2)
                
                # Find method name (usually on next few lines)
                method_name = "unknown_method"
                for j in range(i + 1, min(i + 5, len(lines))):
                    method_match = self.METHOD_PATTERN.search(lines[j])
                    if method_match:
                        method_name = method_match.group(1)
                        break
                
                binding = StepBinding(
                    step_pattern=pattern,
                    annotation_type=annotation_type,
                    class_name=full_class_name,
                    method_name=method_name,
                    file_path=file_path,
                    line_number=i + 1,
                )
                bindings.append(binding)
        
        return bindings


# Auto-select parser based on availability
def get_step_definition_parser():
    """Get the best available step definition parser"""
    if JAVALANG_AVAILABLE:
        logger.info("Using JavaParser (javalang) for step definition parsing")
        return JavaStepDefinitionParser()
    else:
        logger.info("Using RegexStepDefinitionParser (fallback)")
        return RegexStepDefinitionParser()


# Example usage
if __name__ == "__main__":
    parser = get_step_definition_parser()
    
    # Parse a single file
    bindings = parser.parse_file("StepDefinitions.java")
    
    print(f"Found {len(bindings)} step definitions:")
    for binding in bindings:
        print(f"\n{binding.annotation_type}: {binding.step_pattern}")
        print(f"  Method: {binding.class_name}.{binding.method_name}()")
        print(f"  File: {binding.file_path}:{binding.line_number}")
    
    # Parse directory
    if isinstance(parser, JavaStepDefinitionParser):
        all_bindings = parser.parse_directory("src/test/java/stepdefinitions")
        print(f"\nTotal step definitions found: {len(all_bindings)}")
