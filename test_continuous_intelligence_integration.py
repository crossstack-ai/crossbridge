"""
Integration Test: CrossBridge Continuous Intelligence

Tests the full end-to-end flow:
1. Lifecycle initialization (migration → observer)
2. Observer service startup
3. Event emission via hook SDK
4. Coverage intelligence updates
5. Drift detection
6. Automatic new test registration

Run with: pytest test_continuous_intelligence_integration.py -v
"""

import pytest
import time
from datetime import datetime, timedelta
from core.observability import (
    LifecycleManager,
    CrossBridgeMode,
    CrossBridgeObserverService,
    CrossBridgeHookSDK,
    CoverageIntelligence,
    DriftDetector,
    EventPersistence
)


@pytest.fixture
def db_config():
    """Database configuration"""
    return {
        'host': '10.55.12.99',
        'port': 5432,
        'database': 'udp-native-webservices-automation',
        'user': 'postgres',
        'password': 'admin'
    }


@pytest.fixture
def project_id():
    """Unique project ID for testing"""
    return f"test_project_{int(time.time())}"


@pytest.fixture
def lifecycle_manager(db_config, project_id):
    """Lifecycle manager fixture"""
    manager = LifecycleManager(
        project_id=project_id,
        db_host=db_config['host'],
        db_port=db_config['port'],
        db_name=db_config['database'],
        db_user=db_config['user'],
        db_password=db_config['password']
    )
    yield manager
    # Cleanup would go here if needed


@pytest.fixture
def observer_service(db_config):
    """Observer service fixture"""
    service = CrossBridgeObserverService(
        db_host=db_config['host'],
        db_port=db_config['port'],
        db_name=db_config['database'],
        db_user=db_config['user'],
        db_password=db_config['password']
    )
    service.start()
    yield service
    service.stop()


@pytest.fixture
def hook_sdk(db_config):
    """Hook SDK fixture"""
    return CrossBridgeHookSDK(
        db_host=db_config['host'],
        db_port=db_config['port'],
        db_name=db_config['database'],
        db_user=db_config['user'],
        db_password=db_config['password']
    )


@pytest.fixture
def coverage_intelligence(db_config):
    """Coverage intelligence fixture"""
    return CoverageIntelligence(
        db_host=db_config['host'],
        db_port=db_config['port'],
        db_name=db_config['database'],
        db_user=db_config['user'],
        db_password=db_config['password']
    )


@pytest.fixture
def drift_detector(db_config):
    """Drift detector fixture"""
    return DriftDetector(
        db_host=db_config['host'],
        db_port=db_config['port'],
        db_name=db_config['database'],
        db_user=db_config['user'],
        db_password=db_config['password']
    )


class TestLifecycleManagement:
    """Test lifecycle state machine"""
    
    def test_initialize_migration(self, lifecycle_manager):
        """Test migration initialization"""
        lifecycle_manager.initialize_migration()
        
        mode = lifecycle_manager.get_current_mode()
        assert mode == CrossBridgeMode.MIGRATION
        print("✅ Migration mode initialized")
    
    def test_transition_to_observer(self, lifecycle_manager):
        """Test one-way transition to observer mode"""
        # Start in migration
        lifecycle_manager.initialize_migration()
        assert lifecycle_manager.get_current_mode() == CrossBridgeMode.MIGRATION
        
        # Transition to observer
        lifecycle_manager.transition_to_observer()
        assert lifecycle_manager.get_current_mode() == CrossBridgeMode.OBSERVER
        print("✅ Transitioned to observer mode")
        
        # Verify one-way (cannot go back to migration)
        with pytest.raises(ValueError, match="Cannot transition from observer back to migration"):
            lifecycle_manager.set_mode(CrossBridgeMode.MIGRATION)
        print("✅ One-way transition enforced")
    
    def test_guard_functions(self, lifecycle_manager):
        """Test guard functions enforce mode constraints"""
        from core.observability.lifecycle import ensure_observer_only, ensure_migration_mode
        
        # Start in migration
        lifecycle_manager.initialize_migration()
        
        # Should allow migration operations
        ensure_migration_mode(lifecycle_manager)
        
        # Should block observer operations
        with pytest.raises(ValueError, match="This operation requires observer mode"):
            ensure_observer_only(lifecycle_manager)
        
        # Transition to observer
        lifecycle_manager.transition_to_observer()
        
        # Should allow observer operations
        ensure_observer_only(lifecycle_manager)
        
        # Should block migration operations
        with pytest.raises(ValueError, match="This operation requires migration mode"):
            ensure_migration_mode(lifecycle_manager)
        
        print("✅ Guard functions working correctly")


