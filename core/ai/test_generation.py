"""
AI-Powered Test Generation Service.

Provides intelligent test generation capabilities including:
- Natural language to test code conversion
- Context-aware page object detection and usage
- Intelligent assertion generation
- Intent-based test creation
- Code completion and suggestions
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.ai.models import (
    AIExecutionContext,
    AIMessage,
    ModelConfig,
    TaskType,
)
from core.ai.orchestrator import AIOrchestrator
from core.ai.skills import TestGenerator


@dataclass
class TestIntent:
    """
    User intent for test generation.
    
    Parsed from natural language input.
    """
    action: str  # e.g., "click", "verify", "navigate"
    target: Optional[str] = None  # e.g., "login button", "username field"
    expected_outcome: Optional[str] = None  # e.g., "user is logged in"
    data: Dict[str, Any] = field(default_factory=dict)
    context: str = ""  # Original natural language


@dataclass
class PageObject:
    """Detected page object from codebase."""
    name: str
    file_path: Path
    locators: Dict[str, str] = field(default_factory=dict)
    methods: List[str] = field(default_factory=list)
    framework: str = "selenium"  # selenium, playwright, etc.


@dataclass
class Assertion:
    """Intelligent assertion suggestion."""
    assertion_type: str  # equals, contains, visible, enabled, etc.
    target: str
    expected_value: Optional[Any] = None
    code_snippet: str = ""
    confidence: float = 0.0


@dataclass
class TestGenerationResult:
    """Result of AI-powered test generation."""
    test_code: str
    test_name: str
    framework: str
    assertions: List[Assertion] = field(default_factory=list)
    page_objects_used: List[str] = field(default_factory=list)
    setup_code: str = ""
    teardown_code: str = ""
    imports: List[str] = field(default_factory=list)
    confidence: float = 0.0
    suggestions: List[str] = field(default_factory=list)


class NaturalLanguageParser:
    """
    Parse natural language test descriptions into structured intents.
    """
    
    # Action keywords
    ACTION_PATTERNS = {
        "navigate": r"\b(navigate|go|open|visit)\s+to\b",
        "click": r"\b(click|press|tap|select)\b",
        "input": r"\b(enter|type|input|fill|set)\b",
        "verify": r"\b(verify|check|assert|ensure|confirm|validate)\b",
        "wait": r"\b(wait|pause)\b",
        "hover": r"\b(hover|mouse over)\b",
        "scroll": r"\b(scroll|swipe)\b",
        "upload": r"\b(upload|attach)\b",
    }
    
    def parse(self, natural_language: str) -> List[TestIntent]:
        """
        Parse natural language into test intents.
        
        Args:
            natural_language: Natural language test description
        
        Returns:
            List of parsed test intents
        """
        intents = []
        
        # Split into sentences/steps
        steps = self._split_into_steps(natural_language)
        
        for step in steps:
            intent = self._parse_step(step)
            if intent:
                intents.append(intent)
        
        return intents
    
    def _split_into_steps(self, text: str) -> List[str]:
        """Split text into individual test steps."""
        # Split by newlines, numbered lists, or bullet points
        steps = []
        
        # Handle numbered lists (1. 2. 3.)
        numbered = re.split(r'\n\s*\d+\.\s+', text)
        if len(numbered) > 1:
            return [s.strip() for s in numbered if s.strip()]
        
        # Handle bullet points
        bullets = re.split(r'\n\s*[-•*]\s+', text)
        if len(bullets) > 1:
            return [s.strip() for s in bullets if s.strip()]
        
        # Handle sentences
        sentences = re.split(r'[.!]\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _parse_step(self, step: str) -> Optional[TestIntent]:
        """Parse a single step into a test intent."""
        step_lower = step.lower()
        
        # Detect action
        action = None
        for action_name, pattern in self.ACTION_PATTERNS.items():
            if re.search(pattern, step_lower):
                action = action_name
                break
        
        if not action:
            action = "custom"
        
        # Extract target (quoted text or after prepositions)
        target = self._extract_target(step)
        
        # Extract expected outcome
        expected = self._extract_expected_outcome(step)
        
        # Extract data (key-value pairs)
        data = self._extract_data(step)
        
        return TestIntent(
            action=action,
            target=target,
            expected_outcome=expected,
            data=data,
            context=step,
        )
    
    def _extract_target(self, step: str) -> Optional[str]:
        """Extract target element from step."""
        # Look for quoted text
        quoted = re.findall(r'"([^"]+)"', step)
        if quoted:
            return quoted[0]
        
        # Look after "on", "the", "to"
        match = re.search(r'\b(?:on|the|to|at|in)\s+(.+?)(?:\s+with|\s+and|$)', step, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_expected_outcome(self, step: str) -> Optional[str]:
        """Extract expected outcome from step."""
        # Look for "should", "must", "expect"
        match = re.search(r'\b(?:should|must|expect|verify|assert)\s+(.+)', step, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_data(self, step: str) -> Dict[str, Any]:
        """Extract data from step."""
        data = {}
        
        # Look for "with X" or "using Y"
        match = re.search(r'\bwith\s+(.+?)(?:\s+and|$)', step, re.IGNORECASE)
        if match:
            data_str = match.group(1)
            # Try to parse key-value pairs
            pairs = re.findall(r'(\w+)\s*[=:]\s*["\']?([^"\']+)["\']?', data_str)
            for key, value in pairs:
                data[key] = value
        
        return data


class PageObjectDetector:
    """
    Detect and extract page objects from codebase.
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize detector.
        
        Args:
            project_root: Root directory of project
        """
        self.project_root = project_root
        self._page_objects_cache: Dict[str, PageObject] = {}
    
    def detect_page_objects(self, refresh: bool = False) -> List[PageObject]:
        """
        Detect all page objects in project.
        
        Args:
            refresh: Force refresh of cache
        
        Returns:
            List of detected page objects
        """
        if self._page_objects_cache and not refresh:
            return list(self._page_objects_cache.values())
        
        # Clear cache if refreshing
        if refresh:
            self._page_objects_cache.clear()
        
        page_objects = []
        seen_files = set()  # Track processed files to avoid duplicates
        
        # Search for page object files
        page_object_patterns = [
            "**/pages/*.py",
            "**/page_objects/*.py",
            "**/*_page.py",
            "**/*Page.py",
        ]
        
        for pattern in page_object_patterns:
            for file_path in self.project_root.glob(pattern):
                # Skip if already processed
                if file_path in seen_files:
                    continue
                seen_files.add(file_path)
                
                po = self._parse_page_object_file(file_path)
                if po:
                    page_objects.append(po)
                    self._page_objects_cache[po.name] = po
        
        return page_objects
    
    def _parse_page_object_file(self, file_path: Path) -> Optional[PageObject]:
        """Parse a single page object file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Extract class name
            class_match = re.search(r'class\s+(\w+)', content)
            if not class_match:
                return None
            
            class_name = class_match.group(1)
            
            # Extract locators
            locators = {}
            
            # Selenium style: By.ID, By.XPATH, etc.
            selenium_locators = re.findall(
                r'(\w+)\s*=\s*(?:By\.(\w+)|[\'"](.*?)[\'"])',
                content
            )
            for name, by_type, value in selenium_locators:
                if by_type or value:
                    locators[name] = value or by_type
            
            # Playwright style: page.locator()
            playwright_locators = re.findall(
                r'(?:locator|get_by_\w+)\(["\']([^"\']+)["\']\)',
                content
            )
            for i, loc in enumerate(playwright_locators):
                locators[f"locator_{i}"] = loc
            
            # Extract methods
            methods = re.findall(r'def\s+(\w+)\s*\(', content)
            
            # Detect framework
            framework = "selenium"
            if "playwright" in content.lower() or "page.locator" in content:
                framework = "playwright"
            elif "cypress" in content.lower():
                framework = "cypress"
            
            return PageObject(
                name=class_name,
                file_path=file_path,
                locators=locators,
                methods=methods,
                framework=framework,
            )
        
        except Exception:
            return None
    
    def find_relevant_page_objects(
        self, test_intent: TestIntent
    ) -> List[PageObject]:
        """
        Find page objects relevant to test intent.
        
        Args:
            test_intent: Test intent to match
        
        Returns:
            List of relevant page objects
        """
        page_objects = self.detect_page_objects()
        relevant = []
        
        # Match by target name
        if test_intent.target:
            target_lower = test_intent.target.lower()
            
            for po in page_objects:
                # Check class name similarity
                if target_lower in po.name.lower():
                    relevant.append(po)
                    continue
                
                # Check if target matches any locator or method
                for loc_name in po.locators:
                    if target_lower in loc_name.lower():
                        relevant.append(po)
                        break
                else:
                    for method in po.methods:
                        if target_lower in method.lower():
                            relevant.append(po)
                            break
        
        return relevant


