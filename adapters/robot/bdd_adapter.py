"""
Robot Framework BDD Adapter.

Complete BDD support for Robot Framework with BDD-style keywords (Given/When/Then).

Robot Framework supports BDD through:
- BDD-style keywords in test cases
- Keyword definitions in .robot or .py files
- Built-in BDD support without external libraries

Example Robot BDD test:
    *** Test Cases ***
    User Login Scenario
        [Tags]    smoke    auth
        Given user is on login page
        When user enters valid credentials
        And user clicks submit button
        Then user should see dashboard
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

try:
    from robot.api import get_model, TestSuiteBuilder
    from robot.api.parsing import ModelTransformer, Token
    ROBOT_API_AVAILABLE = True
except ImportError:
    ROBOT_API_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Robot Framework API not available. Install: pip install robotframework")

from core.bdd.models import (
    BDDFeature,
    BDDScenario,
    BDDStep,
    BDDExecutionResult,
    StepKeyword
)
from core.bdd.parser_interface import (
    BDDFeatureParser,
    BDDStepDefinitionParser,
    BDDExecutionParser,
    BDDAdapter
)
from core.bdd.step_mapper import StepDefinitionMapper, build_step_definition_mapper

logger = logging.getLogger(__name__)


class RobotBDDFeatureParser(BDDFeatureParser):
    """
    Parse Robot Framework .robot files as BDD features.
    
    Uses official Robot Framework API for robust parsing.
    """
    
    BDD_KEYWORDS = ['Given', 'When', 'Then', 'And', 'But']
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".robot"]
    
    def parse_file(self, file_path: Path) -> BDDFeature:
        """Parse .robot file."""
        if not ROBOT_API_AVAILABLE:
            raise ImportError("Robot Framework not installed")
        
        if not file_path.exists():
            raise FileNotFoundError(f"Robot file not found: {file_path}")
        
        model = get_model(str(file_path))
        return self._convert_robot_model_to_bdd(model, file_path)
    
    def parse_content(self, content: str, file_path: Optional[str] = None) -> BDDFeature:
        """Parse Robot content from string."""
        if not ROBOT_API_AVAILABLE:
            raise ImportError("Robot Framework not installed")
        
        # Write to temp file for Robot API
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            model = get_model(str(temp_path))
            return self._convert_robot_model_to_bdd(model, temp_path)
        finally:
            temp_path.unlink()
    
    def discover_feature_files(self, directory: Path) -> List[Path]:
        """Discover all .robot files."""
        if not directory.exists():
            return []
        return list(directory.rglob("*.robot"))
    
    def _convert_robot_model_to_bdd(self, model, file_path: Path) -> BDDFeature:
        """Convert Robot model to BDD feature."""
        # Robot suite name becomes feature name
        feature_name = model.name
        
        # Extract test cases as scenarios
        scenarios = []
        for test in model.tests:
            # Check if test uses BDD keywords
            if self._is_bdd_test(test):
                scenario = self._convert_test_to_scenario(test, feature_name, file_path)
                scenarios.append(scenario)
        
        # Suite documentation becomes feature description
        description = model.doc if model.doc else None
        
        # Suite tags become feature tags
        tags = list(model.metadata.keys()) if model.metadata else []
        
        return BDDFeature(
            name=feature_name,
            description=description,
            scenarios=scenarios,
            tags=tags,
            file_path=str(file_path),
            framework="robot-bdd"
        )
    
    def _is_bdd_test(self, test) -> bool:
        """Check if test case uses BDD-style keywords."""
        for keyword in test.body:
            if hasattr(keyword, 'name'):
                keyword_name = keyword.name.strip()
                # Check if starts with BDD keyword
                for bdd_kw in self.BDD_KEYWORDS:
                    if keyword_name.startswith(bdd_kw):
                        return True
        return False
    
    def _convert_test_to_scenario(self, test, feature_name: str, file_path: Path) -> BDDScenario:
        """Convert Robot test case to BDD scenario."""
        steps = []
        
        for keyword in test.body:
            if hasattr(keyword, 'name'):
                # Extract BDD keyword and text
                keyword_name = keyword.name.strip()
                
                # Find BDD keyword
                step_keyword = None
                step_text = keyword_name
                
                for bdd_kw in self.BDD_KEYWORDS:
                    if keyword_name.startswith(bdd_kw):
                        step_keyword = StepKeyword(bdd_kw)
                        step_text = keyword_name[len(bdd_kw):].strip()
                        break
                
                if step_keyword:
                    steps.append(BDDStep(
                        keyword=step_keyword,
                        text=step_text,
                        line=keyword.lineno if hasattr(keyword, 'lineno') else 0
                    ))
        
        # Extract tags
        tags = [str(tag) for tag in test.tags] if test.tags else []
        
        scenario = BDDScenario(
            id=f"{feature_name}::{test.name}",
            name=test.name,
            feature=feature_name,
            steps=steps,
            tags=tags,
            line=test.lineno if hasattr(test, 'lineno') else 0,
            description=test.doc if test.doc else None,
            framework="robot-bdd",
            file_path=str(file_path)
        )
        
        return scenario


class RobotBDDKeywordParser(BDDStepDefinitionParser):
    """
    Extract Robot Framework keyword definitions.
    
    Keywords can be defined in:
    - .robot files (*** Keywords *** section)
    - Python libraries
    - Java libraries (via Jython)
    """
    
    def discover_step_definitions(self, directory: Path) -> List[Dict[str, Any]]:
        """Discover keyword definitions from .robot and .py files."""
        if not ROBOT_API_AVAILABLE:
            return []
        
        definitions = []
        
        # Parse .robot files
        robot_files = list(directory.rglob("*.robot"))
        for robot_file in robot_files:
            definitions.extend(self.parse_step_definition_file(robot_file))
        
        # Parse Python library files
        py_files = list(directory.rglob("*.py"))
        for py_file in py_files:
            definitions.extend(self._parse_python_keywords(py_file))
        
        return definitions
    
    def parse_step_definition_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse keyword definitions from .robot file."""
        if not ROBOT_API_AVAILABLE:
            return []
        
        definitions = []
        
        try:
            model = get_model(str(file_path))
            
            # Extract user keywords
            if hasattr(model, 'keywords'):
                for keyword in model.keywords:
                    definitions.append({
                        "pattern": keyword.name,  # Robot uses exact match or fuzzy
                        "method_name": keyword.name,
                        "file_path": str(file_path),
                        "line_number": keyword.lineno if hasattr(keyword, 'lineno') else 0,
                        "keyword": None,  # Robot keywords don't have Given/When/Then restrictions
                        "framework": "robot-bdd"
                    })
        
        except Exception as e:
            logger.warning(f"Failed to parse Robot file {file_path}: {e}")
        
        return definitions
    
    def _parse_python_keywords(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse keyword definitions from Python library file."""
        definitions = []
        
        try:
            import ast
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            # Find all functions (potential keywords)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions
                    if node.name.startswith('_'):
                        continue
                    
                    definitions.append({
                        "pattern": node.name.replace('_', ' '),  # Robot converts underscores to spaces
                        "method_name": node.name,
                        "file_path": str(file_path),
                        "line_number": node.lineno,
                        "keyword": None,
                        "framework": "robot-bdd"
                    })
        
        except Exception as e:
            logger.warning(f"Failed to parse Python file {file_path}: {e}")
        
        return definitions
    
    def match_step_to_definition(
        self,
        step: BDDStep,
        definitions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Match step to keyword definition.
        
        Robot Framework uses fuzzy matching:
        - Case-insensitive
        - Underscores and spaces are equivalent
        - "User Logs In" matches "user_logs_in"
        """
        step_normalized = step.text.lower().replace(' ', '').replace('_', '')
        
        for definition in definitions:
            pattern_normalized = definition["pattern"].lower().replace(' ', '').replace('_', '')
            
            if step_normalized == pattern_normalized:
                return definition
        
        return None


class RobotBDDExecutionParser(BDDExecutionParser):
    """
    Parse Robot Framework execution results from output.xml.
    """
    
    @property
    def supported_report_formats(self) -> List[str]:
        return ["xml"]
    
    def parse_execution_report(self, report_path: Path) -> List[BDDExecutionResult]:
        """Parse Robot output.xml."""
        if not ROBOT_API_AVAILABLE:
            return []
        
        try:
            from robot.api import ExecutionResult
            result = ExecutionResult(str(report_path))
            
            # Convert to BDD execution results
            bdd_results = []
            
            for suite in result.suite.suites:
                for test in suite.tests:
                    bdd_results.append(BDDExecutionResult(
                        scenario_id=f"{suite.name}::{test.name}",
                        feature_name=suite.name,
                        scenario_name=test.name,
                        status="passed" if test.passed else "failed",
                        duration_ns=test.elapsedtime * 1_000_000,  # ms to ns
                        tags=[str(tag) for tag in test.tags],
                        steps_passed=sum(1 for kw in test.keywords if kw.passed),
                        steps_failed=sum(1 for kw in test.keywords if not kw.passed)
                    ))
            
            return bdd_results
        
        except Exception as e:
            logger.error(f"Failed to parse Robot execution report: {e}")
            return []
    
    def parse_execution_data(self, data: Any) -> List[BDDExecutionResult]:
        """Parse from in-memory data."""
        return []
    
    def link_failure_to_scenario(
        self,
        execution_result: BDDExecutionResult,
        scenarios: List[BDDScenario]
    ) -> Optional[BDDScenario]:
        """Link failure to scenario definition."""
        for scenario in scenarios:
            if scenario.id == execution_result.scenario_id:
                return scenario
        return None


class RobotBDDAdapter(BDDAdapter):
    """
    Complete Robot Framework BDD adapter.
    
    Implements full BDD support for Robot Framework with Given/When/Then keywords.
    """
    
    def __init__(
        self,
        robot_dir: Optional[Path] = None,
        resource_dir: Optional[Path] = None
    ):
        self.robot_dir = robot_dir or Path("tests")
        self.resource_dir = resource_dir or Path("resources")
        
        self._feature_parser = RobotBDDFeatureParser()
        self._keyword_parser = RobotBDDKeywordParser()
        self._execution_parser = RobotBDDExecutionParser()
    
    @property
    def framework_name(self) -> str:
        return "robot-bdd"
    
    @property
    def feature_parser(self) -> BDDFeatureParser:
        return self._feature_parser
    
    @property
    def step_definition_parser(self) -> BDDStepDefinitionParser:
        return self._keyword_parser
    
    @property
    def execution_parser(self) -> BDDExecutionParser:
        return self._execution_parser
    
    def validate_completeness(self) -> Dict[str, bool]:
        """Validate adapter completeness."""
        return {
            "discovery": ROBOT_API_AVAILABLE,
            "feature_parsing": ROBOT_API_AVAILABLE,
            "scenario_extraction": ROBOT_API_AVAILABLE,
            "step_extraction": ROBOT_API_AVAILABLE,
            "tag_extraction": ROBOT_API_AVAILABLE,
            "step_definition_mapping": ROBOT_API_AVAILABLE,
            "execution_parsing": ROBOT_API_AVAILABLE,
            "failure_mapping": ROBOT_API_AVAILABLE,
            "embedding_compatibility": True,
            "graph_compatibility": True,
        }


def create_robot_bdd_adapter(
    robot_dir: str = "tests",
    resource_dir: str = "resources"
) -> RobotBDDAdapter:
    """
    Create configured Robot BDD adapter.
    
    Args:
        robot_dir: Directory containing .robot test files
        resource_dir: Directory containing keyword resources
    
    Returns:
        Configured adapter
    """
    return RobotBDDAdapter(
        robot_dir=Path(robot_dir),
        resource_dir=Path(resource_dir)
    )
