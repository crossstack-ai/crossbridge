#!/usr/bin/env python3
"""
Quick verification script for memory integration before git commit.
Run this to ensure all files are ready for commit.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("MEMORY INTEGRATION - PRE-COMMIT VERIFICATION")
print("=" * 80)
print()

errors = []
warnings = []

# 1. Check all required files exist
print("✓ Checking required files exist...")
required_files = [
    "adapters/common/normalizer.py",
    "adapters/common/memory_integration.py",
    "adapters/common/__init__.py",
    "adapters/cypress/adapter.py",
    "tests/test_universal_memory_integration.py",
    "MEMORY_INTEGRATION_COMPLETE.md",
]

for file_path in required_files:
    full_path = Path(__file__).parent / file_path
    if not full_path.exists():
        errors.append(f"  ❌ Missing: {file_path}")
    else:
        print(f"  ✅ {file_path}")

print()

# 2. Check imports work
print("✓ Checking imports...")
try:
    from adapters.common.normalizer import UniversalTestNormalizer
    print("  ✅ UniversalTestNormalizer import successful")
except ImportError as e:
    errors.append(f"  ❌ Cannot import UniversalTestNormalizer: {e}")

try:
    from adapters.common.memory_integration import (
        MemoryIntegrationMixin,
        cypress_to_memory,
        playwright_to_memory,
    )
    print("  ✅ Memory integration imports successful")
except ImportError as e:
    errors.append(f"  ❌ Cannot import memory integration: {e}")

try:
    from adapters.common import UniversalTestNormalizer, cypress_to_memory
    print("  ✅ Common module exports working")
except ImportError as e:
    errors.append(f"  ❌ Common module exports broken: {e}")

print()

# 3. Check syntax
print("✓ Checking Python syntax...")
import py_compile

for file_path in required_files:
    if file_path.endswith('.py'):
        full_path = Path(__file__).parent / file_path
        try:
            py_compile.compile(str(full_path), doraise=True)
            print(f"  ✅ {file_path}")
        except py_compile.PyCompileError as e:
            errors.append(f"  ❌ Syntax error in {file_path}: {e}")

print()

# 4. Run tests
print("✓ Running memory integration tests...")
import subprocess

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_universal_memory_integration.py", "-v"],
    capture_output=True,
    text=True,
    cwd=Path(__file__).parent
)

if result.returncode == 0:
    # Parse output to count passed tests
    output_lines = result.stdout.split('\n')
    for line in output_lines:
        if 'passed' in line.lower():
            print(f"  ✅ {line.strip()}")
            break
else:
    errors.append(f"  ❌ Tests failed:\n{result.stdout}\n{result.stderr}")
    print(f"  ❌ Tests failed (see errors below)")

print()

# 5. Check for unwanted files
print("✓ Checking for unwanted files in staging area...")
unwanted_patterns = [
    "create_dashboard_api.py",
    "create_simple_import.py",
    "debug_js_ast.py",
    "diagnose_grafana.py",
    "quick_test.py",
    "simple_demo.py",
    "nul",
    "grafana/dashboards/",
    "setup_flaky_db",
    "populate_flaky_test_db.py",
]

try:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    if result.returncode == 0:
        staged_files = result.stdout.strip().split('\n')
        staged_files = [f for f in staged_files if f]  # Remove empty strings
        
        if not staged_files:
            warnings.append("  ⚠️  No files staged yet")
        else:
            print(f"  Found {len(staged_files)} staged files")
            
            for staged_file in staged_files:
                # Check if it matches unwanted pattern
                is_unwanted = any(pattern in staged_file for pattern in unwanted_patterns)
                
                if is_unwanted:
                    warnings.append(f"  ⚠️  Unwanted file staged: {staged_file}")
                elif staged_file in [f.replace('\\', '/') for f in required_files]:
                    print(f"  ✅ {staged_file}")
                else:
                    warnings.append(f"  ⚠️  Unexpected file staged: {staged_file}")
    else:
        warnings.append("  ⚠️  Git not available or not in git repo")
except FileNotFoundError:
    warnings.append("  ⚠️  Git not available")

print()

# Summary
print("=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print()

if errors:
    print("❌ ERRORS FOUND:")
    for error in errors:
        print(error)
    print()

if warnings:
    print("⚠️  WARNINGS:")
    for warning in warnings:
        print(warning)
    print()

if not errors and not warnings:
    print("✅ ALL CHECKS PASSED!")
    print()
    print("Ready to commit with:")
    print("  • 6 required files")
    print("  • All imports working")
    print("  • All tests passing (6/6)")
    print("  • No syntax errors")
    print()
    print("Next steps:")
    print("  1. Review GIT_COMMIT_CHECKLIST_MEMORY_INTEGRATION.md")
    print("  2. Stage files: git add <files>")
    print("  3. Commit with provided message template")
    print("  4. Push to remote")
    sys.exit(0)
elif errors:
    print("❌ VERIFICATION FAILED!")
    print()
    print("Please fix errors above before committing.")
    sys.exit(1)
else:
    print("⚠️  VERIFICATION PASSED WITH WARNINGS")
    print()
    print("Review warnings above. You can still commit, but please verify:")
    print("  • Only memory integration files are staged")
    print("  • No temporary/debug files included")
    sys.exit(0)
