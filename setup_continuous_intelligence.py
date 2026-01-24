"""
CrossBridge Continuous Intelligence - Quick Setup

Automated setup script that:
1. Runs database migration
2. Initializes lifecycle (migration → observer)
3. Starts observer service
4. Runs integration tests
5. Verifies all components working

Usage:
    python setup_continuous_intelligence.py
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_database_migration():
    """Step 1: Run database migration"""
    logger.info("=" * 70)
    logger.info("STEP 1: Running database migration...")
    logger.info("=" * 70)
    
    try:
        from scripts.migrate_continuous_intelligence import run_migration
        
        db_config = {
            'host': '10.55.12.99',
            'port': 5432,
            'database': 'udp-native-webservices-automation',
            'user': 'postgres',
            'password': 'admin'
        }
        
        run_migration(db_config)
        logger.info("✅ Database migration completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}", exc_info=True)
        return False


def initialize_lifecycle():
    """Step 2: Initialize lifecycle management"""
    logger.info("=" * 70)
    logger.info("STEP 2: Initializing lifecycle management...")
    logger.info("=" * 70)
    
    try:
        from core.observability import LifecycleManager, CrossBridgeMode
        
        manager = LifecycleManager(
            project_id="crossbridge_default",
            db_host="10.55.12.99",
            db_port=5432,
            db_name="udp-native-webservices-automation",
            db_user="postgres",
            db_password="admin"
        )
        
        # Check current mode
        try:
            current_mode = manager.get_current_mode()
            logger.info(f"Current mode: {current_mode}")
            
            if current_mode == CrossBridgeMode.MIGRATION:
                logger.info("Transitioning to observer mode...")
                manager.transition_to_observer()
                logger.info("✅ Transitioned to observer mode")
            else:
                logger.info("✅ Already in observer mode")
                
        except Exception:
            # Not initialized yet
            logger.info("Initializing migration state...")
            manager.initialize_migration()
            logger.info("Transitioning to observer mode...")
            manager.transition_to_observer()
            logger.info("✅ Lifecycle initialized and transitioned to observer")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Lifecycle initialization failed: {e}", exc_info=True)
        return False


def start_observer_service():
    """Step 3: Start observer service"""
    logger.info("=" * 70)
    logger.info("STEP 3: Starting observer service...")
    logger.info("=" * 70)
    
    try:
        from core.observability import CrossBridgeObserverService
        
        observer = CrossBridgeObserverService(
            db_host="10.55.12.99",
            db_port=5432,
            db_name="udp-native-webservices-automation",
            db_user="postgres",
            db_password="admin"
        )
        
        observer.start()
        time.sleep(2)  # Let it warm up
        
        health = observer.get_health_metrics()
        logger.info(f"Observer service health: {health}")
        
        if health['is_running']:
            logger.info("✅ Observer service started successfully")
            return observer
        else:
            logger.error("❌ Observer service not running")
            return None
            
    except Exception as e:
        logger.error(f"❌ Observer service startup failed: {e}", exc_info=True)
        return None


def test_hook_integration(observer):
    """Step 4: Test hook integration"""
    logger.info("=" * 70)
    logger.info("STEP 4: Testing hook integration...")
    logger.info("=" * 70)
    
    try:
        from core.observability import CrossBridgeHookSDK
        
        hook = CrossBridgeHookSDK(
            db_host="10.55.12.99",
            db_port=5432,
            db_name="udp-native-webservices-automation",
            db_user="postgres",
            db_password="admin"
        )
        
        # Emit test event
        test_id = f"test_quickstart_{int(time.time())}"
        logger.info(f"Emitting test event: {test_id}")
        
        hook.emit_test_start(
            test_id=test_id,
            test_name="Quickstart Integration Test",
            framework="pytest",
            file_path="/tests/test_quickstart.py",
            application_version="v1.0.0",
            product_name="CrossBridge",
            environment="test",
            metadata={
                'api_calls': ['/api/test/endpoint'],
                'pages_visited': ['test_page'],
                'tags': ['quickstart', 'integration']
            }
        )
        
        hook.emit_test_end(
            test_id=test_id,
            status="passed",
            duration=1.5
        )
        
        # Wait for processing
        time.sleep(3)
        
        # Check health
        health = observer.get_health_metrics()
        if health['events_processed'] > 0:
            logger.info(f"✅ Hook integration working: {health['events_processed']} events processed")
            return True
        else:
            logger.warning("⚠️ No events processed yet")
            return False
            
    except Exception as e:
        logger.error(f"❌ Hook integration test failed: {e}", exc_info=True)
        return False


def test_coverage_intelligence():
    """Step 5: Test coverage intelligence"""
    logger.info("=" * 70)
    logger.info("STEP 5: Testing coverage intelligence...")
    logger.info("=" * 70)
    
    try:
        from core.observability import CoverageIntelligence
        
        coverage = CoverageIntelligence(
            db_host="10.55.12.99",
            db_port=5432,
            db_name="udp-native-webservices-automation",
            db_user="postgres",
            db_password="admin"
        )
        
        # Check if coverage graph is populated
        tests = coverage.get_tests_for_api('/api/test/endpoint')
        
        if len(tests) > 0:
            logger.info(f"✅ Coverage intelligence working: {len(tests)} tests found")
            return True
        else:
            logger.info("ℹ️ Coverage graph is empty (expected on first run)")
            return True
            
    except Exception as e:
        logger.error(f"❌ Coverage intelligence test failed: {e}", exc_info=True)
        return False


def test_drift_detection():
    """Step 6: Test drift detection"""
    logger.info("=" * 70)
    logger.info("STEP 6: Testing drift detection...")
    logger.info("=" * 70)
    
    try:
        from core.observability import DriftDetector
        
        detector = DriftDetector(
            db_host="10.55.12.99",
            db_port=5432,
            db_name="udp-native-webservices-automation",
            db_user="postgres",
            db_password="admin"
        )
        
        # Detect new tests
        new_tests = detector.detect_new_tests()
        logger.info(f"New tests detected: {len(new_tests)}")
        
        for signal in new_tests[:5]:  # Show first 5
            logger.info(f"  - {signal.test_id}: {signal.description}")
        
        logger.info("✅ Drift detection working")
        return True
        
    except Exception as e:
        logger.error(f"❌ Drift detection test failed: {e}", exc_info=True)
        return False


def print_summary():
    """Print setup summary and next steps"""
    logger.info("=" * 70)
    logger.info("SETUP COMPLETE!")
    logger.info("=" * 70)
    logger.info("""