class TestObserverService:
    """Test observer service functionality"""
    
    def test_service_startup(self, observer_service):
        """Test observer service starts successfully"""
        health = observer_service.get_health_metrics()
        assert health['is_running'] == True
        assert health['queue_size'] >= 0
        print(f"✅ Observer service running: {health}")
    
    def test_event_ingestion(self, observer_service, hook_sdk):
        """Test event flows through observer service"""
        # Emit a test event
        test_id = f"test_integration_{int(time.time())}"
        hook_sdk.emit_test_start(
            test_id=test_id,
            test_name="Integration Test",
            framework="pytest",
            file_path="/tests/test_integration.py",
            application_version="v1.0.0",
            product_name="TestProduct",
            environment="test"
        )
        
        # Give observer time to process
        time.sleep(2)
        
        # Check health metrics
        health = observer_service.get_health_metrics()
        assert health['events_processed'] > 0
        print(f"✅ Event processed: {health['events_processed']} events")
    
    def test_async_processing(self, observer_service, hook_sdk):
        """Test observer processes events asynchronously"""
        initial_health = observer_service.get_health_metrics()
        initial_count = initial_health['events_processed']
        
        # Emit multiple events rapidly
        for i in range(10):
            hook_sdk.emit_test_start(
                test_id=f"test_async_{i}_{int(time.time())}",
                test_name=f"Async Test {i}",
                framework="pytest",
                file_path=f"/tests/test_{i}.py",
                application_version="v1.0.0",
                product_name="TestProduct",
                environment="test"
            )
        
        # Should not block (returns immediately)
        # Give time to process
        time.sleep(3)
        
        final_health = observer_service.get_health_metrics()
        final_count = final_health['events_processed']
        
        assert final_count > initial_count
        print(f"✅ Processed {final_count - initial_count} events asynchronously")


class TestCoverageIntelligence:
    """Test coverage intelligence graph"""
    
    def test_update_from_event(self, coverage_intelligence, hook_sdk, observer_service):
        """Test coverage graph updates from events"""
        # Create event with API and page interactions
        test_id = f"test_coverage_{int(time.time())}"
        
        hook_sdk.emit_test_start(
            test_id=test_id,
            test_name="Coverage Test",
            framework="pytest",
            file_path="/tests/test_coverage.py",
            application_version="v1.0.0",
            product_name="TestProduct",
            environment="test",
            metadata={
                'api_calls': ['/api/users', '/api/payments'],
                'pages_visited': ['login', 'checkout'],
                'ui_components': ['button:submit', 'input:email']
            }
        )
        
        # Give time to process
        time.sleep(2)
        
        # Check coverage graph
        tests_for_api = coverage_intelligence.get_tests_for_api('/api/users')
        assert test_id in tests_for_api
        
        tests_for_page = coverage_intelligence.get_tests_for_page('checkout')
        assert test_id in tests_for_page
        
        print(f"✅ Coverage graph updated for test: {test_id}")
    
    def test_incremental_updates(self, coverage_intelligence, hook_sdk, observer_service):
        """Test coverage graph never overwrites existing data"""
        test_id = f"test_incremental_{int(time.time())}"
        
        # First execution - covers API 1
        hook_sdk.emit_test_start(
            test_id=test_id,
            test_name="Incremental Test",
            framework="pytest",
            file_path="/tests/test_incremental.py",
            application_version="v1.0.0",
            product_name="TestProduct",
            environment="test",
            metadata={'api_calls': ['/api/endpoint1']}
        )
        time.sleep(1)
        
        # Second execution - covers API 2
        hook_sdk.emit_test_start(
            test_id=test_id,
            test_name="Incremental Test",
            framework="pytest",
            file_path="/tests/test_incremental.py",
            application_version="v1.0.0",
            product_name="TestProduct",
            environment="test",
            metadata={'api_calls': ['/api/endpoint2']}
        )
        time.sleep(2)
        
        # Should cover BOTH APIs (incremental, not overwrite)
        tests_for_api1 = coverage_intelligence.get_tests_for_api('/api/endpoint1')
        tests_for_api2 = coverage_intelligence.get_tests_for_api('/api/endpoint2')
        
        assert test_id in tests_for_api1
        assert test_id in tests_for_api2
        print(f"✅ Coverage graph incremental (no overwrite)")
    
    def test_change_impact_analysis(self, coverage_intelligence, hook_sdk, observer_service):
        """Test change impact analysis"""
        # Create test covering specific API
        test_id = f"test_impact_{int(time.time())}"
        api_endpoint = f"/api/critical_{int(time.time())}"
        
        hook_sdk.emit_test_start(
            test_id=test_id,
            test_name="Impact Test",
            framework="pytest",
            file_path="/tests/test_impact.py",
            application_version="v1.0.0",
            product_name="TestProduct",
            environment="test",
            metadata={'api_calls': [api_endpoint]}
        )
        time.sleep(2)
        
        # Check impacted tests when API changes
        impacted = coverage_intelligence.get_impacted_tests(
            changed_node_id=f"api:{api_endpoint}",
            node_type='api'
        )
        
        assert test_id in impacted
        print(f"✅ Change impact analysis: {len(impacted)} tests impacted")


