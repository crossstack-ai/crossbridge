#!/usr/bin/env python
"""
Validation script for Memory & Embeddings System implementation.

This script verifies that all components are properly installed and configured.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_modules():
    """Check that all required modules can be imported."""
    print("=" * 60)
    print("Checking Module Imports...")
    print("=" * 60)

    modules_to_check = [
        ("core.memory.models", "MemoryRecord, MemoryType, SearchResult"),
        ("core.memory.embedding_provider", "EmbeddingProvider, create_embedding_provider"),
        ("core.memory.vector_store", "VectorStore, create_vector_store"),
        ("core.memory.ingestion", "MemoryIngestionPipeline"),
        ("core.memory.search", "SemanticSearchEngine"),
    ]

    all_passed = True

    for module_name, items in modules_to_check:
        try:
            exec(f"from {module_name} import {items}")
            print(f"✅ {module_name}")
        except Exception as e:
            print(f"❌ {module_name}: {e}")
            all_passed = False

    return all_passed


def check_cli_registration():
    """Check that CLI commands are registered."""
    print("\n" + "=" * 60)
    print("Checking CLI Registration...")
    print("=" * 60)

    try:
        from cli.app import app
        from cli.commands.memory import memory_app, search_app

        # Check if commands are registered
        registered_commands = [cmd.name for cmd in app.registered_commands]
        
        if "memory" in registered_commands:
            print("✅ memory command registered")
        else:
            print("⚠️  memory command not found in registered commands")

        if "search" in registered_commands:
            print("✅ search command registered")
        else:
            print("⚠️  search command not found in registered commands")

        return True
    except Exception as e:
        print(f"❌ CLI registration check failed: {e}")
        return False


def check_configuration():
    """Check that configuration file has memory settings."""
    print("\n" + "=" * 60)
    print("Checking Configuration...")
    print("=" * 60)

    try:
        import yaml
        from pathlib import Path

        config_path = Path("crossbridge.yml")
        if not config_path.exists():
            print("⚠️  crossbridge.yml not found")
            return False

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Handle both flat and nested structure
        if "crossbridge" in config:
            config = config["crossbridge"]

        if "memory" in config:
            memory_config = config["memory"]
            print("✅ memory section found in config")

            if "embedding_provider" in memory_config:
                print(f"  ✅ embedding_provider: {memory_config['embedding_provider'].get('type', 'not set')}")
            else:
                print("  ⚠️  embedding_provider not configured")

            if "vector_store" in memory_config:
                print(f"  ✅ vector_store: {memory_config['vector_store'].get('type', 'not set')}")
            else:
                print("  ⚠️  vector_store not configured")

            return True
        else:
            print("⚠️  memory section not found in config")
            return False

    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        return False


def check_documentation():
    """Check that documentation files exist."""
    print("\n" + "=" * 60)
    print("Checking Documentation...")
    print("=" * 60)

    docs_to_check = [
        "docs/MEMORY_EMBEDDINGS_SYSTEM.md",
        "docs/MEMORY_QUICK_START.md",
        "scripts/setup_memory_db.py",
    ]

    all_exist = True
    for doc in docs_to_check:
        path = Path(doc)
        if path.exists():
            print(f"✅ {doc}")
        else:
            print(f"❌ {doc} not found")
            all_exist = False

    return all_exist


def run_quick_test():
    """Run a quick functional test."""
    print("\n" + "=" * 60)
    print("Running Quick Functional Test...")
    print("=" * 60)

    try:
        from core.memory.models import MemoryRecord, MemoryType

        # Create a test record
        record = MemoryRecord(
            id="test_validation",
            type=MemoryType.TEST,
            text="Validation test record",
            metadata={"framework": "pytest"},
        )

        assert record.id == "test_validation"
        assert record.type == MemoryType.TEST
        print("✅ MemoryRecord creation works")

        # Test text construction
        from core.memory.models import convert_test_to_text

        test_data = {
            "name": "test_example",
            "framework": "pytest",
            "steps": ["step1", "step2"],
        }

        text = convert_test_to_text(test_data)
        assert "test_example" in text
        assert "pytest" in text
        print("✅ Text construction works")

        return True

    except Exception as e:
        print(f"❌ Functional test failed: {e}")
        return False


def main():
    """Run all validation checks."""
    print("\n" + "🔍" * 30)
    print(" " * 10 + "Memory & Embeddings System Validation")
    print("🔍" * 30 + "\n")

    results = []

    results.append(("Module Imports", check_modules()))
    results.append(("CLI Registration", check_cli_registration()))
    results.append(("Configuration", check_configuration()))
    results.append(("Documentation", check_documentation()))
    results.append(("Functional Test", run_quick_test()))

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{check_name:.<40} {status}")

    print("=" * 60)
    print(f"Total: {passed}/{total} checks passed")
    print("=" * 60)

    if passed == total:
        print("\n✅ All validation checks passed!")
        print("\nNext steps:")
        print("  1. Set up PostgreSQL with pgvector extension")
        print("  2. Run: python scripts/setup_memory_db.py")
        print("  3. Configure embedding provider in crossbridge.yml")
        print("  4. Try: crossbridge memory stats")
        print("  5. Read docs/MEMORY_QUICK_START.md for full setup")
        return 0
    else:
        print("\n⚠️  Some validation checks failed.")
        print("Please review the output above and fix any issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
