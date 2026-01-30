"""
Entity Fingerprinting for Change Detection.

Provides lightweight, deterministic fingerprints to detect when
entity content has changed and embeddings need refreshing.
"""

import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def compute_fingerprint(text: str) -> str:
    """
    Compute SHA-256 fingerprint of text.
    
    Args:
        text: Entity text representation
        
    Returns:
        Hex string fingerprint (64 chars)
    """
    if not text:
        return ""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class FingerprintTracker:
    """
    Tracks entity fingerprints to detect changes.
    
    Integrates with existing MemoryRecord.metadata to store fingerprints.
    """
    
    def __init__(self, vector_store):
        """
        Initialize fingerprint tracker.
        
        Args:
            vector_store: Existing VectorStore instance from core.memory
        """
        self.vector_store = vector_store
    
    def compute_and_store(self, record_id: str, text: str) -> str:
        """
        Compute fingerprint and store in metadata.
        
        Args:
            record_id: Memory record ID
            text: Entity text
            
        Returns:
            Computed fingerprint
        """
        fingerprint = compute_fingerprint(text)
        
        # Store in metadata (would need to update record)
        record = self.vector_store.get(record_id)
        if record:
            if not record.metadata:
                record.metadata = {}
            record.metadata['fingerprint'] = fingerprint
            record.metadata['fingerprint_updated_at'] = datetime.utcnow().isoformat()
        
        return fingerprint
    
    def get_fingerprint(self, record_id: str) -> Optional[str]:
        """
        Get stored fingerprint for record.
        
        Args:
            record_id: Memory record ID
            
        Returns:
            Stored fingerprint or None
        """
        record = self.vector_store.get(record_id)
        if not record or not record.metadata:
            return None
        return record.metadata.get('fingerprint')
    
    def has_changed(self, record_id: str, current_text: str) -> bool:
        """
        Check if entity text has changed since last fingerprint.
        
        Args:
            record_id: Memory record ID
            current_text: Current entity text
            
        Returns:
            True if content has changed
        """
        stored_fingerprint = self.get_fingerprint(record_id)
        if not stored_fingerprint:
            return True  # No fingerprint = assume changed
        
        current_fingerprint = compute_fingerprint(current_text)
        return current_fingerprint != stored_fingerprint