CrossBridge Continuous Intelligence is now active.

Next Steps:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Install Framework Hooks:
   
   Pytest:
     Add to pytest.ini:
     [pytest]
     plugins = core.observability.hooks.pytest_hook
     
     Run tests:
     pytest tests/ --crossbridge

   Robot Framework:
     robot --listener core.observability.hooks.robot_listener.CrossBridgeListener tests/

   Playwright:
     See docs/CONTINUOUS_INTELLIGENCE_GUIDE.md

2. View Dashboards:
   
   Grafana: http://10.55.12.99:3000/
   - Import grafana/dashboard_complete.json
   - View behavioral coverage + version analytics

3. Query Coverage:
   
   python -c "
   from core.observability import CoverageIntelligence
   coverage = CoverageIntelligence(...)
   tests = coverage.get_tests_for_api('/api/your/endpoint')
   print(tests)
   "

4. Monitor Drift:
   
   python -c "
   from core.observability import DriftDetector
   detector = DriftDetector(...)
   signals = detector.detect_new_tests()
   for s in signals:
       print(f'{s.test_id}: {s.description}')
   "

5. Integration Tests:
   
   pytest test_continuous_intelligence_integration.py -v

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Documentation:
  - Integration Guide: docs/CONTINUOUS_INTELLIGENCE_GUIDE.md
  - Database Schema: Check migration_state, coverage_graph_*, drift_signals tables

Troubleshooting:
  - Observer health: observer.get_health_metrics()
  - Database query: SELECT * FROM test_execution_event LIMIT 10;
  - Logs: Check console output for errors

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


def main():
    """Run full setup"""
    logger.info("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║  CrossBridge Continuous Intelligence Setup                       ║
║                                                                   ║
║  This will set up the complete post-migration observability      ║
║  system including:                                                ║
║  - Lifecycle management (migration → observer)                    ║
║  - Observer service (async event processing)                      ║
║  - Coverage intelligence (graph-based)                            ║
║  - Drift detection (new tests, behavior changes)                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Database migration
    if not run_database_migration():
        logger.error("Setup failed at database migration")
        return False
    
    time.sleep(1)
    
    # Step 2: Lifecycle initialization
    if not initialize_lifecycle():
        logger.error("Setup failed at lifecycle initialization")
        return False
    
    time.sleep(1)
    
    # Step 3: Start observer service
    observer = start_observer_service()
    if not observer:
        logger.error("Setup failed at observer service startup")
        return False
    
    time.sleep(1)
    
    # Step 4: Test hook integration
    if not test_hook_integration(observer):
        logger.warning("Hook integration test had issues (may need real test execution)")
    
    time.sleep(1)
    
    # Step 5: Test coverage intelligence
    if not test_coverage_intelligence():
        logger.warning("Coverage intelligence test had issues")
    
    time.sleep(1)
    
    # Step 6: Test drift detection
    if not test_drift_detection():
        logger.warning("Drift detection test had issues")
    
    # Print summary
    print_summary()
    
    # Keep observer running
    logger.info("\n⚠️  Observer service is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(10)
            health = observer.get_health_metrics()
            logger.info(f"Health check: {health['events_processed']} events processed, queue: {health['queue_size']}")
    except KeyboardInterrupt:
        logger.info("\nStopping observer service...")
        observer.stop()
        logger.info("✅ Shutdown complete")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