class AssertionGenerator:
    """
    Generate intelligent assertions based on context.
    """
    
    def generate_assertions(
        self,
        test_intent: TestIntent,
        page_objects: List[PageObject],
    ) -> List[Assertion]:
        """
        Generate intelligent assertions.
        
        Args:
            test_intent: Test intent
            page_objects: Relevant page objects
        
        Returns:
            List of generated assertions
        """
        assertions = []
        
        # Generate based on action
        if test_intent.action == "verify":
            assertions.extend(self._generate_verify_assertions(test_intent, page_objects))
        elif test_intent.action == "navigate":
            assertions.extend(self._generate_navigation_assertions(test_intent))
        elif test_intent.action == "click":
            assertions.extend(self._generate_click_assertions(test_intent, page_objects))
        elif test_intent.action == "input":
            assertions.extend(self._generate_input_assertions(test_intent, page_objects))
        
        # Always add assertions for expected outcome
        if test_intent.expected_outcome:
            assertions.extend(
                self._generate_outcome_assertions(test_intent, page_objects)
            )
        
        return assertions
    
    def _generate_verify_assertions(
        self, intent: TestIntent, page_objects: List[PageObject]
    ) -> List[Assertion]:
        """Generate verification assertions."""
        assertions = []
        
        if intent.target and page_objects:
            # Find matching element
            po = page_objects[0]
            
            if po.framework == "selenium":
                code = f"assert element.is_displayed()"
                assertions.append(
                    Assertion(
                        assertion_type="visible",
                        target=intent.target,
                        code_snippet=code,
                        confidence=0.9,
                    )
                )
            elif po.framework == "playwright":
                code = f"await expect(page.locator('{intent.target}')).to_be_visible()"
                assertions.append(
                    Assertion(
                        assertion_type="visible",
                        target=intent.target,
                        code_snippet=code,
                        confidence=0.9,
                    )
                )
        
        return assertions
    
    def _generate_navigation_assertions(self, intent: TestIntent) -> List[Assertion]:
        """Generate navigation assertions."""
        assertions = []
        
        if intent.target:
            code = f"assert '{intent.target}' in driver.current_url"
            assertions.append(
                Assertion(
                    assertion_type="url_contains",
                    target=intent.target,
                    code_snippet=code,
                    confidence=0.8,
                )
            )
        
        return assertions
    
    def _generate_click_assertions(
        self, intent: TestIntent, page_objects: List[PageObject]
    ) -> List[Assertion]:
        """Generate click-related assertions."""
        # Usually click actions don't need assertions unless outcome specified
        return []
    
    def _generate_input_assertions(
        self, intent: TestIntent, page_objects: List[PageObject]
    ) -> List[Assertion]:
        """Generate input-related assertions."""
        assertions = []
        
        if intent.data:
            for key, value in intent.data.items():
                code = f"assert element.get_attribute('value') == '{value}'"
                assertions.append(
                    Assertion(
                        assertion_type="equals",
                        target=key,
                        expected_value=value,
                        code_snippet=code,
                        confidence=0.85,
                    )
                )
        
        return assertions
    
    def _generate_outcome_assertions(
        self, intent: TestIntent, page_objects: List[PageObject]
    ) -> List[Assertion]:
        """Generate assertions for expected outcomes."""
        assertions = []
        outcome = intent.expected_outcome.lower()
        
        # Common outcome patterns
        if "success" in outcome or "successfully" in outcome:
            code = "assert success_message.is_displayed()"
            assertions.append(
                Assertion(
                    assertion_type="success_message",
                    target="success message",
                    code_snippet=code,
                    confidence=0.75,
                )
            )
        
        if "error" in outcome or "fail" in outcome:
            code = "assert error_message.is_displayed()"
            assertions.append(
                Assertion(
                    assertion_type="error_message",
                    target="error message",
                    code_snippet=code,
                    confidence=0.75,
                )
            )
        
        return assertions


