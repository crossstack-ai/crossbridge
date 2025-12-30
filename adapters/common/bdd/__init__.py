"""
BDD (Behavior-Driven Development) common utilities.

Framework-agnostic BDD processing for Scenario Outline expansion,
parameter substitution, and intent extraction.
"""
from .models import ScenarioOutline, ExamplesTable, ExpandedScenario
from .expander import expand_scenario_outline
from .intent_mapper import map_expanded_scenario_to_intent

__all__ = [
    'ScenarioOutline',
    'ExamplesTable',
    'ExpandedScenario',
    'expand_scenario_outline',
    'map_expanded_scenario_to_intent',
]
