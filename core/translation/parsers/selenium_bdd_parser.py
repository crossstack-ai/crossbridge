"""
Selenium Java BDD Parser.

Extracts TestIntent from Selenium Java tests with BDD structure (Cucumber/JBehave style).
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
from core.translation.parsers.selenium_parser import SeleniumParser


class SeleniumJavaBDDParser(SeleniumParser):
    """Parser for Selenium Java tests with BDD (Given/When/Then)."""
    
    def __init__(self, framework: str = "selenium-java-bdd"):
        """Initialize Selenium BDD parser."""
        super().__init__(framework)
    
    def can_parse(self, source_code: str) -> bool:
        """Check if this is Selenium BDD code."""
        bdd_indicators = [
            "@Given",
            "@When",
            "@Then",
            "@And",
            "Scenario:",
            "Feature:",
        ]
        selenium_indicators = super().can_parse(source_code)
        return selenium_indicators and any(indicator in source_code for indicator in bdd_indicators)
    
    def parse(self, source_code: str, source_file: str = "") -> TestIntent:
        """
        Parse Selenium BDD Java code into TestIntent.
        
        Extracts:
        - Scenario name
        - Given/When/Then steps
        - Step implementations with Selenium actions
        - BDD-style assertions
        """
        # Extract scenario
        scenario_name = self._extract_scenario_name(source_code)
        
        # Create test intent with BDD type
        intent = TestIntent(
            test_type=IntentType.BDD,
            name=scenario_name or "test_bdd_translated",
            source_framework=self.framework,
            source_file=source_file,
        )
        
        # Parse BDD structure
        self._parse_bdd_steps(source_code, intent)
        
        # Also parse underlying Selenium code using parent parser
        parent_intent = super().parse(source_code, source_file)
        
        # Merge Selenium actions into BDD structure
        self._merge_actions_into_bdd(intent, parent_intent)
        
        return intent
    
    def _extract_scenario_name(self, source_code: str) -> Optional[str]:
        """Extract scenario name from feature file or test."""
        # From Scenario annotation
        scenario_match = re.search(r'Scenario:\s*(.+)', source_code)
        if scenario_match:
            return self._sanitize_name(scenario_match.group(1))
        
        # From test method with @Test
        test_match = re.search(r'@Test[^\n]*\s+public\s+void\s+(\w+)', source_code)
        if test_match:
            return test_match.group(1)
        
        return None
    
    def _parse_bdd_steps(self, source_code: str, intent: TestIntent):
        """Parse Given/When/Then BDD steps."""
        lines = source_code.split('\n')
        
        current_phase = None  # 'given', 'when', 'then'
        given_steps = []
        when_steps = []
        then_steps = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            if not line or line.startswith('//'):
                continue
            
            # Detect BDD annotations
            if '@Given(' in line or 'Given(' in line:
                current_phase = 'given'
                step_text = self._extract_step_text(line)
                if step_text:
                    given_steps.append(step_text)
                    intent.scenario = (intent.scenario or "") + f"\nGiven {step_text}"
            
            elif '@When(' in line or 'When(' in line:
                current_phase = 'when'
                step_text = self._extract_step_text(line)
                if step_text:
                    when_steps.append(step_text)
                    intent.scenario = (intent.scenario or "") + f"\nWhen {step_text}"
            
            elif '@Then(' in line or 'Then(' in line:
                current_phase = 'then'
                step_text = self._extract_step_text(line)
                if step_text:
                    then_steps.append(step_text)
                    intent.scenario = (intent.scenario or "") + f"\nThen {step_text}"
            
            elif '@And(' in line or 'And(' in line:
                step_text = self._extract_step_text(line)
                if step_text and current_phase:
                    if current_phase == 'given':
                        given_steps.append(step_text)
                    elif current_phase == 'when':
                        when_steps.append(step_text)
                    elif current_phase == 'then':
                        then_steps.append(step_text)
                    intent.scenario = (intent.scenario or "") + f"\nAnd {step_text}"
        
        # Store BDD structure both as separate lists and dict
        intent.bdd_structure = {
            'given_steps': given_steps,
            'when_steps': when_steps,
            'then_steps': then_steps,
        }
    
    def _extract_step_text(self, line: str) -> Optional[str]:
        """Extract step description from annotation."""
        match = re.search(r'@?(?:Given|When|Then|And)\(\s*"([^"]+)"\s*\)', line)
        if match:
            return match.group(1)
        return None
    
    def _merge_actions_into_bdd(self, bdd_intent: TestIntent, selenium_intent: TestIntent):
        """Merge Selenium actions into BDD structure."""
        # Categorize actions into given/when/then based on heuristics
        
        # Setup actions (navigate, waits) → Given
        for action in selenium_intent.steps:
            if action.action_type in [ActionType.NAVIGATE]:
                action.semantics['bdd_phase'] = 'given'
                bdd_intent.given_steps.append(action)
            elif action.action_type in [ActionType.CLICK, ActionType.FILL, ActionType.SELECT]:
                action.semantics['bdd_phase'] = 'when'
                bdd_intent.when_steps.append(action)
            elif action.action_type == ActionType.WAIT:
                # Explicit waits can be in given or when
                if action.line_number and action.line_number < len(selenium_intent.steps) / 2:
                    action.semantics['bdd_phase'] = 'given'
                    bdd_intent.given_steps.append(action)
                else:
                    action.semantics['bdd_phase'] = 'when'
                    bdd_intent.when_steps.append(action)
            else:
                action.semantics['bdd_phase'] = 'when'
                bdd_intent.when_steps.append(action)
        
        # Assertions → Then
        for assertion in selenium_intent.assertions:
            bdd_intent.then_steps.append(assertion)
        
        # Also keep flat structure for compatibility
        bdd_intent.steps = selenium_intent.steps
        bdd_intent.assertions = selenium_intent.assertions
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize scenario name to valid test name."""
        # Convert to snake_case
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', '_', name)
        name = name.lower()
        
        if not name.startswith('test_'):
            name = f'test_{name}'
        
        return name
