"""
Async Processing Pipeline for Sidecar Observer

Non-blocking observation through queue-based async processing.
Prevents observer from blocking test execution.
"""

import asyncio
import threading
import queue
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.OBSERVER)


class EventPriority(Enum):
    """Priority levels for observer events."""
    
    LOW = 1      # Non-critical events (screenshots, logs)
    NORMAL = 2   # Standard events (test start/end)
    HIGH = 3     # Important events (failures, errors)
    CRITICAL = 4 # System events (shutdown, errors)


@dataclass
class ObserverEvent:
    """Event to be processed by observer."""
    
    event_type: str
    priority: EventPriority
    timestamp: datetime
    data: Dict[str, Any]
    callback: Optional[Callable] = None
    
    def __lt__(self, other):
        """Compare events by priority (for priority queue)."""
        if not isinstance(other, ObserverEvent):
            return NotImplemented
        # Higher priority = lower number (for min-heap)
        return self.priority.value > other.priority.value


class AsyncProcessor:
    """
    Async event processor for observer operations.
    
    Processes observer events in background without blocking tests.
    """
    
    def __init__(
        self,
        max_queue_size: int = 1000,
        worker_threads: int = 2,
        use_priority_queue: bool = True
    ):
        """
        Initialize async processor.
        
        Args:
            max_queue_size: Maximum events in queue
            worker_threads: Number of worker threads
            use_priority_queue: Use priority-based processing
        """
        self.max_queue_size = max_queue_size
        self.worker_threads = worker_threads
        
        # Event queue
        if use_priority_queue:
            self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        else:
            self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        
        # Worker threads
        self._workers: List[threading.Thread] = []
        self._shutdown_event = threading.Event()
        self._running = False
        
        # Statistics
        self._events_processed = 0
        self._events_dropped = 0
        self._processing_errors = 0
        self._lock = threading.Lock()
        
        logger.info(
            "Async processor initialized",
            extra={
                "max_queue_size": max_queue_size,
                "worker_threads": worker_threads,
                "use_priority_queue": use_priority_queue
            }
        )
    
    def start(self):
        """Start worker threads."""
        if self._running:
            logger.warning("Async processor already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # Start worker threads
        for i in range(self.worker_threads):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"ObserverWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
        
        logger.info(
            f"Async processor started with {self.worker_threads} workers"
        )
    
    def stop(self, timeout: float = 5.0):
        """
        Stop worker threads gracefully.
        
        Args:
            timeout: Max seconds to wait for workers to finish
        """
        if not self._running:
            return
        
        logger.info("Stopping async processor...")
        self._shutdown_event.set()
        self._running = False
        
        # Wait for workers to finish
        for worker in self._workers:
            worker.join(timeout=timeout)
            if worker.is_alive():
                logger.warning(f"Worker {worker.name} did not stop in time")
        
        self._workers.clear()
        logger.info("Async processor stopped")
    
    def submit_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        callback: Optional[Callable] = None,
        block: bool = False,
        timeout: float = 0.1
    ) -> bool:
        """
        Submit event for async processing.
        
        Args:
            event_type: Type of event
            data: Event data
            priority: Event priority
            callback: Optional callback after processing
            block: Whether to block if queue full
            timeout: Timeout for blocking (seconds)
            
        Returns:
            True if event submitted, False if dropped
        """
        if not self._running:
            logger.error("Cannot submit event: processor not running")
            return False
        
        event = ObserverEvent(
            event_type=event_type,
            priority=priority,
            timestamp=datetime.now(),
            data=data,
            callback=callback
        )
        
        try:
            self._queue.put(event, block=block, timeout=timeout)
            return True
        
        except queue.Full:
            with self._lock:
                self._events_dropped += 1
            
            logger.warning(
                f"Event queue full, dropped event: {event_type}",
                extra={"priority": priority.name, "queue_size": self._queue.qsize()}
            )
            return False
    
    def _worker_loop(self):
        """Main loop for worker threads."""
        logger.debug(f"Worker {threading.current_thread().name} started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get event with timeout
                event = self._queue.get(timeout=0.5)
                
                # Process event
                self._process_event(event)
                
                # Mark task done
                self._queue.task_done()
                
            except queue.Empty:
                continue
            
            except Exception as e:
                logger.error(
                    f"Worker error: {e}",
                    exc_info=True
                )
        
        logger.debug(f"Worker {threading.current_thread().name} stopped")
    
    def _process_event(self, event: ObserverEvent):
        """Process a single event."""
        try:
            logger.debug(
                f"Processing event: {event.event_type}",
                extra={"priority": event.priority.name}
            )
            
            # TODO: Route to appropriate handler based on event_type
            # For now, just execute callback if provided
            if event.callback:
                event.callback(event)
            
            with self._lock:
                self._events_processed += 1
        
        except Exception as e:
            with self._lock:
                self._processing_errors += 1
            
            logger.error(
                f"Error processing event: {event.event_type}",
                extra={"error": str(e)},
                exc_info=True
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with self._lock:
            return {
                "running": self._running,
                "worker_threads": len(self._workers),
                "queue_size": self._queue.qsize(),
                "max_queue_size": self.max_queue_size,
                "events_processed": self._events_processed,
                "events_dropped": self._events_dropped,
                "processing_errors": self._processing_errors,
                "queue_utilization": f"{(self._queue.qsize() / self.max_queue_size) * 100:.1f}%"
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status."""
        stats = self.get_stats()
        
        # Health checks
        queue_full = stats["queue_size"] >= self.max_queue_size * 0.9
        high_error_rate = (
            stats["processing_errors"] > stats["events_processed"] * 0.1
            if stats["events_processed"] > 0 else False
        )
        
        is_healthy = (
            stats["running"] and
            not queue_full and
            not high_error_rate
        )
        
        status = {
            "healthy": is_healthy,
            "queue_utilization": stats["queue_utilization"],
            "events_processed": stats["events_processed"],
            "events_dropped": stats["events_dropped"],
            "processing_errors": stats["processing_errors"]
        }
        
        warnings = []
        if queue_full:
            warnings.append("Event queue near capacity")
        if high_error_rate:
            warnings.append("High event processing error rate")
        if not stats["running"]:
            warnings.append("Async processor not running")
        
        if warnings:
            status["warnings"] = warnings
        
        return status
    
    def wait_for_completion(self, timeout: Optional[float] = None):
        """
        Wait for all queued events to be processed.
        
        Args:
            timeout: Max seconds to wait (None = wait forever)
        """
        try:
            if timeout:
                self._queue.join()
            else:
                # Wait with timeout
                start = datetime.now()
                while not self._queue.empty():
                    elapsed = (datetime.now() - start).total_seconds()
                    if elapsed > timeout:
                        raise TimeoutError("Timeout waiting for queue completion")
                    asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Error waiting for completion: {e}")


# Global async processor instance
async_processor = AsyncProcessor()
