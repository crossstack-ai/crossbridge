"""
Selenium BDD Java Transformers - Convert Cucumber tests to other frameworks.

Provides transformation capabilities from Cucumber/Gherkin to:
- Robot Framework
- pytest-bdd
- Playwright (with BDD patterns)
"""

from typing import Dict, List, Optional, Any
import re
import logging
from dataclasses import dataclass

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

logger = logging.getLogger(__name__)


@dataclass
class CucumberStep:
    """Represents a parsed Cucumber step."""
    keyword: str  # Given, When, Then, And, But
    text: str
    parameters: List[str]
    doc_string: Optional[str] = None
    data_table: Optional[List[List[str]]] = None


@dataclass
class StepDefinition:
    """Represents a parsed Java step definition."""
    annotation: str  # @Given, @When, @Then
    pattern: str  # Regular expression pattern
    method_name: str
    parameters: List[Dict[str, str]]  # {name: type}
    method_body: str
    locators: List[Dict[str, str]] = None  # Extracted WebDriver locators


class CucumberStepTransformer:
    """
    Transform Cucumber steps to target framework formats.
    
    Supports transformation to:
    - Robot Framework keywords
    - pytest-bdd step definitions
    - Playwright Test code with BDD patterns
    """
    
    def __init__(self):
        """Initialize the transformer."""
        self.locator_patterns = [
            r'By\.id\("([^"]+)"\)',
            r'By\.name\("([^"]+)"\)',
            r'By\.className\("([^"]+)"\)',
            r'By\.cssSelector\("([^"]+)"\)',
            r'By\.xpath\("([^"]+)"\)',
            r'By\.linkText\("([^"]+)"\)',
        ]
    
    def transform_to_robot(self, step: CucumberStep, step_def: Optional[StepDefinition] = None) -> str:
        """
        Transform Cucumber step to Robot Framework keyword call.
        
        Args:
            step: Parsed Cucumber step
            step_def: Optional Java step definition for implementation details
            
        Returns:
            Robot Framework keyword syntax
            
        Example:
            Input: Given I am on the login page
            Output: I Am On The Login Page
            
            Input: When I enter username "admin"
            Output: I Enter Username    admin
        """
        # Convert step text to Robot keyword format (Title Case with spaces)
        keyword = self._cucumber_text_to_robot_keyword(step.text, step.parameters)
        
        # Add data table or doc string if present
        if step.data_table:
            # Robot Framework table syntax
            table_lines = []
            for row in step.data_table:
                table_lines.append("    " + "    ".join(row))
            return keyword + "\n" + "\n".join(table_lines)
        
        if step.doc_string:
            # Robot Framework multi-line string
            return f"{keyword}\n    ...    {step.doc_string}"
        
        return keyword
    
    def transform_to_pytest_bdd(
        self, 
        step: CucumberStep, 
        step_def: Optional[StepDefinition] = None
    ) -> str:
        """
        Transform Cucumber step to pytest-bdd step definition.
        
        Args:
            step: Parsed Cucumber step
            step_def: Optional Java step definition for implementation details
            
        Returns:
            Python pytest-bdd step function code
            
        Example:
            Input: Given I am on the login page
            Output:
                @given('I am on the login page')
                def i_am_on_the_login_page(page):
                    page.goto('/login')
        """
        # Determine decorator based on keyword
        decorator_map = {
            "Given": "given",
            "When": "when",
            "Then": "then",
            "And": "then",  # Default to then for And/But
            "But": "then",
        }
        decorator = decorator_map.get(step.keyword, "then")
        
        # Generate function name from step text
        func_name = self._generate_python_function_name(step.text)
        
        # Generate function parameters
        params = ["page"]  # Always include page fixture
        if step.parameters:
            params.extend([self._sanitize_param_name(p) for p in step.parameters])
        
        # Generate pattern with parameter placeholders
        pattern = step.text
        for i, param in enumerate(step.parameters):
            # Replace parameter with capture group
            pattern = pattern.replace(f'"{param}"', '"<param' + str(i) + '>"')
            pattern = pattern.replace(f"'{param}'", "'<param" + str(i) + ">'")
        
        # Generate function body from step definition if available
        if step_def:
            body = self._generate_pytest_body_from_java(step_def)
        else:
            # Generate placeholder body
            body = "    # TODO: Implement step\n    pass"
        
        # Build complete function
        code = f"@{decorator}('{pattern}')\n"
        code += f"def {func_name}({', '.join(params)}):\n"
        code += f'    """{step.keyword} {step.text}"""\n'
        code += body
        
        return code
    
    def transform_to_playwright(
        self, 
        step: CucumberStep, 
        step_def: Optional[StepDefinition] = None
    ) -> str:
        """
        Transform Cucumber step to Playwright Test code.
        
        Args:
            step: Parsed Cucumber step
            step_def: Optional Java step definition for implementation details
            
        Returns:
            Playwright Test code (TypeScript/Python)
            
        Example:
            Input: When I click the login button
            Output:
                await page.locator('[data-testid="login-button"]').click();
        """
        # Map common Cucumber actions to Playwright
        text_lower = step.text.lower()
        
        # Click actions
        if "click" in text_lower:
            element = self._extract_element_from_text(step.text)
            return f'await page.locator(\'{self._generate_locator(element)}\').click();'
        
        # Fill/type actions
        if any(word in text_lower for word in ["enter", "type", "fill", "input"]):
            element = self._extract_element_from_text(step.text)
            value = step.parameters[0] if step.parameters else "value"
            return f'await page.locator(\'{self._generate_locator(element)}\').fill("{value}");'
        
        # Navigation
        if "navigate" in text_lower or "goto" in text_lower or "visit" in text_lower:
            url = step.parameters[0] if step.parameters else "/page"
            return f'await page.goto("{url}");'
        
        # Assertions
        if "should see" in text_lower or "should contain" in text_lower:
            element = self._extract_element_from_text(step.text)
            expected = step.parameters[0] if step.parameters else "text"
            return f'await expect(page.locator(\'{self._generate_locator(element)}\')).toContainText("{expected}");'
        
        # Default: add TODO comment
        return f'// TODO: Implement - {step.keyword} {step.text}'
    
    def _cucumber_text_to_robot_keyword(self, text: str, parameters: List[str]) -> str:
        """
        Convert Cucumber step text to Robot Framework keyword format.
        
        Args:
            text: Original Cucumber step text
            parameters: Extracted parameters
            
        Returns:
            Robot keyword with parameters as separate arguments
            
        Example:
            "I enter username 'admin'" -> "I Enter Username    admin"
        """
        # Remove quoted parameters from text
        keyword_text = text
        for param in parameters:
            keyword_text = keyword_text.replace(f'"{param}"', "")
            keyword_text = keyword_text.replace(f"'{param}'", "")
        
        # Convert to Title Case and clean up extra spaces
        keyword = " ".join(keyword_text.split()).title()
        
        # Add parameters as separate arguments
        if parameters:
            keyword += "    " + "    ".join(parameters)
        
        return keyword
    
    def _generate_python_function_name(self, text: str) -> str:
        """
        Generate Python function name from step text.
        
        Args:
            text: Cucumber step text
            
        Returns:
            Valid Python function name (lowercase with underscores)
        """
        # Remove special characters and convert to lowercase
        name = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
        # Replace spaces with underscores
        name = "_".join(name.split())
        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = "step_" + name
        return name or "step"
    
    def _sanitize_param_name(self, param: str) -> str:
        """Sanitize parameter name for Python."""
        name = re.sub(r'[^a-zA-Z0-9_]', '_', param.lower())
        if name and name[0].isdigit():
            name = "param_" + name
        return name or "param"
    
    def _extract_element_from_text(self, text: str) -> str:
        """Extract element name from step text (e.g., 'login button' from 'click the login button')."""
        # Simple heuristic: take last 2 words
        words = text.split()
        if len(words) >= 2:
            return " ".join(words[-2:])
        return text
    
    def _generate_locator(self, element: str) -> str:
        """Generate a Playwright locator from element description."""
        # Convert to test-id format
        test_id = element.lower().replace(" ", "-")
        return f'[data-testid="{test_id}"]'
    
    def _generate_pytest_body_from_java(self, step_def: StepDefinition) -> str:
        """
        Generate pytest-bdd function body from Java step definition.
        
        Args:
            step_def: Parsed Java step definition
            
        Returns:
            Python function body
        """
        # Extract locators from Java code
        locators = self._extract_locators_from_java(step_def.method_body)
        
        body_lines = []
        
        # Convert Java WebDriver calls to Playwright
        if "click" in step_def.method_body.lower():
            if locators:
                loc = locators[0]
                pw_locator = self._convert_selenium_to_playwright_locator(loc)
                body_lines.append(f"    page.locator('{pw_locator}').click()")
        
        elif "sendKeys" in step_def.method_body:
            if locators and step_def.parameters:
                loc = locators[0]
                pw_locator = self._convert_selenium_to_playwright_locator(loc)
                param_name = step_def.parameters[0]['name']
                body_lines.append(f"    page.locator('{pw_locator}').fill({param_name})")
        
        elif "getText" in step_def.method_body or "assertThat" in step_def.method_body:
            if locators:
                loc = locators[0]
                pw_locator = self._convert_selenium_to_playwright_locator(loc)
                body_lines.append(f"    text = page.locator('{pw_locator}').text_content()")
                body_lines.append(f"    assert text is not None")
        
        if not body_lines:
            body_lines.append("    # TODO: Implement step")
            body_lines.append("    pass")
        
        return "\n".join(body_lines)
    
    def _extract_locators_from_java(self, java_code: str) -> List[Dict[str, str]]:
        """
        Extract Selenium locators from Java code.
        
        Returns:
            List of dicts with 'strategy' and 'value' keys
        """
        locators = []
        
        patterns = {
            'id': r'By\.id\("([^"]+)"\)',
            'name': r'By\.name\("([^"]+)"\)',
            'class': r'By\.className\("([^"]+)"\)',
            'css': r'By\.cssSelector\("([^"]+)"\)',
            'xpath': r'By\.xpath\("([^"]+)"\)',
            'link': r'By\.linkText\("([^"]+)"\)',
        }
        
        for strategy, pattern in patterns.items():
            matches = re.findall(pattern, java_code)
            for match in matches:
                locators.append({'strategy': strategy, 'value': match})
        
        return locators
    
    def _convert_selenium_to_playwright_locator(self, locator: Dict[str, str]) -> str:
        """
        Convert Selenium locator to Playwright locator.
        
        Args:
            locator: Dict with 'strategy' and 'value'
            
        Returns:
            Playwright locator string
        """
        strategy = locator['strategy']
        value = locator['value']
        
        if strategy == 'id':
            return f'#{value}'
        elif strategy == 'name':
            return f'[name="{value}"]'
        elif strategy == 'class':
            return f'.{value}'
        elif strategy == 'css':
            return value
        elif strategy == 'xpath':
            return f'xpath={value}'
        elif strategy == 'link':
            return f'text={value}'
        
        return value


