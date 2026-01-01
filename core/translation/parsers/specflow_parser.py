"""
SpecFlow (.NET C#) Parser for Framework Translation.

Parses SpecFlow BDD tests written in C# with Selenium WebDriver.
Converts them to framework-agnostic TestIntent for translation.
"""

import re
from typing import Optional, List
from core.translation.intent_model import (
    TestIntent, ActionIntent, AssertionIntent,
    IntentType, ActionType, AssertionType
)
from core.translation.pipeline import SourceParser


class SpecFlowParser(SourceParser):
    """
    Parser for .NET SpecFlow BDD tests.
    
    Supports:
    - SpecFlow/Gherkin syntax with [Given], [When], [Then], [And] attributes
    - C# Selenium WebDriver code
    - Page Object Model patterns
    - NUnit/xUnit assertions
    """
    
    def __init__(self):
        super().__init__("specflow-dotnet")
    
    def can_parse(self, source_code: str) -> bool:
        """
        Check if source code is SpecFlow/C#.
        
        Indicators:
        - using TechTalk.SpecFlow
        - [Given], [When], [Then] attributes
        - IWebDriver usage
        - C# syntax (namespace, class, public void)
        """
        indicators = [
            r'using\s+TechTalk\.SpecFlow',
            r'using\s+OpenQA\.Selenium',
            r'\[Given\(',
            r'\[When\(',
            r'\[Then\(',
            r'IWebDriver',
            r'namespace\s+\w+',
            r'public\s+class\s+\w+Steps',
        ]
        
        matches = sum(1 for pattern in indicators if re.search(pattern, source_code))
        return matches >= 3
    
    def parse(self, source_code: str, source_file: Optional[str] = None) -> TestIntent:
        """
        Parse SpecFlow C# code into TestIntent.
        
        Steps:
        1. Extract scenario name from comments or class name
        2. Parse BDD step definitions ([Given]/[When]/[Then])
        3. Extract Selenium WebDriver actions
        4. Extract assertions (Assert.*, Should.*)
        5. Categorize into BDD structure
        """
        # Extract scenario/feature info
        scenario_name = self._extract_scenario_name(source_code)
        
        # Create BDD test intent
        intent = TestIntent(
            test_type=IntentType.BDD,
            name=scenario_name or "specflow_test_translated",
            source_framework=self.framework,
            source_file=source_file or "",
        )
        
        # Parse BDD steps and collect step descriptions
        self._parse_bdd_steps(source_code, intent)
        
        # Parse Selenium actions within each step
        self._parse_selenium_actions(source_code, intent)
        
        # Parse assertions
        self._parse_assertions(source_code, intent)
        
        return intent
    
    def _extract_scenario_name(self, source_code: str) -> Optional[str]:
        """Extract scenario name from feature comments or class name."""
        # From feature/scenario comments
        scenario_match = re.search(r'//\s*Scenario:\s*(.+)', source_code, re.IGNORECASE)
        if scenario_match:
            return self._sanitize_name(scenario_match.group(1))
        
        feature_match = re.search(r'//\s*Feature:\s*(.+)', source_code, re.IGNORECASE)
        if feature_match:
            return self._sanitize_name(feature_match.group(1))
        
        # From class name (e.g., LoginSteps)
        class_match = re.search(r'public\s+class\s+(\w+Steps?)', source_code)
        if class_match:
            name = class_match.group(1).replace('Steps', '').replace('Step', '')
            return self._sanitize_name(name)
        
        return None
    
    def _parse_bdd_steps(self, source_code: str, intent: TestIntent):
        """Parse [Given], [When], [Then] step definitions."""
        lines = source_code.split('\n')
        
        given_steps = []
        when_steps = []
        then_steps = []
        current_phase = None
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            if not line or line.startswith('//'):
                continue
            
            # Detect BDD attributes
            if '[Given(' in line or '[Given @' in line:
                current_phase = 'given'
                step_text = self._extract_step_text(line)
                if step_text:
                    given_steps.append(step_text)
                    intent.scenario = (intent.scenario or "") + f"\nGiven {step_text}"
            
            elif '[When(' in line or '[When @' in line:
                current_phase = 'when'
                step_text = self._extract_step_text(line)
                if step_text:
                    when_steps.append(step_text)
                    intent.scenario = (intent.scenario or "") + f"\nWhen {step_text}"
            
            elif '[Then(' in line or '[Then @' in line:
                current_phase = 'then'
                step_text = self._extract_step_text(line)
                if step_text:
                    then_steps.append(step_text)
                    intent.scenario = (intent.scenario or "") + f"\nThen {step_text}"
            
            elif '[And(' in line or '[And @' in line:
                step_text = self._extract_step_text(line)
                if step_text and current_phase:
                    if current_phase == 'given':
                        given_steps.append(step_text)
                    elif current_phase == 'when':
                        when_steps.append(step_text)
                    elif current_phase == 'then':
                        then_steps.append(step_text)
                    intent.scenario = (intent.scenario or "") + f"\nAnd {step_text}"
        
        # Store BDD structure
        intent.bdd_structure = {
            'given_steps': given_steps,
            'when_steps': when_steps,
            'then_steps': then_steps,
        }
    
    def _extract_step_text(self, line: str) -> Optional[str]:
        """Extract step description from SpecFlow attribute."""
        # Match: [Given("step text")] or [Given(@"step text")]
        match = re.search(r'\[(?:Given|When|Then|And)\s*\(\s*@?"([^"]+)"\s*\)', line)
        if match:
            return match.group(1)
        return None
    
    def _parse_selenium_actions(self, source_code: str, intent: TestIntent):
        """Parse Selenium WebDriver actions from C# code."""
        lines = source_code.split('\n')
        current_phase = 'given'  # Default phase
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track current BDD phase
            if '[Given(' in line_stripped:
                current_phase = 'given'
            elif '[When(' in line_stripped:
                current_phase = 'when'
            elif '[Then(' in line_stripped:
                current_phase = 'then'
            
            # Navigate/GoToUrl
            if 'GoToUrl(' in line_stripped or '.Url =' in line_stripped:
                url_match = re.search(r'(?:GoToUrl|\.Url\s*=)\s*[(@]?"([^"]+)"', line_stripped)
                if url_match:
                    action = ActionIntent(
                        action_type=ActionType.NAVIGATE,
                        target="URL",
                        value=url_match.group(1),
                        line_number=line_num,
                        semantics={'bdd_phase': current_phase}
                    )
                    intent.steps.append(action)
                    if current_phase == 'given':
                        intent.given_steps.append(action)
                    elif current_phase == 'when':
                        intent.when_steps.append(action)
            
            # Click
            if '.Click()' in line_stripped:
                selector = self._extract_csharp_selector(line_stripped)
                action = ActionIntent(
                    action_type=ActionType.CLICK,
                    target=selector or "element",
                    selector=selector,
                    line_number=line_num,
                    semantics={'bdd_phase': current_phase}
                )
                intent.steps.append(action)
                if current_phase == 'when':
                    intent.when_steps.append(action)
            
            # SendKeys
            if '.SendKeys(' in line_stripped:
                selector = self._extract_csharp_selector(line_stripped)
                value_match = re.search(r'SendKeys\s*\(\s*"([^"]+)"\s*\)', line_stripped)
                value = value_match.group(1) if value_match else ""
                
                action = ActionIntent(
                    action_type=ActionType.FILL,
                    target=selector or "input",
                    selector=selector,
                    value=value,
                    line_number=line_num,
                    semantics={'bdd_phase': current_phase}
                )
                intent.steps.append(action)
                if current_phase == 'when':
                    intent.when_steps.append(action)
            
            # SelectElement (dropdown)
            if 'SelectByText(' in line_stripped or 'SelectByValue(' in line_stripped:
                selector = self._extract_csharp_selector(line_stripped)
                value_match = re.search(r'SelectBy(?:Text|Value)\s*\(\s*"([^"]+)"\s*\)', line_stripped)
                value = value_match.group(1) if value_match else ""
                
                action = ActionIntent(
                    action_type=ActionType.SELECT,
                    target=selector or "select",
                    selector=selector,
                    value=value,
                    line_number=line_num,
                    semantics={'bdd_phase': current_phase}
                )
                intent.steps.append(action)
                if current_phase == 'when':
                    intent.when_steps.append(action)
    
    def _parse_assertions(self, source_code: str, intent: TestIntent):
        """Parse NUnit/xUnit/FluentAssertions assertions."""
        lines = source_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Assert.IsTrue / Assert.That(IsTrue)
            if 'Assert.IsTrue(' in line_stripped or 'Assert.That(' in line_stripped:
                if 'Displayed' in line_stripped:
                    selector = self._extract_csharp_selector(line_stripped)
                    assertion = AssertionIntent(
                        assertion_type=AssertionType.VISIBLE,
                        target=selector or "element",
                        selector=selector,
                        expected=True,
                        line_number=line_num
                    )
                    intent.assertions.append(assertion)
                    intent.then_steps.append(assertion)
            
            # Assert.AreEqual / Assert.That(Is.EqualTo)
            if 'Assert.AreEqual(' in line_stripped or 'Is.EqualTo(' in line_stripped:
                # Extract expected and actual values
                values = re.findall(r'"([^"]+)"', line_stripped)
                if len(values) >= 1:
                    expected = values[0]
                    selector = self._extract_csharp_selector(line_stripped)
                    
                    assertion = AssertionIntent(
                        assertion_type=AssertionType.TEXT_CONTENT,
                        target=selector or "element",
                        selector=selector,
                        expected=expected,
                        line_number=line_num
                    )
                    intent.assertions.append(assertion)
                    intent.then_steps.append(assertion)
            
            # FluentAssertions: .Should().Be() / .Should().Contain()
            if '.Should().' in line_stripped:
                if '.Be(' in line_stripped:
                    values = re.findall(r'"([^"]+)"', line_stripped)
                    if values:
                        selector = self._extract_csharp_selector(line_stripped)
                        # For FluentAssertions, the expected value is the last quoted string
                        expected = values[-1] if len(values) > 0 else values[0]
                        assertion = AssertionIntent(
                            assertion_type=AssertionType.EQUALS,
                            target=selector or "value",
                            selector=selector,
                            expected=expected,
                            line_number=line_num
                        )
                        intent.assertions.append(assertion)
                        intent.then_steps.append(assertion)
                
                elif '.Contain(' in line_stripped:
                    values = re.findall(r'"([^"]+)"', line_stripped)
                    if values:
                        selector = self._extract_csharp_selector(line_stripped)
                        assertion = AssertionIntent(
                            assertion_type=AssertionType.CONTAINS,
                            target=selector or "element",
                            selector=selector,
                            expected=values[0],
                            line_number=line_num
                        )
                        intent.assertions.append(assertion)
                        intent.then_steps.append(assertion)
    
    def _extract_csharp_selector(self, line: str) -> Optional[str]:
        """Extract Selenium selector from C# code."""
        # FindElement(By.Id("id"))
        id_match = re.search(r'By\.Id\s*\(\s*"([^"]+)"\s*\)', line)
        if id_match:
            return f"#{id_match.group(1)}"
        
        # FindElement(By.Name("name"))
        name_match = re.search(r'By\.Name\s*\(\s*"([^"]+)"\s*\)', line)
        if name_match:
            return f"[name='{name_match.group(1)}']"
        
        # FindElement(By.ClassName("class"))
        class_match = re.search(r'By\.ClassName\s*\(\s*"([^"]+)"\s*\)', line)
        if class_match:
            return f".{class_match.group(1)}"
        
        # FindElement(By.CssSelector("css"))
        css_match = re.search(r'By\.CssSelector\s*\(\s*"([^"]+)"\s*\)', line)
        if css_match:
            return css_match.group(1)
        
        # FindElement(By.XPath("xpath"))
        xpath_match = re.search(r'By\.XPath\s*\(\s*"([^"]+)"\s*\)', line)
        if xpath_match:
            return xpath_match.group(1)
        
        return None
    
    def _sanitize_name(self, name: str) -> str:
        """Convert name to valid Python identifier."""
        # Remove special characters
        name = re.sub(r'[^\w\s]', '', name)
        # Convert to snake_case
        name = re.sub(r'\s+', '_', name.strip())
        name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
        name = name.lower()
        return name
