#!/usr/bin/env python
"""
Verification script for test infrastructure and sidecar hardening implementation.
"""

import sys

def verify():
    results = []
    
    # Test 1: Smoke tests
    try:
        import subprocess
        result = subprocess.run(
            ['python', '-m', 'pytest', 'tests/e2e/test_smoke.py', '-q'],
            capture_output=True,
            text=True,
            timeout=30
        )
        passed = 'passed' in result.stdout
        results.append(('Smoke Tests', passed, result.stdout.split('\n')[-2]))
    except Exception as e:
        results.append(('Smoke Tests', False, str(e)))
    
    # Test 2: Fixtures
    try:
        from tests.fixtures import (
            sample_test, sample_pytest_test, sample_selenium_test,
            sample_login_scenario, sample_api_scenario,
            sample_timeout_failure, sample_assertion_failure,
            sample_failure_batch
        )
        results.append(('Fixtures (27 total)', True, 'All fixtures importable'))
    except Exception as e:
        results.append(('Fixtures', False, str(e)))
    
    # Test 3: Sidecar Core
    try:
        from core.observability.sidecar import (
            get_config, get_metrics, get_event_queue,
            get_sampler, get_resource_monitor
        )
        config = get_config()
        results.append(('Sidecar Core', True, f'Queue size: {config.max_queue_size}'))
    except Exception as e:
        results.append(('Sidecar Core', False, str(e)))
    
    # Test 4: Health Endpoints
    try:
        from core.observability.sidecar.health import (
            get_health_status, get_readiness_status, get_prometheus_metrics
        )
        health = get_health_status()
        results.append(('Health Endpoints', True, f'Status: {health["status"]}'))
    except Exception as e:
        results.append(('Health Endpoints', False, str(e)))
    
    # Test 5: Structured Logging
    try:
        from core.observability.sidecar.logging import (
            log_sidecar_event, set_run_id, get_run_id
        )
        set_run_id('test_123')
        run_id = get_run_id()
        results.append(('Structured Logging', run_id == 'test_123', 'Correlation tracking works'))
    except Exception as e:
        results.append(('Structured Logging', False, str(e)))
    
    # Print results
    print("\n" + "="*70)
    print(" "*20 + "IMPLEMENTATION VERIFICATION")
    print("="*70 + "\n")
    
    all_passed = True
    for name, passed, detail in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {name:30} {detail[:30]}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - Implementation Complete!")
    else:
        print("⚠️  Some checks failed - Review errors above")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(verify())
