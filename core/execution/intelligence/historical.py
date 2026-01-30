"""
Historical Frequency Tracking

Track failure patterns over time to improve confidence scoring and identify recurring issues.
Uses pattern hashing for deduplication and occurrence tracking.
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass

from core.execution.intelligence.models import FailureSignal


@dataclass
class PatternOccurrence:
    """Single occurrence of a failure pattern"""
    pattern_hash: str
    test_name: str
    timestamp: datetime
    run_id: Optional[str]
    signal_type: str
    confidence: float


@dataclass
class HistoricalPattern:
    """Aggregated historical pattern with frequency data"""
    pattern_hash: str
    pattern_summary: str
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    test_names: List[str]
    avg_confidence: float
    resolution_status: str  # OPEN, INVESTIGATING, RESOLVED, IGNORED


class PatternHasher:
    """Generate consistent hashes for failure patterns"""
    
    # Regex patterns to normalize messages before hashing
    NORMALIZATION_PATTERNS = [
        (r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}', 'TIMESTAMP'),  # Timestamps
        (r'\d+\.\d+\.\d+\.\d+', 'IP_ADDRESS'),  # IP addresses
        (r'port\s+\d+', 'PORT'),  # Port numbers
        (r'timeout\s+after\s+\d+', 'TIMEOUT'),  # Timeout values
        (r'line\s+\d+', 'LINE'),  # Line numbers
        (r'0x[0-9a-fA-F]+', 'HEX_ADDR'),  # Memory addresses
        (r'/[a-zA-Z0-9_\-/]+\.\w+:\d+', 'FILE_PATH'),  # File paths
        (r'expected:\s*\S+\s+actual:\s*\S+', 'ASSERTION_VALUES'),  # Assertion values
    ]
    
    @classmethod
    def normalize_message(cls, message: str) -> str:
        """Normalize message by removing variable parts"""
        normalized = message.lower()
        
        # Apply regex normalizations
        for pattern, replacement in cls.NORMALIZATION_PATTERNS:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    @classmethod
    def hash_pattern(cls, signal: FailureSignal) -> str:
        """Generate hash for failure pattern"""
        # Combine normalized message with signal type
        normalized = cls.normalize_message(signal.message)
        pattern_key = f"{signal.signal_type.value}::{normalized}"
        
        # Generate SHA-256 hash
        return hashlib.sha256(pattern_key.encode('utf-8')).hexdigest()[:16]
    
    @classmethod
    def extract_summary(cls, signal: FailureSignal, max_length: int = 200) -> str:
        """Extract human-readable pattern summary"""
        normalized = cls.normalize_message(signal.message)
        if len(normalized) <= max_length:
            return normalized
        return normalized[:max_length] + "..."


class HistoricalFrequencyTracker:
    """Track and query historical failure patterns"""
    
    def __init__(self, db_connection=None):
        """
        Initialize tracker.
        
        Args:
            db_connection: Database connection (optional, uses in-memory cache if None)
        """
        self.db = db_connection
        self._cache: Dict[str, HistoricalPattern] = {}
    
    def record_occurrence(self, signal: FailureSignal, run_id: Optional[str] = None,
                         test_name: Optional[str] = None) -> str:
        """
        Record a new occurrence of a failure pattern.
        
        Args:
            signal: Failure signal to record
            run_id: Test run identifier
            test_name: Test name
            
        Returns:
            Pattern hash
        """
        pattern_hash = PatternHasher.hash_pattern(signal)
        pattern_summary = PatternHasher.extract_summary(signal)
        now = datetime.now()
        
        if self.db:
            self._record_to_db(pattern_hash, pattern_summary, signal, run_id, test_name, now)
        else:
            self._record_to_cache(pattern_hash, pattern_summary, signal, test_name, now)
        
        return pattern_hash
    
    def _record_to_cache(self, pattern_hash: str, pattern_summary: str,
                        signal: FailureSignal, test_name: Optional[str], now: datetime):
        """Record occurrence to in-memory cache"""
        if pattern_hash in self._cache:
            pattern = self._cache[pattern_hash]
            pattern.occurrence_count += 1
            pattern.last_seen = now
            if test_name and test_name not in pattern.test_names:
                pattern.test_names.append(test_name)
            # Update rolling average confidence
            pattern.avg_confidence = (
                (pattern.avg_confidence * (pattern.occurrence_count - 1) + signal.confidence) /
                pattern.occurrence_count
            )
        else:
            self._cache[pattern_hash] = HistoricalPattern(
                pattern_hash=pattern_hash,
                pattern_summary=pattern_summary,
                first_seen=now,
                last_seen=now,
                occurrence_count=1,
                test_names=[test_name] if test_name else [],
                avg_confidence=signal.confidence,
                resolution_status='OPEN'
            )
    
    def _record_to_db(self, pattern_hash: str, pattern_summary: str,
                     signal: FailureSignal, run_id: Optional[str],
                     test_name: Optional[str], now: datetime):
        """Record occurrence to database"""
        # Insert into pattern_occurrences
        self.db.execute("""
            INSERT INTO pattern_occurrences 
            (pattern_hash, test_name, occurred_at, run_id, signal_type, confidence, message)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (pattern_hash, test_name, now, run_id, signal.signal_type.value,
              signal.confidence, signal.message))
        
        # Upsert into historical_patterns
        self.db.execute("""
            INSERT INTO historical_patterns 
            (pattern_hash, pattern_summary, first_seen, last_seen, occurrence_count, test_names, avg_confidence)
            VALUES (%s, %s, %s, %s, 1, %s, %s)
            ON CONFLICT (pattern_hash) DO UPDATE SET
                last_seen = EXCLUDED.last_seen,
                occurrence_count = historical_patterns.occurrence_count + 1,
                test_names = ARRAY(SELECT DISTINCT UNNEST(historical_patterns.test_names || EXCLUDED.test_names)),
                avg_confidence = (historical_patterns.avg_confidence * historical_patterns.occurrence_count + EXCLUDED.avg_confidence) / (historical_patterns.occurrence_count + 1)
        """, (pattern_hash, pattern_summary, now, now, [test_name] if test_name else [],
              signal.confidence))
    
    def get_frequency(self, signal: FailureSignal, lookback_days: int = 30) -> int:
        """
        Get occurrence frequency for a pattern in the last N days.
        
        Args:
            signal: Failure signal
            lookback_days: Number of days to look back
            
        Returns:
            Number of occurrences
        """
        pattern_hash = PatternHasher.hash_pattern(signal)
        
        if self.db:
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            result = self.db.execute("""
                SELECT COUNT(*) FROM pattern_occurrences
                WHERE pattern_hash = %s AND occurred_at > %s
            """, (pattern_hash, cutoff))
            return result[0][0] if result else 0
        else:
            # Cache-based (no time filtering)
            pattern = self._cache.get(pattern_hash)
            return pattern.occurrence_count if pattern else 0
    
    def get_pattern_details(self, pattern_hash: str) -> Optional[HistoricalPattern]:
        """Get detailed information about a pattern"""
        if self.db:
            result = self.db.execute("""
                SELECT pattern_hash, pattern_summary, first_seen, last_seen,
                       occurrence_count, test_names, avg_confidence, resolution_status
                FROM historical_patterns
                WHERE pattern_hash = %s
            """, (pattern_hash,))
            
            if result:
                row = result[0]
                return HistoricalPattern(
                    pattern_hash=row[0],
                    pattern_summary=row[1],
                    first_seen=row[2],
                    last_seen=row[3],
                    occurrence_count=row[4],
                    test_names=row[5],
                    avg_confidence=row[6],
                    resolution_status=row[7]
                )
        else:
            return self._cache.get(pattern_hash)
        
        return None
    
    def get_top_patterns(self, limit: int = 10,
                        status_filter: Optional[str] = None) -> List[HistoricalPattern]:
        """
        Get top recurring patterns by frequency.
        
        Args:
            limit: Maximum number of patterns to return
            status_filter: Filter by resolution status (OPEN, INVESTIGATING, etc.)
            
        Returns:
            List of historical patterns sorted by frequency
        """
        if self.db:
            where_clause = ""
            params = []
            if status_filter:
                where_clause = "WHERE resolution_status = %s"
                params.append(status_filter)
            
            result = self.db.execute(f"""
                SELECT pattern_hash, pattern_summary, first_seen, last_seen,
                       occurrence_count, test_names, avg_confidence, resolution_status
                FROM historical_patterns
                {where_clause}
                ORDER BY occurrence_count DESC
                LIMIT %s
            """, params + [limit])
            
            return [
                HistoricalPattern(
                    pattern_hash=row[0],
                    pattern_summary=row[1],
                    first_seen=row[2],
                    last_seen=row[3],
                    occurrence_count=row[4],
                    test_names=row[5],
                    avg_confidence=row[6],
                    resolution_status=row[7]
                )
                for row in result
            ]
        else:
            patterns = list(self._cache.values())
            if status_filter:
                patterns = [p for p in patterns if p.resolution_status == status_filter]
            patterns.sort(key=lambda p: p.occurrence_count, reverse=True)
            return patterns[:limit]
    
    def update_resolution_status(self, pattern_hash: str, new_status: str) -> bool:
        """
        Update resolution status for a pattern.
        
        Args:
            pattern_hash: Pattern identifier
            new_status: New status (OPEN, INVESTIGATING, RESOLVED, IGNORED)
            
        Returns:
            True if updated successfully
        """
        if self.db:
            self.db.execute("""
                UPDATE historical_patterns
                SET resolution_status = %s, resolved_at = CASE WHEN %s = 'RESOLVED' THEN NOW() ELSE NULL END
                WHERE pattern_hash = %s
            """, (new_status, new_status, pattern_hash))
            return True
        else:
            if pattern_hash in self._cache:
                self._cache[pattern_hash].resolution_status = new_status
                return True
        
        return False
    
    def calculate_frequency_boost(self, signal: FailureSignal, lookback_days: int = 30) -> float:
        """
        Calculate confidence boost based on historical frequency.
        Uses logarithmic scaling: boost = log(1 + frequency) / log(1 + 20)
        
        Args:
            signal: Failure signal
            lookback_days: Number of days to look back
            
        Returns:
            Confidence boost (0.0 to ~1.0)
        """
        import math
        
        frequency = self.get_frequency(signal, lookback_days)
        if frequency <= 1:
            return 0.0
        
        # Logarithmic scaling: frequent patterns get higher boost
        boost = math.log1p(frequency) / math.log1p(20)
        return min(boost, 1.0)


# Global tracker instance
_tracker: Optional[HistoricalFrequencyTracker] = None


def initialize_tracker(db_connection=None):
    """Initialize global tracker"""
    global _tracker
    _tracker = HistoricalFrequencyTracker(db_connection)


def get_tracker() -> HistoricalFrequencyTracker:
    """Get global tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = HistoricalFrequencyTracker()
    return _tracker
