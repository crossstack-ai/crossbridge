"""
Core BDD (Behavior-Driven Development) Module.

Provides unified BDD support across multiple frameworks:
- Cucumber (Java, JavaScript, Ruby)
- Robot Framework (Python BDD)
- JBehave (Java BDD)
- SpecFlow (.NET BDD)
- Behave (Python BDD)

This module defines canonical models and interfaces that all BDD adapters
must implement, ensuring consistent data normalization and feature parity.
"""

from .models import (
    BDDScenario,
    BDDStep,
    BDDFeature,
    BDDScenarioOutline,
    BDDExampleRow,
    BDDBackground,
    StepKeyword,
    ScenarioType,
    BDDExecutionResult,
    BDDFailure
)

from .parser_interface import (
    BDDFeatureParser,
    BDDStepDefinitionParser,
    BDDExecutionParser
)

from .step_mapper import (
    StepDefinitionMapper,
    StepDefinitionMatch,
    resolve_step_to_implementation
)

__all__ = [
    # Models
    "BDDScenario",
    "BDDStep",
    "BDDFeature",
    "BDDScenarioOutline",
    "BDDExampleRow",
    "BDDBackground",
    "StepKeyword",
    "ScenarioType",
    "BDDExecutionResult",
    "BDDFailure",
    
    # Parser Interfaces
    "BDDFeatureParser",
    "BDDStepDefinitionParser",
    "BDDExecutionParser",
    
    # Step Mapping
    "StepDefinitionMapper",
    "StepDefinitionMatch",
    "resolve_step_to_implementation",
]
