"""
BDD Parser Interfaces.

Defines contracts that all BDD framework adapters must implement.
This ensures consistency and completeness across Cucumber, Robot, JBehave, etc.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import (
    BDDFeature,
    BDDScenario,
    BDDStep,
    BDDExecutionResult
)


class BDDFeatureParser(ABC):
    """
    Abstract parser for BDD feature files (.feature, .robot, .story).
    
    All BDD adapters MUST implement this interface to parse feature definitions.
    """
    
    @abstractmethod
    def parse_file(self, file_path: Path) -> BDDFeature:
        """
        Parse a single feature file.
        
        Args:
            file_path: Path to .feature/.robot/.story file
        
        Returns:
            BDDFeature with scenarios, steps, tags extracted
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ParseError: If file is malformed
        """
        pass
    
    @abstractmethod
    def parse_content(self, content: str, file_path: Optional[str] = None) -> BDDFeature:
        """
        Parse feature content from string.
        
        Args:
            content: Feature file content
            file_path: Optional file path for metadata
        
        Returns:
            BDDFeature object
        """
        pass
    
    @abstractmethod
    def discover_feature_files(self, directory: Path) -> List[Path]:
        """
        Discover all feature files in directory.
        
        Args:
            directory: Root directory to search
        
        Returns:
            List of paths to feature files
        """
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """File extensions this parser supports (e.g., ['.feature', '.robot'])."""
        pass


class BDDStepDefinitionParser(ABC):
    """
    Abstract parser for step definitions (glue code).
    
    This is CRITICAL for stable adapters - maps scenario steps to implementation.
    """
    
    @abstractmethod
    def discover_step_definitions(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Discover all step definition files and parse them.
        
        Args:
            directory: Root directory containing step definitions
        
        Returns:
            List of step definitions with:
                - pattern: Regex or string pattern
                - method_name: Implementation method/function name
                - file_path: Path to definition file
                - line: Line number
                - annotations: List of annotations/decorators
        """
        pass
    
    @abstractmethod
    def parse_step_definition_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse a single step definition file.
        
        For Java: Extract @Given/@When/@Then annotated methods
        For Python: Extract @given/@when/@then decorated functions
        For Robot: Extract keyword definitions
        
        Args:
            file_path: Path to step definition file
        
        Returns:
            List of step definitions from this file
        """
        pass
    
    @abstractmethod
    def match_step_to_definition(
        self,
        step: BDDStep,
        definitions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Match a scenario step to its implementation.
        
        Args:
            step: BDD step from scenario
            definitions: Available step definitions
        
        Returns:
            Matched definition dict, or None if no match
        """
        pass


class BDDExecutionParser(ABC):
    """
    Abstract parser for BDD execution results.
    
    Normalizes framework-specific report formats (Cucumber JSON, Robot XML, etc.)
    into canonical BDDExecutionResult objects.
    """
    
    @abstractmethod
    def parse_execution_report(self, report_path: Path) -> List[BDDExecutionResult]:
        """
        Parse execution results from report file.
        
        Args:
            report_path: Path to report (cucumber.json, output.xml, etc.)
        
        Returns:
            List of execution results, one per scenario
        
        Raises:
            FileNotFoundError: If report doesn't exist
            ParseError: If report format is invalid
        """
        pass
    
    @abstractmethod
    def parse_execution_data(self, data: Any) -> List[BDDExecutionResult]:
        """
        Parse execution results from in-memory data structure.
        
        Args:
            data: Parsed JSON/XML/dict structure
        
        Returns:
            List of execution results
        """
        pass
    
    @abstractmethod
    def link_failure_to_scenario(
        self,
        execution_result: BDDExecutionResult,
        scenarios: List[BDDScenario]
    ) -> Optional[BDDScenario]:
        """
        Link an execution failure back to its scenario definition.
        
        Args:
            execution_result: Result with failure info
            scenarios: Available scenario definitions
        
        Returns:
            Matched scenario, or None
        """
        pass
    
    @property
    @abstractmethod
    def supported_report_formats(self) -> List[str]:
        """Report file formats this parser supports (e.g., ['json', 'xml'])."""
        pass


class BDDAdapter(ABC):
    """
    Complete BDD adapter interface combining all parsers.
    
    Every BDD framework adapter (Cucumber, Robot, JBehave) must implement this.
    """
    
    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Framework name (e.g., 'cucumber-java', 'robot-bdd', 'jbehave')."""
        pass
    
    @property
    @abstractmethod
    def feature_parser(self) -> BDDFeatureParser:
        """Get feature file parser."""
        pass
    
    @property
    @abstractmethod
    def step_definition_parser(self) -> BDDStepDefinitionParser:
        """Get step definition parser."""
        pass
    
    @property
    @abstractmethod
    def execution_parser(self) -> BDDExecutionParser:
        """Get execution result parser."""
        pass
    
    @abstractmethod
    def validate_completeness(self) -> Dict[str, bool]:
        """
        Validate adapter completeness against required capabilities.
        
        Returns:
            Dict mapping capability names to implementation status
        """
        pass


# Helper function for adapter validation
def is_adapter_stable(adapter: BDDAdapter) -> bool:
    """
    Determine if BDD adapter is stable (production-ready).
    
    An adapter is stable if ALL required capabilities are implemented.
    
    Args:
        adapter: BDD adapter to validate
    
    Returns:
        True if adapter is stable, False if still beta
    """
    from .models import ADAPTER_COMPLETENESS_CRITERIA
    
    capabilities = adapter.validate_completeness()
    
    # Check all required capabilities
    for capability in ADAPTER_COMPLETENESS_CRITERIA.keys():
        if not capabilities.get(capability, False):
            return False
    
    return True
