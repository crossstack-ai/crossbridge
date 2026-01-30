"""
Core data models for the Memory and Embeddings system.

These models represent the canonical structure for storing and retrieving
test-related knowledge in CrossBridge.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryType(str, Enum):
    """Types of memory records that can be stored."""

    TEST = "test"  # Test case (method, function)
    SCENARIO = "scenario"  # BDD scenario
    STEP = "step"  # Test step or BDD step
    PAGE = "page"  # Page object or component
    CODE = "code"  # Code coverage unit
    FAILURE = "failure"  # Test failure record
    ASSERTION = "assertion"  # Assertion statement
    LOCATOR = "locator"  # UI locator/selector


@dataclass
class MemoryRecord:
    """
    Canonical representation of a memory unit in CrossBridge.
    
    This is the core data structure that everything builds upon.
    Each record represents a semantic unit (test, scenario, step, etc.)
    that can be embedded and searched.
    """

    id: str  # Stable unique identifier (e.g., "test_login_valid", "scenario_checkout")
    type: MemoryType  # Entity type
    text: str  # Natural language representation for embedding
    metadata: Dict[str, Any]  # Framework, file, tags, intent, etc.
    embedding: Optional[List[float]] = None  # Vector representation (filled by provider)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate and normalize the record."""
        if not self.id:
            raise ValueError("MemoryRecord.id cannot be empty")
        if not self.text:
            raise ValueError("MemoryRecord.text cannot be empty")
        if isinstance(self.type, str):
            self.type = MemoryType(self.type)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "text": self.text,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=MemoryType(data["type"]),
            text=data["text"],
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else datetime.utcnow(),
        )


@dataclass
class SearchResult:
    """
    Result from semantic search query.
    
    Contains the memory record and relevance score.
    """

    record: MemoryRecord
    score: float  # Similarity score (0-1, higher is better)
    rank: int  # Position in results (1-based)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.record.id,
            "type": self.record.type.value,
            "text": self.record.text,
            "metadata": self.record.metadata,
            "score": self.score,
            "rank": self.rank,
        }


# Text construction helpers for different entity types


def convert_test_to_text(test_data: Dict[str, Any]) -> str:
    """Convert test metadata to natural language text for embedding."""
    parts = [f"Test Name: {test_data.get('name', 'unknown')}"]

    if framework := test_data.get("framework"):
        parts.append(f"Framework: {framework}")

    if steps := test_data.get("steps"):
        parts.append(f"Steps: {', '.join(steps)}")

    if intent := test_data.get("intent"):
        parts.append(f"Purpose: {intent}")

    if description := test_data.get("description"):
        parts.append(f"Description: {description}")

    if tags := test_data.get("tags"):
        parts.append(f"Tags: {', '.join(tags)}")

    return "\n".join(parts)


def scenario_to_text(scenario_data: Dict[str, Any]) -> str:
    """Convert BDD scenario to natural language text for embedding."""
    parts = [f"Scenario: {scenario_data.get('name', 'unknown')}"]

    if feature := scenario_data.get("feature"):
        parts.append(f"Feature: {feature}")

    if steps := scenario_data.get("steps"):
        parts.append("Steps:")
        parts.extend([f"  - {step}" for step in steps])

    if tags := scenario_data.get("tags"):
        parts.append(f"Tags: {', '.join(tags)}")

    return "\n".join(parts)


def step_to_text(step_data: Dict[str, Any]) -> str:
    """Convert test step to natural language text for embedding."""
    parts = [f"Step: {step_data.get('text', 'unknown')}"]

    if keyword := step_data.get("keyword"):
        parts.insert(0, f"Type: {keyword}")

    if context := step_data.get("context"):
        parts.append(f"Context: {context}")

    if action := step_data.get("action"):
        parts.append(f"Action: {action}")

    return "\n".join(parts)


def page_to_text(page_data: Dict[str, Any]) -> str:
    """Convert page object to natural language text for embedding."""
    parts = [f"Page: {page_data.get('name', 'unknown')}"]

    if methods := page_data.get("methods"):
        parts.append(f"Methods: {', '.join(methods)}")

    if locators := page_data.get("locators"):
        parts.append(f"Elements: {', '.join(locators.keys())}")

    if purpose := page_data.get("purpose"):
        parts.append(f"Purpose: {purpose}")

    return "\n".join(parts)


def failure_to_text(failure_data: Dict[str, Any]) -> str:
    """Convert test failure to natural language text for embedding."""
    parts = [f"Test Failure: {failure_data.get('test_name', 'unknown')}"]

    if error_type := failure_data.get("error_type"):
        parts.append(f"Error: {error_type}")

    if message := failure_data.get("message"):
        parts.append(f"Message: {message}")

    if context := failure_data.get("context"):
        parts.append(f"Context: {context}")

    if stack_trace := failure_data.get("stack_trace"):
        # Only include first few lines of stack trace
        stack_lines = stack_trace.split("\n")[:3]
        parts.append(f"Stack: {'; '.join(stack_lines)}")

    return "\n".join(parts)
