"""
Unit Tests for Health Check System

Comprehensive tests for health checks and health registry.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import time

from core.runtime.health import (
    HealthStatus,
    HealthResult,
    HealthCheck,
    SimpleHealthCheck,
    PingHealthCheck,
    AIProviderHealthCheck,
    VectorStoreHealthCheck,
    HealthRegistry,
    get_health_registry
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""
    
    def test_status_values(self):
        """Test health status values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestHealthResult:
    """Tests for HealthResult."""
    
    def test_healthy_result(self):
        """Test creating healthy result."""
        result = HealthResult(
            status=HealthStatus.HEALTHY,
            message="All systems operational"
        )
        
        assert result.status == HealthStatus.HEALTHY
        assert result.healthy is True
        assert result.message == "All systems operational"
        assert isinstance(result.timestamp, datetime)
    
    def test_unhealthy_result(self):
        """Test creating unhealthy result."""
        result = HealthResult(
            status=HealthStatus.UNHEALTHY,
            message="Service unavailable"
        )
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.healthy is False
        assert result.message == "Service unavailable"
    
    def test_result_with_details(self):
        """Test result with additional details."""
        result = HealthResult(
            status=HealthStatus.HEALTHY,
            duration_ms=45.2,
            details={"connections": 10, "latency_ms": 5.3}
        )
        
        assert result.duration_ms == 45.2
        assert result.details["connections"] == 10
        assert result.details["latency_ms"] == 5.3
    
    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = HealthResult(
            status=HealthStatus.HEALTHY,
            duration_ms=50.0,
            message="OK",
            details={"version": "1.0"}
        )
        
        data = result.to_dict()
        
        assert data['status'] == "healthy"
        assert data['duration_ms'] == 50.0
        assert data['message'] == "OK"
        assert data['details'] == {"version": "1.0"}
        assert data['healthy'] is True
        assert 'timestamp' in data


class TestSimpleHealthCheck:
    """Tests for SimpleHealthCheck."""
    
    def test_healthy_check(self):
        """Test simple check that passes."""
        check = SimpleHealthCheck(
            name="test_service",
            check_func=lambda: True
        )
        
        result = check.check()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.healthy is True
        assert "OK" in result.message
    
    def test_unhealthy_check(self):
        """Test simple check that fails."""
        check = SimpleHealthCheck(
            name="test_service",
            check_func=lambda: False
        )
        
        result = check.check()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.healthy is False
        assert "False" in result.message
    
    def test_check_with_exception(self):
        """Test check that raises exception."""
        def failing_check():
            raise Exception("Service error")
        
        check = SimpleHealthCheck(
            name="failing_service",
            check_func=failing_check
        )
        
        result = check.check()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "Service error" in result.message
    
    def test_check_measures_duration(self):
        """Test check measures execution duration."""
        def slow_check():
            time.sleep(0.1)
            return True
        
        check = SimpleHealthCheck(
            name="slow_service",
            check_func=slow_check
        )
        
        result = check.check()
        
        assert result.duration_ms >= 100  # At least 100ms
    
    def test_check_name(self):
        """Test check name property."""
        check = SimpleHealthCheck(
            name="my_service",
            check_func=lambda: True
        )
        
        assert check.name == "my_service"


class TestPingHealthCheck:
    """Tests for PingHealthCheck."""
    
    def test_successful_ping(self):
        """Test successful ping check."""
        service = Mock()
        service.ping = Mock(return_value=True)
        
        check = PingHealthCheck("database", service)
        result = check.check()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.healthy is True
        service.ping.assert_called_once()
    
    def test_failed_ping(self):
        """Test failed ping check."""
        service = Mock()
        service.ping = Mock(side_effect=ConnectionError("Connection refused"))
        
        check = PingHealthCheck("database", service)
        result = check.check()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.healthy is False
        assert "Connection refused" in result.message
    
    def test_ping_duration(self):
        """Test ping measures duration."""
        service = Mock()
        
        def slow_ping():
            time.sleep(0.05)
            return True
        
        service.ping = slow_ping
        
        check = PingHealthCheck("database", service)
        result = check.check()
        
        assert result.duration_ms >= 50


