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
    
    # Cucumber
    'CucumberCoverageAggregator',
    'StepDefinitionMapper',
    'CucumberCoverageCollector',
    
    # Persistence
    'CoverageRepository',
    
    # Engine
    'CoverageMappingEngine'
]
