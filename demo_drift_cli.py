"""
Demo script for CLI drift monitoring commands.

This demonstrates:
1. Generating sample drift data
2. Using CLI commands to monitor drift
3. Interpreting CLI output
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from core.intelligence.confidence_drift import DriftDetector
from core.intelligence.drift_persistence import DriftPersistenceManager


def run_cli_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a CLI command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def demo_drift_cli():
    """Demonstrate CLI drift monitoring commands."""
    
    print("\n" + "="*60)
    print("  CROSSBRIDGE DRIFT MONITORING CLI DEMO")
    print("="*60 + "\n")
    
    db_path = "data/demo_drift_cli.db"
    
    # Ensure clean slate
    Path(db_path).unlink(missing_ok=True)
    Path(db_path).parent.mkdir(exist_ok=True)
    
    print("Step 1: Generate sample drift data\n")
    
    manager = DriftPersistenceManager(db_path)
    detector = DriftDetector()
    
    # Create realistic drift scenarios
    
    # Scenario 1: Stable test (test_login)
    print("  • Creating stable test: test_login")
    base_time = datetime.utcnow() - timedelta(days=30)
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        confidence = 0.85 + (i % 3) * 0.01  # Slight variation
        
        manager.store_measurement(
            test_name="test_login",
            confidence=confidence,
            category="authentication",
            timestamp=timestamp
        )
        
        detector.record_confidence(
            test_name="test_login",
            confidence=confidence,
            category="authentication",
            timestamp=timestamp
        )
    
    # Scenario 2: Drifting test (test_checkout) - decreasing confidence
    print("  • Creating drifting test: test_checkout (decreasing)")
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        # Start at 0.90, drop to 0.70
        confidence = 0.90 - (i / 30) * 0.20
        
        manager.store_measurement(
            test_name="test_checkout",
            confidence=confidence,
            category="e-commerce",
            timestamp=timestamp
        )
        
        detector.record_confidence(
            test_name="test_checkout",
            confidence=confidence,
            category="e-commerce",
            timestamp=timestamp
        )
    
    # Scenario 3: Volatile test (test_search)
    print("  • Creating volatile test: test_search")
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        # High volatility
        confidence = 0.75 + (i % 5) * 0.10 - 0.05
        
        manager.store_measurement(
            test_name="test_search",
            confidence=confidence,
            category="search",
            timestamp=timestamp
        )
        
        detector.record_confidence(
            test_name="test_search",
            confidence=confidence,
            category="search",
            timestamp=timestamp
        )
    
    # Generate and store drift analysis
    print("  • Analyzing drift for all tests")
    for test_name in ["test_login", "test_checkout", "test_search"]:
        analysis = detector.detect_drift(test_name)
        if analysis:
            manager.store_drift_analysis(test_name, analysis)
            
            # Create alert if drifting
            if analysis.is_drifting:
                alert = detector.alert_manager.create_alert(test_name, analysis)
                manager.store_alert(alert)
    
    print(f"\n✓ Generated drift data in: {db_path}\n")
    
    # Now demonstrate CLI commands
    
    print("\n" + "-"*60)
    print("Step 2: CLI Command Demonstrations")
    print("-"*60 + "\n")
    
    # Command 1: drift status
    print("Command 1: drift status (overall status)\n")
    print("  $ python -m cli.main drift status --db-path", db_path)
    print()
    
    code, stdout, stderr = run_cli_command([
        sys.executable, "-m", "cli.main",
        "drift", "status",
        "--db-path", db_path
    ])
    
    if code == 0:
        print(stdout)
    else:
        print(f"❌ Command failed: {stderr}")
    
    input("\nPress Enter to continue...")
    
    # Command 2: drift analyze
    print("\n" + "-"*60)
    print("Command 2: drift analyze (specific test)\n")
    print("  $ python -m cli.main drift analyze test_checkout --db-path", db_path)
    print()
    
    code, stdout, stderr = run_cli_command([
        sys.executable, "-m", "cli.main",
        "drift", "analyze", "test_checkout",
        "--db-path", db_path
    ])
    
    if code == 0:
        print(stdout)
    else:
        print(f"❌ Command failed: {stderr}")
    
    input("\nPress Enter to continue...")
    
    # Command 3: drift alerts
    print("\n" + "-"*60)
    print("Command 3: drift alerts (show all alerts)\n")
    print("  $ python -m cli.main drift alerts --hours 720 --db-path", db_path)
    print()
    
    code, stdout, stderr = run_cli_command([
        sys.executable, "-m", "cli.main",
        "drift", "alerts",
        "--hours", "720",  # Last 30 days
        "--db-path", db_path
    ])
    
    if code == 0:
        print(stdout)
    else:
        print(f"❌ Command failed: {stderr}")
    
    input("\nPress Enter to continue...")
    
    # Command 4: drift stats
    print("\n" + "-"*60)
    print("Command 4: drift stats (statistics)\n")
    print("  $ python -m cli.main drift stats --days 30 --db-path", db_path)
    print()
    
    code, stdout, stderr = run_cli_command([
        sys.executable, "-m", "cli.main",
        "drift", "stats",
        "--days", "30",
        "--db-path", db_path
    ])
    
    if code == 0:
        print(stdout)
    else:
        print(f"❌ Command failed: {stderr}")
    
    # Command 5: Category filtering
    print("\n" + "-"*60)
    print("Command 5: drift status with category filter\n")
    print("  $ python -m cli.main drift status --category e-commerce --db-path", db_path)
    print()
    
    code, stdout, stderr = run_cli_command([
        sys.executable, "-m", "cli.main",
        "drift", "status",
        "--category", "e-commerce",
        "--db-path", db_path
    ])
    
    if code == 0:
        print(stdout)
    else:
        print(f"❌ Command failed: {stderr}")
    
    print("\n" + "="*60)
    print("  CLI DEMO COMPLETE")
    print("="*60 + "\n")
    
    print("You can now explore the CLI commands:")
    print(f"  • python -m cli.main drift status --db-path {db_path}")
    print(f"  • python -m cli.main drift analyze <test_name> --db-path {db_path}")
    print(f"  • python -m cli.main drift alerts --db-path {db_path}")
    print(f"  • python -m cli.main drift stats --db-path {db_path}")
    print(f"\nDatabase: {db_path}\n")


if __name__ == "__main__":
    demo_drift_cli()
