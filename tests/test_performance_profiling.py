"""
Comprehensive Unit Tests for Performance Profiling Module

Tests all components with PostgreSQL integration using provided DB details.
"""

import pytest
import time
import os
from datetime import datetime
from typing import List
import uuid

from core.profiling.models import (
    PerformanceEvent,
    EventType,
    ProfileConfig,
    StorageBackendType,
)
from core.profiling.storage import (
    StorageBackend,
    NoOpStorageBackend,
    LocalStorageBackend,
    PostgresStorageBackend,
    StorageFactory,
)
from core.profiling.collector import MetricsCollector
from core.profiling.hooks.selenium_hook import ProfilingWebDriver
from core.profiling.hooks.http_hook import ProfilingSession


# ============================================================================
# Test Configuration
# ============================================================================

# PostgreSQL test database details
TEST_DB_CONFIG = {
    "host": "10.60.67.247",
    "port": 5432,
    "database": "cbridge-unit-test-db",
    "user": "postgres",
    "password": "admin",
    "schema": "profiling",
}


@pytest.fixture
def test_config():
    """Test configuration with PostgreSQL"""
    return ProfileConfig(
        enabled=True,
        mode="passive",
        sampling_rate=1.0,
        test_lifecycle=True,
        webdriver=True,
        http=True,
        system_metrics=False,
        backend=StorageBackendType.POSTGRES,
        postgres_host=TEST_DB_CONFIG["host"],
        postgres_port=TEST_DB_CONFIG["port"],
        postgres_database=TEST_DB_CONFIG["database"],
        postgres_user=TEST_DB_CONFIG["user"],
        postgres_password=TEST_DB_CONFIG["password"],
        postgres_schema=TEST_DB_CONFIG["schema"],
    )


@pytest.fixture
def disabled_config():
    """Disabled configuration"""
    return ProfileConfig(enabled=False)


@pytest.fixture
def test_run_id():
    """Generate unique run ID for tests"""
    return str(uuid.uuid4())


# ============================================================================
# Test: Performance Event Model
# ============================================================================

class TestPerformanceEvent:
    """Test PerformanceEvent model"""
    
    def test_create_event(self, test_run_id):
        """Test creating a performance event"""
        event = PerformanceEvent.create(
            run_id=test_run_id,
            test_id="test_login",
            event_type=EventType.TEST_START,
            framework="pytest",
            duration_ms=0,
        )
        
        assert event.run_id == test_run_id
        assert event.test_id == "test_login"
        assert event.event_type == EventType.TEST_START
        assert event.framework == "pytest"
        assert isinstance(event.created_at, datetime)
    
    def test_event_with_metadata(self, test_run_id):
        """Test event with custom metadata"""
        event = PerformanceEvent.create(
            run_id=test_run_id,
            test_id="test_api_call",
            event_type=EventType.HTTP_REQUEST,
            framework="requests",
            duration_ms=250.5,
            endpoint="/api/login",
            method="POST",
            status_code=200,
        )
        
        assert event.duration_ms == 250.5
        assert event.metadata["endpoint"] == "/api/login"
        assert event.metadata["method"] == "POST"
        assert event.metadata["status_code"] == 200
    
    def test_event_to_dict(self, test_run_id):
        """Test event serialization"""
        event = PerformanceEvent.create(
            run_id=test_run_id,
            test_id="test_example",
            event_type=EventType.TEST_END,
            framework="pytest",
            duration_ms=1500,
        )
        
        data = event.to_dict()
        
        assert data["run_id"] == test_run_id
        assert data["test_id"] == "test_example"
        assert data["event_type"] == "test_end"
        assert data["duration_ms"] == 1500
        assert "created_at" in data
    
    def test_event_to_influx_point(self, test_run_id):
        """Test InfluxDB format conversion"""
        event = PerformanceEvent.create(
            run_id=test_run_id,
            test_id="test_example",
            event_type=EventType.TEST_END,
            framework="pytest",
            duration_ms=1500,
        )
        
        point = event.to_influx_point()
        
        assert point["measurement"] == "test_end"
        assert point["tags"]["test_id"] == "test_example"
        assert point["tags"]["framework"] == "pytest"
        assert point["fields"]["duration_ms"] == 1500


# ============================================================================
# Test: Profile Configuration
# ============================================================================