class GlueCodeParser:
    """
    Parse Java step definition methods (glue code) to extract implementation details.
    
    Parses:
    - Cucumber annotations (@Given, @When, @Then)
    - Method signatures and parameters
    - WebDriver locator calls
    - Page Object pattern usage
    """
    
    def __init__(self):
        """Initialize the parser."""
        self.annotation_pattern = r'@(Given|When|Then|And|But)\("([^"]+)"\)'
        self.method_pattern = r'public\s+void\s+(\w+)\s*\(([^)]*)\)'
        self.parameter_pattern = r'(\w+(?:<[^>]+>)?)\s+(\w+)'
    
    def parse_step_definition(self, java_code: str) -> Optional[StepDefinition]:
        """
        Parse a Java step definition method.
        
        Args:
            java_code: Java method source code
            
        Returns:
            StepDefinition object or None if parsing fails
            
        Example:
            Input:
                @Given("I am on the login page")
                public void iAmOnTheLoginPage() {
                    driver.get("https://example.com/login");
                    driver.findElement(By.id("username")).isDisplayed();
                }
            
            Output:
                StepDefinition(
                    annotation="@Given",
                    pattern="I am on the login page",
                    method_name="iAmOnTheLoginPage",
                    parameters=[],
                    method_body="...",
                    locators=[{"strategy": "id", "value": "username"}]
                )
        """
        # Extract annotation
        annotation_match = re.search(self.annotation_pattern, java_code)
        if not annotation_match:
            logger.warning("No Cucumber annotation found")
            return None
        
        annotation = f"@{annotation_match.group(1)}"
        pattern = annotation_match.group(2)
        
        # Extract method signature
        method_match = re.search(self.method_pattern, java_code)
        if not method_match:
            logger.warning("No method signature found")
            return None
        
        method_name = method_match.group(1)
        params_str = method_match.group(2)
        
        # Parse parameters
        parameters = []
        if params_str.strip():
            for param_match in re.finditer(self.parameter_pattern, params_str):
                param_type = param_match.group(1)
                param_name = param_match.group(2)
                parameters.append({"name": param_name, "type": param_type})
        
        # Extract method body
        # Find everything between { and }
        brace_start = java_code.find('{')
        brace_end = java_code.rfind('}')
        if brace_start == -1 or brace_end == -1:
            method_body = ""
        else:
            method_body = java_code[brace_start+1:brace_end].strip()
        
        # Extract locators from method body
        locators = self._extract_locators(method_body)
        
        return StepDefinition(
            annotation=annotation,
            pattern=pattern,
            method_name=method_name,
            parameters=parameters,
            method_body=method_body,
            locators=locators
        )
    
    def parse_step_definitions_from_file(self, file_path: str) -> List[StepDefinition]:
        """
        Parse all step definitions from a Java file.
        
        Args:
            file_path: Path to Java step definitions file
            
        Returns:
            List of StepDefinition objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except IOError as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []
        
        # Split into individual method definitions
        # Simple approach: split on @Given/@When/@Then annotations
        pattern = r'(@(?:Given|When|Then|And|But)\("[^"]+"\)[^@]*?(?=@(?:Given|When|Then|And|But)|$))'
        matches = re.findall(pattern, content, re.DOTALL)
        
        step_defs = []
        for match in matches:
            step_def = self.parse_step_definition(match)
            if step_def:
                step_defs.append(step_def)
        
        logger.info(f"Parsed {len(step_defs)} step definitions from {file_path}")
        return step_defs
    
    def _extract_locators(self, java_code: str) -> List[Dict[str, str]]:
        """Extract Selenium locators from Java code."""
        locators = []
        
        patterns = {
            'id': r'By\.id\("([^"]+)"\)',
            'name': r'By\.name\("([^"]+)"\)',
            'class': r'By\.className\("([^"]+)"\)',
            'css': r'By\.cssSelector\("([^"]+)"\)',
            'xpath': r'By\.xpath\("([^"]+)"\)',
            'link': r'By\.linkText\("([^"]+)"\)',
        }
        
        for strategy, pattern in patterns.items():
            matches = re.findall(pattern, java_code)
            for match in matches:
                locators.append({'strategy': strategy, 'value': match})
        
        return locators


class CucumberTransformationPipeline:
    """
    End-to-end pipeline for generating test code in target frameworks from Cucumber.
    
    Workflow:
    1. Parse feature files to extract scenarios
    2. Parse Java step definitions for implementation details
    3. Match steps to step definitions
    4. Transform to target framework
    5. Generate complete test files
    """
    
    def __init__(self):
        """Initialize the pipeline."""
        self.transformer = CucumberStepTransformer()
        self.parser = GlueCodeParser()
    
    def generate_robot_framework_tests(
        self, 
        feature_file: str,
        step_defs_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate Robot Framework test suite from Cucumber feature file.
        
        Args:
            feature_file: Path to .feature file
            step_defs_dir: Optional directory containing Java step definitions
            
        Returns:
            Dict with 'test_file' and 'keywords_file' containing generated code
        """
        # TODO: Implement full pipeline
        # 1. Parse feature file
        # 2. Parse step definitions if provided
        # 3. Generate Robot test file
        # 4. Generate Robot keywords file
        
        logger.info(f"Generating Robot Framework tests from {feature_file}")
        return {
            'test_file': "*** Test Cases ***\n# TODO: Generated tests",
            'keywords_file': "*** Keywords ***\n# TODO: Generated keywords"
        }
    
    def generate_pytest_bdd_tests(
        self,
        feature_file: str,
        step_defs_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate pytest-bdd test suite from Cucumber feature file.
        
        Args:
            feature_file: Path to .feature file
            step_defs_dir: Optional directory containing Java step definitions
            
        Returns:
            Dict with 'feature_file', 'conftest', and 'step_defs' containing generated code
        """
        # TODO: Implement full pipeline
        logger.info(f"Generating pytest-bdd tests from {feature_file}")
        return {
            'feature_file': "# Feature file (copy original)",
            'conftest': "# conftest.py with fixtures",
            'step_defs': "# Step definitions"
        }
    
    def generate_playwright_tests(
        self,
        feature_file: str,
        step_defs_dir: Optional[str] = None
    ) -> str:
        """
        Generate Playwright tests from Cucumber feature file.
        
        Args:
            feature_file: Path to .feature file
            step_defs_dir: Optional directory containing Java step definitions
            
        Returns:
            Generated Playwright test code (TypeScript/Python)
        """
        # TODO: Implement full pipeline
        logger.info(f"Generating Playwright tests from {feature_file}")
        return "// TODO: Generated Playwright tests"

# Aliases for backward compatibility
TestGenerationPipeline = CucumberTransformationPipeline
TransformationPipeline = CucumberTransformationPipeline
