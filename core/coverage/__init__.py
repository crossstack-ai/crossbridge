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

# Core models - imported eagerly as they're used by everything
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

# Core parsers - imported eagerly
from core.coverage.jacoco_parser import JaCoCoXMLParser, JaCoCoReportLocator

# Repository and engine - imported eagerly as primary API
from core.coverage.repository import CoverageRepository
from core.coverage.engine import CoverageMappingEngine

# Lazy import helpers for optional/heavy modules
def _lazy_import_cucumber():
    """Lazy import Cucumber coverage (optional dependency)."""
    try:
        from core.coverage.cucumber_coverage import (
            CucumberCoverageAggregator,
            StepDefinitionMapper,
            CucumberCoverageCollector
        )
        return CucumberCoverageAggregator, StepDefinitionMapper, CucumberCoverageCollector
    except ImportError:
        return None, None, None

def _lazy_import_behavioral_collectors():
    """Lazy import behavioral collectors."""
    from core.coverage.behavioral_collectors import (
        ApiEndpointCollector,
        UiComponentCollector,
        NetworkCaptureCollector,
        ContractCoverageCollector
    )
    return ApiEndpointCollector, UiComponentCollector, NetworkCaptureCollector, ContractCoverageCollector

def _lazy_import_console_formatter():
    """Lazy import console formatting functions."""
    from core.coverage.console_formatter import (
        print_functional_coverage_map,
        print_test_to_feature_coverage,
        print_change_impact_surface,
        print_coverage_gaps,
        export_to_csv,
        export_to_json
    )
    return (print_functional_coverage_map, print_test_to_feature_coverage,
            print_change_impact_surface, print_coverage_gaps, export_to_csv, export_to_json)

def _lazy_import_coverage_py_parser():
    """Lazy import coverage.py parser."""
    from core.coverage.coverage_py_parser import CoveragePyParser
    return CoveragePyParser

def _lazy_import_external_extractors():
    """Lazy import external test case extractors."""
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
    return (ExternalTestCaseExtractor, JavaExternalTestCaseExtractor, PytestExternalTestCaseExtractor,
            RobotFrameworkExternalTestCaseExtractor, CucumberExternalTestCaseExtractor,
            ExternalTestCaseExtractorFactory, extract_external_refs_from_test, extract_external_refs_from_file)

def _lazy_import_functional_repository():
    """Lazy import functional coverage repository."""
    from core.coverage.functional_repository import FunctionalCoverageRepository
    return FunctionalCoverageRepository

def _lazy_import_istanbul_parser():
    """Lazy import Istanbul/NYC parser."""
    from core.coverage.istanbul_parser import IstanbulParser
    return IstanbulParser

# Lazy attribute access for optional modules
def __getattr__(name):
    """Lazy load modules on first access to avoid circular dependencies."""
    
    # Cucumber modules
    if name in ('CucumberCoverageAggregator', 'StepDefinitionMapper', 'CucumberCoverageCollector'):
        agg, mapper, collector = _lazy_import_cucumber()
        globals()['CucumberCoverageAggregator'] = agg
        globals()['StepDefinitionMapper'] = mapper
        globals()['CucumberCoverageCollector'] = collector
        return globals()[name]
    
    # Behavioral collectors
    if name in ('ApiEndpointCollector', 'UiComponentCollector', 'NetworkCaptureCollector', 'ContractCoverageCollector'):
        api, ui, net, contract = _lazy_import_behavioral_collectors()
        globals()['ApiEndpointCollector'] = api
        globals()['UiComponentCollector'] = ui
        globals()['NetworkCaptureCollector'] = net
        globals()['ContractCoverageCollector'] = contract
        return globals()[name]
    
    # Console formatter functions
    if name in ('print_functional_coverage_map', 'print_test_to_feature_coverage',
                'print_change_impact_surface', 'print_coverage_gaps', 'export_to_csv', 'export_to_json'):
        funcs = _lazy_import_console_formatter()
        (globals()['print_functional_coverage_map'], globals()['print_test_to_feature_coverage'],
         globals()['print_change_impact_surface'], globals()['print_coverage_gaps'],
         globals()['export_to_csv'], globals()['export_to_json']) = funcs
        return globals()[name]
    
    # Coverage.py parser
    if name == 'CoveragePyParser':
        parser = _lazy_import_coverage_py_parser()
        globals()['CoveragePyParser'] = parser
        return parser
    
    # External extractors
    if name in ('ExternalTestCaseExtractor', 'JavaExternalTestCaseExtractor', 'PytestExternalTestCaseExtractor',
                'RobotFrameworkExternalTestCaseExtractor', 'CucumberExternalTestCaseExtractor',
                'ExternalTestCaseExtractorFactory', 'extract_external_refs_from_test', 'extract_external_refs_from_file'):
        extractors = _lazy_import_external_extractors()
        (globals()['ExternalTestCaseExtractor'], globals()['JavaExternalTestCaseExtractor'],
         globals()['PytestExternalTestCaseExtractor'], globals()['RobotFrameworkExternalTestCaseExtractor'],
         globals()['CucumberExternalTestCaseExtractor'], globals()['ExternalTestCaseExtractorFactory'],
         globals()['extract_external_refs_from_test'], globals()['extract_external_refs_from_file']) = extractors
        return globals()[name]
    
    # Functional models module
    if name == 'functional_models':
        import core.coverage.functional_models as fm
        globals()['functional_models'] = fm
        return fm
    
    # Functional repository
    if name == 'FunctionalCoverageRepository':
        repo = _lazy_import_functional_repository()
        globals()['FunctionalCoverageRepository'] = repo
        return repo
    
    # Istanbul parser
    if name == 'IstanbulParser':
        parser = _lazy_import_istanbul_parser()
        globals()['IstanbulParser'] = parser
        return parser
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    # Core Models (eagerly loaded)
    'CoveredCodeUnit',
    'TestCoverageMapping',
    'ScenarioCoverageMapping',
    'CoverageConfidenceCalculator',
    'CoverageImpactQuery',
    'CoverageType',
    'CoverageSource',
    'ExecutionMode',
    
    # Core Parsers (eagerly loaded)
    'JaCoCoXMLParser',
    'JaCoCoReportLocator',
    
    # Core API (eagerly loaded)
    'CoverageRepository',
    'CoverageMappingEngine',
    
    # Lazy-loaded modules (available via __getattr__)
    'CoveragePyParser',
    'IstanbulParser',
    'CucumberCoverageAggregator',
    'StepDefinitionMapper',
    'CucumberCoverageCollector',
    'ApiEndpointCollector',
    'UiComponentCollector',
    'NetworkCaptureCollector',
    'ContractCoverageCollector',
    'ExternalTestCaseExtractor',
    'JavaExternalTestCaseExtractor',
    'PytestExternalTestCaseExtractor',
    'RobotFrameworkExternalTestCaseExtractor',
    'CucumberExternalTestCaseExtractor',
    'ExternalTestCaseExtractorFactory',
    'extract_external_refs_from_test',
    'extract_external_refs_from_file',
    'functional_models',
    'FunctionalCoverageRepository',
    'print_functional_coverage_map',
    'print_test_to_feature_coverage',
    'print_change_impact_surface',
    'print_coverage_gaps',
    'export_to_csv',
    'export_to_json',
]