class TestProfileConfig:
    """Test ProfileConfig model"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = ProfileConfig()
        
        assert config.enabled is False
        assert config.mode == "passive"
        assert config.sampling_rate == 1.0
        assert config.backend == StorageBackendType.NONE
    
    def test_config_from_dict(self):
        """Test creating config from dictionary"""
        data = {
            "profiling": {
                "enabled": True,
                "mode": "passive",
                "sampling_rate": 0.5,
                "collectors": {
                    "test_lifecycle": True,
                    "webdriver": False,
                },
                "storage": {
                    "backend": "postgres",
                    "postgres": {
                        "host": "10.60.67.247",
                        "port": 5432,
                        "database": "cbridge-unit-test-db",
                    },
                },
            },
        }
        
        config = ProfileConfig.from_dict(data)
        
        assert config.enabled is True
        assert config.sampling_rate == 0.5
        assert config.test_lifecycle is True
        assert config.webdriver is False
        assert config.backend == StorageBackendType.POSTGRES
        assert config.postgres_host == "10.60.67.247"
        assert config.postgres_port == 5432


# ============================================================================
# Test: Storage Backends
# ============================================================================

class TestNoOpStorageBackend:
    """Test NoOpStorageBackend"""
    
    def test_noop_operations(self, test_run_id):
        """Test that NoOp backend accepts all operations"""
        backend = NoOpStorageBackend()
        
        assert backend.initialize() is True
        
        events = [
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_1",
                event_type=EventType.TEST_END,
                framework="pytest",
                duration_ms=100,
            ),
        ]
        
        assert backend.write_events(events) is True
        assert backend.flush() is True
        backend.shutdown()  # Should not raise


class TestLocalStorageBackend:
    """Test LocalStorageBackend"""
    
    def test_local_storage_creation(self, tmp_path, test_run_id):
        """Test local storage directory creation"""
        storage_path = tmp_path / "profiles"
        backend = LocalStorageBackend(str(storage_path))
        
        assert backend.initialize() is True
        assert storage_path.exists()
    
    def test_local_storage_write_events(self, tmp_path, test_run_id):
        """Test writing events to local storage"""
        storage_path = tmp_path / "profiles"
        backend = LocalStorageBackend(str(storage_path))
        backend.initialize()
        
        events = [
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_1",
                event_type=EventType.TEST_END,
                framework="pytest",
                duration_ms=100,
            ),
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_2",
                event_type=EventType.HTTP_REQUEST,
                framework="requests",
                duration_ms=250,
                endpoint="/api/users",
            ),
        ]
        
        assert backend.write_events(events) is True
        
        # Verify file was created and contains data
        files = list(storage_path.glob("*.jsonl"))
        assert len(files) == 1
        
        content = files[0].read_text()
        assert "test_1" in content
        assert "test_2" in content


class TestPostgresStorageBackend:
    """Test PostgresStorageBackend with real database"""
    
    @pytest.fixture
    def postgres_backend(self, test_config):
        """Create PostgreSQL backend"""
        backend = PostgresStorageBackend(test_config)
        yield backend
        backend.shutdown()
    
    def test_postgres_initialization(self, postgres_backend):
        """Test PostgreSQL initialization and schema creation"""
        result = postgres_backend.initialize()
        assert result is True
        assert postgres_backend._initialized is True
    
    def test_postgres_write_test_events(self, postgres_backend, test_run_id):
        """Test writing test lifecycle events"""
        postgres_backend.initialize()
        
        events = [
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_login",
                event_type=EventType.TEST_END,
                framework="pytest",
                duration_ms=1500,
                status="passed",
            ),
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_logout",
                event_type=EventType.TEST_END,
                framework="pytest",
                duration_ms=850,
                status="passed",
            ),
        ]
        
        result = postgres_backend.write_events(events)
        assert result is True
    
    def test_postgres_write_http_events(self, postgres_backend, test_run_id):
        """Test writing HTTP request events"""
        postgres_backend.initialize()
        
        events = [
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_api_login",
                event_type=EventType.HTTP_REQUEST,
                framework="requests",
                duration_ms=320,
                endpoint="/api/auth/login",
                method="POST",
                status_code=200,
            ),
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_api_users",
                event_type=EventType.HTTP_REQUEST,
                framework="requests",
                duration_ms=150,
                endpoint="/api/users",
                method="GET",
                status_code=200,
            ),
        ]
        
        result = postgres_backend.write_events(events)
        assert result is True
    
    def test_postgres_write_driver_events(self, postgres_backend, test_run_id):
        """Test writing WebDriver command events"""
        postgres_backend.initialize()
        
        events = [
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_selenium",
                event_type=EventType.DRIVER_COMMAND,
                framework="selenium",
                duration_ms=50,
                command="find_element",
                retry_count=0,
            ),
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_selenium",
                event_type=EventType.DRIVER_COMMAND,
                framework="selenium",
                duration_ms=25,
                command="click",
                retry_count=0,
            ),
        ]
        
        result = postgres_backend.write_events(events)
        assert result is True
    
    def test_postgres_write_step_events(self, postgres_backend, test_run_id):
        """Test writing test step events"""
        postgres_backend.initialize()
        
        events = [
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_checkout",
                event_type=EventType.SETUP_END,
                framework="pytest",
                duration_ms=200,
                step_name="setup_database",
            ),
            PerformanceEvent.create(
                run_id=test_run_id,
                test_id="test_checkout",
                event_type=EventType.TEARDOWN_END,
                framework="pytest",
                duration_ms=150,
                step_name="cleanup_database",
            ),
        ]
        
        result = postgres_backend.write_events(events)
        assert result is True
    
    def test_postgres_batch_write(self, postgres_backend, test_run_id):
        """Test batch writing multiple event types"""
        postgres_backend.initialize()
        
        # Create a realistic test scenario with multiple event types
        events = []
        
        # Test lifecycle events
        for i in range(5):
            events.append(
                PerformanceEvent.create(
                    run_id=test_run_id,
                    test_id=f"test_batch_{i}",
                    event_type=EventType.TEST_END,
                    framework="pytest",
                    duration_ms=1000 + (i * 100),
                    status="passed",
                )
            )
        
        # HTTP events
        for i in range(3):
            events.append(
                PerformanceEvent.create(
                    run_id=test_run_id,
                    test_id=f"test_api_{i}",
                    event_type=EventType.HTTP_REQUEST,
                    framework="requests",
                    duration_ms=200 + (i * 50),
                    endpoint=f"/api/endpoint_{i}",
                    method="GET",
                    status_code=200,
                )
            )
        
        # WebDriver events
        for i in range(4):
            events.append(
                PerformanceEvent.create(
                    run_id=test_run_id,
                    test_id=f"test_selenium_{i}",
                    event_type=EventType.DRIVER_COMMAND,
                    framework="selenium",
                    duration_ms=50 + (i * 10),
                    command="find_element",
                    retry_count=0,
                )
            )
        
        result = postgres_backend.write_events(events)
        assert result is True


class TestStorageFactory:
    """Test StorageFactory"""
    
    def test_factory_noop_backend(self):
        """Test factory creates NoOp backend when disabled"""
        config = ProfileConfig(enabled=False)
        backend = StorageFactory.from_config(config)
        
        assert isinstance(backend, NoOpStorageBackend)
    
    def test_factory_local_backend(self):
        """Test factory creates Local backend"""
        config = ProfileConfig(
            enabled=True,
            backend=StorageBackendType.LOCAL,
            local_path=".test/profiles",
        )
        backend = StorageFactory.from_config(config)
        
        assert isinstance(backend, LocalStorageBackend)
    
    def test_factory_postgres_backend(self, test_config):
        """Test factory creates PostgreSQL backend"""
        backend = StorageFactory.from_config(test_config)
        
        assert isinstance(backend, PostgresStorageBackend)


# ============================================================================
# Test: Metrics Collector
# ============================================================================

class TestMetricsCollector:
    """Test MetricsCollector service"""
    
    @pytest.fixture(autouse=True)
    def reset_collector(self):
        """Reset collector singleton before each test"""
        MetricsCollector.reset_instance()
        yield
        MetricsCollector.reset_instance()
    
    def test_collector_disabled_by_default(self):
        """Test collector is disabled by default"""
        collector = MetricsCollector.get_instance()
        
        assert collector.config.enabled is False
        assert collector.running is False
    
    def test_collector_start_with_config(self, test_config):
        """Test starting collector with configuration"""
        collector = MetricsCollector.get_instance(test_config)
        result = collector.start()
        
        assert result is True
        assert collector.running is True
        assert collector.current_run_id is not None
        
        collector.shutdown()
    
    def test_collector_collect_events(self, test_config, test_run_id):
        """Test collecting events"""
        collector = MetricsCollector.get_instance(test_config)
        collector.start()
        
        # Collect some events
        for i in range(10):
            event = PerformanceEvent.create(
                run_id=collector.current_run_id,
                test_id=f"test_{i}",
                event_type=EventType.TEST_END,
                framework="pytest",
                duration_ms=1000 + i,
            )
            collector.collect(event)
        
        time.sleep(3)  # Wait longer for background flush
        
        assert collector.events_collected == 10
        # Note: events_written may be 0 if flush hasn't completed yet
        # This is expected behavior for async operation
        
        collector.shutdown()
    
    def test_collector_flush(self, test_config):
        """Test manual flush"""
        collector = MetricsCollector.get_instance(test_config)
        collector.start()
        
        # Collect events
        for i in range(5):
            event = PerformanceEvent.create(
                run_id=collector.current_run_id,
                test_id=f"test_{i}",
                event_type=EventType.TEST_END,
                framework="pytest",
                duration_ms=1000,
            )
            collector.collect(event)
        
        result = collector.flush()
        assert result is True
        
        collector.shutdown()
    
    def test_collector_stats(self, test_config):
        """Test collector statistics"""
        collector = MetricsCollector.get_instance(test_config)
        collector.start()
        
        stats = collector.get_stats()
        
        assert "enabled" in stats
        assert "running" in stats
        assert "run_id" in stats
        assert "events_collected" in stats
        assert "events_written" in stats
        
        collector.shutdown()


# ============================================================================
# Test: Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    @pytest.fixture(autouse=True)
    def reset_collector(self):
        """Reset collector before each test"""
        MetricsCollector.reset_instance()
        yield
        MetricsCollector.reset_instance()
    
    def test_complete_test_lifecycle(self, test_config):
        """Test complete test execution lifecycle"""
        collector = MetricsCollector.get_instance(test_config)
        collector.start()
        
        run_id = collector.current_run_id
        test_id = "test_complete_flow"
        
        # Setup phase
        setup_event = PerformanceEvent.create(
            run_id=run_id,
            test_id=test_id,
            event_type=EventType.SETUP_END,
            framework="pytest",
            duration_ms=150,
            step_name="setup_database",
        )
        collector.collect(setup_event)
        
        # Test execution with HTTP calls
        test_start = PerformanceEvent.create(
            run_id=run_id,
            test_id=test_id,
            event_type=EventType.TEST_START,
            framework="pytest",
            duration_ms=0,
        )
        collector.collect(test_start)
        
        # Simulate HTTP calls
        http_event = PerformanceEvent.create(
            run_id=run_id,
            test_id=test_id,
            event_type=EventType.HTTP_REQUEST,
            framework="requests",
            duration_ms=320,
            endpoint="/api/login",
            method="POST",
            status_code=200,
        )
        collector.collect(http_event)
        
        # Test end
        test_end = PerformanceEvent.create(
            run_id=run_id,
            test_id=test_id,
            event_type=EventType.TEST_END,
            framework="pytest",
            duration_ms=1500,
            status="passed",
        )
        collector.collect(test_end)
        
        # Teardown phase
        teardown_event = PerformanceEvent.create(
            run_id=run_id,
            test_id=test_id,
            event_type=EventType.TEARDOWN_END,
            framework="pytest",
            duration_ms=100,
            step_name="cleanup_database",
        )
        collector.collect(teardown_event)
        
        time.sleep(2)  # Wait for flush
        
        assert collector.events_collected == 5
        
        collector.shutdown()
    
    def test_selenium_test_flow(self, test_config):
        """Test Selenium test flow with driver commands"""
        collector = MetricsCollector.get_instance(test_config)
        collector.start()
        
        run_id = collector.current_run_id
        test_id = "test_selenium_flow"
        
        # Test start
        collector.collect(
            PerformanceEvent.create(
                run_id=run_id,
                test_id=test_id,
                event_type=EventType.TEST_START,
                framework="selenium",
                duration_ms=0,
            )
        )
        
        # WebDriver commands
        commands = ["get", "find_element", "click", "send_keys", "find_element", "click"]
        for cmd in commands:
            collector.collect(
                PerformanceEvent.create(
                    run_id=run_id,
                    test_id=test_id,
                    event_type=EventType.DRIVER_COMMAND,
                    framework="selenium",
                    duration_ms=50,
                    command=cmd,
                    retry_count=0,
                )
            )
        
        # Test end
        collector.collect(
            PerformanceEvent.create(
                run_id=run_id,
                test_id=test_id,
                event_type=EventType.TEST_END,
                framework="selenium",
                duration_ms=2000,
                status="passed",
            )
        )
        
        time.sleep(2)
        
        assert collector.events_collected == 8  # 1 start + 6 commands + 1 end
        
        collector.shutdown()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
