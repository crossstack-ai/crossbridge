#!/usr/bin/env python3
"""
Verification Script: Test Infrastructure & Sidecar Hardening

Quick verification that all components are working correctly.

Usage:
    python verify_implementation.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_header(text: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_success(text: str):
    """Print success message."""
    print(f"✅ {text}")


def print_error(text: str):
    """Print error message."""
    print(f"❌ {text}")


def verify_fixtures():
    """Verify golden fixtures are available."""
    print_header("Verifying Golden Fixtures")
    
    try:
        from tests.fixtures import (
            sample_test,
            sample_pytest_test,
            sample_selenium_test,
            sample_robot_test,
            sample_login_scenario,
            sample_e2e_scenario,
            sample_timeout_failure,
            sample_flaky_failure
        )
        
        # Test basic fixture
        test = sample_test()
        assert test['name'] == 'test_valid_login'
        assert test['timestamp'] == '2026-01-31T10:00:00Z'
        print_success("Basic test fixture works")
        
        # Test scenario
        scenario = sample_login_scenario()
        assert 'test_cases' in scenario
        print_success("Scenario fixture works")
        
        # Test failure
        failure = sample_timeout_failure()
        assert failure['failure_type'] == 'ENVIRONMENT_ISSUE'
        print_success("Failure fixture works")
        
        return True
    
    except Exception as e:
        print_error(f"Fixtures failed: {e}")
        return False


def verify_adapter_contracts():
    """Verify adapter contract framework."""
    print_header("Verifying Adapter Contracts")
    
    try:
        from tests.unit.adapters.test_adapter_contract import (
            AdapterContract,
            run_adapter_contract_tests
        )
        
        # Verify contract interface exists
        assert hasattr(AdapterContract, 'extract_tests')
        assert hasattr(AdapterContract, 'get_framework_name')
        print_success("Adapter contract interface defined")
        
        # Verify test runner exists
        assert callable(run_adapter_contract_tests)
        print_success("Contract test runner available")
        
        return True
    
    except Exception as e:
        print_error(f"Adapter contracts failed: {e}")
        return False


def verify_sidecar_core():
    """Verify sidecar core infrastructure."""
    print_header("Verifying Sidecar Core")
    
    try:
        from core.observability.sidecar import (
            get_config,
            get_metrics,
            get_event_queue,
            get_sampler,
            get_resource_monitor,
            safe_observe
        )
        
        # Verify configuration
        config = get_config()
        assert config.enabled is not None
        assert config.max_queue_size > 0
        print_success("Configuration loads")
        
        # Verify metrics
        metrics = get_metrics()
        metrics.increment('test.counter')
        result = metrics.get_metrics()
        assert 'counters' in result
        print_success("Metrics collection works")
        
        # Verify queue
        queue = get_event_queue()
        test_event = {'type': 'verify', 'id': 'test_1'}
        queue.put(test_event)
        retrieved = queue.get(timeout=1.0)
        assert retrieved is not None
        print_success("Event queue works")
        
        # Verify sampling
        sampler = get_sampler()
        result = sampler.should_sample('events')
        assert isinstance(result, bool)
        print_success("Sampling works")
        
        # Verify resource monitoring
        monitor = get_resource_monitor()
        resources = monitor.check_resources()
        assert 'cpu_percent' in resources
        assert 'memory_mb' in resources
        print_success("Resource monitoring works")
        
        # Verify fail-open
        @safe_observe("test_operation")
        def failing_op():
            raise ValueError("Test error")
        
        result = failing_op()
        assert result is None  # Should return None, not raise
        print_success("Fail-open execution works")
        
        return True
    
    except Exception as e:
        print_error(f"Sidecar core failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_health_endpoints():
    """Verify health and metrics endpoints."""
    print_header("Verifying Health Endpoints")
    
    try:
        from core.observability.sidecar.health import (
            get_health_status,
            get_readiness_status,
            get_prometheus_metrics
        )
        
        # Verify health status
        health = get_health_status()
        assert 'status' in health
        assert 'queue' in health
        assert 'resources' in health
        print_success("Health status works")
        
        # Verify readiness
        readiness = get_readiness_status()
        assert 'ready' in readiness
        print_success("Readiness status works")
        
        # Verify Prometheus metrics
        metrics = get_prometheus_metrics()
        assert isinstance(metrics, str)
        assert len(metrics) > 0
        print_success("Prometheus metrics export works")
        
        return True
    
    except Exception as e:
        print_error(f"Health endpoints failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_structured_logging():
    """Verify structured logging."""
    print_header("Verifying Structured Logging")
    
    try:
        from core.observability.sidecar.logging import (
            set_run_id,
            set_test_id,
            get_run_id,
            get_test_id,
            clear_context,
            log_sidecar_event
        )
        
        # Verify context management
        set_run_id('verify_run_123')
        set_test_id('verify_test_456')
        
        assert get_run_id() == 'verify_run_123'
        assert get_test_id() == 'verify_test_456'
        print_success("Correlation context works")
        
        # Clear context
        clear_context()
        assert get_run_id() is None
        print_success("Context clearing works")
        
        # Verify logging (doesn't raise)
        log_sidecar_event('test_event', test_field='value')
        print_success("Structured logging works")
        
        return True
    
    except Exception as e:
        print_error(f"Structured logging failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_tests_exist():
    """Verify test files exist."""
    print_header("Verifying Test Files")
    
    test_files = [
        'tests/fixtures/__init__.py',
        'tests/fixtures/sample_tests.py',
        'tests/fixtures/sample_scenarios.py',
        'tests/fixtures/sample_failures.py',
        'tests/unit/adapters/test_adapter_contract.py',
        'tests/integration/sidecar/test_sidecar_integration.py',
        'tests/integration/sidecar/test_sidecar_chaos.py',
        'tests/e2e/test_smoke.py',
    ]
    
    all_exist = True
    for file_path in test_files:
        if os.path.exists(file_path):
            print_success(f"{file_path} exists")
        else:
            print_error(f"{file_path} missing")
            all_exist = False
    
    return all_exist


def verify_configuration():
    """Verify configuration files."""
    print_header("Verifying Configuration Files")
    
    config_files = [
        'crossbridge.yml',
        '.ci/test-configuration.yml',
    ]
    
    all_exist = True
    for file_path in config_files:
        if os.path.exists(file_path):
            print_success(f"{file_path} exists")
        else:
            print_error(f"{file_path} missing")
            all_exist = False
    
    return all_exist


def verify_documentation():
    """Verify documentation files."""
    print_header("Verifying Documentation")
    
    doc_files = [
        'docs/TEST_INFRASTRUCTURE_AND_SIDECAR_HARDENING.md',
        'docs/IMPLEMENTATION_SUMMARY.md',
        'docs/QUICKSTART_SIDECAR.md',
    ]
    
    all_exist = True
    for file_path in doc_files:
        if os.path.exists(file_path):
            print_success(f"{file_path} exists")
        else:
            print_error(f"{file_path} missing")
            all_exist = False
    
    return all_exist


def main():
    """Run all verifications."""
    print("\n" + "=" * 80)
    print("  CROSSBRIDGE TEST INFRASTRUCTURE & SIDECAR VERIFICATION")
    print("=" * 80)
    
    results = []
    
    # Run verifications
    results.append(("Golden Fixtures", verify_fixtures()))
    results.append(("Adapter Contracts", verify_adapter_contracts()))
    results.append(("Sidecar Core", verify_sidecar_core()))
    results.append(("Health Endpoints", verify_health_endpoints()))
    results.append(("Structured Logging", verify_structured_logging()))
    results.append(("Test Files", verify_tests_exist()))
    results.append(("Configuration", verify_configuration()))
    results.append(("Documentation", verify_documentation()))
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All verifications passed! Implementation is complete.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} verification(s) failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
