"""
Reindexing Management for Embeddings.

Manages automatic reindexing of stale embeddings through:
- Job queue for reindex tasks
- Reason tracking
- Priority handling
- Integration with existing ingestion pipeline
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from queue import PriorityQueue
import logging

from core.memory.models import MemoryType

logger = logging.getLogger(__name__)


class ReindexReason(str, Enum):
    """Reasons for reindexing."""
    VERSION_UPGRADE = "version_upgrade"
    CONTENT_CHANGED = "content_changed"
    AGE_THRESHOLD = "age_threshold"
    DRIFT_DETECTED = "drift_detected"
    MANUAL_REQUEST = "manual_request"
    SCHEMA_MIGRATION = "schema_migration"


@dataclass
class ReindexJob:
    """Reindexing job for a single entity."""
    entity_id: str
    entity_type: MemoryType
    reason: ReindexReason
    priority: int = 50  # 0-100, higher = more urgent
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue ordering (higher priority first)."""
        return self.priority > other.priority


class ReindexQueue:
    """Priority queue for reindex jobs."""
    
    def __init__(self, max_size: int = 10000):
        self.queue: PriorityQueue = PriorityQueue(maxsize=max_size)
        self.processed_ids: set = set()  # Avoid duplicate processing
    
    def add(self, job: ReindexJob) -> bool:
        """
        Add job to queue.
        
        Args:
            job: ReindexJob to add
            
        Returns:
            True if added, False if duplicate or queue full
        """
        if job.entity_id in self.processed_ids:
            logger.debug(f"Skipping duplicate reindex job: {job.entity_id}")
            return False
        
        try:
            self.queue.put_nowait(job)
            self.processed_ids.add(job.entity_id)
            logger.info(
                f"Added reindex job: {job.entity_id} "
                f"(reason={job.reason.value}, priority={job.priority})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add reindex job: {e}")
            return False
    
    def get(self, timeout: Optional[float] = None) -> Optional[ReindexJob]:
        """
        Get next job from queue.
        
        Args:
            timeout: Timeout in seconds (None = block indefinitely)
            
        Returns:
            Next ReindexJob or None if queue empty (non-blocking)
        """
        try:
            if timeout is None:
                return self.queue.get_nowait()
            return self.queue.get(timeout=timeout)
        except Exception:
            return None
    
    def size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()
    
    def clear_processed(self):
        """Clear processed IDs tracking (for long-running workers)."""
        self.processed_ids.clear()


class ReindexManager:
    """
    Manages reindexing lifecycle.
    
    Coordinates staleness detection, job queuing, and integration
    with existing ingestion pipeline.
    """
    
    def __init__(
        self,
        vector_store,
        staleness_detector,
        drift_detector,
        queue: Optional[ReindexQueue] = None
    ):
        """
        Initialize reindex manager.
        
        Args:
            vector_store: Existing VectorStore from core.memory
            staleness_detector: StalenessDetector instance
            drift_detector: DriftDetector instance
            queue: Reindex queue (created if None)
        """
        self.vector_store = vector_store
        self.staleness_detector = staleness_detector
        self.drift_detector = drift_detector
        self.queue = queue or ReindexQueue()
    
    def check_and_queue_stale(
        self,
        entity_id: str,
        entity_type: MemoryType,
        current_text: Optional[str] = None
    ) -> bool:
        """
        Check if entity needs reindexing and queue if stale.
        
        Args:
            entity_id: Entity identifier
            entity_type: Entity type
            current_text: Current entity text (for fingerprint check)
            
        Returns:
            True if queued for reindexing
        """
        stale_info = self.staleness_detector.is_stale(entity_id, current_text)
        
        if not stale_info:
            return False  # Not stale
        
        # Map staleness reason to reindex reason
        reason_map = {
            "version_mismatch": ReindexReason.VERSION_UPGRADE,
            "content_changed": ReindexReason.CONTENT_CHANGED,
            "age_threshold": ReindexReason.AGE_THRESHOLD,
            "no_version": ReindexReason.VERSION_UPGRADE,
            "no_embedding": ReindexReason.CONTENT_CHANGED,
        }
        
        reindex_reason = reason_map.get(
            stale_info.reason.value,
            ReindexReason.MANUAL_REQUEST
        )
        
        # Determine priority
        priority = self._calculate_priority(stale_info.reason)
        
        # Create and queue job
        job = ReindexJob(
            entity_id=entity_id,
            entity_type=entity_type,
            reason=reindex_reason,
            priority=priority,
            metadata={
                'staleness_reason': stale_info.reason.value,
                'age_days': stale_info.age_days
            }
        )
        
        return self.queue.add(job)
    
    def queue_for_drift(
        self,
        entity_id: str,
        entity_type: MemoryType,
        similarity_score: float
    ) -> bool:
        """
        Queue entity for reindexing due to semantic drift.
        
        Args:
            entity_id: Entity identifier
            entity_type: Entity type
            similarity_score: Drift similarity score
            
        Returns:
            True if queued
        """
        job = ReindexJob(
            entity_id=entity_id,
            entity_type=entity_type,
            reason=ReindexReason.DRIFT_DETECTED,
            priority=70,  # High priority
            metadata={'drift_score': similarity_score}
        )
        return self.queue.add(job)
    
    def _calculate_priority(self, reason: str) -> int:
        """
        Calculate job priority based on staleness reason.
        
        Args:
            reason: Staleness reason
            
        Returns:
            Priority (0-100)
        """
        priority_map = {
            "version_mismatch": 80,     # High - schema changed
            "content_changed": 60,      # Medium-high - entity updated
            "no_version": 40,           # Medium - missing metadata
            "age_threshold": 30,        # Medium-low - just old
            "no_embedding": 50,         # Medium - needs initial embedding
            "manual_stale": 70,         # High - user requested
        }
        return priority_map.get(reason, 50)
    
    def process_next_job(
        self,
        embedding_provider,
        text_builder
    ) -> bool:
        """
        Process next reindex job from queue.
        
        This would integrate with existing ingestion.py pipeline.
        
        Args:
            embedding_provider: Provider from core.memory.embedding_provider
            text_builder: Text builder from core.ai.embeddings.text_builder
            
        Returns:
            True if job processed, False if queue empty
        """
        job = self.queue.get(timeout=0.1)
        if not job:
            return False
        
        logger.info(
            f"Processing reindex job: {job.entity_id} "
            f"(reason={job.reason.value})"
        )
        
        # This would call existing ingestion logic
        # For now, just log
        logger.info(f"Reindexing {job.entity_id} - would call ingestion pipeline")
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reindexing statistics."""
        return {
            'queue_size': self.queue.size(),
            'processed_count': len(self.queue.processed_ids)
        }
