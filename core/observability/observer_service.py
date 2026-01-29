"""
CrossBridge Observer Service

Core runtime that listens for test execution events and maintains continuous intelligence.

IMPORTANT: This service NEVER executes tests. It only observes execution via hooks.
"""

import logging
import threading
import time
from typing import Optional, Callable
from datetime import datetime
from queue import Queue

from .events import CrossBridgeEvent
from .event_persistence import EventPersistence
from .lifecycle import LifecycleManager, CrossBridgeMode, ensure_observer_only
from .coverage_intelligence import CoverageIntelligence
from .drift_detector import DriftDetector

logger = logging.getLogger(__name__)


class CrossBridgeObserverService:
    """
    Continuous intelligence observer service.
    
    This is the core runtime that:
    1. Receives events from framework hooks
    2. Persists events to database
    3. Updates coverage mappings
    4. Detects drift and anomalies
    5. Feeds AI analyzers
    
    Deployment options:
    - Sidecar process (recommended for CI/CD)
    - Local daemon (for development)
    - CI agent process (minimal overhead)
    
    The observer must NEVER invoke test runners or control execution.
    """
    
    def __init__(self, 
                 project_id: str,
                 db_connection=None,
                 enable_ai: bool = False):
        """
        Initialize observer service.
        
        Args:
            project_id: Unique project identifier
            db_connection: PostgreSQL connection for persistence
            enable_ai: Enable AI-powered analysis (Phase 3)
        """
        self.project_id = project_id
        self.db_connection = db_connection
        self.enable_ai = enable_ai
        
        # Core components
        self.lifecycle = LifecycleManager(db_connection)
        self.persistence = EventPersistence()
        self.coverage_intelligence = CoverageIntelligence(db_connection)
        self.drift_detector = DriftDetector(db_connection)
        
        # Event processing
        self.event_queue = Queue()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # Metrics
        self.metrics = {
            'events_received': 0,
            'events_processed': 0,
            'events_dropped': 0,
            'schema_mismatches': 0,
            'last_event_at': None,
            'started_at': None
        }
    
    def start(self):
        """
        Start the observer service.
        
        This starts a background worker thread that processes events
        from the queue in a non-blocking manner.
        """
        # Verify we're in observer mode
        try:
            ensure_observer_only()
        except RuntimeError as e:
            logger.error(f"Cannot start observer: {e}")
            return
        
        if self.running:
            logger.warning("Observer service already running")
            return
        
        logger.info(f"Starting CrossBridge Observer Service for project: {self.project_id}")
        
        self.running = True
        self.metrics['started_at'] = datetime.utcnow()
        
        # Start worker thread
        self.worker_thread = threading.Thread(
            target=self._event_processing_loop,
            daemon=True
        )
        self.worker_thread.start()
        
        logger.info("Observer service started successfully")
    
    def stop(self):
        """Stop the observer service gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping observer service...")
        self.running = False
        
        # Wait for worker to finish processing
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        
        # Flush remaining events
        self._flush_queue()
        
        logger.info("Observer service stopped")
    
    def ingest_event(self, event: CrossBridgeEvent):
        """
        Ingest a test execution event.
        
        This is the primary entry point for framework hooks.
        Events are queued for async processing to avoid blocking test execution.
        
        Args:
            event: CrossBridgeEvent from framework hook
        """
        self.metrics['events_received'] += 1
        self.metrics['last_event_at'] = datetime.utcnow()
        
        # Validate event schema
        if not self._validate_event(event):
            self.metrics['schema_mismatches'] += 1
            logger.warning(f"Invalid event schema: {event}")
            return
        
        # Queue for async processing
        try:
            self.event_queue.put(event, block=False)
        except queue.Full:
            self.metrics['events_dropped'] += 1
            logger.error("Event queue full - dropping event")
    
    def _event_processing_loop(self):
        """Background worker that processes events from queue"""
        logger.info("Event processing loop started")
        
        while self.running:
            try:
                # Get event with timeout to allow periodic checks
                event = self.event_queue.get(timeout=1.0)
                
                # Process event
                self._process_event(event)
                
                self.metrics['events_processed'] += 1
                self.event_queue.task_done()
                
            except queue.Empty:
                # Timeout or empty queue - continue
                continue
        
        logger.info("Event processing loop stopped")
    
    def _process_event(self, event: CrossBridgeEvent):
        """
        Process a single event through the intelligence pipeline.
        
        Pipeline:
        1. Persist event to database
        2. Update coverage mappings
        3. Check for drift/anomalies
        4. Feed AI analyzers (if enabled)
        5. Update lifecycle state
        """
        try:
            # 1. Persist to database
            self.persistence.persist_event(event)
            
            # 2. Update coverage intelligence
            self.coverage_intelligence.process_event(event)
            
            # 3. Detect drift and anomalies
            signals = self.drift_detector.analyze_event(event)
            if signals:
                logger.info(f"Drift signals detected: {signals}")
            
            # 4. AI analysis (Phase 3)
            if self.enable_ai:
                try:
                    self._feed_ai_analyzers(event, signals)
                except Exception as e:
                    logger.error(f"AI analysis failed (non-blocking): {e}")
            
            # 5. Update lifecycle
            self.lifecycle.update_last_event(self.project_id)
            
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
    
    def _validate_event(self, event: CrossBridgeEvent) -> bool:
        """Validate event schema"""
        required_fields = ['event_type', 'framework', 'test_id', 'timestamp']
        
        for field in required_fields:
            if not hasattr(event, field) or getattr(event, field) is None:
                return False
        
        return True
    
    def _flush_queue(self):
        """Flush remaining events in queue"""
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get_nowait()
                self._process_event(event)
                self.event_queue.task_done()
            except queue.Empty:
                break
    
    def _feed_ai_analyzers(self, event: CrossBridgeEvent, drift_signals: list):
        """Feed event to AI analyzers (Phase 3)"""
        # TODO: Implement AI analyzer integration
        pass
    
    def get_health(self) -> dict:
        """Get observer service health metrics"""
        return {
            'running': self.running,
            'project_id': self.project_id,
            'metrics': self.metrics,
            'queue_size': self.event_queue.qsize(),
            'mode': CrossBridgeMode.OBSERVER.value
        }


# Singleton instance (optional)
_observer_instance: Optional[CrossBridgeObserverService] = None


def get_observer(project_id: str, db_connection=None) -> CrossBridgeObserverService:
    """Get or create observer service instance"""
    global _observer_instance
    
    if _observer_instance is None:
        _observer_instance = CrossBridgeObserverService(
            project_id=project_id,
            db_connection=db_connection
        )
    
    return _observer_instance