class TestAIProviderHealthCheck:
    """Tests for AIProviderHealthCheck."""
    
    def test_successful_provider_check(self):
        """Test successful AI provider check."""
        provider = Mock()
        provider.embed = Mock(return_value=[[0.1, 0.2, 0.3]])
        
        check = AIProviderHealthCheck("openai", provider)
        result = check.check()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.healthy is True
        provider.embed.assert_called_once_with(["health_check"])
        assert result.details['embedding_dim'] == 3
    
    def test_provider_returns_empty(self):
        """Test provider returning empty result."""
        provider = Mock()
        provider.embed = Mock(return_value=[])
        
        check = AIProviderHealthCheck("openai", provider)
        result = check.check()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "empty result" in result.message.lower()
    
    def test_provider_fails(self):
        """Test provider failure."""
        provider = Mock()
        provider.embed = Mock(side_effect=Exception("API error"))
        
        check = AIProviderHealthCheck("openai", provider)
        result = check.check()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "API error" in result.message
    
    def test_provider_timeout(self):
        """Test provider timeout."""
        provider = Mock()
        provider.embed = Mock(side_effect=TimeoutError("Request timeout"))
        
        check = AIProviderHealthCheck("openai", provider)
        result = check.check()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.message.lower()


class TestVectorStoreHealthCheck:
    """Tests for VectorStoreHealthCheck."""
    
    def test_store_with_ping(self):
        """Test store with ping method."""
        store = Mock()
        store.ping = Mock(return_value=True)
        
        check = VectorStoreHealthCheck("chromadb", store)
        result = check.check()
        
        assert result.status == HealthStatus.HEALTHY
        store.ping.assert_called_once()
    
    def test_store_with_health_check(self):
        """Test store with health_check method."""
        store = Mock()
        del store.ping  # No ping method
        store.health_check = Mock(return_value=True)
        
        check = VectorStoreHealthCheck("chromadb", store)
        result = check.check()
        
        assert result.status == HealthStatus.HEALTHY
        store.health_check.assert_called_once()
    
    def test_store_with_get_collection(self):
        """Test store with get_collection fallback."""
        store = Mock()
        del store.ping
        del store.health_check
        store.get_collection = Mock(return_value=Mock())
        
        check = VectorStoreHealthCheck("chromadb", store)
        result = check.check()
        
        assert result.status == HealthStatus.HEALTHY
        store.get_collection.assert_called_once()
    
    def test_store_connection_failure(self):
        """Test store connection failure."""
        store = Mock()
        store.ping = Mock(side_effect=ConnectionError("Store unavailable"))
        
        check = VectorStoreHealthCheck("chromadb", store)
        result = check.check()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "unavailable" in result.message.lower()


