"""
Canonical BDD Domain Models.

Framework-agnostic models representing BDD concepts (Features, Scenarios, Steps).
All BDD adapters (Cucumber, Robot, JBehave, etc.) must normalize to these models.

Design principles:
- Framework-neutral: No framework-specific fields leak into models
- Deterministic: Same input always produces same output
- Normalizable: All BDD frameworks can map to these structures
- Database-ready: Clean models for persistence
- Embedding-compatible: Suitable for vector embeddings
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class StepKeyword(str, Enum):
    """Standard Gherkin step keywords."""
    GIVEN = "Given"
    WHEN = "When"
    THEN = "Then"
    AND = "And"
    BUT = "But"
    ASTERISK = "*"  # Generic step keyword


class ScenarioType(str, Enum):
    """Scenario types in BDD."""
    SCENARIO = "scenario"
    SCENARIO_OUTLINE = "scenario_outline"
    BACKGROUND = "background"


@dataclass
class BDDStep:
    """
    Individual BDD step (Given/When/Then/And/But).
    
    Example:
        Given user is logged in
        When user clicks submit button
        Then dashboard is displayed
    """
    keyword: StepKeyword
    text: str
    line: int
    doc_string: Optional[str] = None  # Triple-quoted text block
    data_table: Optional[List[Dict[str, str]]] = None  # Table arguments
    
    # For step definition mapping
    matched_implementation: Optional[str] = None  # Java method name, Python function
    file_path: Optional[str] = None  # Step definition file
    line_number: Optional[int] = None  # Line in step definition file
    
    @property
    def full_text(self) -> str:
        """Full step text with keyword."""
        return f"{self.keyword.value} {self.text}"


@dataclass
class BDDExampleRow:
    """Example row for Scenario Outline."""
    line: int
    cells: Dict[str, str]  # Column name -> value


@dataclass
class BDDBackground:
    """Background steps that run before each scenario."""
    name: str
    steps: List[BDDStep] = field(default_factory=list)
    line: int = 0


@dataclass
class BDDScenario:
    """
    BDD Scenario (single test case).
    
    Canonical internal model - MUST NOT leak framework specifics.
    All BDD adapters (Cucumber, Robot, JBehave) normalize to this.
    """
    id: str  # Unique identifier
    name: str
    feature: str  # Parent feature name
    steps: List[BDDStep] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    line: int = 0
    description: Optional[str] = None
    
    # Framework identification (for adapter routing)
    framework: str = "cucumber"  # cucumber, robot-bdd, jbehave, specflow, behave
    
    # Metadata
    file_path: Optional[str] = None
    duration_ms: Optional[int] = None
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            # Format: feature_name::scenario_name
            safe_feature = self.feature.replace(" ", "_").replace("::", "_")
            safe_scenario = self.name.replace(" ", "_").replace("::", "_")
            self.id = f"{safe_feature}::{safe_scenario}"


@dataclass
class BDDScenarioOutline:
    """
    Scenario Outline (parameterized scenario).
    
    One outline can generate multiple scenario instances via Examples.
    """
    id: str
    name: str
    feature: str
    steps: List[BDDStep] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    examples: List[BDDExampleRow] = field(default_factory=list)
    line: int = 0
    description: Optional[str] = None
    
    framework: str = "cucumber"
    file_path: Optional[str] = None
    
    def expand_scenarios(self) -> List[BDDScenario]:
        """Expand scenario outline into concrete scenarios using examples."""
        scenarios = []
        
        for idx, example in enumerate(self.examples):
            # Substitute placeholders in steps
            expanded_steps = []
            for step in self.steps:
                text = step.text
                for param, value in example.cells.items():
                    text = text.replace(f"<{param}>", value)
                
                expanded_steps.append(BDDStep(
                    keyword=step.keyword,
                    text=text,
                    line=step.line,
                    doc_string=step.doc_string,
                    data_table=step.data_table
                ))
            
            # Create scenario instance
            scenario_id = f"{self.id}_example_{idx+1}"
            scenario = BDDScenario(
                id=scenario_id,
                name=f"{self.name} (Example {idx+1})",
                feature=self.feature,
                steps=expanded_steps,
                tags=self.tags.copy(),
                line=example.line,
                framework=self.framework,
                file_path=self.file_path
            )
            scenarios.append(scenario)
        
        return scenarios


@dataclass
class BDDFeature:
    """
    BDD Feature (collection of scenarios).
    
    Represents a .feature file or equivalent.
    """
    name: str
    description: Optional[str] = None
    scenarios: List[BDDScenario] = field(default_factory=list)
    scenario_outlines: List[BDDScenarioOutline] = field(default_factory=list)
    background: Optional[BDDBackground] = None
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    
    # File metadata
    file_path: Optional[str] = None
    uri: Optional[str] = None  # Relative path (Cucumber format)
    
    # Framework identification
    framework: str = "cucumber"
    
    def all_scenarios(self) -> List[BDDScenario]:
        """Get all concrete scenarios (including expanded outlines)."""
        scenarios = self.scenarios.copy()
        
        # Expand scenario outlines
        for outline in self.scenario_outlines:
            scenarios.extend(outline.expand_scenarios())
        
        return scenarios
    
    @property
    def total_scenarios(self) -> int:
        """Total number of concrete scenarios."""
        return len(self.all_scenarios())


@dataclass
class BDDFailure:
    """Failure information for a failed scenario."""
    scenario_id: str
    step_index: int  # Which step failed (0-based)
    error_type: str  # AssertionError, TimeoutException, etc.
    error_message: str
    stacktrace: Optional[str] = None
    screenshot_path: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class BDDExecutionResult:
    """
    Execution result for a BDD scenario.
    
    Normalized from Cucumber JSON, Robot XML, JBehave reports, etc.
    """
    scenario_id: str
    feature_name: str
    scenario_name: str
    status: str  # passed, failed, skipped, pending
    duration_ns: int  # Nanoseconds (Cucumber standard)
    tags: List[str] = field(default_factory=list)
    
    # Step-level results
    steps_passed: int = 0
    steps_failed: int = 0
    steps_skipped: int = 0
    
    # Failure information (if failed)
    failure: Optional[BDDFailure] = None
    
    # Execution metadata
    timestamp: Optional[datetime] = None
    environment: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration_ns / 1_000_000
    
    @property
    def passed(self) -> bool:
        """Whether scenario passed."""
        return self.status == "passed"


# Adapter completeness checklist (used for validation)
ADAPTER_COMPLETENESS_CRITERIA = {
    "discovery": "Can discover .feature files or equivalent",
    "feature_parsing": "Can parse feature files and extract feature names",
    "scenario_extraction": "Can extract scenarios and scenario outlines",
    "step_extraction": "Can extract steps with keywords (Given/When/Then)",
    "tag_extraction": "Can extract tags from features and scenarios",
    "step_definition_mapping": "Can map steps to implementation code",
    "execution_parsing": "Can parse execution results (JSON/XML reports)",
    "failure_mapping": "Can link failures to specific scenarios and steps",
    "embedding_compatibility": "Scenarios can be converted to embeddings",
    "graph_compatibility": "Can build graph relationships (feature->scenario->step)",
}


def validate_adapter_completeness(adapter_capabilities: Dict[str, bool]) -> tuple[bool, List[str]]:
    """
    Validate if a BDD adapter meets completeness criteria.
    
    Args:
        adapter_capabilities: Dict of capability name -> implemented (bool)
    
    Returns:
        Tuple of (is_complete, missing_capabilities)
    """
    missing = []
    for capability, description in ADAPTER_COMPLETENESS_CRITERIA.items():
        if not adapter_capabilities.get(capability, False):
            missing.append(f"{capability}: {description}")
    
    is_complete = len(missing) == 0
    return is_complete, missing
