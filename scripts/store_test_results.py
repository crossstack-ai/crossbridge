#!/usr/bin/env python3
"""
Store test execution results in PostgreSQL database.

This script parses test results from various formats (pytest JSON, JUnit XML)
and stores them in the CrossBridge database for flaky detection analysis.

Usage:
    python store_test_results.py pytest_results.json
    python store_test_results.py junit_results.xml --format junit
"""

import json
import sys
import os
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.flaky_detection.models import TestExecutionRecord, TestFramework, TestStatus
from core.flaky_detection.persistence import FlakyDetectionRepository


def parse_pytest_json(filepath: str) -> List[TestExecutionRecord]:
    """Parse pytest JSON report format."""
    
    with open(filepath) as f:
        data = json.load(f)
    
    # Get CI/CD context
    git_commit = (
        os.environ.get('GITHUB_SHA') or 
        os.environ.get('CI_COMMIT_SHA') or
        os.environ.get('GIT_COMMIT')
    )
    git_branch = (
        os.environ.get('GITHUB_REF_NAME') or
        os.environ.get('CI_COMMIT_BRANCH') or
        os.environ.get('GIT_BRANCH')
    )
    build_id = (
        os.environ.get('GITHUB_RUN_ID') or
        os.environ.get('CI_JOB_ID') or
        os.environ.get('BUILD_ID')
    )
    environment = os.environ.get('TEST_ENVIRONMENT', 'ci')
    
    # Parse test results
    records = []
    for test in data.get('tests', []):
        # Map pytest outcome to TestStatus
        status_map = {
            'passed': TestStatus.PASSED,
            'failed': TestStatus.FAILED,
            'skipped': TestStatus.SKIPPED,
            'error': TestStatus.ERROR
        }
        
        status = status_map.get(test.get('outcome'), TestStatus.FAILED)
        
        # Extract error information
        error_signature = None
        error_full = None
        if status in (TestStatus.FAILED, TestStatus.ERROR):
            call_info = test.get('call', {})
            error_signature = call_info.get('crash', {}).get('message')
            error_full = call_info.get('longrepr')
        
        # Extract TestRail/Zephyr IDs from test markers or docstring
        external_test_id = None
        external_system = None
        for marker in test.get('markers', []):
            if marker.get('name') == 'testrail':
                external_test_id = marker.get('args', [None])[0]
                external_system = 'testrail'
            elif marker.get('name') == 'zephyr':
                external_test_id = marker.get('args', [None])[0]
                external_system = 'zephyr'
        
        record = TestExecutionRecord(
            test_id=test['nodeid'],
            test_name=test.get('name', test['nodeid']),
            test_file=test.get('file'),
            test_line=test.get('line'),
            framework=TestFramework.PYTEST,
            status=status,
            duration_ms=int(test.get('duration', 0) * 1000),
            executed_at=datetime.now(),
            error_signature=error_signature,
            error_full=error_full,
            git_commit=git_commit,
            git_branch=git_branch,
            environment=environment,
            build_id=build_id,
            external_test_id=external_test_id,
            external_system=external_system,
            tags=test.get('keywords', []),
            metadata={
                'setup_duration': test.get('setup', {}).get('duration'),
                'teardown_duration': test.get('teardown', {}).get('duration'),
                'outcome': test.get('outcome')
            }
        )
        records.append(record)
    
    return records


