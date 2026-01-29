"""
Simple test to generate version-aware data for Grafana visualization

This runs actual CrossBridge hooks with different version configurations
to populate the database with realistic version-tracked test data.
"""

import os
import sys
import time
from datetime import datetime

# Set up paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Disable hooks initially to avoid DB connection during import
os.environ['CROSSBRIDGE_HOOKS_ENABLED'] = 'false'

from core.observability.hook_sdk import CrossBridgeHookSDK
from core.observability.events import TestStartEvent, TestEndEvent

print("=" * 70)
print("Generating Version-Aware Test Data for Grafana")
print("=" * 70)
print()

# Define test scenarios with different versions
scenarios = [
    {
        "product": "MyWebApp",
        "version": "1.0.0",
        "environment": "production",
        "pass_rate": 0.95,
        "test_count": 20
    },
    {
        "product": "MyWebApp",
        "version": "2.0.0",
        "environment": "staging",
        "pass_rate": 0.80,
        "test_count": 25
    },
    {
        "product": "MyWebApp",
        "version": "2.1.0",
        "environment": "dev",
        "pass_rate": 0.70,
        "test_count": 30
    },
    {
        "product": "PaymentAPI",
        "version": "3.2.0",
        "environment": "production",
        "pass_rate": 0.98,
        "test_count": 15
    },
]

test_names = [
    "test_user_login",
    "test_user_registration",
    "test_checkout_flow",
    "test_payment_processing",
    "test_order_confirmation",
    "test_search_functionality",
    "test_filter_products",
    "test_add_to_cart",
]

import random

total_events = 0

for scenario in scenarios:
    print(f"\n📦 {scenario['product']} v{scenario['version']} ({scenario['environment']})")
    print(f"   Pass Rate: {scenario['pass_rate']*100}% | Tests: {scenario['test_count']}")
    
    # Enable hooks and set version info for this scenario
    os.environ['CROSSBRIDGE_HOOKS_ENABLED'] = 'true'
    os.environ['APP_VERSION'] = scenario['version']
    os.environ['PRODUCT_NAME'] = scenario['product']
    os.environ['ENVIRONMENT'] = scenario['environment']
    
    # Reinitialize SDK with new environment
    CrossBridgeHookSDK._instance = None
    sdk = CrossBridgeHookSDK()
    
    # Generate test events
    for i in range(scenario['test_count']):
        test_name = random.choice(test_names)
        test_id = f"pytest::tests/{test_name}.py::{test_name}"
        
        # Determine pass/fail based on pass rate
        passed = random.random() < scenario['pass_rate']
        status = "passed" if passed else "failed"
        duration = random.randint(100, 3000)
        
        try:
            # Emit test start
            start_event = TestStartEvent(
                framework="pytest",
                test_id=test_id,
                application_version=scenario['version'],
                product_name=scenario['product'],
                environment=scenario['environment']
            )
            if sdk.persistence:
                sdk.persistence.store_event(start_event)
            
            # Emit test end
            end_event = TestEndEvent(
                framework="pytest",
                test_id=test_id,
                status=status,
                duration_ms=duration,
                error_message="AssertionError: Test failed" if not passed else None,
                application_version=scenario['version'],
                product_name=scenario['product'],
                environment=scenario['environment']
            )
            if sdk.persistence:
                sdk.persistence.store_event(end_event)
            
            total_events += 2
            
        except Exception as e:
            print(f"   ⚠️  Error emitting event: {e}")
            continue
    
    print(f"   ✓ Generated {scenario['test_count'] * 2} events")

print()
print("=" * 70)
print(f"✅ Successfully generated {total_events} events across {len(scenarios)} versions")
print()
print("🎯 Next Steps:")
print("   1. Open Grafana: http://10.55.12.99:3000/")
print("   2. Go to dashboard (or import grafana/dashboard_version_aware.json)")
print("   3. You should now see:")
print("      • Coverage by version charts")
print("      • Version comparison table")
print("      • Pass rate trends")
print("      • Multi-product tracking")
print()
print("📊 Verify data in database:")
print("   SELECT application_version, product_name, COUNT(*) ")
print("   FROM test_execution_event ")
print("   GROUP BY application_version, product_name;")
print("=" * 70)