class TestHealthRegistry:
    """Tests for HealthRegistry."""
    
    def test_initialization(self):
        """Test registry initialization."""
        registry = HealthRegistry()
        
        assert len(registry.checks) == 0
        assert len(registry.last_results) == 0
    
    def test_register_check(self):
        """Test registering a health check."""
        registry = HealthRegistry()
        check = SimpleHealthCheck("test", lambda: True)
        
        registry.register("test_check", check)
        
        assert "test_check" in registry.checks
        assert registry.checks["test_check"] == check
    
    def test_register_overwrites(self):
        """Test registering with same name overwrites."""
        registry = HealthRegistry()
        check1 = SimpleHealthCheck("test1", lambda: True)
        check2 = SimpleHealthCheck("test2", lambda: True)
        
        registry.register("check", check1)
        registry.register("check", check2)
        
        assert registry.checks["check"] == check2
    
    def test_unregister_check(self):
        """Test unregistering a check."""
        registry = HealthRegistry()
        check = SimpleHealthCheck("test", lambda: True)
        
        registry.register("check", check)
        assert "check" in registry.checks
        
        registry.unregister("check")
        assert "check" not in registry.checks
    
    def test_run_specific_check(self):
        """Test running specific check."""
        registry = HealthRegistry()
        check = SimpleHealthCheck("test", lambda: True)
        
        registry.register("test_check", check)
        result = registry.run("test_check")
        
        assert result.status == HealthStatus.HEALTHY
        assert "test_check" in registry.last_results
    
    def test_run_nonexistent_check(self):
        """Test running non-existent check raises error."""
        registry = HealthRegistry()
        
        with pytest.raises(KeyError, match="Health check not found"):
            registry.run("nonexistent")
    
    def test_run_all_checks(self):
        """Test running all registered checks."""
        registry = HealthRegistry()
        
        registry.register("check1", SimpleHealthCheck("c1", lambda: True))
        registry.register("check2", SimpleHealthCheck("c2", lambda: True))
        registry.register("check3", SimpleHealthCheck("c3", lambda: True))
        
        health = registry.run_all()
        
        assert health['total_checks'] == 3
        assert health['passed'] == 3
        assert health['failed'] == 0
        assert health['healthy'] is True
        assert health['overall_status'] == "healthy"
        assert len(health['checks']) == 3
    
    def test_run_all_with_failures(self):
        """Test running all checks with some failures."""
        registry = HealthRegistry()
        
        registry.register("passing", SimpleHealthCheck("p", lambda: True))
        registry.register("failing", SimpleHealthCheck("f", lambda: False))
        
        health = registry.run_all()
        
        assert health['total_checks'] == 2
        assert health['passed'] == 1
        assert health['failed'] == 1
        assert health['healthy'] is False
        assert health['overall_status'] == "degraded"
    
    def test_run_all_all_failing(self):
        """Test running all checks when all fail."""
        registry = HealthRegistry()
        
        registry.register("fail1", SimpleHealthCheck("f1", lambda: False))
        registry.register("fail2", SimpleHealthCheck("f2", lambda: False))
        
        health = registry.run_all()
        
        assert health['passed'] == 0
        assert health['failed'] == 2
        assert health['overall_status'] == "unhealthy"
    
    def test_get_status(self):
        """Test getting status for specific check."""
        registry = HealthRegistry()
        check = SimpleHealthCheck("test", lambda: True)
        
        registry.register("check", check)
        registry.run("check")
        
        status = registry.get_status("check")
        
        assert status is not None
        assert status.status == HealthStatus.HEALTHY
    
    def test_get_status_not_run(self):
        """Test getting status for check that hasn't run."""
        registry = HealthRegistry()
        check = SimpleHealthCheck("test", lambda: True)
        
        registry.register("check", check)
        
        status = registry.get_status("check")
        assert status is None
    
    def test_get_failed_checks(self):
        """Test getting failed check names."""
        registry = HealthRegistry()
        
        registry.register("pass1", SimpleHealthCheck("p1", lambda: True))
        registry.register("fail1", SimpleHealthCheck("f1", lambda: False))
        registry.register("pass2", SimpleHealthCheck("p2", lambda: True))
        registry.register("fail2", SimpleHealthCheck("f2", lambda: False))
        
        registry.run_all()
        
        failed = registry.get_failed_checks()
        
        assert len(failed) == 2
        assert "fail1" in failed
        assert "fail2" in failed
        assert "pass1" not in failed
    
    def test_is_healthy(self):
        """Test is_healthy method."""
        registry = HealthRegistry()
        
        # No checks = healthy
        assert registry.is_healthy() is True
        
        # All passing = healthy
        registry.register("check1", SimpleHealthCheck("c1", lambda: True))
        registry.register("check2", SimpleHealthCheck("c2", lambda: True))
        assert registry.is_healthy() is True
        
        # One failing = not healthy
        registry.register("check3", SimpleHealthCheck("c3", lambda: False))
        assert registry.is_healthy() is False
    
    def test_clear_registry(self):
        """Test clearing registry."""
        registry = HealthRegistry()
        
        registry.register("check1", SimpleHealthCheck("c1", lambda: True))
        registry.register("check2", SimpleHealthCheck("c2", lambda: True))
        registry.run_all()
        
        assert len(registry.checks) == 2
        assert len(registry.last_results) == 2
        
        registry.clear()
        
        assert len(registry.checks) == 0
        assert len(registry.last_results) == 0
    
    def test_check_exception_handling(self):
        """Test registry handles check exceptions gracefully."""
        registry = HealthRegistry()
        
        def broken_check():
            raise RuntimeError("Check broken")
        
        registry.register("broken", SimpleHealthCheck("b", broken_check))
        registry.register("working", SimpleHealthCheck("w", lambda: True))
        
        # Should not raise exception
        health = registry.run_all()
        
        assert health['total_checks'] == 2
        assert health['passed'] == 1
        assert health['failed'] == 1


