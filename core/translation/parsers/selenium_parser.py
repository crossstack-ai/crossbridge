"""
Selenium Java Parser.

Extracts TestIntent from Selenium Java test code.
"""

import re
from typing import List, Optional

from core.translation.intent_model import (
    ActionIntent,
    ActionType,
    AssertionIntent,
    AssertionType,
    IntentType,
    TestIntent,
)
from core.translation.pipeline import SourceParser


class SeleniumParser(SourceParser):
    """Parser for Selenium Java tests."""
    
    def __init__(self, framework: str = "selenium-java"):
        """Initialize Selenium parser."""
        super().__init__(framework)
        
        # Locator patterns
        self.by_patterns = {
            r'By\.id\("([^"]+)"\)': ("id", "#{0}"),
            r'By\.ID,\s*"([^"]+)"': ("id", "#{0}"),
            r'By\.name\("([^"]+)"\)': ("name", "[name='{0}']"),
            r'By\.className\("([^"]+)"\)': ("class", ".{0}"),
            r'By\.xpath\("([^"]+)"\)': ("xpath", "{0}"),
            r'By\.cssSelector\("([^"]+)"\)': ("css", "{0}"),
            r'By\.linkText\("([^"]+)"\)': ("linkText", "text='{0}'"),
        }
    
    def can_parse(self, source_code: str) -> bool:
        """Check if this is Selenium Java code."""
        indicators = [
            "import org.openqa.selenium",
            "WebDriver",
            "driver.findElement",
            "@Test",
        ]
        return any(indicator in source_code for indicator in indicators)
    
    def parse(self, source_code: str, source_file: str = "") -> TestIntent:
        """
        Parse Selenium Java code into TestIntent.
        
        Extracts:
        - Test methods
        - WebDriver actions
        - Assertions
        - Page objects
        - Wait patterns
        """
        # Extract test method
        test_name = self._extract_test_name(source_code)
        
        # Create test intent
        intent = TestIntent(
            test_type=IntentType.UI,
            name=test_name or "test_selenium_translated",
            source_framework=self.framework,
            source_file=source_file,
        )
        
        # Parse actions
        actions = self._parse_actions(source_code)
        for action in actions:
            intent.add_step(action)
        
        # Parse assertions
        assertions = self._parse_assertions(source_code)
        for assertion in assertions:
            intent.add_assertion(assertion)
        
        # Detect page objects
        page_objects = self._detect_page_objects(source_code)
        intent.page_objects = page_objects
        
        # Detect setup/teardown
        setup_actions = self._parse_setup(source_code)
        intent.setup_steps = setup_actions
        
        teardown_actions = self._parse_teardown(source_code)
        intent.teardown_steps = teardown_actions
        
        return intent
    
    def _extract_test_name(self, source_code: str) -> Optional[str]:
        """Extract test method name."""
        # Look for @Test annotation
        test_pattern = r'@Test[^\n]*\s+public\s+void\s+(\w+)\s*\('
        match = re.search(test_pattern, source_code)
        if match:
            return match.group(1)
        
        # Try JUnit 5 style
        test_pattern = r'@Test\s+void\s+(\w+)\s*\('
        match = re.search(test_pattern, source_code)
        if match:
            return match.group(1)
        
        return None
    
    def _parse_actions(self, source_code: str) -> List[ActionIntent]:
        """Parse Selenium actions into ActionIntents."""
        actions = []
        lines = source_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('//') or line.startswith('/*'):
                continue
            
            # Parse navigation
            if 'driver.get(' in line:
                url = self._extract_string(line)
                actions.append(ActionIntent(
                    action_type=ActionType.NAVIGATE,
                    target="url",
                    value=url,
                    description=f"Navigate to {url}",
                    line_number=line_num,
                ))
            
            # Parse click
            elif '.click()' in line:
                selector_info = self._extract_selector(line)
                if selector_info:
                    target, selector = selector_info
                    actions.append(ActionIntent(
                        action_type=ActionType.CLICK,
                        target=target,
                        selector=selector,
                        description=f"Click {target}",
                        line_number=line_num,
                    ))
            
            # Parse sendKeys / fill
            elif '.sendKeys(' in line:
                selector_info = self._extract_selector(line)
                value = self._extract_send_keys_value(line)
                if selector_info:
                    target, selector = selector_info
                    actions.append(ActionIntent(
                        action_type=ActionType.FILL,
                        target=target,
                        selector=selector,
                        value=value,
                        description=f"Fill {target} with {value}",
                        line_number=line_num,
                    ))
            
            # Parse explicit waits
            elif 'WebDriverWait' in line:
                actions.append(ActionIntent(
                    action_type=ActionType.WAIT,
                    target="explicit_wait",
                    wait_strategy="explicit",
                    description="Explicit wait",
                    line_number=line_num,
                    confidence=0.8,  # Lower confidence - may not be needed
                ))
            
            # Parse Thread.sleep
            elif 'Thread.sleep' in line or 'time.sleep' in line:
                actions.append(ActionIntent(
                    action_type=ActionType.WAIT,
                    target="sleep",
                    description="Sleep (should be removed)",
                    line_number=line_num,
                    confidence=0.5,  # Very low confidence
                ))
        
        return actions
    
    def _parse_assertions(self, source_code: str) -> List[AssertionIntent]:
        """Parse Selenium assertions into AssertionIntents."""
        assertions = []
        lines = source_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments
            if not line or line.startswith('//'):
                continue
            
            # Parse assertTrue/isDisplayed
            if 'assertTrue' in line and 'isDisplayed' in line:
                selector_info = self._extract_selector(line)
                if selector_info:
                    target, selector = selector_info
                    assertions.append(AssertionIntent(
                        assertion_type=AssertionType.VISIBLE,
                        target=target,
                        selector=selector,
                        expected=True,
                        description=f"Assert {target} is visible",
                        line_number=line_num,
                    ))
            
            # Parse assertEquals
            elif 'assertEquals' in line:
                # Extract expected and actual values (handle both order: expected,actual or actual,expected)
                # Try pattern with expected first
                match = re.search(r'assertEquals\s*\(\s*"([^"]+)"\s*,\s*(.+?)\)', line)
                if not match:
                    # Try with actual first (JUnit style can vary)
                    match = re.search(r'assertEquals\s*\(\s*(.+?)\s*,\s*"([^"]+)"\)', line)
                    if match:
                        actual_expr = match.group(1)
                        expected = match.group(2)
                    else:
                        continue
                else:
                    expected = match.group(1)
                    actual_expr = match.group(2)
                
                # Determine what we're asserting on
                if 'getText()' in actual_expr or 'getText()' in line:
                    selector_info = self._extract_selector(line)
                    if selector_info:
                        target, selector = selector_info
                        assertions.append(AssertionIntent(
                            assertion_type=AssertionType.TEXT_CONTENT,
                            target=target,
                            selector=selector,
                            expected=expected,
                            description=f"Assert {target} text equals '{expected}'",
                            line_number=line_num,
                        ))
            
            # Parse assertThat (Hamcrest style)
            elif 'assertThat' in line:
                assertions.append(AssertionIntent(
                    assertion_type=AssertionType.CUSTOM,
                    target="assertion",
                    expected="custom",
                    description="Custom assertion (needs review)",
                    line_number=line_num,
                    confidence=0.7,
                ))
        
        return assertions
    
    def _parse_setup(self, source_code: str) -> List[ActionIntent]:
        """Parse @Before / @BeforeEach setup code."""
        setup_actions = []
        
        # Find setup method
        setup_pattern = r'@Before[Each]?\s+public\s+void\s+\w+\s*\(\)\s*\{([^}]+)\}'
        match = re.search(setup_pattern, source_code, re.DOTALL)
        
        if match:
            setup_code = match.group(1)
            # Parse setup actions (simplified)
            if 'new ChromeDriver' in setup_code:
                setup_actions.append(ActionIntent(
                    action_type=ActionType.CUSTOM,
                    target="setup_driver",
                    description="Initialize browser driver",
                ))
        
        return setup_actions
    
    def _parse_teardown(self, source_code: str) -> List[ActionIntent]:
        """Parse @After / @AfterEach teardown code."""
        teardown_actions = []
        
        # Find teardown method
        teardown_pattern = r'@After[Each]?\s+public\s+void\s+\w+\s*\(\)\s*\{([^}]+)\}'
        match = re.search(teardown_pattern, source_code, re.DOTALL)
        
        if match:
            teardown_code = match.group(1)
            if 'driver.quit' in teardown_code or 'driver.close' in teardown_code:
                teardown_actions.append(ActionIntent(
                    action_type=ActionType.CUSTOM,
                    target="teardown_driver",
                    description="Quit browser driver",
                ))
        
        return teardown_actions
    
    def _detect_page_objects(self, source_code: str) -> List[str]:
        """Detect page object usage."""
        page_objects = []
        
        # Look for page object instantiation
        page_pattern = r'(\w+Page)\s+\w+\s*=\s*new\s+\1'
        matches = re.findall(page_pattern, source_code)
        page_objects.extend(matches)
        
        return list(set(page_objects))  # Unique
    
    def _extract_selector(self, line: str) -> Optional[tuple]:
        """Extract selector from driver.findElement()."""
        for pattern, (locator_type, template) in self.by_patterns.items():
            match = re.search(pattern, line)
            if match:
                locator_value = match.group(1)
                # Generate target name from selector
                target = self._generate_target_name(locator_type, locator_value)
                selector = template.format(locator_value)
                return (target, selector)
        
        return None
    
    def _generate_target_name(self, locator_type: str, locator_value: str) -> str:
        """Generate a semantic target name from locator."""
        # Convert id/name to semantic name
        # e.g., "login-btn" → "login_button"
        name = locator_value.replace('-', '_').replace('.', '_')
        
        # Add suffix if not obvious
        if not any(suffix in name for suffix in ['btn', 'button', 'field', 'input', 'link']):
            if locator_type == 'id':
                name = f"{name}_element"
        
        return name
    
    def _extract_string(self, line: str) -> Optional[str]:
        """Extract string value from line."""
        match = re.search(r'"([^"]+)"', line)
        if match:
            return match.group(1)
        return None
    
    def _extract_send_keys_value(self, line: str) -> Optional[str]:
        """Extract value from sendKeys()."""
        match = re.search(r'sendKeys\s*\(\s*"([^"]+)"\s*\)', line)
        if match:
            return match.group(1)
        
        # Handle variable
        match = re.search(r'sendKeys\s*\(\s*(\w+)\s*\)', line)
        if match:
            return f"${{{match.group(1)}}}"  # Variable placeholder
        
        return None
