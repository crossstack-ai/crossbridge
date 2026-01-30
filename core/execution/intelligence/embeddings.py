"""
Execution Intelligence Embeddings

Generate semantic embeddings for test entities (scenarios, steps, keywords, etc.)
to enable similarity search, duplicate detection, and impact analysis.

Supports:
- Scenario-level embeddings (BDD)
- Step-level embeddings (BDD)
- Keyword-level embeddings (Robot)
- Test-level embeddings (Pytest)
- Assertion-level embeddings (Pytest)
"""

import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

import numpy as np

from core.logging import get_logger
from core.execution.intelligence.models import (
    ExecutionSignal,
    EntityType,
    CucumberScenario,
    CucumberStep,
    RobotTest,
    RobotKeyword,
    PytestTest,
    PytestAssertion,
)

logger = get_logger(__name__)


@dataclass
class Embedding:
    """
    Semantic embedding for a test entity.
    
    Enables similarity search and duplicate detection.
    """
    entity_id: str  # Unique identifier
    entity_type: EntityType
    text: str  # Original text used for embedding
    vector: List[float]  # Embedding vector
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def cosine_similarity(self, other: 'Embedding') -> float:
        """Calculate cosine similarity with another embedding"""
        if len(self.vector) != len(other.vector):
            raise ValueError("Embedding dimensions must match")
        
        # Convert to numpy arrays
        v1 = np.array(self.vector)
        v2 = np.array(other.vector)
        
        # Cosine similarity
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'entity_id': self.entity_id,
            'entity_type': self.entity_type.value,
            'text': self.text,
            'vector': self.vector,
            'metadata': self.metadata,
        }


