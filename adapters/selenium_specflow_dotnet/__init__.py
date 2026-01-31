"""
Selenium + C# (.NET) + SpecFlow + NUnit adapter package for CrossBridge.

Provides comprehensive support for C# BDD tests using Selenium WebDriver,
SpecFlow for Gherkin scenarios, and NUnit/MSTest/xUnit as test runners.

Usage:
    # Auto-detect and use
    from adapters.selenium_specflow_dotnet import SeleniumSpecFlowAdapter
    
    adapter = SeleniumSpecFlowAdapter("/path/to/specflow/project")
    tests = adapter.discover_tests()
    results = adapter.run_tests()
    
    # Get configuration info
    config_info = adapter.get_config_info()
    print(f"Using {config_info['test_framework']} with SpecFlow {config_info['specflow_version']}")
    
    # Extract metadata
    from adapters.selenium_specflow_dotnet import SeleniumSpecFlowExtractor
    
    extractor = SeleniumSpecFlowExtractor("/path/to/project")
    tests = extractor.extract_tests()
    step_defs = extractor.extract_step_definitions()
    page_objects = extractor.extract_page_objects()
"""

from .adapter import (
    SeleniumSpecFlowAdapter,
    SeleniumSpecFlowExtractor,
    SpecFlowProjectDetector,
    SpecFlowProjectConfig,
    SpecFlowFeatureParser,
    SpecFlowStepDefinitionParser,
    DotNetTestFramework,
)
from .value_retriever_handler import ValueRetrieverHandler
from .specflow_plus_handler import SpecFlowPlusHandler

# Scenario Outline expansion (Gap 3.1)
_OUTLINE_EXPANDER_AVAILABLE = False
try:
    from .outline_expander import (
        ScenarioOutlineExpander,
        expand_scenario_outlines,
        ExpandedScenario,
        ScenarioOutline,
        ExamplesTable,
    )
    _OUTLINE_EXPANDER_AVAILABLE = True
except ImportError:
    pass

__all__ = [
    "SeleniumSpecFlowAdapter",
    "SeleniumSpecFlowExtractor",
    "SpecFlowProjectDetector",
    "SpecFlowProjectConfig",
    "SpecFlowFeatureParser",
    "SpecFlowStepDefinitionParser",
    "DotNetTestFramework",
    "ValueRetrieverHandler",
    "SpecFlowPlusHandler",
]

# Add outline expander exports if available
if _OUTLINE_EXPANDER_AVAILABLE:
    __all__.extend([
        "ScenarioOutlineExpander",
        "expand_scenario_outlines",
        "ExpandedScenario",
        "ScenarioOutline",
        "ExamplesTable",
    ])
