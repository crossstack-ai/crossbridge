# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
CrossBridge - Main CLI Entry Point
"""

import argparse
import sys
from pathlib import Path
from typing import Optional
import logging

# Import adapters
from adapters.pytest.adapter import PytestAdapter
from adapters.robot.robot_adapter import RobotAdapter
from adapters.robot.config import RobotConfig
from adapters.selenium_java.extractor import SeleniumJavaExtractor
from adapters.selenium_java.config import SeleniumJavaConfig
from adapters.selenium_bdd_java.extractor import SeleniumBDDJavaExtractor
from adapters.selenium_bdd_java.config import SeleniumBDDJavaConfig
from adapters.common.base import BaseTestAdapter

# Import impact mappers
from adapters.pytest.impact_mapper import create_pytest_impact_map
from adapters.java.impact_mapper import create_impact_map as create_java_impact_map

# Import Selenium-Java runner
from adapters.java.selenium import run_selenium_java_tests

# Import persistence
from persistence import DatabaseConfig
from persistence.orchestrator import persist_discovery

# Import CLI commands
from cli.commands.coverage import add_coverage_commands, execute_coverage_command
from cli.commands.api_diff import register_commands as register_api_diff_commands
from cli.commands.ai_transform import ai_transform

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for loading framework adapters."""
    
    _adapters = {
        "pytest": PytestAdapter,
        "robot": RobotAdapter,
    }
    
    _extractors = {
        "selenium-java": SeleniumJavaExtractor,
        "selenium-bdd-java": SeleniumBDDJavaExtractor,
    }
    
    @classmethod
    def auto_detect_frameworks(cls, project_root: str = ".") -> list:
        """
        Auto-detect all test frameworks in the project.
        
        Returns:
            List of detected framework names.
        """
        detected = []
        root_path = Path(project_root)
        
        # Check for pytest (look for conftest.py, pytest.ini, or test_*.py files)
        if (root_path / "pytest.ini").exists() or \
           (root_path / "conftest.py").exists() or \
           list(root_path.rglob("test_*.py")) or \
           list(root_path.rglob("*_test.py")):
            detected.append("pytest")
        
        # Check for Robot Framework (.robot files)
        if list(root_path.rglob("*.robot")):
            detected.append("robot")
        
        # Check for Java test frameworks
        java_frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=project_root,
            source_root=str(root_path / "src" / "test" / "java")
        )
        if java_frameworks:
            detected.append("selenium-java")
        
        # Check for Cucumber/BDD feature files
        if list(root_path.rglob("*.feature")):
            detected.append("selenium-bdd-java")
        
        return detected
    
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
        all_frameworks = list(cls._adapters.keys()) + list(cls._extractors.keys())
        return all_frameworks
    
    @classmethod
    def is_extractor(cls, framework: str) -> bool:
        """Check if framework is an extractor (not a runner)."""
        return framework in cls._extractors
    
    @classmethod
    def get_extractor(cls, framework: str, project_root: str):
        """Get an extractor instance for the specified framework."""
        extractor_class = cls._extractors.get(framework)
        
        if extractor_class is None:
            raise ValueError(f"No extractor found for framework: {framework}")
        
        # Create config based on framework
        if framework == "selenium-java":
            config = SeleniumJavaConfig(root_dir=project_root)
            return extractor_class(config)
        elif framework == "selenium-bdd-java":
            config = SeleniumBDDJavaConfig(
                features_dir=str(Path(project_root) / "src" / "test" / "resources" / "features")
            )
            return extractor_class(config)
        
        return extractor_class(project_root)


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
        # Check persistence configuration
        persist_enabled = args.persist
        if persist_enabled and not DatabaseConfig.is_configured():
            print("⚠️  --persist flag specified but database not configured.")
            print("   Set CROSSBRIDGE_DB_URL environment variable to enable persistence.")
            print("   Example: export CROSSBRIDGE_DB_URL=postgresql://user:pass@localhost:5432/crossbridge")
            print()
            persist_enabled = False
        
        # Store all discovered tests for persistence
        all_discovered_tests = []
        project_name = Path(args.project_root).resolve().name
        
        # Auto-detect framework if not specified
        if not args.framework:
            detected_frameworks = AdapterRegistry.auto_detect_frameworks(args.project_root)
            
            if not detected_frameworks:
                print("No test frameworks detected in project.")
                print("Tip: Use --framework to explicitly specify a framework.")
                print(f"Supported frameworks: {', '.join(AdapterRegistry.list_frameworks())}")
                return 1
            
            print(f"Detected frameworks: {', '.join(detected_frameworks)}")
            print("Discovering tests...")
            print()
            
            # Discover tests for each detected framework
            total_tests = 0
            for framework in detected_frameworks:
                print(f"[{framework}]")
                
                if framework == "selenium-java":
                    # Special handling for Java: show sub-frameworks
                    test_source_dir = str(Path(args.project_root) / "src" / "test" / "java")
                    
                    java_frameworks = SeleniumJavaConfig.detect_all_frameworks(
                        project_root=args.project_root,
                        source_root=test_source_dir
                    )
                    print(f"  Java test frameworks: {', '.join(sorted(java_frameworks))}")
                    
                    # Extract tests for each Java framework
                    for java_fw in sorted(java_frameworks):
                        config = SeleniumJavaConfig(
                            root_dir=test_source_dir,
                            test_framework=java_fw,
                            project_root=args.project_root
                        )
                        extractor = SeleniumJavaExtractor(config)
                        tests = extractor.extract_tests()
                        
                        if tests:
                            print(f"  [{java_fw}] {len(tests)} test(s)")
                            total_tests += len(tests)
                            all_discovered_tests.extend(tests)  # Collect for persistence
                
                elif AdapterRegistry.is_extractor(framework):
                    extractor = AdapterRegistry.get_extractor(framework, args.project_root)
                    tests = extractor.extract_tests()
                    if tests:
                        print(f"  {len(tests)} test(s)")
                        total_tests += len(tests)
                        all_discovered_tests.extend(tests)  # Collect for persistence
                
                else:
                    adapter = AdapterRegistry.get_adapter(framework, args.project_root)
                    tests = adapter.discover_tests()
                    if tests:
                        print(f"  {len(tests)} test(s)")
                        total_tests += len(tests)
                
                print()
            
            print(f"Total: {total_tests} test(s) across {len(detected_frameworks)} framework(s)")
            
            # Persist if requested
            if persist_enabled and all_discovered_tests:
                print()
                print("💾 Persisting discovery metadata...")
                run_id = persist_discovery(
                    discovered_tests=all_discovered_tests,
                    project_name=project_name,
                    triggered_by="cli"
                )
                if run_id:
                    print(f"✅ Persisted to database. Discovery run ID: {run_id}")
                else:
                    print("⚠️  Failed to persist discovery metadata.")
            
            return 0
        
        else:
            print(f"Discovering tests in {args.project_root} using {args.framework}...")
            print()
        
        # Special handling for selenium-java: detect mixed frameworks
        if args.framework == "selenium-java":
            test_source_dir = str(Path(args.project_root) / "src" / "test" / "java")
            
            detected_frameworks = SeleniumJavaConfig.detect_all_frameworks(
                project_root=args.project_root,
                source_root=test_source_dir
            )
            
            if detected_frameworks:
                print("Detected Java test frameworks:")
                for fw in sorted(detected_frameworks):
                    print(f"  - {fw}")
                print()
            
            # Extract tests for each detected framework separately
            all_tests = []
            for framework in sorted(detected_frameworks) if detected_frameworks else ["junit"]:
                config = SeleniumJavaConfig(
                    root_dir=test_source_dir,
                    test_framework=framework,
                    project_root=args.project_root
                )
                extractor = SeleniumJavaExtractor(config)
                tests = extractor.extract_tests()
                all_tests.extend(tests)
            
            all_discovered_tests = all_tests  # Collect for persistence
            
            if not all_tests:
                print("No tests found.")
                return 0
            
            print(f"Found {len(all_tests)} test(s) total:\n")
            
            # Group by framework
            by_framework = {}
            for test in all_tests:
                fw = test.framework
                if fw not in by_framework:
                    by_framework[fw] = []
                by_framework[fw].append(test)
            
            for fw, tests in sorted(by_framework.items()):
                print(f"[{fw}] {len(tests)} test(s):")
                for test in tests:
                    print(f"  Test: {test.test_name}")
                    print(f"  File: {test.file_path}")
                    if test.tags:
                        print(f"  Tags: {', '.join(test.tags)}")
                    print()
            
            # Persist if requested
            if persist_enabled and all_discovered_tests:
                print()
                print("💾 Persisting discovery metadata...")
                run_id = persist_discovery(
                    discovered_tests=all_discovered_tests,
                    project_name=project_name,
                    triggered_by="cli",
                    framework_hint="selenium-java"
                )
                if run_id:
                    print(f"✅ Persisted to database. Discovery run ID: {run_id}")
                else:
                    print("⚠️  Failed to persist discovery metadata.")
            
            return 0
        
        # Check if this is an extractor or adapter
        elif AdapterRegistry.is_extractor(args.framework):
            # Use extractor
            extractor = AdapterRegistry.get_extractor(args.framework, args.project_root)
            test_metadata = extractor.extract_tests()
            
            all_discovered_tests = test_metadata  # Collect for persistence
            
            if not test_metadata:
                print("No tests found.")
                return 0
            
            print(f"Found {len(test_metadata)} test(s):\n")
            
            # Print metadata (more detailed for extractors)
            for test in test_metadata:
                print(f"  Test: {test.test_name}")
                print(f"  File: {test.file_path}")
                if test.tags:
                    print(f"  Tags: {', '.join(test.tags)}")
                print()
            
            # Persist if requested
            if persist_enabled and all_discovered_tests:
                print()
                print("💾 Persisting discovery metadata...")
                run_id = persist_discovery(
                    discovered_tests=all_discovered_tests,
                    project_name=project_name,
                    triggered_by="cli",
                    framework_hint=args.framework
                )
                if run_id:
                    print(f"✅ Persisted to database. Discovery run ID: {run_id}")
                else:
                    print("⚠️  Failed to persist discovery metadata.")
            
            return 0
        else:
            # Use adapter
            adapter = AdapterRegistry.get_adapter(args.framework, args.project_root)
            tests = adapter.discover_tests()
            
            if not tests:
                print("No tests found.")
                return 0
            
            print(f"Found {len(tests)} test(s):\n")
            
            # Print test names
            for test_name in tests:
                print(f"  - {test_name}")
            
            # Show Page Object mappings if requested
            if args.include_page_mapping and args.framework == "pytest":
                print("\n" + "="*60)
                print("PAGE OBJECT MAPPINGS")
                print("="*60 + "\n")
                _show_pytest_page_mappings(args.project_root, tests)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _run_selenium_java(args):
    """
    Run Selenium-Java tests using the new runner adapter.
    
    Supports selective execution by:
    - Test class names
    - Test methods
    - JUnit 5 tags
    - TestNG groups
    - JUnit 4 categories
    """
    try:
        from adapters.java.selenium import SeleniumJavaAdapter
        
        # Create adapter to get project info
        adapter = SeleniumJavaAdapter(args.project_root)
        info = adapter.get_info()
        
        # Parse test names
        tests = None
        test_methods = None
        if hasattr(args, 'tests') and args.tests:
            test_list = [t.strip() for t in args.tests.split(',')]
            # Separate test classes from test methods
            tests = [t for t in test_list if '#' not in t and '.' not in t.split('/')[-1]]
            test_methods = [t for t in test_list if '#' in t or '.' in t.split('/')[-1]]
        
        # Parse tags/groups/categories
        tags = [t.strip() for t in args.tags.split(',')] if hasattr(args, 'tags') and args.tags else None
        groups = [g.strip() for g in args.groups.split(',')] if hasattr(args, 'groups') and args.groups else None
        categories = [c.strip() for c in args.categories.split(',')] if hasattr(args, 'categories') and args.categories else None
        
        # Parallel execution
        parallel = getattr(args, 'parallel', False)
        thread_count = getattr(args, 'threads', None)
        
        # Additional properties
        properties = {}
        if hasattr(args, 'properties') and args.properties:
            for prop in args.properties.split(','):
                if '=' in prop:
                    key, value = prop.split('=', 1)
                    properties[key.strip()] = value.strip()
        
        # Display configuration
        print("=" * 60)
        print("Selenium-Java Test Execution")
        print("=" * 60)
        print(f"Project: {args.project_root}")
        print(f"Build Tool: {info['build_tool']}")
        print(f"Test Framework: {info['test_framework']}")
        print(f"Report Location: {info['test_output_dir']}")
        if tests:
            print(f"Test Classes: {', '.join(tests)}")
        elif not any([tags, groups, categories]):
            print(f"Test Classes: ALL")
        if test_methods:
            print(f"Test Methods: {', '.join(test_methods)}")
        if tags:
            print(f"Tags: {', '.join(tags)}")
        if groups:
            print(f"Groups: {', '.join(groups)}")
        if categories:
            print(f"Categories: {', '.join(categories)}")
        if parallel:
            print(f"Parallel: Yes ({thread_count} threads)" if thread_count else "Parallel: Yes")
        print("=" * 60)
        print()
        
        # Dry run mode - show command without executing
        if hasattr(args, 'dry_run') and args.dry_run:
            from adapters.java.selenium.maven_runner import MavenRunner
            from adapters.java.selenium.gradle_runner import GradleRunner
            from adapters.java.selenium.models import TestExecutionRequest
            
            request = TestExecutionRequest(
                working_dir=args.project_root,
                tests=tests,
                test_methods=test_methods,
                tags=tags,
                groups=groups,
                categories=categories,
                parallel=parallel,
                thread_count=thread_count,
                properties=properties
            )
            
            if info['build_tool'] == 'maven':
                runner = MavenRunner(args.project_root)
                cmd = runner._build_command(request)
            else:
                runner = GradleRunner(args.project_root)
                cmd = runner._build_command(request)
            
            print("[DRY RUN] Would execute:")
            print(f"  {' '.join(cmd)}")
            print()
            print("Run without --dry-run to execute.")
            return 0
        
        # Execute tests
        print("Executing tests...")
        print()
        result = run_selenium_java_tests(
            project_root=args.project_root,
            tests=tests,
            test_methods=test_methods,
            tags=tags,
            groups=groups,
            categories=categories,
            parallel=parallel,
            thread_count=thread_count,
            properties=properties
        )
        
        # Display results
        print()
        print("=" * 60)
        print(f"Test Execution Result: {result.status.upper()}")
        print("=" * 60)
        print(f"Tests Run:    {result.tests_run}")
        print(f"Tests Passed: {result.tests_passed}")
        print(f"Tests Failed: {result.tests_failed}")
        print(f"Tests Skipped: {result.tests_skipped}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print("=" * 60)
        if result.report_path:
            print()
            print("Test Reports:")
            print(f"  Location: {result.report_path}")
            if info['build_tool'] == 'maven':
                print(f"  JUnit XML: {result.report_path}/TEST-*.xml")
                print(f"  Text Reports: {result.report_path}/*.txt")
            else:
                print(f"  JUnit XML: {result.report_path}/TEST-*.xml")
                print(f"  HTML Report: {args.project_root}/build/reports/tests/test/index.html")
            print()
            print("💡 CI Integration: Use these report paths in your CI/CD pipeline")
        print("=" * 60)
        
        # Show error message if present
        if result.error_message:
            print()
            print("Error Details:")
            print(result.error_message)
        
        # Show raw output if verbose
        if hasattr(args, 'verbose') and args.verbose:
            print()
            print("Raw Output:")
            print("-" * 60)
            print(result.raw_output)
            print("-" * 60)
        
        return result.exit_code
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        if hasattr(args, 'verbose') and args.verbose:
            traceback.print_exc()
        return 1


def cmd_run(args):
    """Handle the run command."""
    try:
        # Special handling for selenium-java (uses new runner adapter)
        if args.framework == "selenium-java":
            return _run_selenium_java(args)
        
        # Check if this is an extractor (extractors don't support run)
        if AdapterRegistry.is_extractor(args.framework):
            print(f"Error: {args.framework} is an extractor and does not support test execution.", file=sys.stderr)
            print(f"Extractors only support the 'discover' command.", file=sys.stderr)
            print(f"To run {args.framework} tests, use Maven/Gradle directly.", file=sys.stderr)
            return 1
        
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


def _show_pytest_page_mappings(project_root: str, tests: list):
    """Show Page Object mappings for pytest tests."""
    try:
        impact_map = create_pytest_impact_map(project_root)
        
        if not impact_map.mappings:
            print("  No Page Object mappings found.")
            return
        
        # Group tests by their test IDs
        test_ids = {test if isinstance(test, str) else test.test_name for test in tests}
        
        for mapping in impact_map.mappings:
            # Check if this test is in our discovered tests
            if mapping.test_id in test_ids or any(tid in mapping.test_id for tid in test_ids):
                print(f"{mapping.test_id}")
                for po in sorted(mapping.page_objects):
                    print(f"  -> {po}")
                print()
    
    except Exception as e:
        print(f"  Warning: Could not generate Page Object mappings: {e}")


def _show_java_page_mappings(project_root: str, tests: list):
    """Show Page Object mappings for Java tests."""
    try:
        impact_map = create_java_impact_map(project_root)
        
        if not impact_map.mappings:
            print("  No Page Object mappings found.")
            return
        
        # Extract test names
        test_names = {test.test_name for test in tests}
        
        for mapping in impact_map.mappings:
            # Check if this test is in our discovered tests
            if mapping.test_id in test_names or any(name in mapping.test_id for name in test_names):
                print(f"{mapping.test_id}")
                for po in sorted(mapping.page_objects):
                    print(f"  -> {po}")
                print()
    
    except Exception as e:
        print(f"  Warning: Could not generate Page Object mappings: {e}")


def cmd_impact(args):
    """Handle the impact analysis command."""
    try:
        # Auto-detect framework if not specified
        if not args.framework:
            detected = AdapterRegistry.auto_detect_frameworks(args.project_root)
            if not detected:
                print("No test frameworks detected.", file=sys.stderr)
                return 1
            args.framework = detected[0]  # Use first detected
            print(f"Detected framework: {args.framework}\n")
        
        print(f"Analyzing impact of changes to: {args.page_object}")
        print(f"Minimum confidence: {args.min_confidence}")
        print()
        
        # Generate impact map based on framework
        if args.framework == "pytest":
            impact_map = create_pytest_impact_map(args.project_root)
        elif args.framework == "selenium-java":
            impact_map = create_java_impact_map(args.project_root)
        else:
            print(f"Impact analysis not yet supported for {args.framework}", file=sys.stderr)
            return 1
        
        # Get impacted tests
        impacted_tests = impact_map.get_impacted_tests(args.page_object)
        
        if not impacted_tests:
            print(f"No tests found using {args.page_object}")
            return 0
        
        # Filter by confidence if needed
        filtered_tests = []
        for test_id in impacted_tests:
            # Find the mapping
            for mapping in impact_map.mappings:
                if mapping.test_id == test_id and mapping.confidence >= args.min_confidence:
                    if args.page_object in mapping.page_objects:
                        filtered_tests.append((test_id, mapping.confidence))
                        break
        
        if not filtered_tests:
            print(f"No tests found with confidence >= {args.min_confidence}")
            return 0
        
        # Print results
        print(f"Impacted tests ({len(filtered_tests)}):")
        print()
        
        # Sort by confidence (descending)
        for test_id, confidence in sorted(filtered_tests, key=lambda x: x[1], reverse=True):
            print(f"  • {test_id}")
            print(f"    Confidence: {confidence:.2f}")
        
        print()
        print(f"Total: {len(filtered_tests)} test(s) may be affected by changes to {args.page_object}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cmd_show_mappings(args):
    """Show step-to-code-path mappings."""
    from adapters.common.mapping.persistence import MappingPersistence
    import json
    
    persistence = MappingPersistence()
    
    try:
        if args.test_id and args.run_id:
            # Show single mapping
            mapping = persistence.load_mapping(args.test_id, args.run_id)
            if not mapping:
                print(f"❌ No mapping found for test_id={args.test_id}, run_id={args.run_id}")
                return 1
            
            if args.format == "json":
                print(json.dumps(mapping.to_dict(), indent=2))
            else:
                print(f"\n📍 Mapping for: {mapping.step}")
                print(f"   Page Objects: {', '.join(mapping.page_objects) or 'none'}")
                print(f"   Methods: {', '.join(mapping.methods) or 'none'}")
                print(f"   Code Paths:")
                for cp in mapping.code_paths:
                    print(f"     • {cp}")
        
        elif args.run_id:
            # Show all mappings for run
            mappings = persistence.load_mappings_for_run(args.run_id)
            if not mappings:
                print(f"❌ No mappings found for run_id={args.run_id}")
                return 1
            
            if args.format == "json":
                output = {tid: m.to_dict() for tid, m in mappings.items()}
                print(json.dumps(output, indent=2))
            elif args.format == "summary":
                print(f"\n📊 Mapping Summary for Run: {args.run_id}")
                print(f"   Total Tests: {len(mappings)}")
                total_paths = sum(len(m.code_paths) for m in mappings.values())
                print(f"   Total Code Paths: {total_paths}")
                mapped = len([m for m in mappings.values() if m.code_paths])
                print(f"   Tests with Mappings: {mapped}/{len(mappings)} ({mapped/len(mappings)*100:.1f}%)")
            else:  # table
                print(f"\n📋 Mappings for Run: {args.run_id}\n")
                for test_id, mapping in sorted(mappings.items()):
                    status = "✅" if mapping.code_paths else "⚠️ "
                    print(f"{status} {test_id}")
                    print(f"   Step: {mapping.step}")
                    if mapping.code_paths:
                        print(f"   Paths: {', '.join(mapping.code_paths)}")
                    print()
        
        else:
            print("❌ Please specify either --test-id with --run-id, or just --run-id")
            return 1
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_analyze_impact(args):
    """Analyze impact of code changes using step-to-code mappings."""
    from adapters.common.mapping.persistence import MappingPersistence
    import json
    
    persistence = MappingPersistence()
    
    try:
        changed_paths = [cp.strip() for cp in args.changed.split(',')]
        
        print(f"\n🔍 Analyzing impact of changes:")
        for cp in changed_paths:
            print(f"   • {cp}")
        print()
        
        # Find affected tests for each changed path
        all_affected = {}
        for code_path in changed_paths:
            affected = persistence.find_tests_by_code_path(code_path, args.run_id)
            for test_id in affected:
                if test_id not in all_affected:
                    all_affected[test_id] = []
                all_affected[test_id].append(code_path)
        
        if not all_affected:
            print("✅ No tests affected by these changes")
            return 0
        
        if args.format == "json":
            print(json.dumps(all_affected, indent=2))
        elif args.format == "detailed":
            print(f"⚠️  {len(all_affected)} test(s) affected:\n")
            for test_id, paths in sorted(all_affected.items()):
                print(f"📌 {test_id}")
                for path in paths:
                    print(f"   └─ {path}")
                print()
        else:  # list
            print(f"⚠️  {len(all_affected)} test(s) affected:\n")
            for test_id in sorted(all_affected.keys()):
                print(f"  • {test_id}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_validate_coverage(args):
    """Validate step-to-code mapping coverage."""
    from adapters.common.mapping.persistence import MappingPersistence
    import json
    
    persistence = MappingPersistence()
    
    try:
        report = persistence.get_coverage_report(args.run_id)
        
        if args.format == "json":
            print(json.dumps(report, indent=2))
        elif args.format == "detailed":
            print(f"\n📊 Coverage Report for Run: {report['run_id']}\n")
            print(f"Total Tests: {report['total_tests']}")
            print(f"Code Paths Covered: {report['code_paths_covered']}")
            print(f"Page Objects Used: {report['page_objects_used']}")
            print(f"Methods Used: {report['methods_used']}")
            print(f"Coverage: {report['coverage_percentage']:.1f}%\n")
            
            if args.show_unmapped and report['steps_without_mapping']:
                print(f"⚠️  Steps Without Mappings ({len(report['steps_without_mapping'])}):\n")
                for step in report['steps_without_mapping']:
                    print(f"  • {step}")
        else:  # summary
            print(f"\n📊 Coverage Summary")
            print(f"   Run ID: {report['run_id']}")
            print(f"   Tests: {report['total_tests']}")
            print(f"   Coverage: {report['coverage_percentage']:.1f}%")
            print(f"   Code Paths: {report['code_paths_covered']}")
            
            if report['steps_without_mapping']:
                print(f"   ⚠️  {len(report['steps_without_mapping'])} steps unmapped")
                if args.show_unmapped:
                    print()
                    for step in report['steps_without_mapping']:
                        print(f"      • {step}")
        
        print()
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point for the CrossBridge CLI."""
    parser = argparse.ArgumentParser(
        description="CrossBridge - Framework-agnostic test automation platform",
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
        required=False,
        choices=AdapterRegistry.list_frameworks(),
        help="Test framework to use (optional, auto-detects if not specified)"
    )
    discover_parser.add_argument(
        "--include-page-mapping",
        action="store_true",
        help="Include Page Object mappings for each test"
    )
    discover_parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist discovery metadata to PostgreSQL (requires CROSSBRIDGE_DB_URL)"
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
        required=False,
        help="Comma-separated list of test IDs to run (e.g., com.example.LoginTest,com.example.OrderTest#testCheckout). If not specified, runs all tests."
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running tests"
    )
    run_parser.add_argument(
        "--tags",
        help="Comma-separated list of JUnit 5 tags to run (e.g., smoke,integration)"
    )
    run_parser.add_argument(
        "--groups",
        help="Comma-separated list of TestNG groups to run (e.g., smoke,regression)"
    )
    run_parser.add_argument(
        "--categories",
        help="Comma-separated list of JUnit 4 categories to run"
    )
    run_parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel test execution (Java only)"
    )
    run_parser.add_argument(
        "--threads",
        type=int,
        help="Number of parallel threads (Java only)"
    )
    run_parser.add_argument(
        "--properties",
        help="Additional system properties as key=value,key2=value2 (Java only)"
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
    
    # Impact command
    impact_parser = subparsers.add_parser(
        "impact",
        help="Analyze impact of Page Object changes"
    )
    impact_parser.add_argument(
        "--framework",
        required=False,
        choices=AdapterRegistry.list_frameworks(),
        help="Test framework (auto-detects if not specified)"
    )
    impact_parser.add_argument(
        "--page-object",
        required=True,
        help="Page Object class name that changed"
    )
    impact_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum confidence threshold (default: 0.5)"
    )
    impact_parser.set_defaults(func=cmd_impact)
    
    # Show mappings command
    mappings_parser = subparsers.add_parser(
        "show-mappings",
        help="Show step-to-code-path mappings"
    )
    mappings_parser.add_argument(
        "--run-id",
        help="Test run ID to show mappings for"
    )
    mappings_parser.add_argument(
        "--test-id",
        help="Show mappings for specific test ID"
    )
    mappings_parser.add_argument(
        "--pattern",
        help="Filter mappings by step pattern"
    )
    mappings_parser.add_argument(
        "--format",
        choices=["table", "json", "summary"],
        default="table",
        help="Output format (default: table)"
    )
    mappings_parser.set_defaults(func=cmd_show_mappings)
    
    # Analyze impact command (enhanced with mapping support)
    analyze_impact_parser = subparsers.add_parser(
        "analyze-impact",
        help="Find tests affected by code changes using step-to-code mappings"
    )
    analyze_impact_parser.add_argument(
        "--changed",
        required=True,
        help="Comma-separated list of changed code paths (e.g., pages/login.py::LoginPage.login)"
    )
    analyze_impact_parser.add_argument(
        "--run-id",
        help="Test run ID to analyze (if not specified, uses latest)"
    )
    analyze_impact_parser.add_argument(
        "--format",
        choices=["list", "detailed", "json"],
        default="list",
        help="Output format (default: list)"
    )
    analyze_impact_parser.set_defaults(func=cmd_analyze_impact)
    
    # Validate coverage command
    coverage_parser = subparsers.add_parser(
        "validate-coverage",
        help="Check step-to-code mapping coverage"
    )
    coverage_parser.add_argument(
        "--run-id",
        required=True,
        help="Test run ID to validate"
    )
    coverage_parser.add_argument(
        "--show-unmapped",
        action="store_true",
        help="Show steps without code path mappings"
    )
    coverage_parser.add_argument(
        "--format",
        choices=["summary", "detailed", "json"],
        default="summary",
        help="Output format (default: summary)"
    )
    coverage_parser.set_defaults(func=cmd_validate_coverage)
    
    # Add coverage mapping commands
    add_coverage_commands(subparsers)
    
    # Add AI transformation commands
    subparsers.add_parser('ai-transform', add_help=False, parents=[ai_transform])
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command specified
    if not args.command:
        parser.print_help()
        return 0
    
    # Execute coverage commands if specified
    if args.command == 'coverage':
        return execute_coverage_command(args)
    
    # Execute command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
