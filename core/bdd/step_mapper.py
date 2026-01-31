"""
BDD Step Definition Mapper.

Maps BDD steps (from scenarios) to their implementations (step definitions).
This is the CRITICAL component that determines adapter stability.

Supports:
- Regex pattern matching (Cucumber-style)
- String matching (exact or fuzzy)
- Parameter extraction from steps
- Multi-framework mapping
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Pattern
from pathlib import Path

from .models import BDDStep, StepKeyword


@dataclass
class StepDefinitionMatch:
    """Result of matching a step to its definition."""
    step_text: str
    definition_pattern: str
    method_name: str
    file_path: str
    line_number: int
    parameters: Dict[str, str]  # Extracted parameter values
    confidence: float  # Match confidence (0.0 - 1.0)
    
    @property
    def is_exact_match(self) -> bool:
        """Whether this is an exact match (confidence = 1.0)."""
        return self.confidence >= 0.99


class StepDefinitionMapper:
    """
    Maps BDD steps to their implementation code.
    
    Handles:
    - Regex patterns from @Given/@When/@Then annotations
    - Parameter extraction
    - Fuzzy matching for close matches
    - Multiple pattern formats (Java regex, Python regex, Robot keywords)
    """
    
    def __init__(self):
        self.definitions: List[Dict[str, Any]] = []
        self.compiled_patterns: Dict[str, Pattern] = {}
    
    def add_definition(
        self,
        pattern: str,
        method_name: str,
        file_path: str,
        line_number: int,
        keyword: Optional[StepKeyword] = None,
        framework: str = "cucumber"
    ):
        """
        Register a step definition.
        
        Args:
            pattern: Regex pattern or string pattern
            method_name: Name of implementation method/function
            file_path: Path to definition file
            line_number: Line number in file
            keyword: Optional keyword restriction (Given/When/Then)
            framework: Framework type (cucumber, robot, jbehave)
        """
        definition = {
            "pattern": pattern,
            "method_name": method_name,
            "file_path": file_path,
            "line_number": line_number,
            "keyword": keyword,
            "framework": framework
        }
        self.definitions.append(definition)
        
        # Pre-compile regex patterns
        try:
            if self._is_regex_pattern(pattern):
                self.compiled_patterns[pattern] = re.compile(pattern)
        except re.error:
            # Invalid regex, skip compilation
            pass
    
    def match_step(self, step: BDDStep) -> Optional[StepDefinitionMatch]:
        """
        Find the best matching step definition for a step.
        
        Args:
            step: BDD step from scenario
        
        Returns:
            Best match, or None if no match found
        """
        matches: List[StepDefinitionMatch] = []
        
        for definition in self.definitions:
            match = self._try_match_definition(step, definition)
            if match:
                matches.append(match)
        
        if not matches:
            return None
        
        # Return best match (highest confidence)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches[0]
    
    def match_all_steps(self, steps: List[BDDStep]) -> Dict[str, Optional[StepDefinitionMatch]]:
        """
        Match multiple steps to definitions.
        
        Args:
            steps: List of steps to match
        
        Returns:
            Dict mapping step.full_text -> match (or None)
        """
        matches = {}
        for step in steps:
            matches[step.full_text] = self.match_step(step)
        return matches
    
    def get_unmapped_steps(self, steps: List[BDDStep]) -> List[BDDStep]:
        """
        Find steps that don't have matching definitions.
        
        Args:
            steps: Steps to check
        
        Returns:
            List of steps without matches
        """
        unmapped = []
        for step in steps:
            if self.match_step(step) is None:
                unmapped.append(step)
        return unmapped
    
    def _try_match_definition(
        self,
        step: BDDStep,
        definition: Dict[str, Any]
    ) -> Optional[StepDefinitionMatch]:
        """Try to match step against a definition."""
        pattern = definition["pattern"]
        
        # Check keyword compatibility if specified
        if definition.get("keyword") and definition["keyword"] != step.keyword:
            return None
        
        # Try regex match first
        if self._is_regex_pattern(pattern):
            return self._match_regex(step, definition, pattern)
        
        # Try exact string match
        if step.text.strip() == pattern.strip():
            return StepDefinitionMatch(
                step_text=step.full_text,
                definition_pattern=pattern,
                method_name=definition["method_name"],
                file_path=definition["file_path"],
                line_number=definition["line_number"],
                parameters={},
                confidence=1.0
            )
        
        # Try fuzzy match (for Robot keywords)
        return self._match_fuzzy(step, definition, pattern)
    
    def _match_regex(
        self,
        step: BDDStep,
        definition: Dict[str, Any],
        pattern: str
    ) -> Optional[StepDefinitionMatch]:
        """Match step using regex pattern."""
        compiled = self.compiled_patterns.get(pattern)
        if not compiled:
            return None
        
        match = compiled.match(step.text.strip())
        if not match:
            return None
        
        # Extract parameters from regex groups
        parameters = {}
        for i, group in enumerate(match.groups(), start=1):
            parameters[f"param{i}"] = group
        
        return StepDefinitionMatch(
            step_text=step.full_text,
            definition_pattern=pattern,
            method_name=definition["method_name"],
            file_path=definition["file_path"],
            line_number=definition["line_number"],
            parameters=parameters,
            confidence=1.0
        )
    
    def _match_fuzzy(
        self,
        step: BDDStep,
        definition: Dict[str, Any],
        pattern: str
    ) -> Optional[StepDefinitionMatch]:
        """
        Fuzzy match for Robot Framework keywords.
        
        Robot allows underscores, spaces, and case variations.
        """
        step_normalized = step.text.strip().lower().replace(" ", "").replace("_", "")
        pattern_normalized = pattern.strip().lower().replace(" ", "").replace("_", "")
        
        if step_normalized == pattern_normalized:
            return StepDefinitionMatch(
                step_text=step.full_text,
                definition_pattern=pattern,
                method_name=definition["method_name"],
                file_path=definition["file_path"],
                line_number=definition["line_number"],
                parameters={},
                confidence=0.9  # Fuzzy match, slightly lower confidence
            )
        
        return None
    
    def _is_regex_pattern(self, pattern: str) -> bool:
        """Check if pattern is a regex (contains regex metacharacters)."""
        regex_chars = ['(', ')', '[', ']', '{', '}', '^', '$', '.', '*', '+', '?', '|', '\\']
        return any(char in pattern for char in regex_chars)
    
    def get_coverage_statistics(self, steps: List[BDDStep]) -> Dict[str, Any]:
        """
        Analyze step definition coverage.
        
        Args:
            steps: All steps from scenarios
        
        Returns:
            Statistics dict with counts and percentages
        """
        total = len(steps)
        if total == 0:
            return {
                "total_steps": 0,
                "mapped_steps": 0,
                "unmapped_steps": 0,
                "coverage_percent": 0.0
            }
        
        unmapped = self.get_unmapped_steps(steps)
        mapped = total - len(unmapped)
        
        return {
            "total_steps": total,
            "mapped_steps": mapped,
            "unmapped_steps": len(unmapped),
            "coverage_percent": (mapped / total) * 100,
            "unmapped_step_list": [step.full_text for step in unmapped]
        }


def resolve_step_to_implementation(
    step: BDDStep,
    step_definitions_dir: Path,
    framework: str = "cucumber"
) -> Optional[StepDefinitionMatch]:
    """
    High-level helper to resolve a step to its implementation.
    
    Args:
        step: BDD step to resolve
        step_definitions_dir: Directory containing step definitions
        framework: Framework type (cucumber, robot, jbehave)
    
    Returns:
        Match result, or None
    
    Example:
        >>> step = BDDStep(keyword=StepKeyword.GIVEN, text="user is logged in", line=5)
        >>> match = resolve_step_to_implementation(
        ...     step,
        ...     Path("src/test/java/steps"),
        ...     framework="cucumber"
        ... )
        >>> if match:
        ...     print(f"Implemented in: {match.method_name} at {match.file_path}:{match.line_number}")
    """
    # This would integrate with the framework-specific step definition parser
    # For now, return None as a placeholder
    # In real implementation, this would:
    # 1. Use appropriate parser (JavaParser, ast.parse, Robot API)
    # 2. Extract step definitions from files
    # 3. Build mapper and match
    return None


def build_step_definition_mapper(
    step_definitions: List[Dict[str, Any]]
) -> StepDefinitionMapper:
    """
    Build a mapper from a list of step definitions.
    
    Args:
        step_definitions: List of definition dicts with:
            - pattern: Regex or string pattern
            - method_name: Implementation name
            - file_path: Definition file
            - line_number: Line in file
            - keyword: Optional keyword (Given/When/Then)
    
    Returns:
        Configured mapper ready for matching
    """
    mapper = StepDefinitionMapper()
    
    for definition in step_definitions:
        mapper.add_definition(
            pattern=definition["pattern"],
            method_name=definition["method_name"],
            file_path=definition["file_path"],
            line_number=definition.get("line_number", 0),
            keyword=definition.get("keyword"),
            framework=definition.get("framework", "cucumber")
        )
    
    return mapper
