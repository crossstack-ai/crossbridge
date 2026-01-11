"""
Java Step Definition and Locator Extractor
Extracts step definitions and element locators from Java code.
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass


@dataclass
class JavaStepDefinition:
    """Represents a Java step definition."""
    annotation: str  # @Given, @When, @Then
    pattern: str  # Step pattern with parameters
    method_name: str
    parameters: List[str]
    body: str
    file_path: str
    line_number: int


@dataclass
class ElementLocator:
    """Represents an element locator from Java code."""
    name: str
    locator_type: str  # id, xpath, css, name, etc.
    value: str
    file_path: str
    line_number: int


class JavaCodeAnalyzer:
    """Analyzes Java code to extract step definitions and locators."""
    
    # Cucumber annotations
    STEP_ANNOTATIONS = ['@Given', '@When', '@Then', '@And', '@But']
    
    # Selenium locator patterns
    # Updated patterns to handle quotes inside XPath/CSS selectors by matching the outer quotes specifically
    LOCATOR_PATTERNS = {
        'id': r'By\.id\(["\']([^"\']*)["\'\)]',
        'name': r'By\.name\(["\']([^"\']*)["\'\)]',
        'xpath': r'By\.xpath\((["\'])(.+?)\1\)',
        'css': r'By\.cssSelector\((["\'])(.+?)\1\)',
        'className': r'By\.className\(["\']([^"\']+)["\']\)',
        'tagName': r'By\.tagName\(["\']([^"\']+)["\']\)',
        'linkText': r'By\.linkText\(["\']([^"\']+)["\']\)',
        'partialLinkText': r'By\.partialLinkText\(["\']([^"\']+)["\']\)',
    }
    
    # WebElement annotations
    FIND_BY_PATTERN = r'@FindBy\(([^)]+)\)'
    
    def __init__(self):
        self.step_definitions: List[JavaStepDefinition] = []
        self.locators: List[ElementLocator] = []
    
    def analyze_directory(self, directory: str, file_pattern: str = "**/*.java") -> None:
        """
        Analyze all Java files in a directory.
        
        Args:
            directory: Root directory to search
            file_pattern: Glob pattern for files
        """
        path = Path(directory)
        for java_file in path.glob(file_pattern):
            self.analyze_file(str(java_file))
    
    def analyze_file(self, file_path: str) -> None:
        """
        Analyze a single Java file.
        
        Args:
            file_path: Path to Java file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract step definitions
            steps = self._extract_step_definitions(content, file_path)
            self.step_definitions.extend(steps)
            
            # Extract locators
            locators = self._extract_locators(content, file_path)
            self.locators.extend(locators)
            
        except Exception as e:
            print(f"Error analyzing file {file_path}: {e}")
    
    def _extract_step_definitions(
        self,
        content: str,
        file_path: str
    ) -> List[JavaStepDefinition]:
        """
        Extract Cucumber step definitions from Java code.
        
        Args:
            content: Java file content
            file_path: Path to the file
            
        Returns:
            List of JavaStepDefinition objects
        """
        step_defs = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for step annotation
            for annotation in self.STEP_ANNOTATIONS:
                if line.startswith(annotation):
                    # Extract pattern
                    pattern_match = re.search(r'["\'](.+?)["\']', line)
                    if pattern_match:
                        pattern = pattern_match.group(1)
                        
                        # Find method declaration (next non-empty line)
                        i += 1
                        while i < len(lines) and not lines[i].strip():
                            i += 1
                        
                        if i < len(lines):
                            method_line = lines[i].strip()
                            method_match = re.search(
                                r'public\s+\w+\s+(\w+)\s*\(([^)]*)\)',
                                method_line
                            )
                            
                            if method_match:
                                method_name = method_match.group(1)
                                params_str = method_match.group(2)
                                
                                # Parse parameters
                                params = []
                                if params_str.strip():
                                    for param in params_str.split(','):
                                        param = param.strip()
                                        # Extract parameter name (last word)
                                        parts = param.split()
                                        if parts:
                                            params.append(parts[-1])
                                
                                # Extract method body
                                body_lines = []
                                i += 1
                                brace_count = 0
                                found_opening = False
                                
                                while i < len(lines):
                                    body_line = lines[i]
                                    
                                    # Stop if we encounter another annotation
                                    if any(body_line.strip().startswith(ann) for ann in self.STEP_ANNOTATIONS):
                                        i -= 1  # Back up so outer loop processes this annotation
                                        break
                                    
                                    if '{' in body_line:
                                        found_opening = True
                                        brace_count += body_line.count('{')
                                    if '}' in body_line:
                                        brace_count -= body_line.count('}')
                                    
                                    if found_opening:
                                        body_lines.append(body_line)
                                    
                                    if found_opening and brace_count == 0:
                                        break
                                    i += 1
                                
                                body = '\n'.join(body_lines)
                                
                                step_def = JavaStepDefinition(
                                    annotation=annotation,
                                    pattern=pattern,
                                    method_name=method_name,
                                    parameters=params,
                                    body=body,
                                    file_path=file_path,
                                    line_number=i
                                )
                                step_defs.append(step_def)
            
            i += 1
        
        return step_defs
    
    def _extract_locators(
        self,
        content: str,
        file_path: str
    ) -> List[ElementLocator]:
        """
        Extract element locators from Java code.
        
        Args:
            content: Java file content
            file_path: Path to the file
            
        Returns:
            List of ElementLocator objects
        """
        locators = []
        lines = content.split('\n')
        
        # Extract By.* locators
        for locator_type, pattern in self.LOCATOR_PATTERNS.items():
            for line_num, line in enumerate(lines):
                matches = re.finditer(pattern, line)
                for match in matches:
                    # For xpath and css, group 2 has the value (group 1 is the quote)
                    # For others, group 1 has the value
                    if locator_type in ['xpath', 'css']:
                        value = match.group(2)
                    else:
                        value = match.group(1)
                    
                    # Try to find variable name
                    var_match = re.search(r'(\w+)\s*=.*' + re.escape(match.group(0)), line)
                    name = var_match.group(1) if var_match else f"{locator_type}_locator"
                    
                    locator = ElementLocator(
                        name=name,
                        locator_type=locator_type,
                        value=value,
                        file_path=file_path,
                        line_number=line_num + 1
                    )
                    locators.append(locator)
        
        # Extract @FindBy annotations
        for line_num, line in enumerate(lines):
            if '@FindBy' in line:
                match = re.search(self.FIND_BY_PATTERN, line)
                if match:
                    annotation_content = match.group(1)
                    
                    # Parse annotation parameters
                    locator_type = None
                    value = None
                    
                    # Check for different locator types
                    if 'id' in annotation_content:
                        locator_type = 'id'
                        value_match = re.search(r'id\s*=\s*["\']([^"\']+)["\']', annotation_content)
                        if value_match:
                            value = value_match.group(1)
                    elif 'xpath' in annotation_content:
                        locator_type = 'xpath'
                        # Use quote-matching pattern to handle quotes inside XPath
                        value_match = re.search(r'xpath\s*=\s*(["\'])(.+?)\1', annotation_content)
                        if value_match:
                            value = value_match.group(2)
                    elif 'css' in annotation_content:
                        locator_type = 'css'
                        value_match = re.search(r'css\s*=\s*["\']([^"\']+)["\']', annotation_content)
                        if value_match:
                            value = value_match.group(1)
                    elif 'name' in annotation_content:
                        locator_type = 'name'
                        value_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', annotation_content)
                        if value_match:
                            value = value_match.group(1)
                    
                    if locator_type and value:
                        # Try to find field name
                        next_line = lines[line_num + 1] if line_num + 1 < len(lines) else ""
                        field_match = re.search(r'WebElement\s+(\w+)', next_line)
                        name = field_match.group(1) if field_match else f"{locator_type}_element"
                        
                        locator = ElementLocator(
                            name=name,
                            locator_type=locator_type,
                            value=value,
                            file_path=file_path,
                            line_number=line_num + 1
                        )
                        locators.append(locator)
        
        return locators
    
    def get_step_by_pattern(self, pattern: str) -> Optional[JavaStepDefinition]:
        """
        Find step definition by pattern.
        
        Args:
            pattern: Step pattern to search for
            
        Returns:
            JavaStepDefinition or None
        """
        for step in self.step_definitions:
            if step.pattern == pattern:
                return step
        return None
    
    def get_locators_by_file(self, file_path: str) -> List[ElementLocator]:
        """
        Get all locators from a specific file.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of ElementLocator objects
        """
        return [loc for loc in self.locators if loc.file_path == file_path]
    
    def convert_locator_to_robot(self, locator: ElementLocator) -> str:
        """
        Convert Java locator to Robot Framework syntax.
        
        Args:
            locator: ElementLocator object
            
        Returns:
            Robot Framework locator string
        """
        type_map = {
            'id': 'id=',
            'name': 'name=',
            'xpath': 'xpath=',
            'css': 'css=',
            'className': 'css=.',
            'tagName': '',
            'linkText': 'text=',
            'partialLinkText': 'text=',
        }
        
        prefix = type_map.get(locator.locator_type, '')
        
        # Special handling for className
        if locator.locator_type == 'className':
            return f"{prefix}{locator.value}"
        
        return f"{prefix}{locator.value}"
    
    def match_step_pattern(self, gherkin_step: str, pattern: str) -> Optional[Dict[str, str]]:
        """
        Match a Gherkin step against a Cucumber pattern and extract parameters.
        
        Args:
            gherkin_step: Gherkin step text
            pattern: Cucumber pattern with parameters
            
        Returns:
            Dictionary of parameter values or None if no match
        """
        # Convert Cucumber pattern to regex
        # Handle {string}, {int}, {word}, etc.
        regex_pattern = pattern
        regex_pattern = re.sub(r'\{string\}', r'["\']([^"\']+)["\']', regex_pattern)
        regex_pattern = re.sub(r'\{int\}', r'(\\d+)', regex_pattern)
        regex_pattern = re.sub(r'\{word\}', r'(\\w+)', regex_pattern)
        regex_pattern = re.sub(r'\{float\}', r'([\\d.]+)', regex_pattern)
        regex_pattern = re.sub(r'\{.*?\}', r'(.+?)', regex_pattern)  # Generic catch-all
        
        # Escape special regex characters that aren't part of our capture groups
        # Note: We already have capture groups, so don't double-escape parentheses in replacement patterns
        
        match = re.match(regex_pattern, gherkin_step)
        if match:
            return {f'param{i+1}': val for i, val in enumerate(match.groups())}
        return None


