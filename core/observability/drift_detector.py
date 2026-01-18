"""
Drift Detection System

Automatically detects changes in test behavior, coverage gaps, and anomalies.

Detectors:
- New test detected
- Test removed (no events for N days)
- Behavior change (duration / steps / APIs differ)
- Coverage gap introduced
- Flakiness increase
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from .events import CrossBridgeEvent

logger = logging.getLogger(__name__)


@dataclass
class DriftSignal:
    """Represents a detected drift/anomaly"""
    signal_type: str  # new_test | removed_test | behavior_change | coverage_gap | flaky
    test_id: str
    severity: str  # low | medium | high
    description: str
    metadata: dict
    detected_at: datetime


class DriftDetector:
    """
    Detects drift and anomalies in test execution patterns.
    
    This feeds the AI layer and provides actionable signals for:
    - Test maintenance
    - Coverage optimization
    - Risk assessment
    """
    
    def __init__(self, db_connection=None):
        self.db_connection = db_connection
        self.test_registry: Dict[str, dict] = {}
        self.test_history: Dict[str, List[CrossBridgeEvent]] = {}
    
    def analyze_event(self, event: CrossBridgeEvent) -> List[DriftSignal]:
        """
        Analyze event for drift signals.
        
        Returns:
            List of detected drift signals
        """
        signals = []
        
        # Check for new test
        if self._is_new_test(event):
            signals.append(self._create_new_test_signal(event))
        
        # Check for behavior changes
        if event.event_type == "test_end":
            behavior_signal = self._check_behavior_change(event)
            if behavior_signal:
                signals.append(behavior_signal)
        
        # Update history
        self._update_history(event)
        
        return signals
    
    def _is_new_test(self, event: CrossBridgeEvent) -> bool:
        """Check if this is a new test (never seen before)"""
        test_id = event.test_id
        
        if test_id in self.test_registry:
            return False
        
        # Check database for historical data
        if self.db_connection:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM test_execution_event 
                WHERE test_id = %s
            """, (test_id,))
            count = cursor.fetchone()[0]
            cursor.close()
            
            if count > 0:
                # Seen before - register locally
                self.test_registry[test_id] = {
                    'first_seen': datetime.utcnow(),
                    'framework': event.framework
                }
                return False
        
        # Truly new test
        self.test_registry[test_id] = {
            'first_seen': datetime.utcnow(),
            'framework': event.framework
        }
        return True
    
    def _create_new_test_signal(self, event: CrossBridgeEvent) -> DriftSignal:
        """Create signal for new test detection"""
        return DriftSignal(
            signal_type='new_test',
            test_id=event.test_id,
            severity='low',
            description=f"New test detected: {event.test_id}",
            metadata={
                'framework': event.framework,
                'first_seen': datetime.utcnow().isoformat(),
                'version': event.application_version,
                'product': event.product_name
            },
            detected_at=datetime.utcnow()
        )
    
    def _check_behavior_change(self, event: CrossBridgeEvent) -> Optional[DriftSignal]:
        """Check if test behavior has changed significantly"""
        test_id = event.test_id
        
        # Need history to compare
        if test_id not in self.test_history or len(self.test_history[test_id]) < 5:
            return None
        
        # Get historical baseline
        history = self.test_history[test_id][-10:]  # Last 10 executions
        avg_duration = sum(e.duration_ms or 0 for e in history) / len(history)
        
        # Check duration change
        if event.duration_ms and avg_duration > 0:
            change_percent = abs(event.duration_ms - avg_duration) / avg_duration * 100
            
            if change_percent > 50:  # 50% change threshold
                return DriftSignal(
                    signal_type='behavior_change',
                    test_id=test_id,
                    severity='medium',
                    description=f"Test duration changed by {change_percent:.1f}%",
                    metadata={
                        'current_duration_ms': event.duration_ms,
                        'avg_duration_ms': avg_duration,
                        'change_percent': change_percent,
                        'framework': event.framework
                    },
                    detected_at=datetime.utcnow()
                )
        
        return None
    
    def detect_removed_tests(self, inactive_days: int = 7) -> List[DriftSignal]:
        """
        Detect tests that haven't run in N days (potentially removed).
        
        Args:
            inactive_days: Number of days without events to consider removed
        """
        if not self.db_connection:
            return []
        
        signals = []
        cutoff_date = datetime.utcnow() - timedelta(days=inactive_days)
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT DISTINCT test_id, MAX(created_at) as last_seen
            FROM test_execution_event
            GROUP BY test_id
            HAVING MAX(created_at) < %s
        """, (cutoff_date,))
        
        for row in cursor.fetchall():
            test_id, last_seen = row
            signals.append(DriftSignal(
                signal_type='removed_test',
                test_id=test_id,
                severity='low',
                description=f"Test inactive for {inactive_days}+ days",
                metadata={
                    'last_seen': last_seen.isoformat(),
                    'days_inactive': (datetime.utcnow() - last_seen).days
                },
                detected_at=datetime.utcnow()
            ))
        
        cursor.close()
        return signals
    
    def detect_flakiness(self, test_id: str, window_size: int = 10) -> Optional[DriftSignal]:
        """
        Detect if test has become flaky (pass/fail oscillation).
        
        Args:
            test_id: Test to analyze
            window_size: Number of recent executions to examine
        """
        if not self.db_connection:
            return None
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT status 
            FROM test_execution_event
            WHERE test_id = %s AND event_type = 'test_end'
            ORDER BY created_at DESC
            LIMIT %s
        """, (test_id, window_size))
        
        statuses = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        if len(statuses) < window_size:
            return None
        
        # Calculate flakiness: number of status changes
        changes = sum(1 for i in range(len(statuses) - 1) if statuses[i] != statuses[i + 1])
        flakiness_rate = changes / (len(statuses) - 1)
        
        if flakiness_rate > 0.3:  # 30% status change rate
            return DriftSignal(
                signal_type='flaky',
                test_id=test_id,
                severity='high',
                description=f"Test shows flaky behavior: {flakiness_rate*100:.1f}% status changes",
                metadata={
                    'flakiness_rate': flakiness_rate,
                    'recent_statuses': statuses,
                    'window_size': window_size
                },
                detected_at=datetime.utcnow()
            )
        
        return None
    
    def _update_history(self, event: CrossBridgeEvent):
        """Update local event history for pattern detection"""
        test_id = event.test_id
        
        if test_id not in self.test_history:
            self.test_history[test_id] = []
        
        self.test_history[test_id].append(event)
        
        # Keep only recent history (last 20 events)
        if len(self.test_history[test_id]) > 20:
            self.test_history[test_id] = self.test_history[test_id][-20:]
    
    def get_all_signals(self, project_id: str) -> List[DriftSignal]:
        """Get all active drift signals for a project"""
        signals = []
        
        # Check for removed tests
        signals.extend(self.detect_removed_tests(inactive_days=7))
        
        # Check for flaky tests
        if self.db_connection:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT DISTINCT test_id 
                FROM test_execution_event
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """)
            
            for (test_id,) in cursor.fetchall():
                flaky_signal = self.detect_flakiness(test_id)
                if flaky_signal:
                    signals.append(flaky_signal)
            
            cursor.close()
        
        return signals
