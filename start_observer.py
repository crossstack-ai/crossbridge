#!/usr/bin/env python3
"""
Start CrossBridge Observer in Sidecar Mode

Runs health server and keeps container alive for external test connections.
"""

import os
import sys
import logging
import signal
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.observability.health_endpoints import start_health_server
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.OBSERVER)

# Global flag for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info(f"Received signal {sig}, shutting down...")
    running = False
    sys.exit(0)


def main():
    """Start observer in sidecar mode."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get configuration from environment
    api_port = int(os.getenv('CROSSBRIDGE_API_PORT', '8765'))
    api_host = os.getenv('CROSSBRIDGE_API_HOST', '0.0.0.0')
    mode = os.getenv('CROSSBRIDGE_MODE', 'observer')
    framework = os.getenv('CROSSBRIDGE_FRAMEWORK', 'robot')
    
    logger.info("=" * 60)
    logger.info("CrossBridge Observer - Sidecar Mode")
    logger.info("=" * 60)
    logger.info(f"Mode: {mode}")
    logger.info(f"Framework: {framework}")
    logger.info(f"API Host: {api_host}")
    logger.info(f"API Port: {api_port}")
    logger.info("=" * 60)
    
    # Start health server in a separate thread
    health_thread = threading.Thread(
        target=start_health_server,
        args=(api_port, api_host),
        daemon=True,
        name="health-server"
    )
    health_thread.start()
    
    logger.info(f"✅ Health server started on {api_host}:{api_port}")
    logger.info(f"   Available endpoints:")
    logger.info(f"   - http://{api_host}:{api_port}/health")
    logger.info(f"   - http://{api_host}:{api_port}/health/v1")
    logger.info(f"   - http://{api_host}:{api_port}/health/v2")
    logger.info(f"   - http://{api_host}:{api_port}/ready")
    logger.info(f"   - http://{api_host}:{api_port}/live")
    logger.info(f"   - http://{api_host}:{api_port}/metrics")
    logger.info("")
    logger.info("🔍 Observer ready - waiting for test connections...")
    logger.info("   Configure your tests with:")
    logger.info(f"   export CROSSBRIDGE_API_HOST={api_host}")
    logger.info(f"   export CROSSBRIDGE_API_PORT={api_port}")
    logger.info("")
    
    # Keep main thread alive
    try:
        health_thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")


if __name__ == '__main__':
    main()
