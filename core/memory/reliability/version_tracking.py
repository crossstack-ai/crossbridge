"""
Embedding Version Tracking.

Tracks embedding versions to detect when reindexing is needed due to:
- Schema changes (how embeddings are structured)
- Content changes (what information is embedded)
- Model changes (embedding provider/model upgrades)
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingVersion:
    """
    Semantic version for embeddings.
    
    Format: <schema_version>::<content_version>::<model_family>
    
    Examples:
        v1::text-only::openai
        v2::text+ast::anthropic
        v3::text+ast+exec::openai
    """
    schema_version: str      # v1, v2, v3 - structural changes
    content_version: str     # what's embedded (text-only, text+ast, etc.)
    model_family: str        # provider (openai, anthropic, local, etc.)
    
    def __str__(self) -> str:
        return f"{self.schema_version}::{self.content_version}::{self.model_family}"
    
    @classmethod
    def from_string(cls, version_str: str) -> 'EmbeddingVersion':
        """Parse version string."""
        try:
            parts = version_str.split("::")
            if len(parts) != 3:
                raise ValueError(f"Invalid format: {version_str}")
            return cls(schema_version=parts[0], content_version=parts[1], model_family=parts[2])
        except Exception as e:
            logger.error(f"Failed to parse version '{version_str}': {e}")
            raise
    
    def is_compatible_with(self, other: 'EmbeddingVersion') -> bool:
        """Check if two versions can be compared (same schema/content)."""
        return (
            self.schema_version == other.schema_version and
            self.content_version == other.content_version
        )


# Current version constants (from existing EMBEDDING_VERSION in semantic_service.py)
SCHEMA_VERSION = "v1"
CONTENT_VERSION = "text-only"  # Matches existing text_builder behavior
MODEL_FAMILY = "openai"        # Default provider

CURRENT_VERSION = EmbeddingVersion(
    schema_version=SCHEMA_VERSION,
    content_version=CONTENT_VERSION,
    model_family=MODEL_FAMILY
)


def get_current_version(model_family: Optional[str] = None) -> EmbeddingVersion:
    """Get current version with optional model family override."""
    if model_family:
        return EmbeddingVersion(SCHEMA_VERSION, CONTENT_VERSION, model_family)
    return CURRENT_VERSION


class VersionTracker:
    """Tracks embedding versions in the database."""
    
    def __init__(self, vector_store):
        """
        Initialize version tracker.
        
        Args:
            vector_store: Existing VectorStore instance from core.memory
        """
        self.vector_store = vector_store
    
    def get_version(self, record_id: str) -> Optional[EmbeddingVersion]:
        """
        Get embedding version for a record.
        
        Args:
            record_id: Memory record ID
            
        Returns:
            EmbeddingVersion if found, None otherwise
        """
        # Version would be stored in MemoryRecord.metadata
        record = self.vector_store.get(record_id)
        if not record or not record.metadata:
            return None
        
        version_str = record.metadata.get('embedding_version')
        if not version_str:
            return None
        
        try:
            return EmbeddingVersion.from_string(version_str)
        except Exception:
            return None
    
    def is_current(self, record_id: str, expected_version: Optional[EmbeddingVersion] = None) -> bool:
        """
        Check if record's embedding is current version.
        
        Args:
            record_id: Memory record ID
            expected_version: Version to check against (defaults to CURRENT_VERSION)
            
        Returns:
            True if embedding is current version
        """
        if expected_version is None:
            expected_version = CURRENT_VERSION
        
        record_version = self.get_version(record_id)
        if not record_version:
            return False  # No version = stale
        
        return str(record_version) == str(expected_version)
