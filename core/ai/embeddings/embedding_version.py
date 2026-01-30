"""
Embedding Version Management

Tracks embedding versions for reindexing and compatibility.
Critical for production: never mix embeddings from different versions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional


# Current embedding version - increment when text builder or model changes
EMBEDDING_VERSION = "v2-text+ast"

# Version history for backward compatibility
VERSION_HISTORY = {
    "v1-text": {
        "description": "Basic text-only embeddings",
        "text_builder": "basic",
        "ast_augmentation": False,
        "deprecated": True,
        "deprecated_date": "2026-01-15"
    },
    "v2-text+ast": {
        "description": "Text embeddings with AST augmentation",
        "text_builder": "enhanced",
        "ast_augmentation": True,
        "deprecated": False,
        "introduced_date": "2026-01-31"
    }
}


@dataclass
class EmbeddingVersionInfo:
    """
    Embedding version metadata
    
    Stores version info with every embedded entity for:
    - Reindexing detection
    - Compatibility checks
    - Migration planning
    """
    version: str
    model: str                # e.g., "text-embedding-3-large"
    dimensions: int           # e.g., 3072
    text_builder: str         # Text builder variant used
    ast_augmented: bool       # Whether AST was included
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "version": self.version,
            "model": self.model,
            "dimensions": self.dimensions,
            "text_builder": self.text_builder,
            "ast_augmented": self.ast_augmented,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingVersionInfo":
        """Create from dictionary"""
        return cls(
            version=data["version"],
            model=data["model"],
            dimensions=data["dimensions"],
            text_builder=data["text_builder"],
            ast_augmented=data["ast_augmented"],
            created_at=datetime.fromisoformat(data["created_at"])
        )
    
    def is_compatible_with(self, other: "EmbeddingVersionInfo") -> bool:
        """
        Check if this version is compatible with another
        
        Compatible means:
        - Same version string
        - Same model
        - Same dimensions
        """
        return (
            self.version == other.version and
            self.model == other.model and
            self.dimensions == other.dimensions
        )


def get_current_version_info(
    model: str,
    dimensions: int,
    ast_augmented: bool = True
) -> EmbeddingVersionInfo:
    """
    Get current version info
    
    Args:
        model: Embedding model name
        dimensions: Vector dimensions
        ast_augmented: Whether AST augmentation is enabled
    
    Returns:
        Current embedding version info
    """
    version_data = VERSION_HISTORY[EMBEDDING_VERSION]
    
    return EmbeddingVersionInfo(
        version=EMBEDDING_VERSION,
        model=model,
        dimensions=dimensions,
        text_builder=version_data["text_builder"],
        ast_augmented=ast_augmented,
        created_at=datetime.now(timezone.utc)
    )


def is_version_deprecated(version: str) -> bool:
    """
    Check if a version is deprecated
    
    Args:
        version: Version string to check
    
    Returns:
        True if deprecated
    """
    if version not in VERSION_HISTORY:
        return True  # Unknown versions are considered deprecated
    
    return VERSION_HISTORY[version].get("deprecated", False)


def get_version_info(version: str) -> Optional[Dict[str, Any]]:
    """
    Get version information
    
    Args:
        version: Version string
    
    Returns:
        Version metadata or None if not found
    """
    return VERSION_HISTORY.get(version)
