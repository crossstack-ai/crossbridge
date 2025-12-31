"""
Playwright Code Generator

Generates Python Playwright test code from Java Selenium BDD step definitions.
Produces pytest-bdd compatible tests with Playwright Page Objects.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import re

from adapters.selenium_bdd_java.step_definition_parser import (
    StepDefinitionIntent,
    PageObjectCall,
    SeleniumAction,
    SELENIUM_TO_PLAYWRIGHT
)


@dataclass
class PlaywrightPageObject:
    """Generated Playwright Page Object"""
    class_name: str
    locators: dict[str, str] = field(default_factory=dict)  # method_name -> locator
    methods: dict[str, str] = field(default_factory=dict)   # method_name -> method_body
    imports: set[str] = field(default_factory=set)


@dataclass
class PlaywrightStepDefinition:
    """Generated pytest-bdd step definition"""
    keyword: str  # given, when, then
    pattern: str
    function_name: str
    function_body: str
    fixtures: list[str] = field(default_factory=list)
    imports: set[str] = field(default_factory=set)


@dataclass
class PlaywrightTestSuite:
    """Complete generated test suite"""
    feature_file: Optional[str] = None
    step_definitions: list[PlaywrightStepDefinition] = field(default_factory=list)
    page_objects: list[PlaywrightPageObject] = field(default_factory=list)
    conftest_fixtures: list[str] = field(default_factory=list)


class PlaywrightPageObjectGenerator:
    """
    Generate Playwright Page Object classes from Java Page Objects.
    
    Converts Java Selenium Page Objects to Python Playwright idioms.
    """
    
    def __init__(self):
        self.generated_locators = {}  # Track generated locators
    
    def generate_page_object(
        self,
        java_class_name: str,
        method_calls: list[PageObjectCall]
    ) -> PlaywrightPageObject:
        """
        Generate a Playwright Page Object from Java method calls.
        
        Args:
            java_class_name: Original Java class name (e.g., "LoginPage")
            method_calls: List of method calls extracted from Java
        
        Returns:
            PlaywrightPageObject with locators and methods
        """
        po = PlaywrightPageObject(class_name=java_class_name)
        po.imports.add("from playwright.sync_api import Page")
        
        for call in method_calls:
            method_name = self._to_snake_case(call.method_name)
            
            # Generate method implementation
            if "click" in call.method_name.lower():
                # Click action
                locator_name = method_name.replace("click_", "") + "_locator"
                po.locators[locator_name] = self._infer_locator(call.method_name)
                po.methods[method_name] = f"self.{locator_name}.click()"
            
            elif any(kw in call.method_name.lower() for kw in ["enter", "type", "input", "set"]):
                # Fill/input action
                locator_name = method_name.replace("enter_", "").replace("set_", "") + "_input"
                po.locators[locator_name] = self._infer_locator(call.method_name)
                
                # Determine parameter name
                param_name = call.parameters[0] if call.parameters else "value"
                po.methods[method_name] = f"self.{locator_name}.fill({param_name})"
            
            elif any(kw in call.method_name.lower() for kw in ["get", "text", "read"]):
                # Get text action
                locator_name = method_name.replace("get_", "") + "_element"
                po.locators[locator_name] = self._infer_locator(call.method_name)
                po.methods[method_name] = f"return self.{locator_name}.text_content()"
            
            else:
                # Generic action - add TODO
                locator_name = method_name + "_element"
                po.locators[locator_name] = self._infer_locator(call.method_name)
                po.methods[method_name] = f"# TODO: Implement {method_name}\n        pass"
        
        return po
    
    def _to_snake_case(self, name: str) -> str:
        """Convert camelCase to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _infer_locator(self, method_name: str) -> str:
        """
        Infer Playwright locator from Java method name.
        
        This uses heuristics - in reality, would need to analyze Java PageObject.
        """
        # Extract element name from method
        name_lower = method_name.lower()
        
        # Common patterns
        if "login" in name_lower and "button" in name_lower:
            return 'self.page.locator("button:has-text(\'Login\')")'
        elif "username" in name_lower:
            return 'self.page.locator("input[name=\'username\']")'
        elif "password" in name_lower:
            return 'self.page.locator("input[type=\'password\']")'
        elif "submit" in name_lower:
            return 'self.page.locator("button[type=\'submit\']")'
        elif "button" in name_lower:
            element = name_lower.replace("click", "").replace("button", "").strip("_")
            return f'self.page.locator("button#{element}")'
        elif "link" in name_lower:
            element = name_lower.replace("click", "").replace("link", "").strip("_")
            return f'self.page.locator("a:has-text(\'{element.title()}\')")'
        else:
            # Generic - add TODO
            element = name_lower.replace("click", "").replace("get", "").replace("enter", "").strip("_")
            return f'self.page.locator("#{element}")  # TODO: Update locator'
    
    def render_page_object(self, po: PlaywrightPageObject) -> str:
        """
        Render PlaywrightPageObject to Python code.
        
        Returns properly formatted Python class code.
        """
        lines = []
        
        # Imports
        for imp in sorted(po.imports):
            lines.append(imp)
        lines.append("")
        lines.append("")
        
        # Class definition
        lines.append(f"class {po.class_name}:")
        lines.append('    """Generated Playwright Page Object"""')
        lines.append("")
        
        # __init__ with locators
        lines.append("    def __init__(self, page: Page):")
        lines.append("        self.page = page")
        
        for locator_name, locator_def in po.locators.items():
            lines.append(f"        self.{locator_name} = {locator_def}")
        
        lines.append("")
        
        # Methods
        for method_name, method_body in po.methods.items():
            # Determine signature
            if "fill(" in method_body:
                # Extract parameter name from method body
                param_match = re.search(r'fill\((\w+)\)', method_body)
                param = param_match.group(1) if param_match else "value"
                lines.append(f"    def {method_name}(self, {param}: str):")
            elif "return" in method_body:
                lines.append(f"    def {method_name}(self) -> str:")
            else:
                lines.append(f"    def {method_name}(self):")
            
            lines.append(f"        {method_body}")
            lines.append("")
        
        return "\n".join(lines)


