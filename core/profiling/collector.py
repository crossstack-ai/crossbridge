"""
Metrics Collector Service

Non-blocking, async metrics collector with batching and backpressure handling.
"""

import logging
import queue
import threading
import time
import os
from typing import List, Optional
import uuid

from core.profiling.models import PerformanceEvent, ProfileConfig, EventType
from core.profiling.storage import StorageBackend, StorageFactory

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Non-blocking metrics collector service.
    
    Key principles:
    - Collector failures never fail tests
    - All operations are non-blocking
    - Backpressure handling via queue drop
    - Automatic batching for performance
    """
    
    _instance: Optional["MetricsCollector"] = None
    _lock = threading.Lock()
    
    def __init__(self, config: ProfileConfig, storage: StorageBackend):
        self.config = config
        self.storage = storage
        self.queue: queue.Queue = queue.Queue(maxsize=10000)
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.current_run_id: Optional[str] = None
        
        # Performance tracking
        self.events_collected = 0
        self.events_dropped = 0
        self.events_written = 0
    
    @classmethod
    def get_instance(cls, config: Optional[ProfileConfig] = None) -> "MetricsCollector":
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if config is None:
                        # Create disabled instance
                        from core.profiling.models import ProfileConfig
                        from core.profiling.storage import NoOpStorageBackend
                        config = ProfileConfig(enabled=False)
                        storage = NoOpStorageBackend()
                    else:
                        storage = StorageFactory.from_config(config)
                    
                    cls._instance = cls(config, storage)
        
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)"""
        with cls._lock:
            if cls._instance:
                cls._instance.shutdown()
            cls._instance = None
    
    def start(self) -> bool:
        """Start the metrics collector"""
        # Check if disabled via environment variable
        if os.environ.get("CROSSBRIDGE_PROFILING", "").lower() == "false":
            logger.info("Profiling disabled via environment variable")
            return False
        
        if not self.config.enabled:
            logger.info("Profiling disabled in configuration")
            return False
        
        try:
            # Initialize storage
            if not self.storage.initialize():
                logger.error("Failed to initialize storage backend")
                return False
            
            # Generate run ID
            self.current_run_id = str(uuid.uuid4())
            
            # Start worker thread
            self.running = True
            self.worker_thread = threading.Thread(target=self._background_flush, daemon=True)
            self.worker_thread.start()
            
            logger.info(f"Metrics collector started (run_id={self.current_run_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start metrics collector: {e}")
            return False
    
    def collect(self, event: PerformanceEvent) -> None:
        """
        Collect a performance event.
        
        This method never raises exceptions.
        """
        if not self.config.enabled or not self.running:
            return
        
        try:
            # Apply sampling
            if self.config.sampling_rate < 1.0:
                import random
                if random.random() > self.config.sampling_rate:
                    return
            
            # Try to add to queue (non-blocking)
            try:
                self.queue.put_nowait(event)
                self.events_collected += 1
            except queue.Full:
                # Backpressure: drop event
                self.events_dropped += 1
                if self.events_dropped % 100 == 0:
                    logger.warning(f"Dropped {self.events_dropped} events due to backpressure")
        
        except Exception as e:
            # Swallow all exceptions
            logger.debug(f"Error collecting event: {e}")
    
    def _background_flush(self) -> None:
        """Background worker thread for flushing events"""
        batch_size = 100
        flush_interval = 1.0  # seconds
        
        while self.running:
            try:
                # Collect batch
                batch: List[PerformanceEvent] = []
                deadline = time.time() + flush_interval
                
                while len(batch) < batch_size and time.time() < deadline:
                    try:
                        timeout = max(0.1, deadline - time.time())
                        event = self.queue.get(timeout=timeout)
                        batch.append(event)
                    except queue.Empty:
                        break
                
                # Write batch
                if batch:
                    try:
                        if self.storage.write_events(batch):
                            self.events_written += len(batch)
                        else:
                            logger.warning(f"Failed to write {len(batch)} events")
                    except Exception as e:
                        logger.error(f"Error writing events: {e}")
                
            except Exception as e:
                logger.error(f"Error in background flush: {e}")
                time.sleep(1.0)
    
    def flush(self) -> bool:
        """Flush all pending events"""
        if not self.config.enabled:
            return True
        
        try:
            # Drain queue
            batch: List[PerformanceEvent] = []
            while not self.queue.empty():
                try:
                    event = self.queue.get_nowait()
                    batch.append(event)
                except queue.Empty:
                    break
            
            # Write final batch
            if batch:
                if self.storage.write_events(batch):
                    self.events_written += len(batch)
            
            # Flush storage
            return self.storage.flush()
            
        except Exception as e:
            logger.error(f"Error flushing events: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the metrics collector"""
        if not self.running:
            return
        
        try:
            logger.info("Shutting down metrics collector...")
            
            # Stop worker
            self.running = False
            
            # Wait for worker thread
            if self.worker_thread:
                self.worker_thread.join(timeout=5.0)
            
            # Final flush
            self.flush()
            
            # Shutdown storage
            self.storage.shutdown()
            
            logger.info(
                f"Metrics collector shutdown complete "
                f"(collected={self.events_collected}, "
                f"dropped={self.events_dropped}, "
                f"written={self.events_written})"
            )
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def get_stats(self) -> dict:
        """Get collector statistics"""
        return {
            "enabled": self.config.enabled,
            "running": self.running,
            "run_id": self.current_run_id,
            "events_collected": self.events_collected,
            "events_dropped": self.events_dropped,
            "events_written": self.events_written,
            "queue_size": self.queue.qsize(),
        }
    
    # ========================================================================
    # Convenience Methods for Test Recording
    # ========================================================================
    
    def record_test_start(self, test_id: str, framework: str, metadata: dict = None) -> None:
        """Record test start event"""
        event = PerformanceEvent(
            run_id=self.current_run_id or str(uuid.uuid4()),
            test_id=test_id,
            event_type=EventType.TEST_START,
            start_time=time.monotonic(),
            end_time=time.monotonic(),
            duration_ms=0,
            framework=framework,
            metadata=metadata or {}
        )
        self.collect(event)
    
    def record_test_end(self, test_id: str, framework: str, duration_ms: int, status: str, metadata: dict = None) -> None:
        """Record test end event"""
        event = PerformanceEvent(
            run_id=self.current_run_id or str(uuid.uuid4()),
            test_id=test_id,
            event_type=EventType.TEST_END,
            start_time=time.monotonic(),
            end_time=time.monotonic() + (duration_ms / 1000),
            duration_ms=duration_ms,
            framework=framework,
            metadata={**(metadata or {}), "status": status}
        )
        self.collect(event)
    
    def record_step_start(self, test_id: str, framework: str, step_name: str, metadata: dict = None) -> None:
        """Record step start event"""
        event = PerformanceEvent(
            run_id=self.current_run_id or str(uuid.uuid4()),
            test_id=test_id,
            event_type=EventType.STEP_START,
            start_time=time.monotonic(),
            end_time=time.monotonic(),
            duration_ms=0,
            framework=framework,
            step_name=step_name,
            metadata=metadata or {}
        )
        self.collect(event)
    
    def record_step_end(self, test_id: str, framework: str, step_name: str, duration_ms: int, metadata: dict = None) -> None:
        """Record step end event"""
        event = PerformanceEvent(
            run_id=self.current_run_id or str(uuid.uuid4()),
            test_id=test_id,
            event_type=EventType.STEP_END,
            start_time=time.monotonic(),
            end_time=time.monotonic() + (duration_ms / 1000),
            duration_ms=duration_ms,
            framework=framework,
            step_name=step_name,
            metadata=metadata or {}
        )
        self.collect(event)


# Global convenience functions
def start_profiling(config: ProfileConfig) -> bool:
    """Start performance profiling"""
    collector = MetricsCollector.get_instance(config)
    return collector.start()


def collect_event(event: PerformanceEvent) -> None:
    """Collect a performance event"""
    collector = MetricsCollector.get_instance()
    collector.collect(event)


def stop_profiling() -> None:
    """Stop performance profiling"""
    collector = MetricsCollector.get_instance()
    collector.shutdown()
