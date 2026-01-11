"""
Coverage CLI Commands.

Commands for collecting and querying test coverage mappings.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Set

from core.coverage import CoverageMappingEngine


def add_coverage_commands(subparsers):
    """Add coverage commands to CLI."""
    
    # Main coverage command group
    coverage_parser = subparsers.add_parser(
        'coverage',
        help='Test coverage mapping commands'
    )
    
    coverage_subparsers = coverage_parser.add_subparsers(dest='coverage_command')
    
    # collect-isolated command
    collect_isolated_parser = coverage_subparsers.add_parser(
        'collect-isolated',
        help='Collect coverage for a single test (isolated execution)'
    )
    collect_isolated_parser.add_argument(
        '--test-id',
        required=True,
        help='Test identifier'
    )
    collect_isolated_parser.add_argument(
        '--test-command',
        required=True,
        help='Command to run test (e.g., "mvn test -Dtest=LoginTest#testSuccessfulLogin")'
    )
    collect_isolated_parser.add_argument(
        '--working-dir',
        default='.',
        help='Working directory (default: current directory)'
    )
    collect_isolated_parser.add_argument(
        '--framework',
        default='junit',
        help='Test framework (default: junit)'
    )
    collect_isolated_parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Execution timeout in seconds (default: 300)'
    )
    collect_isolated_parser.add_argument(
        '--db',
        default='crossbridge.db',
        help='Database path (default: crossbridge.db)'
    )
    
    # collect-batch command
    collect_batch_parser = coverage_subparsers.add_parser(
        'collect-batch',
        help='Collect coverage for multiple tests (batch execution)'
    )
    collect_batch_parser.add_argument(
        '--test-command',
        required=True,
        help='Command to run all tests (e.g., "mvn test")'
    )
    collect_batch_parser.add_argument(
        '--working-dir',
        default='.',
        help='Working directory'
    )
    collect_batch_parser.add_argument(
        '--framework',
        default='junit',
        help='Test framework'
    )
    collect_batch_parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help='Execution timeout in seconds (default: 600)'
    )
    collect_batch_parser.add_argument(
        '--db',
        default='crossbridge.db',
        help='Database path'
    )
    collect_batch_parser.add_argument(
        'test_ids',
        nargs='+',
        help='Test identifiers to collect coverage for'
    )
    
    # show command
    show_parser = coverage_subparsers.add_parser(
        'show',
        help='Show coverage for a specific test'
    )
    show_parser.add_argument(
        '--test-id',
        required=True,
        help='Test identifier'
    )
    show_parser.add_argument(
        '--db',
        default='crossbridge.db',
        help='Database path'
    )
    show_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    # stats command
    stats_parser = coverage_subparsers.add_parser(
        'stats',
        help='Show coverage statistics'
    )
    stats_parser.add_argument(
        '--db',
        default='crossbridge.db',
        help='Database path'
    )
    
    # impact command
    impact_parser = coverage_subparsers.add_parser(
        'impact',
        help='Query which tests are impacted by changed classes'
    )
    impact_parser.add_argument(
        '--db',
        default='crossbridge.db',
        help='Database path'
    )
    impact_parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.5,
        help='Minimum confidence threshold (default: 0.5)'
    )
    impact_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format'
    )
    impact_parser.add_argument(
        'changed_classes',
        nargs='+',
        help='Changed class names'
    )
    
    # tests-for-class command
    tests_for_class_parser = coverage_subparsers.add_parser(
        'tests-for-class',
        help='Find all tests that cover a specific class'
    )
    tests_for_class_parser.add_argument(
        '--class-name',
        required=True,
        help='Fully qualified class name'
    )
    tests_for_class_parser.add_argument(
        '--db',
        default='crossbridge.db',
        help='Database path'
    )
    tests_for_class_parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.5,
        help='Minimum confidence threshold'
    )
    
    # tests-for-method command
    tests_for_method_parser = coverage_subparsers.add_parser(
        'tests-for-method',
        help='Find all tests that cover a specific method'
    )
    tests_for_method_parser.add_argument(
        '--class-name',
        required=True,
        help='Fully qualified class name'
    )
    tests_for_method_parser.add_argument(
        '--method-name',
        required=True,
        help='Method name'
    )
    tests_for_method_parser.add_argument(
        '--db',
        default='crossbridge.db',
        help='Database path'
    )
    tests_for_method_parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.5,
        help='Minimum confidence threshold'
    )


def execute_coverage_command(args):
    """Execute coverage command based on arguments."""
    
    if args.coverage_command == 'collect-isolated':
        return _collect_isolated(args)
    elif args.coverage_command == 'collect-batch':
        return _collect_batch(args)
    elif args.coverage_command == 'show':
        return _show_coverage(args)
    elif args.coverage_command == 'stats':
        return _show_stats(args)
    elif args.coverage_command == 'impact':
        return _query_impact(args)
    elif args.coverage_command == 'tests-for-class':
        return _tests_for_class(args)
    elif args.coverage_command == 'tests-for-method':
        return _tests_for_method(args)
    else:
        print("Error: No coverage command specified", file=sys.stderr)
        return 1


def _collect_isolated(args):
    """Collect coverage for a single test."""
    engine = CoverageMappingEngine(db_path=Path(args.db))
    
    mapping = engine.collect_coverage_isolated(
        test_id=args.test_id,
        test_command=args.test_command,
        working_dir=Path(args.working_dir),
        test_framework=args.framework,
        timeout=args.timeout
    )
    
    if mapping:
        print("✓ Coverage collected successfully")
        print(f"  Classes covered: {len(mapping.covered_classes)}")
        print(f"  Methods covered: {len(mapping.covered_methods)}")
        print(f"  Confidence: {mapping.confidence:.2f}")
        return 0
    else:
        print("✗ Failed to collect coverage", file=sys.stderr)
        return 1


def _collect_batch(args):
    """Collect coverage for multiple tests."""
    engine = CoverageMappingEngine(db_path=Path(args.db))
    
    mappings = engine.collect_coverage_batch(
        test_ids=args.test_ids,
        test_command=args.test_command,
        working_dir=Path(args.working_dir),
        test_framework=args.framework,
        timeout=args.timeout
    )
    
    if mappings:
        print(f"✓ Coverage collected for {len(mappings)} tests")
        
        all_classes = set()
        all_methods = set()
        for mapping in mappings:
            all_classes.update(mapping.covered_classes)
            all_methods.update(mapping.covered_methods)
        
        print(f"  Total classes covered: {len(all_classes)}")
        print(f"  Total methods covered: {len(all_methods)}")
        return 0
    else:
        print("✗ Failed to collect coverage", file=sys.stderr)
        return 1


def _show_coverage(args):
    """Show coverage for a specific test."""
    engine = CoverageMappingEngine(db_path=Path(args.db))
    
    coverage_records = engine.repository.get_coverage_for_test(args.test_id)
    
    if not coverage_records:
        print(f"No coverage found for test: {args.test_id}", file=sys.stderr)
        return 1
    
    if args.format == 'json':
        print(json.dumps(coverage_records, indent=2))
    else:
        print(f"\nCoverage for: {args.test_id}")
        print(f"Total records: {len(coverage_records)}\n")
        
        # Group by class
        by_class = {}
        for record in coverage_records:
            class_name = record['class_name']
            if class_name not in by_class:
                by_class[class_name] = []
            by_class[class_name].append(record)
        
        for class_name, records in sorted(by_class.items()):
            print(f"  {class_name}")
            for record in records:
                method = record['method_name'] or '(class-level)'
                coverage = record['coverage_percentage']
                confidence = record['confidence']
                print(f"    - {method}: {coverage:.1f}% (confidence: {confidence:.2f})")
            print()
    
    return 0


def _show_stats(args):
    """Show coverage statistics."""
    engine = CoverageMappingEngine(db_path=Path(args.db))
    
    stats = engine.get_statistics()
    
    print("\nCoverage Statistics:")
    print(f"  Total tests: {stats['total_tests']}")
    print(f"  Total classes covered: {stats['total_classes']}")
    print(f"  Total methods covered: {stats['total_methods']}")
    print(f"  Average confidence: {stats['average_confidence']:.2f}")
    
    if stats['by_framework']:
        print("\n  By framework:")
        for framework, count in sorted(stats['by_framework'].items()):
            print(f"    {framework}: {count} tests")
    
    return 0


def _query_impact(args):
    """Query impact of changed classes."""
    engine = CoverageMappingEngine(db_path=Path(args.db))
    
    query_result = engine.query_impact(
        changed_classes=set(args.changed_classes),
        min_confidence=args.min_confidence
    )
    
    if args.format == 'json':
        print(json.dumps({
            'changed_classes': list(query_result.changed_classes),
            'affected_tests': query_result.affected_tests,
            'affected_test_count': query_result.affected_test_count,
            'min_confidence': args.min_confidence
        }, indent=2))
    else:
        print(f"\nImpact Analysis:")
        print(f"  Changed classes: {len(query_result.changed_classes)}")
        for class_name in sorted(query_result.changed_classes):
            print(f"    - {class_name}")
        
        print(f"\n  Affected tests: {query_result.affected_test_count}")
        
        if hasattr(query_result, 'detailed_results'):
            # Sort by confidence
            sorted_results = sorted(
                query_result.detailed_results,
                key=lambda x: x['confidence'],
                reverse=True
            )
            
            for result in sorted_results:
                print(f"    - {result['test_name']} ({result['test_framework']})")
                print(f"      Confidence: {result['confidence']:.2f}")
                print(f"      Covers: {', '.join(sorted(result['covered_changed_classes']))}")
    
    return 0


def _tests_for_class(args):
    """Find tests that cover a specific class."""
    engine = CoverageMappingEngine(db_path=Path(args.db))
    
    tests = engine.repository.get_tests_covering_class(
        class_name=args.class_name,
        min_confidence=args.min_confidence
    )
    
    if not tests:
        print(f"No tests found covering: {args.class_name}")
        return 0
    
    print(f"\nTests covering {args.class_name}:")
    print(f"Total: {len(tests)}\n")
    
    for test in tests:
        print(f"  {test['test_name']} ({test['test_framework']})")
        print(f"    Confidence: {test['confidence']:.2f}")
        print(f"    Methods covered: {test['methods_covered']}")
        print(f"    Latest discovery: {test['latest_discovery']}")
        print()
    
    return 0


def _tests_for_method(args):
    """Find tests that cover a specific method."""
    engine = CoverageMappingEngine(db_path=Path(args.db))
    
    tests = engine.repository.get_tests_covering_method(
        class_name=args.class_name,
        method_name=args.method_name,
        min_confidence=args.min_confidence
    )
    
    if not tests:
        print(f"No tests found covering: {args.class_name}.{args.method_name}")
        return 0
    
    print(f"\nTests covering {args.class_name}.{args.method_name}:")
    print(f"Total: {len(tests)}\n")
    
    for test in tests:
        print(f"  {test['test_name']} ({test['test_framework']})")
        print(f"    Confidence: {test['confidence']:.2f}")
        print(f"    Latest discovery: {test['latest_discovery']}")
        print()
    
    return 0

