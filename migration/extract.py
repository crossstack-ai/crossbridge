"""
Migration extraction module.

This module provides framework-agnostic extraction utilities that bridge
adapters and future AI translation capabilities. It operates purely on
the adapter interface without knowledge of specific frameworks.
"""

from typing import List

from adapters.common.base import TestFrameworkAdapter
from adapters.common.models import IntentModel, TestMetadata


def extract_intent_from_adapter(adapter: TestFrameworkAdapter, test_id: str) -> IntentModel:
    """
    Extract test intent using a framework adapter.
    
    This function serves as a bridge between framework-specific adapters
    and the migration pipeline. It delegates to the adapter's extract_intent
    method and returns a framework-agnostic IntentModel that can be used
    for cross-framework migration, AI analysis, or test documentation.
    
    Args:
        adapter: Framework adapter instance (must implement TestFrameworkAdapter).
        test_id: Unique identifier of the test to extract intent from.
        
    Returns:
        IntentModel: Framework-agnostic representation of the test's intent,
            including high-level description, steps, and assertions.
            
    Raises:
        Exception: If extraction fails (propagated from adapter).
        
    Example:
        >>> adapter = PytestAdapter("/path/to/project")
        >>> intent = extract_intent_from_adapter(adapter, "test_login")
        >>> print(intent.test_name, intent.intent)
    """
    return adapter.extract_intent(test_id)


def extract_intents_batch(adapter: TestFrameworkAdapter, test_ids: List[str]) -> List[IntentModel]:
    """
    Extract intents for multiple tests in batch.
    
    This function extracts intent models for multiple tests, useful for
    bulk migration operations or analysis across an entire test suite.
    
    Args:
        adapter: Framework adapter instance.
        test_ids: List of test identifiers to extract intents from.
        
    Returns:
        List[IntentModel]: List of extracted intent models, one per test.
            Failed extractions are skipped (no partial results returned).
            
    Example:
        >>> adapter = PytestAdapter("/path/to/project")
        >>> tests = adapter.discover_tests()
        >>> test_ids = [t.id for t in tests]
        >>> intents = extract_intents_batch(adapter, test_ids)
    """
    intents = []
    
    for test_id in test_ids:
        try:
            intent = extract_intent_from_adapter(adapter, test_id)
            intents.append(intent)
        except Exception as e:
            print(f"Warning: Failed to extract intent for {test_id}: {e}")
            continue
    
    return intents


def discover_and_extract_all(adapter: TestFrameworkAdapter) -> List[IntentModel]:
    """
    Discover all tests and extract their intents in one operation.
    
    This is a convenience function that combines test discovery with intent
    extraction, useful for initializing migration pipelines or performing
    comprehensive test suite analysis.
    
    Args:
        adapter: Framework adapter instance.
        
    Returns:
        List[IntentModel]: Intent models for all discovered tests.
        
    Example:
        >>> adapter = PytestAdapter("/path/to/project")
        >>> all_intents = discover_and_extract_all(adapter)
        >>> print(f"Extracted {len(all_intents)} test intents")
    """
    # Discover all tests
    tests = adapter.discover_tests()
    
    # Extract test IDs
    test_ids = [test.id for test in tests]
    
    # Extract intents in batch
    return extract_intents_batch(adapter, test_ids)
