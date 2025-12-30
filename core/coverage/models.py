"""
Coverage Mapping Models for CrossBridge.

Maps tests/scenarios/steps to production code paths using coverage data.
Enables:
- Precise change-impact analysis
- Coverage-weighted flaky detection
- AI-assisted test selection
- BI & reporting

Supports:
- JaCoCo (Java/Selenium)
- Cucumber JVM (BDD scenarios)
- coverage.py (Pytest) - Phase-2
- Robot Framework - Phase-2
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set
from datetime import datetime
from enum import Enum


class CoverageType(str, Enum):
    """Type of coverage measurement."""
    INSTRUCTION = "instruction"  # JaCoCo instruction coverage
    LINE = "line"                # Line coverage
    BRANCH = "branch"            # Branch/condition coverage
    METHOD = "method"            # Method-level coverage


class CoverageSource(str, Enum):
    """Source tool that produced coverage data."""
    JACOCO = "jacoco"            # Java/Selenium (JaCoCo)
    COVERAGE_PY = "coverage.py"  # Python (coverage.py)
    ISTANBUL = "istanbul"        # JavaScript (Istanbul)
    ROBOT_TRACE = "robot_trace"  # Robot Framework tracing


class ExecutionMode(str, Enum):
    """How coverage was collected."""
    ISOLATED = "isolated"        # Single test in isolation
    SMALL_BATCH = "small_batch"  # Small batch of tests
    FULL_SUITE = "full_suite"    # Entire test suite


@dataclass
class CoveredCodeUnit:
    """
    Represents a covered code unit (class, method, function, etc.).
    
    Framework-agnostic model for code coverage.
    """
    
    # Code location
    class_name: str                     # Fully qualified class/module name
    method_name: Optional[str] = None   # Method/function name (if applicable)
    file_path: Optional[str] = None     # Source file path
    
    # Coverage details
    line_numbers: List[int] = field(default_factory=list)  # Covered lines
    covered_branches: int = 0           # Number of covered branches
    total_branches: int = 0             # Total branches
    
    # Metrics
    instruction_coverage: Optional[float] = None  # JaCoCo instruction coverage
    line_coverage: Optional[float] = None         # Line coverage percentage
    branch_coverage: Optional[float] = None       # Branch coverage percentage
    
    def __hash__(self):
        """Allow use in sets."""
        return hash((self.class_name, self.method_name))
    
    def __eq__(self, other):
        """Equality based on class and method."""
        if not isinstance(other, CoveredCodeUnit):
            return False
        return (self.class_name == other.class_name and 
                self.method_name == other.method_name)


@dataclass
class TestCoverageMapping:
    """
    Maps a test/scenario to the production code it covers.
    
    This is the core model for coverage-driven impact analysis.
    """
    
    # Test identification
    test_id: str                        # Stable test identifier
    test_name: Optional[str] = None     # Human-readable name
    test_framework: str = "unknown"     # junit | cucumber | pytest | robot
    
    # Coverage data
    covered_classes: Set[str] = field(default_factory=set)    # Class names
    covered_methods: Set[str] = field(default_factory=set)    # Method signatures
    covered_code_units: List[CoveredCodeUnit] = field(default_factory=list)
    
    # Metadata
    coverage_type: CoverageType = CoverageType.INSTRUCTION
    coverage_source: CoverageSource = CoverageSource.JACOCO
    execution_mode: ExecutionMode = ExecutionMode.ISOLATED
    
    # Confidence & quality
    confidence: float = 1.0             # Confidence in mapping (0-1)
    execution_time: datetime = field(default_factory=datetime.now)
    discovery_run_id: Optional[str] = None  # Batch/run identifier
    
    # Git context
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    
    def get_unique_classes(self) -> Set[str]:
        """Get set of unique class names."""
        return self.covered_classes
    
    def get_unique_methods(self) -> Set[str]:
        """Get set of unique method signatures."""
        return self.covered_methods
    
    def total_covered_units(self) -> int:
        """Total number of covered code units."""
        return len(self.covered_code_units)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "test_framework": self.test_framework,
            "covered_classes": list(self.covered_classes),
            "covered_methods": list(self.covered_methods),
            "coverage_type": self.coverage_type.value,
            "coverage_source": self.coverage_source.value,
            "execution_mode": self.execution_mode.value,
            "confidence": self.confidence,
            "total_units": self.total_covered_units(),
            "execution_time": self.execution_time.isoformat(),
            "git_commit": self.git_commit,
        }


@dataclass
class ScenarioCoverageMapping:
    """
    Coverage mapping for BDD scenarios (aggregated from steps).
    
    Cucumber/BDD scenarios execute multiple steps, each with coverage.
    This aggregates step coverage into scenario-level coverage.
    """
    
    # Scenario identification
    scenario_id: str
    scenario_name: str
    feature_name: Optional[str] = None
    feature_file: Optional[str] = None
    
    # Step coverage (constituent parts)
    step_coverage_mappings: List[TestCoverageMapping] = field(default_factory=list)
    
    # Aggregated coverage (union of all steps)
    aggregated_classes: Set[str] = field(default_factory=set)
    aggregated_methods: Set[str] = field(default_factory=set)
    aggregated_code_units: List[CoveredCodeUnit] = field(default_factory=list)
    
    # Metadata
    coverage_source: CoverageSource = CoverageSource.JACOCO
    confidence: float = 1.0
    execution_time: datetime = field(default_factory=datetime.now)
    discovery_run_id: Optional[str] = None
    git_commit: Optional[str] = None
    
    def aggregate_coverage(self):
        """
        Aggregate coverage from all steps.
        
        Scenario coverage = union of all step coverages.
        """
        self.aggregated_classes.clear()
        self.aggregated_methods.clear()
        self.aggregated_code_units.clear()
        
        seen_units = set()
        
        for step_mapping in self.step_coverage_mappings:
            # Aggregate classes
            self.aggregated_classes.update(step_mapping.covered_classes)
            
            # Aggregate methods
            self.aggregated_methods.update(step_mapping.covered_methods)
            
            # Aggregate code units (avoid duplicates)
            for unit in step_mapping.covered_code_units:
                unit_key = (unit.class_name, unit.method_name)
                if unit_key not in seen_units:
                    self.aggregated_code_units.append(unit)
                    seen_units.add(unit_key)
        
        # Confidence is minimum of step confidences
        if self.step_coverage_mappings:
            self.confidence = min(m.confidence for m in self.step_coverage_mappings)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "feature_name": self.feature_name,
            "covered_classes": list(self.aggregated_classes),
            "covered_methods": list(self.aggregated_methods),
            "total_steps": len(self.step_coverage_mappings),
            "total_units": len(self.aggregated_code_units),
            "confidence": self.confidence,
            "execution_time": self.execution_time.isoformat(),
        }


@dataclass
class CoverageConfidenceCalculator:
    """
    Calculate confidence scores for coverage mappings.
    
    Confidence depends on:
    - Execution mode (isolated > batch > suite)
    - Data quality (has source paths, etc.)
    - Temporal freshness
    """
    
    # Confidence by execution mode
    ISOLATED_CONFIDENCE = 0.95      # Single test isolation
    SMALL_BATCH_CONFIDENCE = 0.75   # Small batch (2-10 tests)
    FULL_SUITE_CONFIDENCE = 0.50    # Full suite (shared coverage)
    
    # Quality multipliers
    HAS_SOURCE_PATHS = 1.0          # Source file paths available
    NO_SOURCE_PATHS = 0.9           # Missing source paths
    
    @classmethod
    def calculate(
        cls,
        execution_mode: ExecutionMode,
        has_source_paths: bool = True,
        batch_size: int = 1
    ) -> float:
        """
        Calculate confidence score for coverage mapping.
        
        Args:
            execution_mode: How coverage was collected
            has_source_paths: Whether source paths are available
            batch_size: Number of tests in batch (for correlation)
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence from execution mode
        if execution_mode == ExecutionMode.ISOLATED:
            base_confidence = cls.ISOLATED_CONFIDENCE
        elif execution_mode == ExecutionMode.SMALL_BATCH:
            base_confidence = cls.SMALL_BATCH_CONFIDENCE
            # Reduce confidence based on batch size
            if batch_size > 1:
                batch_penalty = min(0.2, (batch_size - 1) * 0.03)
                base_confidence -= batch_penalty
        else:
            base_confidence = cls.FULL_SUITE_CONFIDENCE
        
        # Apply quality multiplier
        quality_multiplier = cls.HAS_SOURCE_PATHS if has_source_paths else cls.NO_SOURCE_PATHS
        
        return min(1.0, base_confidence * quality_multiplier)


@dataclass
class CoverageImpactQuery:
    """
    Query model for coverage-driven impact analysis.
    
    Given changed files/classes, find affected tests.
    """
    
    # Changed code
    changed_classes: Set[str] = field(default_factory=set)
    changed_methods: Set[str] = field(default_factory=set)
    changed_files: Set[str] = field(default_factory=set)
    
    # Query filters
    min_confidence: float = 0.7
    framework_filter: Optional[str] = None
    git_commit: Optional[str] = None
    
    # Results
    affected_tests: List[str] = field(default_factory=list)
    confidence_scores: dict = field(default_factory=dict)  # test_id -> confidence
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "changed_classes": list(self.changed_classes),
            "changed_methods": list(self.changed_methods),
            "changed_files": list(self.changed_files),
            "min_confidence": self.min_confidence,
            "affected_tests": self.affected_tests,
            "average_confidence": (
                sum(self.confidence_scores.values()) / len(self.confidence_scores)
                if self.confidence_scores else 0.0
            )
        }
