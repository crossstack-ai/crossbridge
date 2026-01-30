"""
Framework-Specific Embedding Adapters

Adapters for generating embeddings from framework-specific entities
(Cucumber scenarios, Robot tests, Pytest tests, etc.)
"""

from typing import List, Any
from core.embeddings.interface import IEmbeddingProvider, Embedding


class CucumberAdapter:
    """Adapter for Cucumber/BDD scenarios and steps"""
    
    def generate_embeddings(
        self,
        scenarios: List[Any],
        provider: IEmbeddingProvider,
        include_steps: bool = False
    ) -> List[Embedding]:
        """
        Generate embeddings for Cucumber scenarios.
        
        Args:
            scenarios: List of CucumberScenario objects
            provider: Embedding provider
            include_steps: Include step-level embeddings
            
        Returns:
            List of embeddings
        """
        embeddings = []
        
        for scenario in scenarios:
            # Scenario-level embedding
            text = self._scenario_to_text(scenario)
            vector = provider.embed(text)
            
            embeddings.append(Embedding(
                entity_id=f"scenario:{scenario.feature_name}:{scenario.name}",
                entity_type="scenario",
                text=text,
                vector=vector,
                metadata={
                    "feature_name": scenario.feature_name,
                    "tags": scenario.tags,
                    "step_count": len(scenario.steps),
                    "framework": "cucumber"
                },
                model=provider.get_model_name()
            ))
            
            # Step-level embeddings
            if include_steps:
                for step in scenario.steps:
                    step_text = f"{step.keyword} {step.text}"
                    step_vector = provider.embed(step_text)
                    
                    embeddings.append(Embedding(
                        entity_id=f"step:{scenario.name}:{step.keyword}:{step.text}",
                        entity_type="step",
                        text=step_text,
                        vector=step_vector,
                        metadata={
                            "scenario_name": scenario.name,
                            "feature_name": scenario.feature_name,
                            "keyword": step.keyword,
                            "framework": "cucumber"
                        },
                        model=provider.get_model_name()
                    ))
        
        return embeddings
    
    def _scenario_to_text(self, scenario) -> str:
        """Convert scenario to text for embedding"""
        parts = [
            f"Feature: {scenario.feature_name}",
            f"Scenario: {scenario.name}"
        ]
        
        if scenario.tags:
            parts.append(f"Tags: {', '.join(scenario.tags)}")
        
        for step in scenario.steps:
            parts.append(f"{step.keyword} {step.text}")
        
        return "\n".join(parts)


class RobotAdapter:
    """Adapter for Robot Framework tests and keywords"""
    
    def generate_embeddings(
        self,
        tests: List[Any],
        provider: IEmbeddingProvider,
        include_keywords: bool = False
    ) -> List[Embedding]:
        """
        Generate embeddings for Robot tests.
        
        Args:
            tests: List of RobotTest objects
            provider: Embedding provider
            include_keywords: Include keyword-level embeddings
            
        Returns:
            List of embeddings
        """
        embeddings = []
        
        for test in tests:
            # Test-level embedding
            text = self._test_to_text(test)
            vector = provider.embed(text)
            
            embeddings.append(Embedding(
                entity_id=f"test:{test.suite_name}:{test.name}",
                entity_type="test",
                text=text,
                vector=vector,
                metadata={
                    "suite_name": test.suite_name,
                    "tags": test.tags,
                    "keyword_count": len(test.keywords),
                    "framework": "robot"
                },
                model=provider.get_model_name()
            ))
            
            # Keyword-level embeddings
            if include_keywords:
                for keyword in test.keywords:
                    kw_text = f"{keyword.library}.{keyword.name}"
                    if keyword.arguments:
                        kw_text += f" with args: {', '.join(map(str, keyword.arguments))}"
                    
                    kw_vector = provider.embed(kw_text)
                    
                    embeddings.append(Embedding(
                        entity_id=f"keyword:{test.name}:{keyword.name}",
                        entity_type="keyword",
                        text=kw_text,
                        vector=kw_vector,
                        metadata={
                            "test_name": test.name,
                            "suite_name": test.suite_name,
                            "library": keyword.library,
                            "framework": "robot"
                        },
                        model=provider.get_model_name()
                    ))
        
        return embeddings
    
    def _test_to_text(self, test) -> str:
        """Convert test to text for embedding"""
        parts = [
            f"Suite: {test.suite_name}",
            f"Test: {test.name}"
        ]
        
        if test.tags:
            parts.append(f"Tags: {', '.join(test.tags)}")
        
        for keyword in test.keywords:
            parts.append(f"{keyword.library}.{keyword.name}")
        
        return "\n".join(parts)


class PytestAdapter:
    """Adapter for Pytest tests and assertions"""
    
    def generate_embeddings(
        self,
        tests: List[Any],
        provider: IEmbeddingProvider,
        include_assertions: bool = False
    ) -> List[Embedding]:
        """
        Generate embeddings for Pytest tests.
        
        Args:
            tests: List of PytestTest objects
            provider: Embedding provider
            include_assertions: Include assertion-level embeddings
            
        Returns:
            List of embeddings
        """
        embeddings = []
        
        for test in tests:
            # Test-level embedding
            text = self._test_to_text(test)
            vector = provider.embed(text)
            
            embeddings.append(Embedding(
                entity_id=f"function:{test.module}::{test.name}",
                entity_type="function",
                text=text,
                vector=vector,
                metadata={
                    "module": test.module,
                    "markers": test.markers,
                    "fixture_count": len(test.fixtures) if hasattr(test, 'fixtures') else 0,
                    "framework": "pytest"
                },
                model=provider.get_model_name()
            ))
            
            # Assertion-level embeddings
            if include_assertions and hasattr(test, 'assertions'):
                for assertion in test.assertions:
                    assert_text = assertion.expression
                    assert_vector = provider.embed(assert_text)
                    
                    embeddings.append(Embedding(
                        entity_id=f"assertion:{test.name}:{assertion.expression}",
                        entity_type="assertion",
                        text=assert_text,
                        vector=assert_vector,
                        metadata={
                            "test_name": test.name,
                            "module": test.module,
                            "framework": "pytest"
                        },
                        model=provider.get_model_name()
                    ))
        
        return embeddings
    
    def _test_to_text(self, test) -> str:
        """Convert test to text for embedding"""
        parts = [
            f"Module: {test.module}",
            f"Test: {test.name}"
        ]
        
        if hasattr(test, 'markers') and test.markers:
            parts.append(f"Markers: {', '.join(test.markers)}")
        
        if hasattr(test, 'fixtures') and test.fixtures:
            parts.append(f"Fixtures: {', '.join(f.name for f in test.fixtures)}")
        
        return "\n".join(parts)