def parse_junit_xml(filepath: str) -> List[TestExecutionRecord]:
    """Parse JUnit XML format."""
    
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    # Get CI/CD context
    git_commit = os.environ.get('GITHUB_SHA') or os.environ.get('CI_COMMIT_SHA')
    build_id = os.environ.get('GITHUB_RUN_ID') or os.environ.get('CI_JOB_ID')
    environment = os.environ.get('TEST_ENVIRONMENT', 'ci')
    
    records = []
    
    # Handle both <testsuite> and <testsuites> root elements
    testsuites = root.findall('.//testsuite') if root.tag == 'testsuites' else [root]
    
    for testsuite in testsuites:
        for testcase in testsuite.findall('testcase'):
            classname = testcase.get('classname', '')
            name = testcase.get('name', '')
            test_id = f"{classname}::{name}" if classname else name
            
            # Determine status
            failure = testcase.find('failure')
            error = testcase.find('error')
            skipped = testcase.find('skipped')
            
            if failure is not None:
                status = TestStatus.FAILED
                error_signature = failure.get('message')
                error_full = failure.text
            elif error is not None:
                status = TestStatus.ERROR
                error_signature = error.get('message')
                error_full = error.text
            elif skipped is not None:
                status = TestStatus.SKIPPED
                error_signature = None
                error_full = None
            else:
                status = TestStatus.PASSED
                error_signature = None
                error_full = None
            
            duration_ms = int(float(testcase.get('time', 0)) * 1000)
            
            record = TestExecutionRecord(
                test_id=test_id,
                test_name=name,
                framework=TestFramework.JUNIT,
                status=status,
                duration_ms=duration_ms,
                executed_at=datetime.now(),
                error_signature=error_signature,
                error_full=error_full,
                git_commit=git_commit,
                environment=environment,
                build_id=build_id,
                metadata={
                    'classname': classname,
                    'testsuite': testsuite.get('name')
                }
            )
            records.append(record)
    
    return records


def main():
    parser = argparse.ArgumentParser(
        description='Store test execution results in CrossBridge database'
    )
    parser.add_argument(
        'filepath',
        help='Path to test results file'
    )
    parser.add_argument(
        '--format',
        choices=['pytest', 'junit', 'auto'],
        default='auto',
        help='Test results format (default: auto-detect)'
    )
    parser.add_argument(
        '--db-url',
        default=os.environ.get('CROSSBRIDGE_DB_URL'),
        help='Database URL (default: from CROSSBRIDGE_DB_URL env var)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for database inserts (default: 100)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate database URL
    if not args.db_url:
        print("❌ Error: Database URL not provided")
        print("Set CROSSBRIDGE_DB_URL environment variable or use --db-url option")
        sys.exit(1)
    
    # Auto-detect format if needed
    format_type = args.format
    if format_type == 'auto':
        if args.filepath.endswith('.json'):
            format_type = 'pytest'
        elif args.filepath.endswith('.xml'):
            format_type = 'junit'
        else:
            print("❌ Error: Cannot auto-detect format. Please specify --format")
            sys.exit(1)
    
    print(f"📊 Parsing {format_type} test results from {args.filepath}...")
    
    # Parse test results
    try:
        if format_type == 'pytest':
            records = parse_pytest_json(args.filepath)
        elif format_type == 'junit':
            records = parse_junit_xml(args.filepath)
        else:
            print(f"❌ Error: Unsupported format: {format_type}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error parsing test results: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    if not records:
        print("⚠️  No test records found in file")
        sys.exit(0)
    
    print(f"   Found {len(records)} test executions")
    
    # Display summary
    passed = sum(1 for r in records if r.status == TestStatus.PASSED)
    failed = sum(1 for r in records if r.status == TestStatus.FAILED)
    skipped = sum(1 for r in records if r.status == TestStatus.SKIPPED)
    
    print(f"   ✅ Passed:  {passed}")
    print(f"   ❌ Failed:  {failed}")
    print(f"   ⏭️  Skipped: {skipped}")
    print()
    
    # Store in database
    print("💾 Storing results in database...")
    
    try:
        repo = FlakyDetectionRepository(args.db_url)
        
        # Store in batches
        for i in range(0, len(records), args.batch_size):
            batch = records[i:i + args.batch_size]
            repo.save_executions_batch(batch)
            
            if args.verbose:
                print(f"   Stored batch {i // args.batch_size + 1}/{(len(records) + args.batch_size - 1) // args.batch_size}")
        
        print(f"✅ Successfully stored {len(records)} test execution records")
        
    except Exception as e:
        print(f"❌ Error storing results: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