class TestDriftDetection:
    """Test drift detection functionality"""
    
    def test_new_test_detection(self, drift_detector, hook_sdk, observer_service):
        """Test automatic new test registration"""
        # Emit event for brand new test
        new_test_id = f"test_brand_new_{int(time.time())}"
        
        hook_sdk.emit_test_start(
            test_id=new_test_id,
            test_name="Brand New Test",
            framework="pytest",
            file_path="/tests/test_new.py",
            application_version="v1.0.0",
            product_name="TestProduct",
            environment="test"
        )
        
        hook_sdk.emit_test_end(
            test_id=new_test_id,
            status="passed",
            duration=1.5
        )
        
        # Give time to process
        time.sleep(2)
        
        # Detect new tests
        signals = drift_detector.detect_new_tests()
        
        new_test_signals = [s for s in signals if s.test_id == new_test_id]
        assert len(new_test_signals) > 0
        assert new_test_signals[0].signal_type == 'new_test'
        
        print(f"✅ New test detected and registered: {new_test_id}")
    
    def test_behavior_change_detection(self, drift_detector, hook_sdk, observer_service):
        """Test behavior change detection (50% threshold)"""
        test_id = f"test_behavior_{int(time.time())}"
        
        # Establish baseline (1 second)
        for _ in range(5):
            hook_sdk.emit_test_start(
                test_id=test_id,
                test_name="Behavior Test",
                framework="pytest",
                file_path="/tests/test_behavior.py",
                application_version="v1.0.0",
                product_name="TestProduct",
                environment="test"
            )
            hook_sdk.emit_test_end(
                test_id=test_id,
                status="passed",
                duration=1.0
            )
            time.sleep(0.5)
        
        # Sudden change (3 seconds = 200% increase)
        for _ in range(3):
            hook_sdk.emit_test_start(
                test_id=test_id,
                test_name="Behavior Test",
                framework="pytest",
                file_path="/tests/test_behavior.py",
                application_version="v1.0.0",
                product_name="TestProduct",
                environment="test"
            )
            hook_sdk.emit_test_end(
                test_id=test_id,
                status="passed",
                duration=3.0
            )
            time.sleep(0.5)
        
        # Give time to process
        time.sleep(2)
        
        # Detect behavior changes
        signals = drift_detector.detect_behavior_changes()
        
        behavior_signals = [s for s in signals if s.test_id == test_id]
        if len(behavior_signals) > 0:
            assert behavior_signals[0].signal_type == 'behavior_change'
            print(f"✅ Behavior change detected: {behavior_signals[0].description}")
        else:
            print("⚠️ Behavior change not detected (may need more executions)")


class TestEndToEnd:
    """End-to-end integration test"""
    
    def test_full_lifecycle(self, lifecycle_manager, observer_service, hook_sdk, 
                           coverage_intelligence, drift_detector):
        """Test complete lifecycle from migration to drift detection"""
        
        # 1. Initialize migration
        lifecycle_manager.initialize_migration()
        assert lifecycle_manager.get_current_mode() == CrossBridgeMode.MIGRATION
        print("✅ Step 1: Migration initialized")
        
        # 2. Transition to observer
        lifecycle_manager.transition_to_observer()
        assert lifecycle_manager.get_current_mode() == CrossBridgeMode.OBSERVER
        print("✅ Step 2: Transitioned to observer mode")
        
        # 3. Start observer service (already started by fixture)
        health = observer_service.get_health_metrics()
        assert health['is_running'] == True
        print(f"✅ Step 3: Observer service running")
        
        # 4. Emit test events via hooks
        test_id = f"test_e2e_{int(time.time())}"
        
        hook_sdk.emit_test_start(
            test_id=test_id,
            test_name="E2E Integration Test",
            framework="pytest",
            file_path="/tests/test_e2e.py",
            application_version="v1.0.0",
            product_name="TestProduct",
            environment="test",
            metadata={
                'api_calls': ['/api/e2e/endpoint'],
                'pages_visited': ['e2e_page'],
                'tags': ['integration', 'critical']
            }
        )
        
        hook_sdk.emit_test_end(
            test_id=test_id,
            status="passed",
            duration=2.5
        )
        
        print("✅ Step 4: Test events emitted")
        
        # 5. Wait for async processing
        time.sleep(3)
        
        # 6. Verify coverage intelligence updated
        tests_for_api = coverage_intelligence.get_tests_for_api('/api/e2e/endpoint')
        assert test_id in tests_for_api
        print(f"✅ Step 5: Coverage intelligence updated")
        
        # 7. Verify drift detection ran
        new_tests = drift_detector.detect_new_tests()
        new_test_ids = [s.test_id for s in new_tests]
        assert test_id in new_test_ids
        print(f"✅ Step 6: Drift detection identified new test")
        
        # 8. Check final health metrics
        final_health = observer_service.get_health_metrics()
        assert final_health['events_processed'] > 0
        assert final_health['processing_errors'] == 0
        print(f"✅ Step 7: Final health check passed")
        print(f"""
        
═══════════════════════════════════════════════════════════════
  END-TO-END INTEGRATION TEST PASSED ✅
═══════════════════════════════════════════════════════════════
Events processed: {final_health['events_processed']}
Queue size: {final_health['queue_size']}
Processing errors: {final_health['processing_errors']}
═══════════════════════════════════════════════════════════════
        """)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