class StepDefinitionMapper:
    """Maps Gherkin steps to Robot Framework keywords using Java analysis."""
    
    def __init__(self, java_analyzer: JavaCodeAnalyzer):
        self.analyzer = java_analyzer
        self.mappings: Dict[str, str] = {}
    
    def map_steps_to_keywords(self, gherkin_steps: List[str]) -> Dict[str, Tuple[str, List[str]]]:
        """
        Map Gherkin steps to Robot Framework keywords.
        
        Args:
            gherkin_steps: List of Gherkin step texts
            
        Returns:
            Dictionary mapping step text to (keyword_name, implementation_lines)
        """
        mappings = {}
        
        for step in gherkin_steps:
            # Try to find matching Java step definition
            matched = False
            for java_step in self.analyzer.step_definitions:
                params = self.analyzer.match_step_pattern(step, java_step.pattern)
                if params:
                    # Generate Robot keyword
                    keyword_name = self._generate_keyword_name(step)
                    impl_lines = self._convert_java_to_robot(java_step, params)
                    mappings[step] = (keyword_name, impl_lines)
                    matched = True
                    break
            
            if not matched:
                # Create placeholder
                keyword_name = self._generate_keyword_name(step)
                mappings[step] = (keyword_name, [
                    "[Documentation]    TODO: Implement step",
                    f"Log    Step: {step}"
                ])
        
        return mappings
    
    def _generate_keyword_name(self, step: str) -> str:
        """Generate Robot keyword name from Gherkin step."""
        # Remove parameters in quotes
        name = re.sub(r'"[^"]*"', '', step)
        # Convert to title case
        name = ' '.join(word.capitalize() for word in name.split())
        return name.strip()
    
    def _convert_java_to_robot(
        self,
        java_step: JavaStepDefinition,
        params: Dict[str, str]
    ) -> List[str]:
        """
        Convert Java step implementation to Robot Framework.
        
        Args:
            java_step: Java step definition
            params: Extracted parameters
            
        Returns:
            List of Robot Framework implementation lines
        """
        lines = []
        
        # Add documentation
        lines.append(f"[Documentation]    {java_step.pattern}")
        
        # Add arguments if parameters exist
        if java_step.parameters:
            args = "    ".join(f"${{{p}}}" for p in java_step.parameters)
            lines.append(f"[Arguments]    {args}")
        
        # Try to convert common Selenium actions to Browser library
        body = java_step.body
        
        # Extract locators from body
        locators = self.analyzer._extract_locators(body, java_step.file_path)
        
        # Convert common actions
        if 'click()' in body:
            for locator in locators:
                robot_loc = self.analyzer.convert_locator_to_robot(locator)
                lines.append(f"Click    {robot_loc}")
        elif 'sendKeys(' in body:
            for locator in locators:
                robot_loc = self.analyzer.convert_locator_to_robot(locator)
                param_name = java_step.parameters[0] if java_step.parameters else "text"
                lines.append(f"Fill Text    {robot_loc}    ${{{param_name}}}")
        elif 'getText()' in body:
            for locator in locators:
                robot_loc = self.analyzer.convert_locator_to_robot(locator)
                lines.append(f"Get Text    {robot_loc}")
        else:
            # Generic placeholder
            lines.append("# TODO: Convert Java implementation to Robot Framework")
            lines.append(f"Log    Executing: {java_step.method_name}")
        
        return lines


def analyze_java_code(directory: str) -> JavaCodeAnalyzer:
    """
    Convenience function to analyze Java code in a directory.
    
    Args:
        directory: Root directory containing Java files
        
    Returns:
        JavaCodeAnalyzer with extracted data
    """
    analyzer = JavaCodeAnalyzer()
    analyzer.analyze_directory(directory)
    return analyzer