class TestGlobalHealthRegistry:
    """Tests for global health registry singleton."""
    
    def test_get_health_registry_singleton(self):
        """Test global registry is singleton."""
        registry1 = get_health_registry()
        registry2 = get_health_registry()
        
        assert registry1 is registry2
    
    def test_global_registry_shared_state(self):
        """Test global registry maintains shared state."""
        registry1 = get_health_registry()
        registry1.clear()  # Clear any existing state
        
        registry1.register("test", SimpleHealthCheck("t", lambda: True))
        
        registry2 = get_health_registry()
        
        assert "test" in registry2.checks


class TestHealthCheckScenarios:
    """Real-world health check scenarios."""
    
    def test_multi_service_health_monitoring(self):
        """Test monitoring multiple services."""
        registry = HealthRegistry()
        
        # Database
        db = Mock()
        db.ping = Mock(return_value=True)
        registry.register("database", PingHealthCheck("db", db))
        
        # Cache
        cache = Mock()
        cache.ping = Mock(return_value=True)
        registry.register("cache", PingHealthCheck("cache", cache))
        
        # AI Provider
        ai = Mock()
        ai.embed = Mock(return_value=[[0.1, 0.2]])
        registry.register("ai", AIProviderHealthCheck("ai", ai))
        
        health = registry.run_all()
        
        assert health['healthy'] is True
        assert health['total_checks'] == 3
        assert health['passed'] == 3
    
    def test_degraded_service_detection(self):
        """Test detecting degraded service state."""
        registry = HealthRegistry()
        
        # Some services healthy
        registry.register("service1", SimpleHealthCheck("s1", lambda: True))
        registry.register("service2", SimpleHealthCheck("s2", lambda: True))
        
        # Some services unhealthy
        registry.register("service3", SimpleHealthCheck("s3", lambda: False))
        
        health = registry.run_all()
        
        assert health['overall_status'] == "degraded"
        assert health['healthy'] is False
        assert health['passed'] > 0
        assert health['failed'] > 0
    
    def test_health_check_timeout_handling(self):
        """Test handling slow health checks."""
        def slow_check():
            time.sleep(0.1)
            return True
        
        registry = HealthRegistry()
        registry.register("slow", SimpleHealthCheck("slow", slow_check))
        
        result = registry.run("slow")
        
        assert result.status == HealthStatus.HEALTHY
        assert result.duration_ms >= 100
    
    def test_cascading_failure_detection(self):
        """Test detecting cascading failures."""
        registry = HealthRegistry()
        
        # Simulate multiple related services failing
        registry.register("db", SimpleHealthCheck("db", lambda: False))
        registry.register("cache", SimpleHealthCheck("cache", lambda: False))
        registry.register("api", SimpleHealthCheck("api", lambda: False))
        
        health = registry.run_all()
        
        assert health['overall_status'] == "unhealthy"
        assert health['failed'] == 3
        assert len(registry.get_failed_checks()) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