class PytestBDDStepGenerator:
    """
    Generate pytest-bdd step definitions from Java step definitions.
    
    Converts Java Cucumber steps to Python pytest-bdd steps.
    """
    
    def __init__(self):
        self.generated_steps = []
    
    def generate_step_definition(
        self,
        step_def: StepDefinitionIntent,
        page_objects: dict[str, str]  # po_name -> class_name
    ) -> PlaywrightStepDefinition:
        """
        Generate pytest-bdd step from Java step definition.
        
        Args:
            step_def: Parsed Java step definition
            page_objects: Mapping of page object variable names to class names
        
        Returns:
            PlaywrightStepDefinition
        """
        keyword = step_def.step_type.lower()
        pattern = self._convert_cucumber_pattern(step_def.pattern)
        function_name = self._to_snake_case(step_def.method_name)
        
        step = PlaywrightStepDefinition(
            keyword=keyword,
            pattern=pattern,
            function_name=function_name,
            function_body="",
            fixtures=["page"]
        )
        
        step.imports.add("from pytest_bdd import given, when, then, parsers")
        
        # Determine required page object fixtures
        for po_call in step_def.page_object_calls:
            po_fixture = self._to_snake_case(po_call.page_object_name)
            if po_fixture not in step.fixtures:
                step.fixtures.append(po_fixture)
        
        # Generate function body
        step.function_body = self._generate_step_body(step_def)
        
        return step
    
    def _convert_cucumber_pattern(self, java_pattern: str) -> str:
        """
        Convert Cucumber Java pattern to pytest-bdd pattern.
        
        Examples:
            "user enters username {string}" -> "user enters username {username}"
            "user enters password (.*)" -> "user enters password {password}"
        """
        # Remove regex anchors
        pattern = java_pattern.strip("^$")
        
        # Replace {string} with named parameters
        pattern = re.sub(r'\{string\}', lambda m: '{param}', pattern)
        
        # Replace (.*) with named parameters
        pattern = re.sub(r'\(\.\*\)', lambda m: '{param}', pattern)
        
        # Try to infer parameter names from context
        if "username" in pattern.lower():
            pattern = pattern.replace("{param}", "{username}", 1)
        elif "password" in pattern.lower():
            pattern = pattern.replace("{param}", "{password}", 1)
        elif "email" in pattern.lower():
            pattern = pattern.replace("{param}", "{email}", 1)
        else:
            # Generic numbering
            count = 0
            while "{param}" in pattern:
                pattern = pattern.replace("{param}", f"{{param{count}}}", 1)
                count += 1
        
        return pattern
    
    def _generate_step_body(self, step_def: StepDefinitionIntent) -> str:
        """Generate the Python function body for the step"""
        lines = []
        
        if step_def.page_object_calls:
            # Generate Page Object method calls
            for call in step_def.page_object_calls:
                po_var = self._to_snake_case(call.page_object_name)
                method = self._to_snake_case(call.method_name)
                
                if call.parameters:
                    # Has parameters - pass them
                    params_str = ", ".join(call.parameters)
                    lines.append(f"{po_var}.{method}({params_str})")
                else:
                    lines.append(f"{po_var}.{method}()")
        
        elif step_def.selenium_actions:
            # Direct Selenium actions - convert to Playwright
            for action in step_def.selenium_actions:
                pw_action = SELENIUM_TO_PLAYWRIGHT.get(action.action_type, action.action_type)
                
                if pw_action == "fill":
                    lines.append(f'page.locator("TODO").fill("{action.parameters[0] if action.parameters else "value"}")')
                elif pw_action == "click":
                    lines.append('page.locator("TODO").click()')
                else:
                    lines.append(f'page.locator("TODO").{pw_action}()')
                
                lines.append("# TODO: Update locator selector")
        
        else:
            # No implementation found - add placeholder
            lines.append("# TODO: Implement step logic")
            lines.append("pass")
        
        # Join lines - the indentation will be added by render_step_definition
        if not lines:
            return "pass"
        return "\n".join(lines)
    
    def _to_snake_case(self, name: str) -> str:
        """Convert camelCase to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def render_step_definition(self, step: PlaywrightStepDefinition) -> str:
        """
        Render step definition to Python code.
        
        Returns properly formatted pytest-bdd step function.
        """
        lines = []
        
        # Decorator with pattern
        if "{" in step.pattern:
            # Has parameters - use parsers.parse
            lines.append(f'@{step.keyword}(parsers.parse("{step.pattern}"))')
        else:
            # No parameters - literal string
            lines.append(f'@{step.keyword}("{step.pattern}")')
        
        # Function signature
        fixtures_str = ", ".join(step.fixtures)
        
        # Extract parameter names from pattern
        params = re.findall(r'\{(\w+)\}', step.pattern)
        if params:
            all_params = fixtures_str + ", " + ", ".join(params)
        else:
            all_params = fixtures_str
        
        lines.append(f"def {step.function_name}({all_params}):")
        
        # Docstring
        lines.append(f'    """Step: {step.keyword} {step.pattern}"""')
        
        # Body
        for line in step.function_body.split("\n"):
            lines.append(f"    {line}")
        
        return "\n".join(lines)


class PlaywrightFixtureGenerator:
    """Generate pytest fixtures for Playwright"""
    
    @staticmethod
    def generate_page_fixtures(page_objects: list[str]) -> list[str]:
        """
        Generate pytest fixtures for Page Objects.
        
        Args:
            page_objects: List of Page Object class names
        
        Returns:
            List of fixture code strings
        """
        fixtures = []
        
        for po_class in page_objects:
            fixture_name = PlaywrightFixtureGenerator._to_snake_case(po_class)
            
            fixture_code = f'''@pytest.fixture
def {fixture_name}(page):
    """Fixture for {po_class}"""
    return {po_class}(page)'''
            
            fixtures.append(fixture_code)
        
        return fixtures
    
    @staticmethod
    def generate_base_fixtures() -> str:
        """Generate base Playwright fixtures (browser, page)"""
        return '''import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser():
    """Playwright browser instance"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Playwright page instance"""
    page = browser.new_page()
    yield page
    page.close()