class AITestGenerationService:
    """
    Main AI-powered test generation service.
    
    Orchestrates all components to provide intelligent test generation.
    """
    
    def __init__(
        self,
        orchestrator: AIOrchestrator,
        project_root: Optional[Path] = None,
    ):
        """
        Initialize service.
        
        Args:
            orchestrator: AI orchestrator for LLM access
            project_root: Project root for page object detection
        """
        self.orchestrator = orchestrator
        self.project_root = project_root or Path.cwd()
        
        # Initialize components
        self.nl_parser = NaturalLanguageParser()
        self.po_detector = PageObjectDetector(self.project_root)
        self.assertion_generator = AssertionGenerator()
    
    def generate_from_natural_language(
        self,
        natural_language: str,
        framework: str = "pytest",
        language: str = "python",
        context: Optional[AIExecutionContext] = None,
    ) -> TestGenerationResult:
        """
        Generate test from natural language description.
        
        Args:
            natural_language: Natural language test description
            framework: Target test framework
            language: Programming language
            context: AI execution context
        
        Returns:
            Generated test result
        """
        # 1. Parse natural language into intents
        intents = self.nl_parser.parse(natural_language)
        
        # 2. Detect relevant page objects
        all_page_objects = self.po_detector.detect_page_objects()
        relevant_pos = []
        for intent in intents:
            relevant_pos.extend(
                self.po_detector.find_relevant_page_objects(intent)
            )
        
        # Deduplicate
        relevant_pos = list({po.name: po for po in relevant_pos}.values())
        
        # 3. Generate assertions
        all_assertions = []
        for intent in intents:
            assertions = self.assertion_generator.generate_assertions(
                intent, relevant_pos
            )
            all_assertions.extend(assertions)
        
        # 4. Build context for AI generation
        ai_context = self._build_ai_context(
            natural_language=natural_language,
            intents=intents,
            page_objects=relevant_pos,
            assertions=all_assertions,
        )
        
        # 5. Use AI to generate complete test
        if context is None:
            context = AIExecutionContext(
                task_type=TaskType.TEST_GENERATION,
                allow_external_ai=True,
            )
        
        skill = TestGenerator()
        result = self.orchestrator.execute_skill(
            skill=skill,
            inputs={
                "source_file": "user_intent.txt",
                "source_code": ai_context,
                "language": language,
                "test_framework": framework,
                "existing_tests": "",
                "coverage_gaps": "Generated from natural language intent",
            },
            context=context,
        )
        
        # 6. Parse and enhance result
        test_code = result.get("test_code", "")
        
        # Extract imports
        imports = self._extract_imports(test_code)
        
        # Extract setup/teardown
        setup, teardown = self._extract_setup_teardown(test_code)
        
        # Generate test name from first intent
        test_name = self._generate_test_name(intents[0] if intents else None)
        
        return TestGenerationResult(
            test_code=test_code,
            test_name=test_name,
            framework=framework,
            assertions=all_assertions,
            page_objects_used=[po.name for po in relevant_pos],
            setup_code=setup,
            teardown_code=teardown,
            imports=imports,
            confidence=0.85,
            suggestions=self._generate_suggestions(intents, relevant_pos),
        )
    
    def enhance_existing_test(
        self,
        existing_test: str,
        enhancement_request: str,
        context: Optional[AIExecutionContext] = None,
    ) -> str:
        """
        Enhance an existing test with AI suggestions.
        
        Args:
            existing_test: Existing test code
            enhancement_request: What to enhance
            context: AI execution context
        
        Returns:
            Enhanced test code
        """
        # Parse enhancement request
        intents = self.nl_parser.parse(enhancement_request)
        
        # Generate additional assertions
        assertions = []
        for intent in intents:
            assertions.extend(
                self.assertion_generator.generate_assertions(intent, [])
            )
        
        # Build enhancement prompt
        enhancement_prompt = f"""
Existing Test:
{existing_test}

Enhancement Request:
{enhancement_request}

Suggested Assertions:
{self._format_assertions(assertions)}

Please enhance the test by:
1. Adding the requested functionality
2. Incorporating the suggested assertions
3. Maintaining code quality and readability
"""
        
        if context is None:
            context = AIExecutionContext(
                task_type=TaskType.TEST_GENERATION,
                allow_external_ai=True,
            )
        
        skill = TestGenerator()
        result = self.orchestrator.execute_skill(
            skill=skill,
            inputs={
                "source_file": "existing_test.py",
                "source_code": enhancement_prompt,
                "language": "python",
                "test_framework": "pytest",
                "existing_tests": existing_test,
            },
            context=context,
        )
        
        return result.get("test_code", existing_test)
    
    def _build_ai_context(
        self,
        natural_language: str,
        intents: List[TestIntent],
        page_objects: List[PageObject],
        assertions: List[Assertion],
    ) -> str:
        """Build comprehensive context for AI generation."""
        context_parts = []
        
        # Natural language description
        context_parts.append(f"Test Description:\n{natural_language}\n")
        
        # Parsed intents
        if intents:
            context_parts.append("\nParsed Test Steps:")
            for i, intent in enumerate(intents, 1):
                context_parts.append(
                    f"{i}. {intent.action.upper()}: {intent.target or intent.context}"
                )
                if intent.expected_outcome:
                    context_parts.append(f"   Expected: {intent.expected_outcome}")
        
        # Available page objects
        if page_objects:
            context_parts.append("\n\nAvailable Page Objects:")
            for po in page_objects:
                context_parts.append(f"- {po.name} ({po.framework})")
                if po.methods:
                    context_parts.append(f"  Methods: {', '.join(po.methods[:5])}")
        
        # Suggested assertions
        if assertions:
            context_parts.append("\n\nSuggested Assertions:")
            for assertion in assertions:
                context_parts.append(f"- {assertion.code_snippet}")
        
        return "\n".join(context_parts)
    
    def _extract_imports(self, test_code: str) -> List[str]:
        """Extract import statements from generated code."""
        imports = []
        for line in test_code.split("\n"):
            if line.strip().startswith(("import ", "from ")):
                imports.append(line.strip())
        return imports
    
    def _extract_setup_teardown(self, test_code: str) -> Tuple[str, str]:
        """Extract setup and teardown code."""
        setup = ""
        teardown = ""
        
        # Look for pytest fixtures or unittest setUp/tearDown
        setup_match = re.search(
            r'@pytest\.fixture.*?\ndef\s+\w+.*?(?=\ndef|\Z)',
            test_code,
            re.DOTALL
        )
        if setup_match:
            setup = setup_match.group(0)
        
        teardown_match = re.search(
            r'def\s+teardown.*?(?=\ndef|\Z)',
            test_code,
            re.DOTALL
        )
        if teardown_match:
            teardown = teardown_match.group(0)
        
        return setup, teardown
    
    def _generate_test_name(self, intent: Optional[TestIntent]) -> str:
        """Generate a test name from intent."""
        if not intent:
            return "test_generated"
        
        # Convert to snake_case test name
        name_parts = ["test"]
        
        if intent.action:
            name_parts.append(intent.action)
        
        if intent.target:
            # Clean and convert target
            target_clean = re.sub(r'[^\w\s]', '', intent.target)
            target_snake = target_clean.lower().replace(' ', '_')
            name_parts.append(target_snake)
        
        return "_".join(name_parts)
    
    def _format_assertions(self, assertions: List[Assertion]) -> str:
        """Format assertions for prompt."""
        if not assertions:
            return "No specific assertions suggested"
        
        lines = []
        for assertion in assertions:
            lines.append(f"- {assertion.code_snippet}")
        
        return "\n".join(lines)
    
    def _generate_suggestions(
        self, intents: List[TestIntent], page_objects: List[PageObject]
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        if not page_objects:
            suggestions.append(
                "Consider creating page objects for better test maintainability"
            )
        
        if len(intents) > 5:
            suggestions.append(
                "Test has many steps - consider splitting into multiple tests"
            )
        
        # Check for missing assertions
        has_assertions = any(
            intent.expected_outcome for intent in intents
        )
        if not has_assertions:
            suggestions.append(
                "Add assertions to verify expected outcomes"
            )
        
        return suggestions
