"""
Data models for BDD scenario outline processing.

Framework-agnostic models for representing Scenario Outlines,
Examples tables, and expanded scenarios.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class ExamplesTable:
    """
    Represents an Examples table in a Scenario Outline.
    
    Attributes:
        headers: Column names from the Examples table (e.g., ["username", "password", "result"])
        rows: List of data rows, each row is a dict mapping header -> value
    """
    headers: tuple[str, ...]  # Immutable for safety
    rows: tuple[tuple[Any, ...], ...]  # Immutable list of rows
    
    def __post_init__(self):
        """Validate that all rows have the same length as headers."""
        for i, row in enumerate(self.rows):
            if len(row) != len(self.headers):
                raise ValueError(
                    f"Row {i} has {len(row)} values but {len(self.headers)} headers"
                )
    
    def get_row_dict(self, row_index: int) -> Dict[str, Any]:
        """
        Get a specific row as a dictionary mapping header -> value.
        
        Args:
            row_index: Index of the row to retrieve (0-based)
            
        Returns:
            Dictionary mapping column name to value for the specified row
        """
        if row_index < 0 or row_index >= len(self.rows):
            raise IndexError(f"Row index {row_index} out of range")
        return dict(zip(self.headers, self.rows[row_index]))


@dataclass(frozen=True)
class ScenarioOutline:
    """
    Represents a Scenario Outline with parameterized steps.
    
    Attributes:
        name: The scenario outline name (e.g., "User logs in")
        steps: List of step templates with placeholders (e.g., ["login with <username> and <password>"])
        tags: Optional tags for the scenario outline
    """
    name: str
    steps: tuple[str, ...]  # Immutable for safety
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExpandedScenario:
    """
    Represents a single concrete scenario expanded from a Scenario Outline.
    
    Each ExpandedScenario corresponds to one row in the Examples table,
    with all placeholders replaced by actual values.
    
    Attributes:
        name: Scenario name with parameter values (e.g., "User logs in [admin/admin123]")
        steps: Steps with placeholders replaced (e.g., ["login with admin and admin123"])
        parameters: Dictionary of parameter name -> value from the Examples row
        tags: Tags inherited from the original Scenario Outline
        original_outline_name: Name of the original Scenario Outline
    """
    name: str
    steps: tuple[str, ...]
    parameters: Dict[str, Any]
    tags: tuple[str, ...] = field(default_factory=tuple)
    original_outline_name: str = ""