'''
    
    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert camelCase to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class MigrationOrchestrator:
    """
    Orchestrates the complete migration process.
    
    Coordinates parsing, generation, and file writing.
    """
    
    def __init__(self):
        self.po_generator = PlaywrightPageObjectGenerator()
        self.step_generator = PytestBDDStepGenerator()
        self.fixture_generator = PlaywrightFixtureGenerator()
    
    def migrate_step_definitions(
        self,
        java_step_defs: list[StepDefinitionIntent],
        output_dir: Path,
        mode: str = "assistive"
    ) -> PlaywrightTestSuite:
        """
        Migrate Java step definitions to Playwright.
        
        Args:
            java_step_defs: Parsed Java step definitions
            output_dir: Output directory for generated files
            mode: "assistive" (with TODOs) or "auto" (full generation)
        
        Returns:
            Generated test suite
        """
        suite = PlaywrightTestSuite()
        
        # Collect all page objects
        page_objects_map = {}  # po_name -> class_name
        po_methods = {}  # class_name -> [method_calls]
        
        for step_def in java_step_defs:
            for po_call in step_def.page_object_calls:
                po_name = po_call.page_object_name
                po_class = self._extract_class_name(po_name)
                
                page_objects_map[po_name] = po_class
                
                if po_class not in po_methods:
                    po_methods[po_class] = []
                po_methods[po_class].append(po_call)
        
        # Generate Page Objects
        for po_class, methods in po_methods.items():
            po = self.po_generator.generate_page_object(po_class, methods)
            suite.page_objects.append(po)
        
        # Generate step definitions
        for step_def in java_step_defs:
            step = self.step_generator.generate_step_definition(
                step_def,
                page_objects_map
            )
            suite.step_definitions.append(step)
        
        # Generate fixtures
        suite.conftest_fixtures = self.fixture_generator.generate_page_fixtures(
            list(po_methods.keys())
        )
        
        return suite
    
    def write_migration_output(
        self,
        suite: PlaywrightTestSuite,
        output_dir: Path
    ):
        """
        Write generated code to files.
        
        Creates:
            - page_objects/*.py - Page Object classes
            - step_definitions/*.py - Step definition files
            - conftest.py - Fixtures
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directories
        po_dir = output_dir / "page_objects"
        po_dir.mkdir(exist_ok=True)
        
        step_dir = output_dir / "step_definitions"
        step_dir.mkdir(exist_ok=True)
        
        # Create __init__.py files
        (po_dir / "__init__.py").write_text("", encoding="utf-8")
        (step_dir / "__init__.py").write_text("", encoding="utf-8")
        
        # Write Page Objects
        for po in suite.page_objects:
            po_file = po_dir / f"{self._to_snake_case(po.class_name)}.py"
            content = self.po_generator.render_page_object(po)
            po_file.write_text(content, encoding="utf-8")
        
        # Write step definitions (grouped by file - simplified: one file)
        if suite.step_definitions:
            step_file = step_dir / "test_steps.py"
            
            # Collect all imports
            imports = set()
            for step in suite.step_definitions:
                imports.update(step.imports)
            
            # Add Page Object imports
            for po in suite.page_objects:
                imports.add(f"from page_objects.{self._to_snake_case(po.class_name)} import {po.class_name}")
            
            # Write file
            lines = []
            lines.append('"""Generated pytest-bdd step definitions"""')
            for imp in sorted(imports):
                lines.append(imp)
            lines.append("")
            lines.append("")
            
            for step in suite.step_definitions:
                lines.append(self.step_generator.render_step_definition(step))
                lines.append("")
                lines.append("")
            
            step_file.write_text("\n".join(lines), encoding="utf-8")
        
        # Write conftest.py
        conftest_file = output_dir / "conftest.py"
        conftest_lines = []
        
        # Base fixtures
        conftest_lines.append(self.fixture_generator.generate_base_fixtures())
        conftest_lines.append("")
        
        # Page Object imports
        for po in suite.page_objects:
            conftest_lines.append(
                f"from page_objects.{self._to_snake_case(po.class_name)} import {po.class_name}"
            )
        conftest_lines.append("")
        conftest_lines.append("")
        
        # Page Object fixtures
        for fixture in suite.conftest_fixtures:
            conftest_lines.append(fixture)
            conftest_lines.append("")
            conftest_lines.append("")
        
        conftest_file.write_text("\n".join(conftest_lines), encoding="utf-8")
        
        # Write README
        readme_file = output_dir / "README.md"
        readme_content = self._generate_readme(suite)
        readme_file.write_text(readme_content, encoding="utf-8")
    
    def _extract_class_name(self, var_name: str) -> str:
        """Extract class name from variable name (loginPage -> LoginPage)"""
        return var_name[0].upper() + var_name[1:]
    
    def _to_snake_case(self, name: str) -> str:
        """Convert camelCase to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _generate_readme(self, suite: PlaywrightTestSuite) -> str:
        """Generate README for migrated tests"""
        return f"""# Migrated Playwright Tests

This test suite was generated by CrossBridge from Java Selenium BDD tests.

## Structure

- `page_objects/` - Playwright Page Object classes ({len(suite.page_objects)} files)
- `step_definitions/` - pytest-bdd step definitions ({len(suite.step_definitions)} steps)
- `conftest.py` - pytest fixtures for Playwright

## Running Tests

```bash
# Install dependencies
pip install pytest pytest-bdd playwright

# Install Playwright browsers
playwright install chromium

# Run tests
pytest step_definitions/
```

## Migration Notes

⚠️ **ASSISTIVE MODE** - This code was generated with TODOs and requires review:

1. **Review all locator selectors** - Many are inferred and marked with TODO
2. **Update Page Object locators** - Verify selectors match your application
3. **Test all step implementations** - Some may need manual adjustment
4. **Add assertions** - Verify test assertions are complete

## Next Steps

1. Review generated code
2. Update locator strategies
3. Run tests and fix failures
4. Add additional assertions as needed
5. Commit to version control

---

Generated by CrossBridge Migration Tool
Date: {Path(__file__).stat().st_mtime if Path(__file__).exists() else 'N/A'}
"""
