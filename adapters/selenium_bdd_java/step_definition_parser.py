"""
Java BDD Step Definition Parser

Parses Java Cucumber step definition files to extract:
- Step annotations (@Given, @When, @Then)
- Step patterns (regex)
- Method implementations
- Page Object usage
- Selenium actions

This is the critical bridge between Gherkin and Java implementation.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SeleniumAction:
    """Represents a Selenium WebDriver action"""
    action_type: str  # click, sendKeys, getText, etc.
    target: str  # element reference
    parameters: list[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class PageObjectCall:
    """Represents a call to a Page Object method"""
    page_object_name: str
    method_name: str
    parameters: list[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class StepDefinitionIntent:
    """
    Neutral representation of a step definition.
    This decouples Java implementation from target framework.
    """
    step_type: str  # Given, When, Then, And, But
    pattern: str  # Original regex pattern
    pattern_text: str  # Human-readable pattern (without regex)
    method_name: str
    method_body: str
    page_object_calls: list[PageObjectCall] = field(default_factory=list)
    selenium_actions: list[SeleniumAction] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    assertions: list[str] = field(default_factory=list)
    file_path: str = ""
    line_number: int = 0
    
    @property
    def intent_type(self) -> str:
        """Classify step intent based on keyword and content"""
        body_lower = self.method_body.lower()
        
        # Setup intent
        if self.step_type in ["Given"] and any(
            keyword in body_lower
            for keyword in ["navigate", "open", "goto", "setup", "driver.get"]
        ):
            return "setup"
        
        # Assertion intent
        if self.step_type in ["Then"] or self.assertions or "assert" in body_lower:
            return "assertion"
        
        # Action intent (clicks, inputs, etc)
        if self.step_type in ["When", "And"] and any(
            action.action_type in ["click", "sendKeys", "submit"]
            for action in self.selenium_actions
        ):
            return "action"
        
        # Default based on keyword
        if self.step_type == "Given":
            return "setup"
        elif self.step_type == "Then":
            return "assertion"
        else:
            return "action"


@dataclass
class StepDefinitionFile:
    """Represents a complete step definition file"""
    file_path: str
    class_name: str
    step_definitions: list[StepDefinitionIntent] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    page_object_fields: dict[str, str] = field(default_factory=dict)  # field_name -> type


class JavaStepDefinitionParser:
    """
    Parse Java Cucumber step definition files.
    
    Extracts step patterns, implementations, and dependencies.
    """
    
    # Cucumber step annotations
    STEP_ANNOTATIONS = ["Given", "When", "Then", "And", "But"]
    
    # Selenium action patterns
    SELENIUM_PATTERNS = {
        "click": r"\.click\(\)",
        "sendKeys": r"\.sendKeys\((.*?)\)",
        "getText": r"\.getText\(\)",
        "clear": r"\.clear\(\)",
        "submit": r"\.submit\(\)",
        "isDisplayed": r"\.isDisplayed\(\)",
        "isEnabled": r"\.isEnabled\(\)",
        "isSelected": r"\.isSelected\(\)",
        "findElement": r"\.findElement\((.*?)\)",
        "findElements": r"\.findElements\((.*?)\)",
    }
    
    # Common assertion patterns
    ASSERTION_PATTERNS = [
        r"assert(True|False|Equals|NotEquals|NotNull|Null)",
        r"verify(True|False|Equals)",
        r"expect\(",
        r"should\(",
    ]
    
    def parse_file(self, file_path: Path) -> Optional[StepDefinitionFile]:
        """Parse a single step definition file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.parse_content(content, str(file_path))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def parse_content(self, content: str, file_path: str = "") -> StepDefinitionFile:
        """Parse step definition content"""
        
        result = StepDefinitionFile(
            file_path=file_path,
            class_name=self._extract_class_name(content)
        )
        
        # Extract imports
        result.imports = self._extract_imports(content)
        
        # Extract page object fields
        result.page_object_fields = self._extract_page_object_fields(content)
        
        # Extract step definitions
        result.step_definitions = self._extract_step_definitions(content, file_path)
        
        return result
    
    def _extract_class_name(self, content: str) -> str:
        """Extract class name from Java file"""
        match = re.search(r'public\s+class\s+(\w+)', content)
        return match.group(1) if match else "Unknown"
    
    def _extract_imports(self, content: str) -> list[str]:
        """Extract import statements"""
        imports = []
        for line in content.split('\n'):
            match = re.match(r'import\s+([\w.]+);', line.strip())
            if match:
                imports.append(match.group(1))
        return imports
    
    def _extract_page_object_fields(self, content: str) -> dict[str, str]:
        """
        Extract Page Object field declarations.
        
        Example:
            private LoginPage loginPage;
            @Autowired private HomePage homePage;
        """
        fields = {}
        
        # Pattern: field declaration with potential annotations
        pattern = r'(?:@\w+\s+)*(?:private|protected|public)\s+(\w+Page)\s+(\w+)\s*;'
        
        for match in re.finditer(pattern, content):
            page_type = match.group(1)
            field_name = match.group(2)
            fields[field_name] = page_type
        
        return fields
    
    def _extract_step_definitions(
        self, 
        content: str, 
        file_path: str
    ) -> list[StepDefinitionIntent]:
        """Extract all step definitions from content"""
        
        step_defs = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for step annotation
            step_type, pattern = self._parse_step_annotation(line)
            
            if step_type and pattern:
                # Found a step definition, extract the method
                method_start = i + 1
                method_name, method_body, method_end = self._extract_method(
                    lines, method_start
                )
                
                if method_name:
                    step_def = StepDefinitionIntent(
                        step_type=step_type,
                        pattern=pattern,
                        pattern_text=self._regex_to_text(pattern),
                        method_name=method_name,
                        method_body=method_body,
                        file_path=file_path,
                        line_number=i + 1
                    )
                    
                    # Analyze method body
                    self._analyze_method_body(step_def, method_body)
                    
                    step_defs.append(step_def)
                    
                    i = method_end
                    continue
            
            i += 1
        
        return step_defs
    
    def _parse_step_annotation(self, line: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse Cucumber step annotation.
        
        Examples:
            @Given("user is on login page")
            @When("^user clicks login button$")
            @Then("user should see dashboard")
        """
        for step_type in self.STEP_ANNOTATIONS:
            # Pattern: @Given("pattern") or @Given(value = "pattern")
            patterns = [
                rf'@{step_type}\s*\(\s*"([^"]+)"\s*\)',
                rf'@{step_type}\s*\(\s*value\s*=\s*"([^"]+)"\s*\)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    return step_type, match.group(1)
        
        return None, None
    
    def _regex_to_text(self, pattern: str) -> str:
        """
        Convert regex pattern to human-readable text.
        
        Examples:
            "^user clicks (.*) button$" -> "user clicks {param} button"
            "user enters \"([^\"]*)\"" -> "user enters {param}"
        """
        text = pattern
        
        # Remove anchors
        text = text.strip('^$')
        
        # Replace capture groups with {param}
        text = re.sub(r'\([^)]*\)', '{param}', text)
        
        # Remove regex escapes
        text = text.replace('\\"', '"').replace('\\(', '(').replace('\\)', ')')
        
        return text
    
    def _extract_method(
        self, 
        lines: list[str], 
        start_idx: int
    ) -> tuple[Optional[str], str, int]:
        """
        Extract method name and body.
        
        Returns: (method_name, method_body, end_line_index)
        """
        # Find method signature
        method_line = ""
        idx = start_idx
        
        while idx < len(lines):
            line = lines[idx].strip()
            method_line += " " + line
            
            if '{' in line:
                break
            idx += 1
        
        # Extract method name
        match = re.search(r'(?:public|private|protected)?\s*(?:void|\w+)\s+(\w+)\s*\(', method_line)
        method_name = match.group(1) if match else None
        
        if not method_name:
            return None, "", idx
        
        # Extract method body
        body_lines = []
        brace_count = 1
        idx += 1
        
        while idx < len(lines) and brace_count > 0:
            line = lines[idx]
            
            brace_count += line.count('{')
            brace_count -= line.count('}')
            
            if brace_count > 0:
                body_lines.append(line)
            
            idx += 1
        
        method_body = '\n'.join(body_lines)
        
        return method_name, method_body, idx
    
    def _analyze_method_body(self, step_def: StepDefinitionIntent, body: str):
        """Analyze method body to extract semantic information"""
        
        # Extract Page Object method calls
        step_def.page_object_calls = self._extract_page_object_calls(body)
        
        # Extract direct Selenium actions
        step_def.selenium_actions = self._extract_selenium_actions(body)
        
        # Extract variables
        step_def.variables = self._extract_variables(body)
        
        # Extract assertions
        step_def.assertions = self._extract_assertions(body)
    
    def _extract_page_object_calls(self, body: str) -> list[PageObjectCall]:
        """
        Extract Page Object method calls.
        
        Examples:
            loginPage.enterUsername(username);
            homePage.clickProfile();
        """
        calls = []
        
        # Pattern: objectName.methodName(params)
        pattern = r'(\w+(?:Page|page))\s*\.\s*(\w+)\s*\((.*?)\)'
        
        for match in re.finditer(pattern, body):
            po_name = match.group(1)
            method_name = match.group(2)
            params_str = match.group(3).strip()
            
            # Parse parameters
            params = [p.strip() for p in params_str.split(',') if p.strip()]
            
            calls.append(PageObjectCall(
                page_object_name=po_name,
                method_name=method_name,
                parameters=params,
                line_number=0  # TODO: track line numbers
            ))
        
        return calls
    
    def _extract_selenium_actions(self, body: str) -> list[SeleniumAction]:
        """Extract direct Selenium WebDriver calls"""
        actions = []
        
        for action_name, pattern in self.SELENIUM_PATTERNS.items():
            for match in re.finditer(pattern, body):
                # Extract target element (preceding reference)
                # This is a simplified heuristic
                target = "element"
                
                # Extract parameters if any
                params = []
                if match.groups():
                    params = [g for g in match.groups() if g]
                
                actions.append(SeleniumAction(
                    action_type=action_name,
                    target=target,
                    parameters=params,
                    line_number=0
                ))
        
        return actions
    
    def _extract_variables(self, body: str) -> list[str]:
        """Extract variable declarations"""
        variables = []
        
        # Pattern: Type varName = ...
        pattern = r'(?:String|int|boolean|WebElement)\s+(\w+)\s*='
        
        for match in re.finditer(pattern, body):
            variables.append(match.group(1))
        
        return variables
    
    def _extract_assertions(self, body: str) -> list[str]:
        """Extract assertion statements"""
        assertions = []
        
        for pattern in self.ASSERTION_PATTERNS:
            for match in re.finditer(pattern, body):
                # Extract full assertion line
                start = match.start()
                
                # Find the full statement (until semicolon)
                semicolon = body.find(';', start)
                if semicolon != -1:
                    assertion = body[start:semicolon + 1].strip()
                    assertions.append(assertion)
        
        return assertions
    
    def parse_directory(self, directory: Path) -> list[StepDefinitionFile]:
        """Parse all step definition files in a directory"""
        results = []
        
        # Common patterns for step definition files
        patterns = [
            "*StepDef*.java",
            "*StepDefinition*.java",
            "*Steps.java",
            "*Test.java"  # Some projects use this
        ]
        
        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                result = self.parse_file(file_path)
                if result and result.step_definitions:
                    results.append(result)
        
        return results
    
    def match_step_to_definition(
        self,
        step_text: str,
        step_definitions: list[StepDefinitionIntent]
    ) -> Optional[StepDefinitionIntent]:
        """
        Match a Gherkin step text to a step definition.
        
        This is critical for linking .feature files to implementations.
        """
        for step_def in step_definitions:
            # Convert Cucumber regex pattern to Python regex
            pattern = step_def.pattern
            
            # Remove Cucumber-specific anchors
            pattern = pattern.strip('^$')
            
            # Try to match
            try:
                if re.match(pattern, step_text):
                    return step_def
            except re.error:
                # Invalid regex, try exact match
                if step_def.pattern_text.replace('{param}', '.*') in step_text:
                    return step_def
        
        return None


class StepDefinitionMapper:
    """
    Maps Gherkin scenarios to their Java implementations.
    
    This creates the complete picture needed for migration.
    """
    
    def __init__(self, parser: JavaStepDefinitionParser):
        self.parser = parser
    
    def create_scenario_mapping(
        self,
        scenario_steps: list[tuple[str, str]],  # [(keyword, text), ...]
        step_definitions: list[StepDefinitionIntent]
    ) -> dict[str, StepDefinitionIntent]:
        """
        Map scenario steps to their implementations.
        
        Returns: {step_text: StepDefinitionIntent}
        """
        mapping = {}
        
        for keyword, step_text in scenario_steps:
            # Try to find matching step definition
            step_def = self.parser.match_step_to_definition(
                step_text, 
                step_definitions
            )
            
            if step_def:
                mapping[step_text] = step_def
            else:
                # Log unmapped step (these need manual attention)
                print(f"⚠️  Unmapped step: {keyword} {step_text}")
        
        return mapping


# Selenium to Playwright action mapping
SELENIUM_TO_PLAYWRIGHT = {
    "click": "click",
    "sendKeys": "fill",
    "getText": "text_content",
    "clear": "fill",  # fill('') in Playwright
    "submit": "click",  # Usually submit button
    "isDisplayed": "is_visible",
    "isEnabled": "is_enabled",
    "isSelected": "is_checked",
    "findElement": "locator",
    "findElements": "locator",  # Returns multiple
}


def translate_selenium_to_playwright(action: SeleniumAction) -> dict:
    """
    Translate Selenium action to Playwright equivalent.
    
    Returns a dict with Playwright method and parameters.
    """
    pw_action = SELENIUM_TO_PLAYWRIGHT.get(action.action_type, action.action_type)
    
    result = {
        "method": pw_action,
        "parameters": action.parameters,
        "notes": []
    }
    
    # Special handling
    if action.action_type == "sendKeys":
        result["method"] = "fill"
        result["notes"].append("Playwright auto-clears before fill")
    
    elif action.action_type == "clear":
        result["method"] = "fill"
        result["parameters"] = ['""']
        result["notes"].append("Clear by filling empty string")
    
    elif action.action_type == "submit":
        result["method"] = "click"
        result["notes"].append("Click submit button instead of form.submit()")
    
    return result
