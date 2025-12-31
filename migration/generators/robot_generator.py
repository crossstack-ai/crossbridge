"""
Robot Framework Code Generator for Java Selenium BDD Migration

Generates Robot Framework test files and resource files (Page Objects)
from parsed Java Cucumber step definitions.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set
import re

from adapters.selenium_bdd_java.step_definition_parser import (
    StepDefinitionIntent,
    PageObjectCall,
    SeleniumAction,
)


@dataclass
class RobotKeyword:
    """Represents a Robot Framework keyword"""
    name: str
    arguments: List[str] = field(default_factory=list)
    implementation: List[str] = field(default_factory=list)  # Lines of implementation
    documentation: str = ""


@dataclass
class RobotResource:
    """Represents a Robot Framework Resource file (Page Object)"""
    resource_name: str
    keywords: Dict[str, RobotKeyword] = field(default_factory=dict)
    library_imports: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)  # locators


@dataclass
class RobotTestCase:
    """Represents a Robot Framework test case"""
    name: str
    steps: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    documentation: str = ""


@dataclass
class RobotTestSuite:
    """Complete Robot Framework test suite"""
    suite_name: str
    test_cases: List[RobotTestCase] = field(default_factory=list)
    resources: List[RobotResource] = field(default_factory=list)
    settings: Dict[str, List[str]] = field(default_factory=dict)


class RobotResourceGenerator:
    """
    Generates Robot Framework Resource files (Page Objects).
    
    Converts Java Page Object method calls into Robot Framework keywords.
    """
    
    def generate_resource(
        self,
        resource_name: str,
        method_calls: List[PageObjectCall]
    ) -> RobotResource:
        """Generate a Robot Framework resource file"""
        resource = RobotResource(
            resource_name=resource_name,
            library_imports=["Browser"],  # robotframework-browser
            variables={}
        )
        
        # Group method calls by method name
        methods_seen = set()
        
        for call in method_calls:
            if call.method_name in methods_seen:
                continue
            methods_seen.add(call.method_name)
            
            keyword = self._create_keyword(call)
            resource.keywords[keyword.name] = keyword
            
            # Add locator variable if needed
            locator_var = self._infer_locator_variable(call.method_name)
            if locator_var:
                resource.variables[locator_var["name"]] = locator_var["value"]
        
        return resource
    
    def _create_keyword(self, call: PageObjectCall) -> RobotKeyword:
        """Create a Robot Framework keyword from Page Object call"""
        # Convert camelCase to Title Case for Robot keyword
        keyword_name = self._to_title_case(call.method_name)
        
        # Determine keyword type and implementation
        method_lower = call.method_name.lower()
        
        if any(word in method_lower for word in ["click", "press", "submit"]):
            return self._create_click_keyword(keyword_name, call)
        elif any(word in method_lower for word in ["enter", "type", "input", "fill"]):
            return self._create_input_keyword(keyword_name, call)
        elif any(word in method_lower for word in ["get", "read", "verify", "check", "assert"]):
            return self._create_verification_keyword(keyword_name, call)
        else:
            return self._create_generic_keyword(keyword_name, call)
    
    def _create_click_keyword(self, name: str, call: PageObjectCall) -> RobotKeyword:
        """Create a click keyword"""
        locator_var = self._get_locator_var_name(call.method_name)
        
        return RobotKeyword(
            name=name,
            arguments=[],
            implementation=[
                f"Click    ${{{locator_var}}}"
            ],
            documentation=f"Click on {self._to_readable(call.method_name)}"
        )
    
    def _create_input_keyword(self, name: str, call: PageObjectCall) -> RobotKeyword:
        """Create an input/fill keyword"""
        locator_var = self._get_locator_var_name(call.method_name)
        
        # Infer argument name from method name
        arg_name = "text"
        if "username" in call.method_name.lower():
            arg_name = "username"
        elif "password" in call.method_name.lower():
            arg_name = "password"
        elif "email" in call.method_name.lower():
            arg_name = "email"
        
        return RobotKeyword(
            name=name,
            arguments=[f"${{{arg_name}}}"],
            implementation=[
                f"Fill Text    ${{{locator_var}}}    ${{{arg_name}}}"
            ],
            documentation=f"Enter {arg_name} into {self._to_readable(call.method_name)}"
        )
    
    def _create_verification_keyword(self, name: str, call: PageObjectCall) -> RobotKeyword:
        """Create a verification/assertion keyword"""
        locator_var = self._get_locator_var_name(call.method_name)
        
        return RobotKeyword(
            name=name,
            arguments=[],
            implementation=[
                f"Get Element States    ${{{locator_var}}}    validate    value & visible"
            ],
            documentation=f"Verify {self._to_readable(call.method_name)}"
        )
    
    def _create_generic_keyword(self, name: str, call: PageObjectCall) -> RobotKeyword:
        """Create a generic keyword"""
        return RobotKeyword(
            name=name,
            arguments=call.parameters if call.parameters else [],
            implementation=[
                "# TODO: Implement keyword logic"
            ],
            documentation=f"Keyword: {name}"
        )
    
    def _infer_locator_variable(self, method_name: str) -> Dict[str, str]:
        """Infer Robot Framework locator variable from method name"""
        var_name = self._get_locator_var_name(method_name)
        
        # Smart locator inference
        method_lower = method_name.lower()
        
        if "username" in method_lower:
            return {"name": var_name, "value": "id=username"}
        elif "password" in method_lower:
            return {"name": var_name, "value": "id=password"}
        elif "email" in method_lower:
            return {"name": var_name, "value": "id=email"}
        elif "login" in method_lower and "button" in method_lower:
            return {"name": var_name, "value": "css=button[type='submit']"}
        elif "submit" in method_lower:
            return {"name": var_name, "value": "css=button[type='submit']"}
        elif "button" in method_lower:
            button_text = self._extract_button_text(method_name)
            return {"name": var_name, "value": f"text={button_text}"}
        else:
            # Generic selector
            element_name = self._to_readable(method_name).lower().replace(" ", "_")
            return {"name": var_name, "value": f"id={element_name}"}
    
    def _get_locator_var_name(self, method_name: str) -> str:
        """Get locator variable name for method"""
        # Convert clickLoginButton -> LOGIN_BUTTON_LOCATOR
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', method_name)
        # Remove action words
        words = [w for w in words if w.lower() not in ["click", "enter", "type", "get", "verify", "check"]]
        return "_".join(words).upper() + "_LOCATOR"
    
    def _extract_button_text(self, method_name: str) -> str:
        """Extract button text from method name"""
        # clickLoginButton -> Login
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', method_name)
        words = [w for w in words if w.lower() not in ["click", "button", "press"]]
        return " ".join(words).title()
    
    def _to_title_case(self, camel_case: str) -> str:
        """Convert camelCase to Title Case for Robot keywords"""
        # clickLoginButton -> Click Login Button
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', camel_case)
        return " ".join(word.capitalize() for word in words)
    
    def _to_readable(self, camel_case: str) -> str:
        """Convert camelCase to readable text"""
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', camel_case)
        return " ".join(words).lower()
    
    def render_resource(self, resource: RobotResource) -> str:
        """Render Robot Framework resource file"""
        lines = []
        
        # Settings section
        lines.append("*** Settings ***")
        for library in resource.library_imports:
            lines.append(f"Library    {library}")
        lines.append("")
        
        # Variables section
        if resource.variables:
            lines.append("*** Variables ***")
            for var_name, var_value in resource.variables.items():
                lines.append(f"${{{var_name}}}    {var_value}")
            lines.append("")
        
        # Keywords section
        if resource.keywords:
            lines.append("*** Keywords ***")
            for keyword_name, keyword in resource.keywords.items():
                lines.append(keyword_name)
                if keyword.arguments:
                    args_str = "    ".join(keyword.arguments)
                    lines.append(f"    [Arguments]    {args_str}")
                if keyword.documentation:
                    lines.append(f"    [Documentation]    {keyword.documentation}")
                for impl_line in keyword.implementation:
                    lines.append(f"    {impl_line}")
                lines.append("")
        
        return "\n".join(lines)


class RobotTestGenerator:
    """
    Generates Robot Framework test cases from step definitions.
    
    Converts Java Cucumber steps into Robot Framework test steps.
    """
    
    def generate_test_case(
        self,
        step_def: StepDefinitionIntent,
        page_objects_map: Dict[str, str]
    ) -> RobotTestCase:
        """Generate a Robot test case from step definition"""
        test_name = self._to_test_name(step_def.pattern_text)
        
        # Convert step to Robot keyword call
        keyword_call = self._convert_step_to_keyword(step_def, page_objects_map)
        
        return RobotTestCase(
            name=test_name,
            steps=[keyword_call],
            documentation=f"{step_def.step_type}: {step_def.pattern_text}"
        )
    
    def _convert_step_to_keyword(
        self,
        step_def: StepDefinitionIntent,
        page_objects_map: Dict[str, str]
    ) -> str:
        """Convert step definition to Robot keyword call"""
        # If step has Page Object calls, use the resource keyword
        if step_def.page_object_calls:
            po_call = step_def.page_object_calls[0]  # Use first call
            keyword_name = self._to_title_case(po_call.method_name)
            
            # Add arguments if any
            if po_call.parameters:
                args = "    ".join(po_call.parameters)
                return f"{keyword_name}    {args}"
            return keyword_name
        
        # Otherwise, create a direct Browser library call
        if step_def.selenium_actions:
            action = step_def.selenium_actions[0]
            return self._translate_selenium_action(action)
        
        # Fallback: create a TODO keyword
        return f"# TODO: Implement step - {step_def.pattern_text}"
    
    def _translate_selenium_action(self, action: SeleniumAction) -> str:
        """Translate Selenium action to Robot Browser keyword"""
        action_type = action.action_type.lower()
        
        if action_type == "click":
            return f"Click    {action.target or 'LOCATOR'}"
        elif action_type == "sendkeys":
            return f"Fill Text    {action.target or 'LOCATOR'}    {action.value or 'TEXT'}"
        elif action_type == "gettext":
            return f"Get Text    {action.target or 'LOCATOR'}"
        elif action_type == "navigate":
            return f"Go To    {action.value or 'URL'}"
        else:
            return f"# TODO: Translate {action_type}"
    
    def _to_title_case(self, text: str) -> str:
        """Convert text to Title Case"""
        # camelCase or text -> Title Case
        if any(c.isupper() for c in text[1:]):  # Has camelCase
            words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', text)
            return " ".join(word.capitalize() for word in words)
        else:
            return text.title()
    
    def _to_test_name(self, pattern: str) -> str:
        """Convert step pattern to test case name"""
        # "user is on login page" -> "User Is On Login Page"
        return pattern.title()


class RobotMigrationOrchestrator:
    """
    Orchestrates complete Java BDD → Robot Framework migration.
    
    Coordinates resource generation, test generation, and file writing.
    """
    
    def __init__(self):
        self.resource_generator = RobotResourceGenerator()
        self.test_generator = RobotTestGenerator()
    
    def migrate_step_definitions(
        self,
        step_defs: List[StepDefinitionIntent],
        output_dir: Path
    ) -> RobotTestSuite:
        """
        Migrate Java step definitions to Robot Framework.
        
        Args:
            step_defs: Parsed Java step definitions
            output_dir: Output directory path
            
        Returns:
            Complete Robot test suite
        """
        # Aggregate Page Objects from all steps
        page_objects = self._aggregate_page_objects(step_defs)
        
        # Generate resources for each Page Object
        resources = []
        page_objects_map = {}
        
        for po_name, method_calls in page_objects.items():
            resource = self.resource_generator.generate_resource(po_name, method_calls)
            resources.append(resource)
            page_objects_map[po_name.lower()] = po_name
        
        # Generate test cases
        test_cases = []
        for step_def in step_defs:
            test_case = self.test_generator.generate_test_case(step_def, page_objects_map)
            test_cases.append(test_case)
        
        # Create test suite
        suite = RobotTestSuite(
            suite_name="Migrated Tests",
            test_cases=test_cases,
            resources=resources,
            settings={
                "Library": ["Browser"],
                "Resource": [f"resources/{r.resource_name}.robot" for r in resources]
            }
        )
        
        return suite
    
    def _aggregate_page_objects(
        self,
        step_defs: List[StepDefinitionIntent]
    ) -> Dict[str, List[PageObjectCall]]:
        """Aggregate Page Object calls by Page Object name"""
        page_objects = {}
        
        for step_def in step_defs:
            for po_call in step_def.page_object_calls:
                # Normalize Page Object name - capitalize first letter
                po_name = po_call.page_object_name
                # loginPage -> LoginPage, homePage -> HomePage
                po_name = po_name[0].upper() + po_name[1:] if po_name else po_name
                
                if po_name not in page_objects:
                    page_objects[po_name] = []
                
                page_objects[po_name].append(po_call)
        
        return page_objects
    
    def write_migration_output(self, suite: RobotTestSuite, output_dir: Path):
        """Write Robot Framework files to disk"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        resources_dir = output_dir / "resources"
        tests_dir = output_dir / "tests"
        resources_dir.mkdir(exist_ok=True)
        tests_dir.mkdir(exist_ok=True)
        
        # Write resource files
        for resource in suite.resources:
            resource_file = resources_dir / f"{resource.resource_name}.robot"
            content = self.resource_generator.render_resource(resource)
            resource_file.write_text(content, encoding="utf-8")
        
        # Write test file
        test_file = tests_dir / "test_suite.robot"
        content = self._render_test_suite(suite)
        test_file.write_text(content, encoding="utf-8")
        
        # Write README
        readme = output_dir / "README.md"
        readme.write_text(self._generate_readme(suite), encoding="utf-8")
    
    def _render_test_suite(self, suite: RobotTestSuite) -> str:
        """Render complete Robot Framework test suite"""
        lines = []
        
        # Settings
        lines.append("*** Settings ***")
        lines.append("Documentation    Migrated from Java Selenium BDD")
        for library in suite.settings.get("Library", []):
            lines.append(f"Library    {library}")
        for resource in suite.settings.get("Resource", []):
            lines.append(f"Resource    ../{resource}")
        lines.append("")
        
        # Test Cases
        lines.append("*** Test Cases ***")
        for test_case in suite.test_cases:
            lines.append(test_case.name)
            if test_case.documentation:
                lines.append(f"    [Documentation]    {test_case.documentation}")
            if test_case.tags:
                lines.append(f"    [Tags]    {' '.join(test_case.tags)}")
            for step in test_case.steps:
                lines.append(f"    {step}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_readme(self, suite: RobotTestSuite) -> str:
        """Generate README for migrated project"""
        return f"""# Robot Framework Migration Output

## Overview
This project was automatically migrated from Java Selenium BDD to Robot Framework with Playwright.

## Structure
```
.
├── resources/           # Page Object resources
│   {"".join(f"├── {r.resource_name}.robot" + chr(10) + "│   " for r in suite.resources)}
├── tests/              # Test cases
│   └── test_suite.robot
└── README.md
```

## Installation

```bash
# Install Robot Framework and Browser library
pip install robotframework
pip install robotframework-browser

# Initialize Browser library
rfbrowser init
```

## Running Tests

```bash
# Run all tests
robot tests/

# Run specific test
robot --test "Test Name" tests/

# Run with tags
robot --include smoke tests/

# Generate report
robot --outputdir results tests/
```

## Migration Notes

- **Resources**: {len(suite.resources)} Page Object resources generated
- **Test Cases**: {len(suite.test_cases)} test cases migrated
- **Browser Library**: Uses robotframework-browser (Playwright-based)

## Manual Review Needed

Some steps may require manual adjustment:
1. Review locator strategies in resource files
2. Update TODO comments with actual implementation
3. Verify keyword parameters match test data
4. Add test setup/teardown as needed

## Resources

- [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- [Browser Library Documentation](https://marketsquare.github.io/robotframework-browser/)
- [CrossBridge Documentation](https://github.com/your-org/crossbridge)

---
*Generated by CrossBridge Migration Tool*
"""
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case"""
        # Handle camelCase
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()
