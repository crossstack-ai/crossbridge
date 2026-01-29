"""
CrossBridge Continuous Intelligence - Live Demo

This demo shows:
1. Lifecycle initialization
2. Observer service startup
3. Simulated test executions
4. Coverage intelligence updates
5. Drift detection
6. Real-time monitoring

Run: python demo_continuous_intelligence.py
"""

import time
import random
from datetime import datetime, timedelta
from core.observability import (
    LifecycleManager,
    CrossBridgeMode,
    CrossBridgeObserverService,
    CrossBridgeHookSDK,
    CoverageIntelligence,
    DriftDetector
)


def print_header(title):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_step(step_num, description):
    """Print step indicator"""
    print(f"\n[STEP {step_num}] {description}")
    print("-" * 70)


def demo_lifecycle():
    """Demo: Lifecycle management"""
    print_header("DEMO 1: Lifecycle Management")
    
    manager = LifecycleManager(
        project_id="demo_project",
        db_host="10.55.12.99",
        db_port=5432,
        db_name="udp-native-webservices-automation",
        db_user="postgres",
        db_password="admin"
    )
    
    print_step(1, "Initialize migration state")
    try:
        manager.initialize_migration()
        mode = manager.get_current_mode()
        print(f"✅ Current mode: {mode}")
    except Exception:
        # Already exists
        mode = manager.get_current_mode()
        print(f"ℹ️ Already initialized, current mode: {mode}")
    
    print_step(2, "Transition to observer mode")
    if mode == CrossBridgeMode.MIGRATION:
        manager.transition_to_observer()
        print("✅ Transitioned to OBSERVER mode (permanent)")
    else:
        print("ℹ️ Already in OBSERVER mode")
    
    print_step(3, "Verify one-way transition")
    try:
        manager.set_mode(CrossBridgeMode.MIGRATION)
        print("❌ ERROR: Should not allow going back to migration!")
    except ValueError as e:
        print(f"✅ One-way transition enforced: {e}")
    
    return manager


def demo_observer_service():
    """Demo: Observer service"""
    print_header("DEMO 2: Observer Service")
    
    print_step(1, "Start observer service")
    observer = CrossBridgeObserverService(
        db_host="10.55.12.99",
        db_port=5432,
        db_name="udp-native-webservices-automation",
        db_user="postgres",
        db_password="admin"
    )
    
    observer.start()
    time.sleep(1)
    
    health = observer.get_health_metrics()
    print(f"✅ Observer service started")
    print(f"   - Running: {health['is_running']}")
    print(f"   - Queue size: {health['queue_size']}")
    print(f"   - Events processed: {health['events_processed']}")
    
    return observer


def demo_test_execution(observer, hook):
    """Demo: Simulated test execution"""
    print_header("DEMO 3: Test Execution Simulation")
    
    # Test scenarios
    test_scenarios = [
        {
            'id': 'test_login',
            'name': 'User Login Flow',
            'framework': 'pytest',
            'file': '/tests/test_auth.py',
            'status': 'passed',
            'duration': 1.2,
            'metadata': {
                'api_calls': ['/api/auth/login', '/api/users/profile'],
                'pages_visited': ['login', 'dashboard'],
                'ui_components': ['button:login', 'input:email', 'input:password']
            }
        },
        {
            'id': 'test_checkout',
            'name': 'Checkout Process',
            'framework': 'pytest',
            'file': '/tests/test_payment.py',
            'status': 'passed',
            'duration': 2.5,
            'metadata': {
                'api_calls': ['/api/cart/add', '/api/payments/create', '/api/orders/confirm'],
                'pages_visited': ['cart', 'checkout', 'confirmation'],
                'ui_components': ['button:checkout', 'input:card_number', 'button:confirm']
            }
        },
        {
            'id': 'test_search',
            'name': 'Product Search',
            'framework': 'pytest',
            'file': '/tests/test_search.py',
            'status': 'passed',
            'duration': 0.8,
            'metadata': {
                'api_calls': ['/api/products/search', '/api/products/filter'],
                'pages_visited': ['home', 'search_results'],
                'ui_components': ['input:search', 'button:search']
            }
        },
        {
            'id': 'test_profile',
            'name': 'User Profile Update',
            'framework': 'robot',
            'file': '/tests/test_profile.robot',
            'status': 'passed',
            'duration': 1.5,
            'metadata': {
                'api_calls': ['/api/users/profile', '/api/users/update'],
                'pages_visited': ['profile', 'settings'],
                'ui_components': ['input:name', 'button:save']
            }
        },
        {
            'id': 'test_flaky',
            'name': 'Flaky Test Example',
            'framework': 'pytest',
            'file': '/tests/test_flaky.py',
            'status': random.choice(['passed', 'failed']),
            'duration': random.uniform(0.5, 3.0),
            'metadata': {
                'api_calls': ['/api/external/service'],
                'pages_visited': ['external_integration'],
                'ui_components': []
            }
        }
    ]
    
    print_step(1, "Emit test execution events")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n[Test {i}/5] {scenario['name']}")
        
        # Emit test_start
        hook.emit_test_start(
            test_id=scenario['id'],
            test_name=scenario['name'],
            framework=scenario['framework'],
            file_path=scenario['file'],
            application_version="v2.1.0",
            product_name="MyWebApp",
            environment="staging",
            metadata=scenario['metadata']
        )
        
        # Simulate test execution
        time.sleep(0.2)
        
        # Emit test_end
        hook.emit_test_end(
            test_id=scenario['id'],
            status=scenario['status'],
            duration=scenario['duration']
        )
        
        print(f"  ✅ {scenario['status'].upper()} in {scenario['duration']:.2f}s")
        print(f"     APIs: {len(scenario['metadata']['api_calls'])}, "
              f"Pages: {len(scenario['metadata']['pages_visited'])}")
    
    print_step(2, "Wait for observer to process events")
    time.sleep(3)
    
    health = observer.get_health_metrics()
    print(f"✅ Events processed: {health['events_processed']}")
    print(f"   Queue size: {health['queue_size']}")


