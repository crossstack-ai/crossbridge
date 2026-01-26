"""
Coverage Mapping Module.

Enables precise test-to-code coverage mapping for impact analysis.

Key Components:
- models: Coverage data models (CoveredCodeUnit, TestCoverageMapping, ScenarioCoverageMapping)
- jacoco_parser: JaCoCo XML parser for Java/Selenium coverage
- cucumber_coverage: Cucumber scenario coverage aggregation
- repository: Database persistence for coverage mappings
- engine: Orchestration of coverage collection and queries

Usage:
    from core.coverage import CoverageMappingEngine
    
    engine = CoverageMappingEngine(db_path=Path("crossbridge.db"))
    
    # Collect isolated coverage (high confidence)
    mapping = engine.collect_coverage_isolated(
        test_id="LoginTest.testSuccessfulLogin",
        test_command="mvn test -Dtest=LoginTest#testSuccessfulLogin",
        working_dir=Path("./my-project")
    )
    
    # Query impact
    impact = engine.query_impact(
        changed_classes={"com.example.LoginService", "com.example.UserService"},
        min_confidence=0.7
    )
    print(f"Affected tests: {impact.affected_test_count}")
"""

from core.coverage.models import (
    CoveredCodeUnit,
    TestCoverageMapping,
    ScenarioCoverageMapping,
    CoverageConfidenceCalculator,
    CoverageImpactQuery,
    CoverageType,
    CoverageSource,
    ExecutionMode
)
from core.coverage.jacoco_parser import JaCoCoXMLParser, JaCoCoReportLocator

# Import Cucumber coverage (optional, requires selenium_bdd_java adapter)
try:
    from core.coverage.cucumber_coverage import (
        CucumberCoverageAggregator,
        StepDefinitionMapper,
        CucumberCoverageCollector
    )
except ImportError:
    CucumberCoverageAggregator = None
    StepDefinitionMapper = None
    CucumberCoverageCollector = None

# Import Phase 3 coverage modules
from core.coverage.behavioral_collectors import (
    ApiEndpointCollector,
    UiComponentCollector,
    NetworkCaptureCollector,
    ContractCoverageCollector
)
from core.coverage.console_formatter import (
    print_functional_coverage_map,
    print_test_to_feature_coverage,
    print_change_impact_surface,
    print_coverage_gaps,
    export_to_csv,
    export_to_json
)
from core.coverage.coverage_py_parser import CoveragePyParser
from core.coverage.external_extractors import (
    ExternalTestCaseExtractor,
    JavaExternalTestCaseExtractor,
    PytestExternalTestCaseExtractor,
    RobotFrameworkExternalTestCaseExtractor,
    CucumberExternalTestCaseExtractor,
    ExternalTestCaseExtractorFactory,
    extract_external_refs_from_test,
    extract_external_refs_from_file
)
# Import all functional models
import core.coverage.functional_models as functional_models
from core.coverage.functional_repository import FunctionalCoverageRepository

from core.coverage.repository import CoverageRepository
from core.coverage.engine import CoverageMappingEngine

__all__ = [
    # Models
    'CoveredCodeUnit',
    'TestCoverageMapping',
    'ScenarioCoverageMapping',
    'CoverageConfidenceCalculator',
    'CoverageImpactQuery',
    'CoverageType',
    'CoverageSource',
    'ExecutionMode',
    
    # Parsers
    'JaCoCoXMLParser',
    'JaCoCoReportLocator',
    'CoveragePyParser',
    
    # Cucumber
    'CucumberCoverageAggregator',
    'StepDefinitionMapper',
    'CucumberCoverageCollector',
    
    # Behavioral Collectors
    'ApiEndpointCollector',
    'UiComponentCollector',
    'NetworkCaptureCollector',
    'ContractCoverageCollector',
    
    # External Extractors
    'ExternalTestCaseExtractor',
    'JavaExternalTestCaseExtractor',
    'PytestExternalTestCaseExtractor',
    'RobotFrameworkExternalTestCaseExtractor',
    'CucumberExternalTestCaseExtractor',
    'ExternalTestCaseExtractorFactory',
    'extract_external_refs_from_test',
    'extract_external_refs_from_file',
    
    # Functional Models (import via functional_models module)
    'functional_models',
    
    # Console Formatting Functions
    'print_functional_coverage_map',
    'print_test_to_feature_coverage',
    'print_change_impact_surface',
    'print_coverage_gaps',
    'export_to_csv',
    'export_to_json',
    
    # Persistence
    'CoverageRepository',
    'FunctionalCoverageRepository',
    
    # Engine
    'CoverageMappingEngine'
]
