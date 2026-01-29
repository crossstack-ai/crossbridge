"""
Quick validation test for CrossBridge Hook Auto-Integration

This script tests that the hook integration works correctly.
"""

import sys
import os
from pathlib import Path
import tempfile

# Set environment to disable hooks (avoids DB connection)
os.environ['CROSSBRIDGE_HOOKS_ENABLED'] = 'false'

from core.observability.hook_integrator import HookIntegrator


def test_pytest_hook_integration():
    """Test pytest hook integration."""
    print("\n🧪 Testing pytest hook integration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Integrate hooks
        result = HookIntegrator.integrate_hooks(
            output_dir=output_dir,
            target_framework="pytest",
            enable_hooks=True
        )
        
        # Verify result
        assert result['status'] == 'integrated', f"Expected 'integrated', got {result['status']}"
        assert len(result['files']) > 0, "No files created"
        
        # Check conftest.py exists
        conftest_path = output_dir / "conftest.py"
        assert conftest_path.exists(), "conftest.py not created"
        
        # Check content
        content = conftest_path.read_text()
        assert 'crossbridge.hooks.pytest_hooks' in content, "Hook not registered in conftest.py"
        
        # Check crossbridge.yaml exists
        config_path = output_dir / "crossbridge.yaml"
        assert config_path.exists(), "crossbridge.yaml not created"
        
        # Check README exists
        readme_path = output_dir / "CROSSBRIDGE_INTELLIGENCE.md"
        assert readme_path.exists(), "CROSSBRIDGE_INTELLIGENCE.md not created"
        
        print(f"  ✓ Created {len(result['files'])} files")
        for file_path, purpose in result['files'].items():
            print(f"    • {Path(file_path).name}: {purpose}")
        
        print("  ✓ pytest hook integration PASSED")


def test_robot_hook_integration():
    """Test Robot Framework hook integration."""
    print("\n🧪 Testing Robot Framework hook integration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Integrate hooks
        result = HookIntegrator.integrate_hooks(
            output_dir=output_dir,
            target_framework="robot",
            enable_hooks=True
        )
        
        # Verify result
        assert result['status'] == 'integrated', f"Expected 'integrated', got {result['status']}"
        assert len(result['files']) > 0, "No files created"
        
        # Check setup instructions exist
        setup_path = output_dir / "CROSSBRIDGE_ROBOT_SETUP.md"
        assert setup_path.exists(), "CROSSBRIDGE_ROBOT_SETUP.md not created"
        
        # Check crossbridge.yaml exists
        config_path = output_dir / "crossbridge.yaml"
        assert config_path.exists(), "crossbridge.yaml not created"
        
        print(f"  ✓ Created {len(result['files'])} files")
        for file_path, purpose in result['files'].items():
            print(f"    • {Path(file_path).name}: {purpose}")
        
        print("  ✓ Robot Framework hook integration PASSED")


def test_hook_disabled():
    """Test that hooks are not integrated when disabled."""
    print("\n🧪 Testing hook integration disabled...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Integrate hooks with enable_hooks=False
        result = HookIntegrator.integrate_hooks(
            output_dir=output_dir,
            target_framework="pytest",
            enable_hooks=False
        )
        
        # Verify result
        assert result['status'] == 'skipped', f"Expected 'skipped', got {result['status']}"
        
        # Check no files created
        conftest_path = output_dir / "conftest.py"
        assert not conftest_path.exists(), "conftest.py created when hooks disabled"
        
        print("  ✓ Hook integration correctly skipped when disabled")
        print("  ✓ Disable flag PASSED")


def test_integration_message():
    """Test user-friendly integration message generation."""
    print("\n🧪 Testing integration message generation...")
    
    files_created = {
        '/path/to/conftest.py': 'CrossBridge pytest hooks',
        '/path/to/crossbridge.yaml': 'Configuration file',
        '/path/to/CROSSBRIDGE_INTELLIGENCE.md': 'User documentation'
    }
    
    message = HookIntegrator.get_integration_message(
        target_framework="pytest",
        files_created=files_created
    )
    
    # Verify message content
    assert "CrossBridge Continuous Intelligence Enabled" in message
    assert "conftest.py" in message
    assert "crossbridge.yaml" in message
    assert "CROSSBRIDGE_HOOKS_ENABLED=false" in message
    assert "Automatic coverage tracking" in message
    assert "Flaky test detection" in message
    
    print("  ✓ Message contains all required information")
    print("  ✓ Integration message PASSED")


def test_append_to_existing_conftest():
    """Test that existing conftest.py is preserved and appended to."""
    print("\n🧪 Testing append to existing conftest.py...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Create existing conftest.py
        conftest_path = output_dir / "conftest.py"
        existing_content = """
import pytest

@pytest.fixture
def my_fixture():
    return "test"
"""
        conftest_path.write_text(existing_content)
        
        # Integrate hooks
        result = HookIntegrator.integrate_pytest_hooks(output_dir)
        
        # Verify content
        content = conftest_path.read_text()
        assert "my_fixture" in content, "Existing content lost"
        assert "crossbridge.hooks.pytest_hooks" in content, "Hook not added"
        
        print("  ✓ Existing conftest.py preserved")
        print("  ✓ Hook appended successfully")
        print("  ✓ Append to existing conftest PASSED")


if __name__ == "__main__":
    print("=" * 70)
    print("CrossBridge Hook Auto-Integration - Validation Tests")
    print("=" * 70)
    
    try:
        test_pytest_hook_integration()
        test_robot_hook_integration()
        test_hook_disabled()
        test_integration_message()
        test_append_to_existing_conftest()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Hook integration is working correctly!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
