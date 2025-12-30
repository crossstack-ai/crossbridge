"""
Neutral domain models for Cucumber BDD test results.

These models provide a framework-agnostic representation of test execution data,
independent of the underlying Cucumber implementation (JVM, JS, etc.).
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StepResult:
    """Represents the result of a single test step execution."""
    
    name: str
    status: str  # passed | failed | skipped | pending | undefined
    duration_ns: int
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate step status."""
        valid_statuses = {"passed", "failed", "skipped", "pending", "undefined"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid step status: {self.status}. Must be one of {valid_statuses}")


@dataclass
class ScenarioResult:
    """Represents the result of a scenario execution."""
    
    feature: str
    scenario: str
    scenario_type: str  # scenario | scenario_outline
    tags: List[str]
    steps: List[StepResult]
    status: str  # passed | failed | skipped
    uri: str
    line: int
    
    def __post_init__(self):
        """Validate scenario type and status."""
        valid_types = {"scenario", "scenario_outline", "background"}
        if self.scenario_type not in valid_types:
            raise ValueError(f"Invalid scenario type: {self.scenario_type}")
        
        valid_statuses = {"passed", "failed", "skipped"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid scenario status: {self.status}")
    
    @property
    def total_duration_ns(self) -> int:
        """Calculate total duration of all steps."""
        return sum(step.duration_ns for step in self.steps)
    
    @property
    def failed_steps(self) -> List[StepResult]:
        """Return list of failed steps."""
        return [step for step in self.steps if step.status == "failed"]


@dataclass
class FeatureResult:
    """Represents the result of a feature file execution."""
    
    name: str
    uri: str
    scenarios: List[ScenarioResult] = field(default_factory=list)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    @property
    def total_scenarios(self) -> int:
        """Total number of scenarios in this feature."""
        return len(self.scenarios)
    
    @property
    def passed_scenarios(self) -> int:
        """Number of passed scenarios."""
        return sum(1 for s in self.scenarios if s.status == "passed")
    
    @property
    def failed_scenarios(self) -> int:
        """Number of failed scenarios."""
        return sum(1 for s in self.scenarios if s.status == "failed")
    
    @property
    def skipped_scenarios(self) -> int:
        """Number of skipped scenarios."""
        return sum(1 for s in self.scenarios if s.status == "skipped")
    
    @property
    def overall_status(self) -> str:
        """Overall feature status based on scenario results."""
        if self.failed_scenarios > 0:
            return "failed"
        elif self.skipped_scenarios == self.total_scenarios:
            return "skipped"
        elif self.passed_scenarios == self.total_scenarios:
            return "passed"
        else:
            return "partial"