def demo_coverage_intelligence(coverage):
    """Demo: Coverage intelligence"""
    print_header("DEMO 4: Coverage Intelligence")
    
    print_step(1, "Query API coverage")
    tests = coverage.get_tests_for_api('/api/auth/login')
    print(f"Tests covering '/api/auth/login': {tests}")
    
    tests = coverage.get_tests_for_api('/api/payments/create')
    print(f"Tests covering '/api/payments/create': {tests}")
    
    print_step(2, "Query page coverage")
    tests = coverage.get_tests_for_page('checkout')
    print(f"Tests visiting 'checkout' page: {tests}")
    
    tests = coverage.get_tests_for_page('login')
    print(f"Tests visiting 'login' page: {tests}")
    
    print_step(3, "Change impact analysis")
    impacted = coverage.get_impacted_tests(
        changed_node_id='api:/api/payments/create',
        node_type='api'
    )
    print(f"Tests impacted by payment API change: {impacted}")
    
    impacted = coverage.get_impacted_tests(
        changed_node_id='page:checkout',
        node_type='page'
    )
    print(f"Tests impacted by checkout page change: {impacted}")


def demo_drift_detection(detector):
    """Demo: Drift detection"""
    print_header("DEMO 5: Drift Detection")
    
    print_step(1, "Detect new tests")
    signals = detector.detect_new_tests()
    print(f"New tests detected: {len(signals)}")
    for signal in signals[:5]:
        print(f"  🆕 {signal.test_id}: {signal.description}")
    
    print_step(2, "Detect behavior changes")
    signals = detector.detect_behavior_changes()
    print(f"Behavior changes detected: {len(signals)}")
    for signal in signals[:3]:
        print(f"  ⚠️ {signal.test_id}: {signal.description}")
    
    print_step(3, "Detect flaky tests")
    signals = detector.detect_flaky_tests()
    print(f"Flaky tests detected: {len(signals)}")
    for signal in signals[:3]:
        print(f"  ⚡ {signal.test_id}: {signal.description}")
    
    print_step(4, "Detect removed tests")
    signals = detector.detect_removed_tests()
    print(f"Removed tests detected: {len(signals)}")
    for signal in signals[:3]:
        print(f"  🗑️ {signal.test_id}: {signal.description}")


def demo_real_time_monitoring(observer):
    """Demo: Real-time monitoring"""
    print_header("DEMO 6: Real-time Monitoring")
    
    print("Monitoring observer service health for 10 seconds...")
    print("(Processing events in background)\n")
    
    for i in range(10):
        health = observer.get_health_metrics()
        
        status_icon = "🟢" if health['is_running'] else "🔴"
        error_icon = "⚠️" if health['processing_errors'] > 0 else "✅"
        
        print(f"[{i+1:2d}s] {status_icon} Running | "
              f"Processed: {health['events_processed']:3d} | "
              f"Queue: {health['queue_size']:2d} | "
              f"{error_icon} Errors: {health['processing_errors']}")
        
        time.sleep(1)
    
    print("\n✅ Monitoring complete")


def main():
    """Run complete demo"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║  CrossBridge Continuous Intelligence - Live Demo                 ║
║                                                                   ║
║  This demo shows the complete post-migration observability       ║
║  system in action with simulated test executions.                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Demo 1: Lifecycle
    lifecycle_manager = demo_lifecycle()
    time.sleep(1)
    
    # Demo 2: Observer service
    observer = demo_observer_service()
    time.sleep(1)
    
    # Create hook SDK
    hook = CrossBridgeHookSDK(
        db_host="10.55.12.99",
        db_port=5432,
        db_name="udp-native-webservices-automation",
        db_user="postgres",
        db_password="admin"
    )
    
    # Demo 3: Test execution
    demo_test_execution(observer, hook)
    time.sleep(1)
    
    # Create coverage and detector
    coverage = CoverageIntelligence(
        db_host="10.55.12.99",
        db_port=5432,
        db_name="udp-native-webservices-automation",
        db_user="postgres",
        db_password="admin"
    )
    
    detector = DriftDetector(
        db_host="10.55.12.99",
        db_port=5432,
        db_name="udp-native-webservices-automation",
        db_user="postgres",
        db_password="admin"
    )
    
    # Demo 4: Coverage intelligence
    demo_coverage_intelligence(coverage)
    time.sleep(1)
    
    # Demo 5: Drift detection
    demo_drift_detection(detector)
    time.sleep(1)
    
    # Demo 6: Real-time monitoring
    demo_real_time_monitoring(observer)
    
    # Cleanup
    print_header("CLEANUP")
    print("Stopping observer service...")
    observer.stop()
    print("✅ Demo complete!\n")
    
    print("""
Next Steps:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. View data in Grafana:
   http://10.55.12.99:3000/

2. Query database:
   SELECT * FROM test_execution_event ORDER BY event_timestamp DESC LIMIT 10;
   SELECT * FROM drift_signals ORDER BY detected_at DESC LIMIT 10;
   SELECT node_type, COUNT(*) FROM coverage_graph_nodes GROUP BY node_type;

3. Install framework hooks:
   - Pytest: See docs/CONTINUOUS_INTELLIGENCE_GUIDE.md
   - Robot: robot --listener core.observability.hooks.robot_listener...
   - Playwright: See docs/CONTINUOUS_INTELLIGENCE_GUIDE.md

4. Run integration tests:
   pytest test_continuous_intelligence_integration.py -v

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


if __name__ == "__main__":
    main()
