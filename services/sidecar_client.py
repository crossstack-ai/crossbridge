"""
Remote Sidecar Client

Sends test execution events to remote sidecar observer API.
Supports all frameworks through unified event format.

Features:
- Automatic batching for efficiency
- Retry logic with exponential backoff
- Async sending to avoid blocking test execution
- Connection pooling
- Fail-open design (never blocks tests)
"""

import asyncio
import json
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import deque
from datetime import datetime
import httpx

from core.logging import get_logger, LogCategory
from core.sidecar.observer import Event
from services.sidecar_api import RemoteSidecarConfig, EventPayload

logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)


class RemoteSidecarClient:
    """
    Remote Sidecar Client
    
    Sends events to remote sidecar API in a fail-open manner.
    NEVER blocks or crashes the test execution.
    """
    
    def __init__(
        self,
        config: RemoteSidecarConfig,
        framework: str,
        environment: str = "unknown",
        enabled: bool = True
    ):
        """
        Initialize remote sidecar client
        
        Args:
            config: Remote sidecar configuration
            framework: Test framework name
            environment: Environment name
            enabled: Whether client is enabled
        """
        self.config = config
        self.framework = framework
        self.environment = environment
        self.enabled = enabled
        
        # Event buffer for batching
        self._buffer: deque = deque(maxlen=config.batch_size * 2)
        self._buffer_lock = threading.Lock()
        self._last_flush = time.time()
        
        # Background sender thread
        self._sender_thread: Optional[threading.Thread] = None
        self._running = False
        
        # HTTP client with connection pooling
        self._http_client: Optional[httpx.AsyncClient] = None
        
        # Statistics
        self._stats = {
            'events_sent': 0,
            'events_failed': 0,
            'batches_sent': 0,
            'retries': 0,
            'last_error': None
        }
        self._stats_lock = threading.Lock()
        
        # Start background sender if enabled
        if self.enabled:
            self._start_sender()
    
    def _start_sender(self):
        """Start background sender thread"""
        if self._sender_thread and self._sender_thread.is_alive():
            return
        
        self._running = True
        self._sender_thread = threading.Thread(
            target=self._sender_loop,
            daemon=True,
            name="CrossBridge-RemoteSidecar-Sender"
        )
        self._sender_thread.start()
        logger.info(f"Remote sidecar client started - sending to {self.config.base_url}")
    
    def _sender_loop(self):
        """Background loop for sending batched events"""
        asyncio.run(self._async_sender_loop())
    
    async def _async_sender_loop(self):
        """Async sender loop"""
        # Create HTTP client with connection pooling
        self._http_client = httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        try:
            while self._running:
                try:
                    # Check if we should flush batch
                    should_flush = False
                    
                    with self._buffer_lock:
                        buffer_size = len(self._buffer)
                        time_since_flush = time.time() - self._last_flush
                        
                        # Flush conditions
                        if buffer_size >= self.config.batch_size:
                            should_flush = True
                        elif buffer_size > 0 and time_since_flush * 1000 >= self.config.batch_timeout_ms:
                            should_flush = True
                    
                    if should_flush:
                        await self._flush_batch()
                    else:
                        # Sleep briefly to avoid tight loop
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Error in sender loop: {e}")
                    await asyncio.sleep(1)  # Back off on error
        
        finally:
            # Close HTTP client
            if self._http_client:
                await self._http_client.aclose()
    
    async def _flush_batch(self):
        """Flush buffered events to remote API"""
        # Get events from buffer
        events_to_send = []
        with self._buffer_lock:
            while self._buffer and len(events_to_send) < self.config.batch_size:
                events_to_send.append(self._buffer.popleft())
            self._last_flush = time.time()
        
        if not events_to_send:
            return
        
        # Send batch with retry
        success = await self._send_batch_with_retry(events_to_send)
        
        if success:
            with self._stats_lock:
                self._stats['events_sent'] += len(events_to_send)
                self._stats['batches_sent'] += 1
        else:
            with self._stats_lock:
                self._stats['events_failed'] += len(events_to_send)
    
    async def _send_batch_with_retry(self, events: List[Dict[str, Any]]) -> bool:
        """
        Send batch of events with retry logic
        
        Returns:
            True if sent successfully, False otherwise
        """
        url = f"{self.config.base_url}/events/batch"
        
        payload = {
            "events": events,
            "batch_id": f"batch-{int(time.time()*1000)}"
        }
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = await self._http_client.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.debug(f"Batch sent successfully: {len(events)} events")
                    return True
                else:
                    logger.warning(f"Batch send failed with status {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Failed to send batch (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                
                with self._stats_lock:
                    self._stats['retries'] += 1
                    self._stats['last_error'] = str(e)
                
                if attempt < self.config.retry_attempts - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
        
        return False
    
    def send_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        execution_id: Optional[str] = None,
        test_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Send event to remote sidecar (non-blocking)
        
        Args:
            event_type: Type of event
            data: Event data
            execution_id: Execution ID
            test_id: Test ID
            run_id: Run ID
            metadata: Additional metadata
        """
        if not self.enabled:
            return
        
        try:
            event_payload = {
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().timestamp(),
                "execution_id": execution_id,
                "test_id": test_id,
                "run_id": run_id,
                "framework": self.framework,
                "environment": self.environment,
                "metadata": metadata or {}
            }
            
            with self._buffer_lock:
                self._buffer.append(event_payload)
                
        except Exception as e:
            # Fail-open: log but don't raise
            logger.warning(f"Failed to buffer event: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        with self._stats_lock:
            return dict(self._stats)
    
    def stop(self, timeout: float = 5.0):
        """
        Stop the client and flush remaining events
        
        Args:
            timeout: Max time to wait for flush
        """
        logger.info("Stopping remote sidecar client...")
        self._running = False
        
        # Wait for sender thread to finish
        if self._sender_thread:
            self._sender_thread.join(timeout=timeout)
        
        # Log final stats
        stats = self.get_stats()
        logger.info(f"Remote sidecar client stopped. Stats: {stats}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# ============================================================================
# Factory Function
# ============================================================================

def create_remote_client_from_env() -> Optional[RemoteSidecarClient]:
    """
    Create remote sidecar client from environment variables
    
    Environment variables:
        CROSSBRIDGE_SIDECAR_HOST: Host of remote sidecar
        CROSSBRIDGE_SIDECAR_PORT: Port of remote sidecar (default: 8765)
        CROSSBRIDGE_SIDECAR_ENABLED: Enable/disable remote client (default: true)
        CROSSBRIDGE_FRAMEWORK: Test framework name
        CROSSBRIDGE_ENVIRONMENT: Environment name
    
    Returns:
        RemoteSidecarClient if configured, None otherwise
    """
    import os
    
    host = os.getenv('CROSSBRIDGE_SIDECAR_HOST')
    if not host:
        return None
    
    enabled = os.getenv('CROSSBRIDGE_SIDECAR_ENABLED', 'true').lower() == 'true'
    if not enabled:
        return None
    
    config = RemoteSidecarConfig(
        host=host,
        port=int(os.getenv('CROSSBRIDGE_SIDECAR_PORT', '8765')),
        protocol=os.getenv('CROSSBRIDGE_SIDECAR_PROTOCOL', 'http')
    )
    
    framework = os.getenv('CROSSBRIDGE_FRAMEWORK', 'unknown')
    environment = os.getenv('CROSSBRIDGE_ENVIRONMENT', 'unknown')
    
    logger.info(f"Creating remote sidecar client for {framework} in {environment}")
    
    return RemoteSidecarClient(
        config=config,
        framework=framework,
        environment=environment,
        enabled=True
    )