class EmbeddingGenerator:
    """
    Generate embeddings for test entities.
    
    Uses sentence-transformers for high-quality embeddings.
    Falls back to simple TF-IDF if sentence-transformers unavailable.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Sentence transformer model name
                       Default: 'all-MiniLM-L6-v2' (fast, good quality, 384 dims)
        """
        self.model_name = model_name
        self.model = None
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading embedding model: {model_name}")
                self.model = SentenceTransformer(model_name)
                logger.info(f"Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                logger.warning("Falling back to TF-IDF embeddings")
        else:
            logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")
            logger.warning("Using fallback TF-IDF embeddings")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector (list of floats)
        """
        if self.model:
            # Use sentence-transformers
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        else:
            # Fallback: simple hash-based embedding (not ideal but deterministic)
            return self._fallback_embedding(text)
    
    def _fallback_embedding(self, text: str, dimension: int = 384) -> List[float]:
        """
        Generate fallback embedding using hash functions.
        
        Not as good as neural embeddings but deterministic and fast.
        """
        # Generate multiple hashes for different dimensions
        embeddings = []
        for i in range(dimension):
            # Use different hash seeds
            hash_input = f"{text}_{i}".encode('utf-8')
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            # Normalize to [-1, 1]
            normalized = (hash_value % 2000 - 1000) / 1000.0
            embeddings.append(normalized)
        
        # Normalize to unit vector
        norm = np.linalg.norm(embeddings)
        if norm > 0:
            embeddings = [e / norm for e in embeddings]
        
        return embeddings


class ScenarioEmbeddingGenerator:
    """Generate embeddings for BDD scenarios"""
    
    def __init__(self, generator: EmbeddingGenerator):
        self.generator = generator
    
    def generate_scenario_embedding(self, scenario: CucumberScenario) -> Embedding:
        """
        Generate embedding for a Cucumber scenario.
        
        Combines:
        - Scenario name
        - Feature name
        - Step texts
        - Tags
        """
        # Construct rich text representation
        text_parts = [
            f"Scenario: {scenario.name}",
            f"Feature: {scenario.feature_name}",
        ]
        
        # Add step texts
        for step in scenario.steps:
            text_parts.append(f"{step.keyword} {step.text}")
        
        # Add tags if present
        if scenario.tags:
            text_parts.append(f"Tags: {', '.join(scenario.tags)}")
        
        text = "\n".join(text_parts)
        
        # Generate embedding
        vector = self.generator.generate_embedding(text)
        
        # Create entity ID
        entity_id = self._generate_id(scenario.feature_name, scenario.name)
        
        return Embedding(
            entity_id=entity_id,
            entity_type=EntityType.SCENARIO,
            text=text,
            vector=vector,
            metadata={
                'scenario_name': scenario.name,
                'feature_name': scenario.feature_name,
                'tags': scenario.tags,
                'step_count': len(scenario.steps),
            }
        )
    
    def generate_step_embedding(self, step: CucumberStep, scenario_name: str, feature_name: str) -> Embedding:
        """
        Generate embedding for a Cucumber step.
        
        Combines:
        - Step keyword + text
        - Scenario context
        - Feature context
        """
        text = f"{step.keyword} {step.text}\nScenario: {scenario_name}\nFeature: {feature_name}"
        
        vector = self.generator.generate_embedding(text)
        
        entity_id = self._generate_id(feature_name, scenario_name, step.text)
        
        return Embedding(
            entity_id=entity_id,
            entity_type=EntityType.STEP,
            text=text,
            vector=vector,
            metadata={
                'step_keyword': step.keyword,
                'step_text': step.text,
                'scenario_name': scenario_name,
                'feature_name': feature_name,
            }
        )
    
    def _generate_id(self, *parts: str) -> str:
        """Generate deterministic ID from parts"""
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]


class RobotEmbeddingGenerator:
    """Generate embeddings for Robot Framework entities"""
    
    def __init__(self, generator: EmbeddingGenerator):
        self.generator = generator
    
    def generate_test_embedding(self, test: RobotTest) -> Embedding:
        """
        Generate embedding for a Robot test.
        
        Combines:
        - Test name
        - Suite name
        - Keyword names
        - Tags
        """
        text_parts = [
            f"Test: {test.name}",
            f"Suite: {test.suite_name}",
        ]
        
        # Add keyword names
        for kw in test.keywords:
            text_parts.append(f"{kw.name} [{kw.library}]")
        
        # Add tags
        if test.tags:
            text_parts.append(f"Tags: {', '.join(test.tags)}")
        
        text = "\n".join(text_parts)
        
        vector = self.generator.generate_embedding(text)
        
        entity_id = self._generate_id(test.suite_name, test.name)
        
        return Embedding(
            entity_id=entity_id,
            entity_type=EntityType.TEST,
            text=text,
            vector=vector,
            metadata={
                'test_name': test.name,
                'suite_name': test.suite_name,
                'tags': test.tags,
                'keyword_count': len(test.keywords),
            }
        )
    
    def generate_keyword_embedding(self, keyword: RobotKeyword, test_name: str, suite_name: str) -> Embedding:
        """
        Generate embedding for a Robot keyword.
        
        Combines:
        - Keyword name
        - Library
        - Arguments
        - Test context
        """
        text_parts = [
            f"Keyword: {keyword.name}",
            f"Library: {keyword.library}",
        ]
        
        if keyword.arguments:
            text_parts.append(f"Arguments: {', '.join(keyword.arguments)}")
        
        text_parts.append(f"Test: {test_name}")
        text_parts.append(f"Suite: {suite_name}")
        
        text = "\n".join(text_parts)
        
        vector = self.generator.generate_embedding(text)
        
        entity_id = self._generate_id(suite_name, test_name, keyword.name)
        
        return Embedding(
            entity_id=entity_id,
            entity_type=EntityType.KEYWORD,
            text=text,
            vector=vector,
            metadata={
                'keyword_name': keyword.name,
                'library': keyword.library,
                'test_name': test_name,
                'suite_name': suite_name,
            }
        )
    
    def _generate_id(self, *parts: str) -> str:
        """Generate deterministic ID from parts"""
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]


class PytestEmbeddingGenerator:
    """Generate embeddings for Pytest entities"""
    
    def __init__(self, generator: EmbeddingGenerator):
        self.generator = generator
    
    def generate_test_embedding(self, test: PytestTest) -> Embedding:
        """
        Generate embedding for a Pytest test.
        
        Combines:
        - Test name
        - Module
        - Markers
        - Fixture names
        """
        text_parts = [
            f"Test: {test.name}",
            f"Module: {test.module}",
        ]
        
        if test.markers:
            text_parts.append(f"Markers: {', '.join(test.markers)}")
        
        if test.fixtures:
            fixture_names = [f.name for f in test.fixtures]
            text_parts.append(f"Fixtures: {', '.join(fixture_names)}")
        
        text = "\n".join(text_parts)
        
        vector = self.generator.generate_embedding(text)
        
        entity_id = self._generate_id(test.module, test.name)
        
        return Embedding(
            entity_id=entity_id,
            entity_type=EntityType.FUNCTION,
            text=text,
            vector=vector,
            metadata={
                'test_name': test.name,
                'module': test.module,
                'markers': test.markers,
            }
        )
    
    def generate_assertion_embedding(self, assertion: PytestAssertion, test_name: str, module: str) -> Embedding:
        """
        Generate embedding for a Pytest assertion.
        
        Combines:
        - Assertion expression
        - Test context
        """
        text_parts = [
            f"Assertion: {assertion.expression}",
            f"Test: {test_name}",
            f"Module: {module}",
        ]
        
        if assertion.error_message:
            text_parts.append(f"Error: {assertion.error_message}")
        
        text = "\n".join(text_parts)
        
        vector = self.generator.generate_embedding(text)
        
        entity_id = self._generate_id(module, test_name, assertion.expression)
        
        return Embedding(
            entity_id=entity_id,
            entity_type=EntityType.ASSERTION,
            text=text,
            vector=vector,
            metadata={
                'assertion_expression': assertion.expression,
                'test_name': test_name,
                'module': module,
            }
        )
    
    def _generate_id(self, *parts: str) -> str:
        """Generate deterministic ID from parts"""
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]


class EmbeddingStore:
    """
    In-memory store for embeddings with similarity search.
    
    For production, consider using a vector database (Pinecone, Weaviate, Chroma, etc.)
    """
    
    def __init__(self):
        self.embeddings: Dict[str, Embedding] = {}
        self.index_by_type: Dict[EntityType, List[str]] = {}
    
    def add(self, embedding: Embedding):
        """Add embedding to store"""
        self.embeddings[embedding.entity_id] = embedding
        
        # Update index by type
        if embedding.entity_type not in self.index_by_type:
            self.index_by_type[embedding.entity_type] = []
        
        if embedding.entity_id not in self.index_by_type[embedding.entity_type]:
            self.index_by_type[embedding.entity_type].append(embedding.entity_id)
    
    def get(self, entity_id: str) -> Optional[Embedding]:
        """Get embedding by ID"""
        return self.embeddings.get(entity_id)
    
    def find_similar(
        self,
        query_embedding: Embedding,
        top_k: int = 10,
        entity_type: Optional[EntityType] = None,
        min_similarity: float = 0.0
    ) -> List[Tuple[Embedding, float]]:
        """
        Find similar embeddings.
        
        Args:
            query_embedding: Query embedding
            top_k: Number of results to return
            entity_type: Filter by entity type
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (embedding, similarity_score) tuples, sorted by similarity
        """
        # Get candidate embeddings
        if entity_type:
            candidate_ids = self.index_by_type.get(entity_type, [])
            candidates = [self.embeddings[eid] for eid in candidate_ids]
        else:
            candidates = list(self.embeddings.values())
        
        # Calculate similarities
        results = []
        for candidate in candidates:
            # Skip self
            if candidate.entity_id == query_embedding.entity_id:
                continue
            
            similarity = query_embedding.cosine_similarity(candidate)
            
            if similarity >= min_similarity:
                results.append((candidate, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K
        return results[:top_k]
    
    def find_duplicates(
        self,
        entity_type: Optional[EntityType] = None,
        similarity_threshold: float = 0.95
    ) -> List[Tuple[Embedding, Embedding, float]]:
        """
        Find potential duplicate test entities.
        
        Args:
            entity_type: Filter by entity type
            similarity_threshold: Minimum similarity to consider as duplicate
            
        Returns:
            List of (embedding1, embedding2, similarity) tuples
        """
        # Get candidates
        if entity_type:
            candidate_ids = self.index_by_type.get(entity_type, [])
            candidates = [self.embeddings[eid] for eid in candidate_ids]
        else:
            candidates = list(self.embeddings.values())
        
        duplicates = []
        
        # Compare all pairs
        for i, emb1 in enumerate(candidates):
            for emb2 in candidates[i+1:]:
                similarity = emb1.cosine_similarity(emb2)
                
                if similarity >= similarity_threshold:
                    duplicates.append((emb1, emb2, similarity))
        
        # Sort by similarity (descending)
        duplicates.sort(key=lambda x: x[2], reverse=True)
        
        return duplicates
    
    def stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        return {
            'total_embeddings': len(self.embeddings),
            'by_type': {
                entity_type.value: len(entity_ids)
                for entity_type, entity_ids in self.index_by_type.items()
            }
        }


# Convenience functions

def generate_all_embeddings(
    scenarios: List[CucumberScenario] = None,
    robot_tests: List[RobotTest] = None,
    pytest_tests: List[PytestTest] = None,
    include_granular: bool = True
) -> EmbeddingStore:
    """
    Generate embeddings for all test entities.
    
    Args:
        scenarios: Cucumber scenarios
        robot_tests: Robot tests
        pytest_tests: Pytest tests
        include_granular: Include step/keyword/assertion level embeddings
        
    Returns:
        EmbeddingStore with all embeddings
    """
    generator = EmbeddingGenerator()
    store = EmbeddingStore()
    
    # Cucumber
    if scenarios:
        scenario_gen = ScenarioEmbeddingGenerator(generator)
        
        for scenario in scenarios:
            # Scenario-level
            emb = scenario_gen.generate_scenario_embedding(scenario)
            store.add(emb)
            
            # Step-level
            if include_granular:
                for step in scenario.steps:
                    emb = scenario_gen.generate_step_embedding(
                        step, scenario.name, scenario.feature_name
                    )
                    store.add(emb)
    
    # Robot
    if robot_tests:
        robot_gen = RobotEmbeddingGenerator(generator)
        
        for test in robot_tests:
            # Test-level
            emb = robot_gen.generate_test_embedding(test)
            store.add(emb)
            
            # Keyword-level
            if include_granular:
                for kw in test.keywords:
                    emb = robot_gen.generate_keyword_embedding(
                        kw, test.name, test.suite_name
                    )
                    store.add(emb)
    
    # Pytest
    if pytest_tests:
        pytest_gen = PytestEmbeddingGenerator(generator)
        
        for test in pytest_tests:
            # Test-level
            emb = pytest_gen.generate_test_embedding(test)
            store.add(emb)
            
            # Assertion-level
            if include_granular:
                for assertion in test.assertions:
                    emb = pytest_gen.generate_assertion_embedding(
                        assertion, test.name, test.module
                    )
                    store.add(emb)
    
    logger.info(f"Generated embeddings: {store.stats()}")
    
    return store


# Example usage
if __name__ == "__main__":
    from core.execution.intelligence.cucumber_parser import CucumberJSONParser
    
    # Parse Cucumber scenarios
    parser = CucumberJSONParser()
    scenarios = parser.parse_file("cucumber.json")
    
    # Generate embeddings
    store = generate_all_embeddings(scenarios=scenarios, include_granular=True)
    
    print(f"Generated {store.stats()['total_embeddings']} embeddings")
    print(f"By type: {store.stats()['by_type']}")
    
    # Find similar scenarios
    if scenarios:
        generator = EmbeddingGenerator()
        scenario_gen = ScenarioEmbeddingGenerator(generator)
        
        query = scenario_gen.generate_scenario_embedding(scenarios[0])
        similar = store.find_similar(query, top_k=5, entity_type=EntityType.SCENARIO)
        
        print(f"\nTop 5 similar scenarios to '{scenarios[0].name}':")
        for emb, score in similar:
            print(f"  {emb.metadata['scenario_name']} (similarity: {score:.3f})")
    
    # Find duplicates
    duplicates = store.find_duplicates(entity_type=EntityType.SCENARIO, similarity_threshold=0.95)
    
    if duplicates:
        print(f"\nFound {len(duplicates)} potential duplicate scenarios:")
        for emb1, emb2, score in duplicates[:5]:
            print(f"  '{emb1.metadata['scenario_name']}' ≈ '{emb2.metadata['scenario_name']}' ({score:.3f})")
