"""
Java Step Definition Parser for Cucumber/BDD.

Extracts step definitions from Java Cucumber step definition files
using javalang for accurate AST-based parsing.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class JavaStepDefinition:
    """Represents a Cucumber step definition in Java."""
    
    def __init__(
        self,
        step_type: str,  # Given, When, Then, And, But
        pattern: str,     # Regex pattern or Cucumber expression
        method_name: str,
        file_path: str,
        line_number: int,
        parameters: List[str] = None,
    ):
        self.step_type = step_type
        self.pattern = pattern
        self.method_name = method_name
        self.file_path = file_path
        self.line_number = line_number
        self.parameters = parameters or []
    
    def __repr__(self):
        return f"JavaStepDefinition({self.step_type} '{self.pattern}' -> {self.method_name})"


class JavaStepDefinitionParser:
    """
    Parser for Java Cucumber step definitions.
    
    Uses javalang for accurate AST parsing, with regex fallback.
    """
    
    STEP_ANNOTATIONS = ['Given', 'When', 'Then', 'And', 'But']
    
    def __init__(self):
        """Initialize the parser."""
        self.step_definitions: List[JavaStepDefinition] = []
        self._has_javalang = self._check_javalang()
    
    def _check_javalang(self) -> bool:
        """Check if javalang is available."""
        try:
            import javalang
            return True
        except ImportError:
            logger.warning("javalang not installed. Using regex fallback.")
            return False
    
    def parse_file(self, file_path: Path) -> List[JavaStepDefinition]:
        """
        Parse a single Java step definition file.
        
        Args:
            file_path: Path to Java file (str or Path)
            
        Returns:
            List of JavaStepDefinition objects
        """
        try:
            # Convert to Path if string
            path_obj = Path(file_path) if isinstance(file_path, str) else file_path
            source_code = path_obj.read_text(encoding='utf-8')
            
            if self._has_javalang:
                steps = self._parse_with_javalang(source_code, str(path_obj))
            else:
                steps = self._parse_with_regex(source_code, str(path_obj))
            
            self.step_definitions.extend(steps)
            return steps
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []
    
    def parse_directory(self, directory: Path, pattern: str = "**/*Steps.java") -> List[JavaStepDefinition]:
        """
        Parse all step definition files in a directory.
        
        Args:
            directory: Root directory to search
            pattern: Glob pattern for step definition files
            
        Returns:
            List of all step definitions found
        """
        all_steps = []
        
        for java_file in directory.glob(pattern):
            steps = self.parse_file(java_file)
            all_steps.extend(steps)
        
        logger.info(f"Parsed {len(all_steps)} step definitions from {directory}")
        return all_steps
    
    def _parse_with_javalang(self, source_code: str, file_path: str) -> List[JavaStepDefinition]:
        """Parse using javalang AST."""
        import javalang
        
        try:
            tree = javalang.parse.parse(source_code)
        except Exception as e:
            logger.error(f"javalang parse failed: {e}")
            return self._parse_with_regex(source_code, file_path)
        
        step_defs = []
        
        # Iterate through all classes
        for path, class_node in tree.filter(javalang.tree.ClassDeclaration):
            # Iterate through all methods
            for method in class_node.methods:
                if not method.annotations:
                    continue
                
                # Check for step annotations
                for annotation in method.annotations:
                    if annotation.name in self.STEP_ANNOTATIONS:
                        # Extract the step pattern from annotation
                        pattern = self._extract_pattern_from_annotation(annotation)
                        
                        if pattern:
                            # Extract method parameters
                            params = [param.name for param in (method.parameters or [])]
                            
                            # Create step definition
                            step_def = JavaStepDefinition(
                                step_type=annotation.name,
                                pattern=pattern,
                                method_name=method.name,
                                file_path=file_path,
                                line_number=method.position.line if method.position else 0,
                                parameters=params,
                            )
                            step_defs.append(step_def)
        
        return step_defs
    
    def _extract_pattern_from_annotation(self, annotation) -> Optional[str]:
        """Extract the step pattern from a Cucumber annotation."""
        if not annotation.element:
            return None
        
        # Handle direct string literal
        if isinstance(annotation.element, str):
            return annotation.element.strip('"')
        
        # Handle javalang Literal node
        if hasattr(annotation.element, 'value'):
            value = annotation.element.value
            if isinstance(value, str):
                # Remove surrounding quotes if present
                return value.strip('"').strip("'")
            return str(value)
        
        # Handle annotation with array/member expressions
        if hasattr(annotation.element, '__iter__'):
            for elem in annotation.element:
                if hasattr(elem, 'value'):
                    value = elem.value
                    if isinstance(value, str):
                        return value.strip('"').strip("'")
                    return str(value)
        
        return None
    
    def _parse_with_regex(self, source_code: str, file_path: str) -> List[JavaStepDefinition]:
        """
        Parse using regex patterns (fallback).
        
        Matches patterns like:
            @Given("user is on login page")
            @When("user enters {string} and {string}")
            @Then("^user should see welcome message$")
        """
        step_defs = []
        lines = source_code.split('\n')
        
        # Pattern to match step annotations
        annotation_pattern = re.compile(
            r'@(Given|When|Then|And|But)\s*\(\s*"([^"]+)"\s*\)'
        )
        
        # Pattern to match method declaration (on next line)
        method_pattern = re.compile(
            r'public\s+void\s+(\w+)\s*\('
        )
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for step annotation
            match = annotation_pattern.search(line)
            if match:
                step_type = match.group(1)
                pattern = match.group(2)
                
                # Look for method name on next non-empty line
                method_name = "unknown"
                j = i + 1
                while j < len(lines) and j < i + 5:  # Look ahead max 5 lines
                    next_line = lines[j].strip()
                    method_match = method_pattern.search(next_line)
                    if method_match:
                        method_name = method_match.group(1)
                        break
                    j += 1
                
                # Extract parameters from pattern
                params = self._extract_params_from_pattern(pattern)
                
                step_def = JavaStepDefinition(
                    step_type=step_type,
                    pattern=pattern,
                    method_name=method_name,
                    file_path=file_path,
                    line_number=i + 1,
                    parameters=params,
                )
                step_defs.append(step_def)
            
            i += 1
        
        return step_defs
    
    def _extract_params_from_pattern(self, pattern: str) -> List[str]:
        """Extract parameter placeholders from Cucumber expression."""
        # Match {string}, {int}, {float}, etc.
        cucumber_params = re.findall(r'\{(\w+)\}', pattern)
        if cucumber_params:
            return cucumber_params
        
        # Match regex capture groups
        regex_params = re.findall(r'\([^)]+\)', pattern)
        return [f"param{i}" for i in range(len(regex_params))]
    
    def find_step_definition(self, step_text: str, step_type: str) -> Optional[JavaStepDefinition]:
        """
        Find the step definition that matches a given step text.
        
        Args:
            step_text: The step text from feature file (e.g., "user enters 'john' and 'pass123'")
            step_type: The step type (Given, When, Then)
            
        Returns:
            Matching JavaStepDefinition or None
        """
        for step_def in self.step_definitions:
            if step_def.step_type != step_type:
                continue
            
            # Try regex match
            try:
                pattern = step_def.pattern
                # Convert Cucumber expression to regex if needed
                if '{string}' in pattern:
                    pattern = pattern.replace('{string}', "'([^']*)'")
                if '{int}' in pattern:
                    pattern = pattern.replace('{int}', r'(\d+)')
                if '{float}' in pattern:
                    pattern = pattern.replace('{float}', r'(\d+\.?\d*)')
                
                if re.match(pattern, step_text):
                    return step_def
            except re.error:
                # Pattern is not valid regex, try exact match
                if step_def.pattern == step_text:
                    return step_def
        
        return None
    
    def get_step_bindings_map(self) -> Dict[str, List[JavaStepDefinition]]:
        """
        Get a map of step types to their definitions.
        
        Returns:
            Dict mapping step types (Given/When/Then) to list of definitions
        """
        bindings_map = {step_type: [] for step_type in self.STEP_ANNOTATIONS}
        
        for step_def in self.step_definitions:
            bindings_map[step_def.step_type].append(step_def)
        
        return bindings_map


def parse_java_step_definitions(project_root: Path, pattern: str = "**/*Steps.java") -> JavaStepDefinitionParser:
    """
    Convenience function to parse all Java step definitions in a project.
    
    Args:
        project_root: Root directory of the project
        pattern: Glob pattern for step definition files
        
    Returns:
        JavaStepDefinitionParser with all parsed definitions
    
    Example:
        >>> parser = parse_java_step_definitions(Path("src/test/java"))
        >>> parser.parse_directory(Path("src/test/java/steps"))
        >>> step_def = parser.find_step_definition("user is on login page", "Given")
        >>> if step_def:
        ...     print(f"Found: {step_def.method_name} in {step_def.file_path}")
    """
    parser = JavaStepDefinitionParser()
    parser.step_definitions = parser.parse_directory(project_root, pattern)
    return parser
