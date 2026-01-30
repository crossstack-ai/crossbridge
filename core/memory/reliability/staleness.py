"""
Staleness Detection for Embeddings.

Detects when embeddings are stale and need reindexing based on:
- Version changes
- Content changes (fingerprint mismatch)
- Age thresholds
- Manual staleness flags
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import logging

from .version_tracking import VersionTracker, CURRENT_VERSION
from .fingerprint import FingerprintTracker

logger = logging.getLogger(__name__)


class StalenessReason(str, Enum):
    """Reasons why an embedding might be stale."""
    VERSION_MISMATCH = "version_mismatch"
    CONTENT_CHANGED = "content_changed"
    AGE_THRESHOLD = "age_threshold"
    MANUAL_STALE = "manual_stale"
    NO_VERSION = "no_version"
    NO_EMBEDDING = "no_embedding"


@dataclass
class StaleEmbedding:
    """Information about a stale embedding."""
    record_id: str
    reason: StalenessReason
    current_version: Optional[str] = None
    stored_version: Optional[str] = None
    age_days: Optional[int] = None
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()


class StalenessDetector:
    """
    Detects stale embeddings that need reindexing.
    
    Integrates with existing MemoryRecord and VectorStore.
    """
    
    def __init__(
        self,
        vector_store,
        max_age_days: int = 90,  # Configurable via crossbridge.yml
        version_tracker: Optional[VersionTracker] = None,
        fingerprint_tracker: Optional[FingerprintTracker] = None
    ):
        """
        Initialize staleness detector.
        
        Args:
            vector_store: Existing VectorStore from core.memory
            max_age_days: Maximum age before embedding considered stale
            version_tracker: Version tracker (created if None)
            fingerprint_tracker: Fingerprint tracker (created if None)
        """
        self.vector_store = vector_store
        self.max_age_days = max_age_days
        self.version_tracker = version_tracker or VersionTracker(vector_store)
        self.fingerprint_tracker = fingerprint_tracker or FingerprintTracker(vector_store)
    
    def is_stale(
        self,
        record_id: str,
        current_text: Optional[str] = None
    ) -> Optional[StaleEmbedding]:
        """
        Check if embedding is stale.
        
        Args:
            record_id: Memory record ID
            current_text: Current entity text (for fingerprint check)
            
        Returns:
            StaleEmbedding if stale, None if fresh
        """
        record = self.vector_store.get(record_id)
        
        if not record:
            return StaleEmbedding(
                record_id=record_id,
                reason=StalenessReason.NO_EMBEDDING
            )
        
        # Check 1: No embedding vector
        if not record.embedding:
            return StaleEmbedding(
                record_id=record_id,
                reason=StalenessReason.NO_EMBEDDING
            )
        
        # Check 2: No version info
        if not record.metadata or 'embedding_version' not in record.metadata:
            return StaleEmbedding(
                record_id=record_id,
                reason=StalenessReason.NO_VERSION
            )
        
        # Check 3: Version mismatch
        stored_version = record.metadata.get('embedding_version')
        if stored_version != str(CURRENT_VERSION):
            return StaleEmbedding(
                record_id=record_id,
                reason=StalenessReason.VERSION_MISMATCH,
                current_version=str(CURRENT_VERSION),
                stored_version=stored_version
            )
        
        # Check 4: Content changed (fingerprint mismatch)
        if current_text:
            if self.fingerprint_tracker.has_changed(record_id, current_text):
                return StaleEmbedding(
                    record_id=record_id,
                    reason=StalenessReason.CONTENT_CHANGED
                )
        
        # Check 5: Age threshold exceeded
        if record.updated_at:
            age = datetime.utcnow() - record.updated_at
            if age.days > self.max_age_days:
                return StaleEmbedding(
                    record_id=record_id,
                    reason=StalenessReason.AGE_THRESHOLD,
                    age_days=age.days
                )
        
        # Check 6: Manual stale flag
        if record.metadata.get('manually_stale'):
            return StaleEmbedding(
                record_id=record_id,
                reason=StalenessReason.MANUAL_STALE
            )
        
        # Fresh!
        return None
    
    def mark_stale(self, record_id: str):
        """
        Manually mark embedding as stale.
        
        Args:
            record_id: Memory record ID
        """
        record = self.vector_store.get(record_id)
        if record:
            if not record.metadata:
                record.metadata = {}
            record.metadata['manually_stale'] = True
            record.metadata['stale_marked_at'] = datetime.utcnow().isoformat()
            logger.info(f"Marked embedding as stale: {record_id}")
    
    def clear_stale_flag(self, record_id: str):
        """
        Clear manual stale flag.
        
        Args:
            record_id: Memory record ID
        """
        record = self.vector_store.get(record_id)
        if record and record.metadata:
            record.metadata.pop('manually_stale', None)
            record.metadata.pop('stale_marked_at', None)
