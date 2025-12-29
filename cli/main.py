"""
CrossBridge AI - Main CLI Entry Point
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Import adapters
from adapters.pytest.adapter import PytestAdapter
from adapters.robot.robot_adapter import RobotAdapter
from adapters.robot.config import RobotConfig
from adapters.common.base import BaseTestAdapter


class AdapterRegistry:
    """Registry for loading framework adapters."""
    
    _adapters = {
        "pytest": PytestAdapter,
        "robot": RobotAdapter,
    }
    
    @classmethod
    def get_adapter(cls, framework: str, project_root: str) -> BaseTestAdapter:
        """
        Get an adapter instance for the specified framework.
        
        Args:
            framework: Framework name (e.g., 'pytest', 'robot').
            project_root: Root directory of the test project.
            
        Returns:
            BaseTestAdapter: Initialized adapter instance.
            
        Raises:
            ValueError: If framework is not supported.
        """
        adapter_class = cls._adapters.get(framework)
        
        if adapter_class is None:
            supported = ', '.join(cls._adapters.keys())
            raise ValueError(f"Unsupported framework: {framework}. Supported frameworks: {supported}")
        
        # Special handling for Robot adapter which needs config
        if framework == "robot":
            return adapter_class(
                RobotConfig(
                    tests_path=project_root,
                    pythonpath="."
                )
            )
        
        return adapter_class(project_root)
    
    @classmethod
    def list_frameworks(cls):
        """Get list of supported frameworks."""
        return list(cls._adapters.keys())


def run_robot_adapter(selected_tests, selected_tags):
    from adapters.robot.robot_adapter import RobotAdapter
    from adapters.robot.config import RobotConfig

    adapter = RobotAdapter(
        RobotConfig(
            tests_path="Test/UDPWebservicesTest",
            pythonpath="src"
        )
    )

    results = adapter.run_tests(
        tests=selected_tests,
        tags=selected_tags
    )

    return results


def cmd_discover(args):
    """Handle the discover command."""
    try:
        # Load adapter
        adapter = AdapterRegistry.get_adapter(args.framework, args.project_root)
        
        print(f"Discovering tests in {args.project_root} using {args.framework}...")
        print()
        
        # Discover tests (returns List[str])
        tests = adapter.discover_tests()
        
        if not tests:
            print("No tests found.")
            return 0
        
        print(f"Found {len(tests)} test(s):\n")
        
        # Print results (test names only)
        for test_name in tests:
            print(f"  - {test_name}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_run(args):
    """Handle the run command."""
    try:
        # Load adapter
        adapter = AdapterRegistry.get_adapter(args.framework, args.project_root)
        
        # Parse test names
        test_names = [tid.strip() for tid in args.tests.split(',')]
        
        print(f"Running {len(test_names)} test(s) using {args.framework}...")
        print()
        
        # Parse tags if provided
        tags = [tag.strip() for tag in args.tags.split(',')] if hasattr(args, 'tags') and args.tags else None
        
        # Run tests (new interface: tests and tags parameters)
        results = adapter.run_tests(tests=test_names, tags=tags)
        
        # Print results
        passed = 0
        failed = 0
        skipped = 0
        
        for result in results:
            status_symbol = "[PASS]" if result.status == "pass" else "[FAIL]"
            print(f"{status_symbol} {result.name} - {result.status.upper()} ({result.duration_ms}ms)")
            
            if result.status == "pass":
                passed += 1
            elif result.status == "fail":
                failed += 1
            else:
                skipped += 1
            
            # Print message if verbose or test failed
            if hasattr(args, 'verbose') and args.verbose or result.status != "pass":
                if result.message:
                    print(f"  Message: {result.message[:200]}")
            print()
        
        # Print summary
        print("-" * 50)
        print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
        print("-" * 50)
        
        return 0 if failed == 0 and errors == 0 else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_extract(args):
    """Handle the extract command (extract test intent)."""
    try:
        # Load adapter
        adapter = AdapterRegistry.get_adapter(args.framework, args.project_root)
        
        print(f"Extracting intent for test: {args.test_id}")
        print()
        
        # Extract intent
        intent = adapter.extract_intent(args.test_id)
        
        # Print intent model
        print(f"Test Name: {intent.test_name}")
        print(f"Intent: {intent.intent}")
        print()
        
        if intent.steps:
            print(f"Steps ({len(intent.steps)}):")
            for i, step in enumerate(intent.steps, 1):
                print(f"  {i}. {step.description}")
                print(f"     Action: {step.action}")
                if step.target:
                    print(f"     Target: {step.target}")
            print()
        
        if intent.assertions:
            print(f"Assertions ({len(intent.assertions)}):")
            for i, assertion in enumerate(intent.assertions, 1):
                print(f"  {i}. Type: {assertion.type.value}")
                print(f"     Expected: {assertion.expected}")
            print()
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point for the CrossBridge AI CLI."""
    parser = argparse.ArgumentParser(
        description="CrossBridge AI - Framework-agnostic test automation platform",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global arguments
    parser.add_argument(
        "--project-root",
        default=".",
        help="Root directory of the test project (default: current directory)"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Discover command
    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover tests in a project"
    )
    discover_parser.add_argument(
        "--framework",
        required=True,
        choices=AdapterRegistry.list_frameworks(),
        help="Test framework to use"
    )
    discover_parser.set_defaults(func=cmd_discover)
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run specified tests"
    )
    run_parser.add_argument(
        "--framework",
        required=True,
        choices=AdapterRegistry.list_frameworks(),
        help="Test framework to use"
    )
    run_parser.add_argument(
        "--tests",
        required=True,
        help="Comma-separated list of test IDs to run"
    )
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    run_parser.set_defaults(func=cmd_run)
    
    # Extract command
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract intent from a test"
    )
    extract_parser.add_argument(
        "--framework",
        required=True,
        choices=AdapterRegistry.list_frameworks(),
        help="Test framework to use"
    )
    extract_parser.add_argument(
        "--test-id",
        required=True,
        help="Test ID to extract intent from"
    )
    extract_parser.set_defaults(func=cmd_extract)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command specified
    if not args.command:
        parser.print_help()
        return 0
    
    # Execute command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
