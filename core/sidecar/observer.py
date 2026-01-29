"""
Sidecar Observer - Fail-Open Event Collection

Core observer that collects events with:
- Non-blocking operations
- Bounded queues with backpressure handling
- Exception isolation
- Drop-on-overload semantics
"""

import queue
import threading
import time
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

from core.logging import get_logger, LogCategory
from cli.errors import CrossBridgeError

logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)


@dataclass
class Event:
    """Observed event with metadata"""
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    execution_id: Optional[str] = None
    test_id: Optional[str] = None
    run_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'event_type': self.event_type,
            'data': self.data,
            'timestamp': self.timestamp,
            'execution_id': self.execution_id,
            'test_id': self.test_id,
            'run_id': self.run_id,
        }


class SidecarObserver:
    """
    Resilient sidecar observer with fail-open design
    
    NEVER blocks or crashes the main process.
    Drops events under load rather than backpressuring.
    """
    
    # Resource limits (configurable)
    MAX_QUEUE_SIZE = 10_000
    MAX_MEMORY_MB = 100
    MAX_CPU_PERCENT = 5.0
    
    def __init__(
        self,
        sampler,
        metrics_collector=None,
        max_queue_size: int = MAX_QUEUE_SIZE,
        drop_on_full: bool = True
    ):
        """
        Initialize sidecar observer
        
        Args:
            sampler: Sampler instance for sampling decisions
            metrics_collector: Optional metrics collector
            max_queue_size: Maximum queue size before dropping
            drop_on_full: If True, drop events when queue is full
        """
        self._sampler = sampler
        self._metrics = metrics_collector
        self._max_queue_size = max_queue_size
        self._drop_on_full = drop_on_full
        
        # Bounded queue for fail-open behavior
        self._event_queue: deque = deque(maxlen=max_queue_size)
        self._queue_lock = threading.Lock()
        
        # Statistics
        self._stats = {
            'events_received': 0,
            'events_sampled': 0,
            'events_dropped': 0,
            'events_processed': 0,
            'errors': 0,
            'last_error': None,
        }
        self._stats_lock = threading.Lock()
        
        # Event handlers
        self._handlers: Dict[str, Callable] = {}
        
        # Running state
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        logger.info("SidecarObserver initialized", extra={
            'max_queue_size': max_queue_size,
            'drop_on_full': drop_on_full
        })
    
    def observe_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        execution_id: Optional[str] = None,
        test_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> bool:
        """
        Observe an event (non-blocking, fail-open)
        
        Args:
            event_type: Type of event
            data: Event data
            execution_id: Execution context ID
            test_id: Test context ID
            run_id: Run context ID
            
        Returns:
            True if event was accepted, False if dropped
        """
        try:
            # Update stats
            with self._stats_lock:
                self._stats['events_received'] += 1
            
            # Sample decision
            if not self._sampler.should_sample(event_type):
                return False
            
            with self._stats_lock:
                self._stats['events_sampled'] += 1
            
            # Check queue capacity
            with self._queue_lock:
                if len(self._event_queue) >= self._max_queue_size:
                    if self._drop_on_full:
                        # Drop oldest event (or this one)
                        self._event_queue.popleft()  # Drop oldest
                        with self._stats_lock:
                            self._stats['events_dropped'] += 1
                        
                        if self._metrics:
                            self._metrics.increment('sidecar_events_dropped_total')
                        
                        logger.warning("Queue overflow, dropped oldest event", extra={
                            'queue_size': len(self._event_queue),
                            'max_size': self._max_queue_size
                        })
                    else:
                        # Reject this event
                        with self._stats_lock:
                            self._stats['events_dropped'] += 1
                        return False
                
                # Add to queue
                event = Event(
                    event_type=event_type,
                    data=data,
                    execution_id=execution_id,
                    test_id=test_id,
                    run_id=run_id
                )
                self._event_queue.append(event)
            
            if self._metrics:
                self._metrics.increment('sidecar_events_total')
            
            return True
            
        except Exception as e:
            # NEVER let exceptions escape to main process
            with self._stats_lock:
                self._stats['errors'] += 1
                self._stats['last_error'] = str(e)
            
            logger.error("Sidecar dropped event due to error", extra={
                'error': str(e),
                'event_type': event_type
            })
            
            if self._metrics:
                self._metrics.increment('sidecar_errors_total')
            
            return False
    
    def register_handler(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Register a handler for a specific event type"""
        self._handlers[event_type] = handler
    
    def start(self) -> None:
        """Start background processing thread"""
        if self._running:
            logger.warning("SidecarObserver already running")
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._process_events,
            daemon=True,
            name="sidecar-observer"
        )
        self._worker_thread.start()
        logger.info("SidecarObserver started")
    
    def stop(self, timeout: float = 5.0) -> None:
        """Stop background processing (graceful shutdown)"""
        if not self._running:
            return
        
        logger.info("Stopping SidecarObserver...")
        self._running = False
        
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
        
        logger.info("SidecarObserver stopped", extra={
            'remaining_events': len(self._event_queue)
        })
    
    def _process_events(self) -> None:
        """Background event processing loop"""
        while self._running:
            try:
                # Get event from queue
                event = None
                with self._queue_lock:
                    if self._event_queue:
                        event = self._event_queue.popleft()
                
                if event is None:
                    # Queue empty, sleep briefly
                    time.sleep(0.01)
                    continue
                
                # Process event
                start_time = time.time()
                self._process_event(event)
                processing_time = (time.time() - start_time) * 1000  # ms
                
                # Update stats
                with self._stats_lock:
                    self._stats['events_processed'] += 1
                
                # Track latency
                if self._metrics:
                    self._metrics.observe('sidecar_processing_latency_ms', processing_time)
                
            except Exception as e:
                # NEVER let exceptions kill the worker thread
                with self._stats_lock:
                    self._stats['errors'] += 1
                    self._stats['last_error'] = str(e)
                
                logger.error("Error processing event", extra={'error': str(e)})
                
                if self._metrics:
                    self._metrics.increment('sidecar_errors_total')
    
    def _process_event(self, event: Event) -> None:
        """Process a single event"""
        try:
            # Call registered handler if exists
            if event.event_type in self._handlers:
                handler = self._handlers[event.event_type]
                handler(event)
            else:
                # Default: just log
                logger.debug("Observed event", extra={
                    'event_type': event.event_type,
                    'execution_id': event.execution_id,
                    'test_id': event.test_id,
                    'run_id': event.run_id
                })
        except Exception as e:
            logger.error("Handler error", extra={
                'event_type': event.event_type,
                'error': str(e)
            })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get observer statistics"""
        with self._stats_lock, self._queue_lock:
            return {
                **self._stats,
                'queue_size': len(self._event_queue),
                'queue_capacity': self._max_queue_size,
                'queue_utilization': len(self._event_queue) / self._max_queue_size,
                'running': self._running,
            }
    
    def reset_stats(self) -> None:
        """Reset statistics"""
        with self._stats_lock:
            self._stats = {
                'events_received': 0,
                'events_sampled': 0,
                'events_dropped': 0,
                'events_processed': 0,
                'errors': 0,
                'last_error': None,
            }
