# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Cypress Results Parser for CrossBridge Intelligence.

Parse Cypress test results for execution analysis:
- Test results (mochawesome, JSON)
- Screenshots and videos
- Network request logs
- Performance metrics
- Command logs
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CypressCommand:
    """Represents a Cypress command."""
    name: str  # 'visit', 'click', 'type', 'should', etc.
    selector: Optional[str] = None
    value: Optional[Any] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class CypressTest:
    """Represents a Cypress test case."""
    title: str
    full_title: str
    state: str  # 'passed', 'failed', 'pending', 'skipped'
    duration_ms: float = 0.0
    error: Optional[str] = None
    error_stack: Optional[str] = None
    commands: List[CypressCommand] = field(default_factory=list)
    screenshot_path: Optional[str] = None
    video_path: Optional[str] = None
    attempt: int = 1


@dataclass
class CypressTestSuite:
    """Represents a Cypress test suite (describe block)."""
    title: str
    tests: List[CypressTest] = field(default_factory=list)
    suites: List['CypressTestSuite'] = field(default_factory=list)  # Nested suites


@dataclass
class CypressRunResult:
    """Complete Cypress test run result."""
    suites: List[CypressTestSuite] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    browser: Optional[str] = None
    cypress_version: Optional[str] = None
    
    def get_all_tests(self) -> List[CypressTest]:
        """Get all tests from all suites."""
        tests = []
        for suite in self.suites:
            tests.extend(self._collect_tests(suite))
        return tests
    
    def _collect_tests(self, suite: CypressTestSuite) -> List[CypressTest]:
        """Recursively collect all tests."""
        tests = list(suite.tests)
        for nested_suite in suite.suites:
            tests.extend(self._collect_tests(nested_suite))
        return tests
    
    def get_failed_tests(self) -> List[CypressTest]:
        """Get all failed tests."""
        return [t for t in self.get_all_tests() if t.state == 'failed']
    
    def get_slow_tests(self, threshold_ms: float = 5000) -> List[CypressTest]:
        """Get tests slower than threshold."""
        return [t for t in self.get_all_tests() if t.duration_ms > threshold_ms]
    
    def get_slow_commands(self, threshold_ms: float = 1000) -> List[tuple]:
        """Get slow commands across all tests. Returns (test, command) tuples."""
        slow_commands = []
        for test in self.get_all_tests():
            for cmd in test.commands:
                if cmd.duration_ms > threshold_ms:
                    slow_commands.append((test, cmd))
        return slow_commands


class CypressResultsParser:
    """
    Parse Cypress test results.
    
    Supports multiple result formats:
    - Mochawesome JSON
    - Cypress native JSON
    - JUnit XML (basic parsing)
    """
    
    def __init__(self):
        self.result_data = None
        self._last_result = None  # Cache last parsed result
    
    def parse(self, data: Dict) -> Dict[str, Any]:
        """
        Parse Cypress results from JSON dict (for sidecar API).
        
        Args:
            data: Cypress results as dict
            
        Returns:
            Dict with parsed results in API format
        """
        # Parse using existing logic
        self.result_data = data
        
        # Detect format and parse accordingly
        if 'results' in data and isinstance(data['results'], list):
            result = self._parse_mochawesome(data)
        elif 'runs' in data:
            result = self._parse_cypress_native(data)
        elif 'tests' in data:
            result = self._parse_simple_format(data)
        else:
            result = self._parse_generic(data)
        
        self._last_result = result
        
        # Convert to API dict format
        all_tests = result.get_all_tests()
        failed_tests = result.get_failed_tests()
        
        return {
            "framework": "cypress",
            "total_tests": len(all_tests),
            "passed": len([t for t in all_tests if t.state == 'passed']),
            "failed": len(failed_tests),
            "skipped": len([t for t in all_tests if t.state in ['skipped', 'pending']]),
            "pass_rate": (len([t for t in all_tests if t.state == 'passed']) / len(all_tests) * 100) if all_tests else 0,
            "duration_ms": result.duration_ms,
            "failed_tests": [
                {
                    "test_name": t.full_title,
                    "title": t.title,
                    "status": t.state,
                    "error_message": t.error or "",
                    "stack_trace": t.error_stack or "",
                    "duration_ms": t.duration_ms,
                    "screenshot_path": t.screenshot_path,
                    "video_path": t.video_path,
                }
                for t in failed_tests
            ],
            "all_tests": [
                {
                    "test_name": t.full_title,
                    "title": t.title,
                    "status": t.state,
                    "error_message": t.error or "",
                    "duration_ms": t.duration_ms,
                }
                for t in all_tests
            ],
            "insights": {
                "slow_tests": len(result.get_slow_tests()),
                "browser": result.browser,
                "cypress_version": result.cypress_version,
            }
        }
    
    def parse_results(self, results_path: Path) -> Optional[CypressRunResult]:
        """
        Parse Cypress results file.
        
        Args:
            results_path: Path to results JSON file
            
        Returns:
            CypressRunResult or None if parsing fails
        """
        try:
            if not results_path.exists():
                logger.error(f"Results file not found: {results_path}")
                return None
            
            with open(results_path, 'r', encoding='utf-8') as f:
                results_json = json.load(f)
            
            self.result_data = results_json
            
            # Detect format and parse accordingly
            if 'results' in results_json and isinstance(results_json['results'], list):
                # Mochawesome format
                return self._parse_mochawesome(results_json)
            elif 'runs' in results_json:
                # Cypress native format
                return self._parse_cypress_native(results_json)
            elif 'tests' in results_json:
                # Simple Cypress JSON
                return self._parse_simple_format(results_json)
            else:
                logger.warning("Unknown Cypress results format")
                return self._parse_generic(results_json)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in results file: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse results {results_path}: {e}")
            return None
    
    def _parse_mochawesome(self, data: Dict) -> CypressRunResult:
        """Parse Mochawesome JSON format."""
        result = CypressRunResult()
        
        # Extract stats
        result.stats = data.get('stats', {})
        
        # Extract timing
        if 'stats' in data:
            start = data['stats'].get('start')
            end = data['stats'].get('end')
            if start:
                result.start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            if end:
                result.end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
            result.duration_ms = data['stats'].get('duration', 0)
        
        # Parse test results
        results = data.get('results', [])
        for result_item in results:
            suites = result_item.get('suites', [])
            for suite_data in suites:
                suite = self._parse_mochawesome_suite(suite_data)
                result.suites.append(suite)
        
        return result
    
    def _parse_mochawesome_suite(self, suite_data: Dict) -> CypressTestSuite:
        """Parse a single Mochawesome suite."""
        suite = CypressTestSuite(
            title=suite_data.get('title', 'Unknown Suite')
        )
        
        # Parse tests
        tests = suite_data.get('tests', [])
        for test_data in tests:
            test = CypressTest(
                title=test_data.get('title', ''),
                full_title=test_data.get('fullTitle', ''),
                state=test_data.get('state', 'unknown'),
                duration_ms=test_data.get('duration', 0),
                error=test_data.get('err', {}).get('message') if test_data.get('err') else None,
                error_stack=test_data.get('err', {}).get('stack') if test_data.get('err') else None
            )
            
            # Parse commands if available
            if 'context' in test_data:
                test.commands = self._parse_commands_from_context(test_data['context'])
            
            suite.tests.append(test)
        
        # Parse nested suites
        nested_suites = suite_data.get('suites', [])
        for nested_data in nested_suites:
            nested_suite = self._parse_mochawesome_suite(nested_data)
            suite.suites.append(nested_suite)
        
        return suite
    
    def _parse_cypress_native(self, data: Dict) -> CypressRunResult:
        """Parse Cypress native JSON format."""
        result = CypressRunResult()
        
        # Extract metadata
        result.cypress_version = data.get('cypressVersion')
        result.browser = data.get('browserName')
        
        # Extract stats
        result.stats = {
            'tests': data.get('totalTests', 0),
            'passes': data.get('totalPassed', 0),
            'failures': data.get('totalFailed', 0),
            'pending': data.get('totalPending', 0),
            'skipped': data.get('totalSkipped', 0),
        }
        
        # Parse runs (each spec file)
        runs = data.get('runs', [])
        for run in runs:
            # Get spec info
            spec = run.get('spec', {})
            
            # Parse tests from this spec
            tests = run.get('tests', [])
            
            # Create a suite for this spec
            suite = CypressTestSuite(
                title=spec.get('name', 'Unknown')
            )
            
            for test_data in tests:
                test = self._parse_cypress_test(test_data, run)
                suite.tests.append(test)
            
            result.suites.append(suite)
        
        # Calculate total duration
        result.duration_ms = sum(run.get('stats', {}).get('duration', 0) for run in runs)
        
        return result
    
    def _parse_cypress_test(self, test_data: Dict, run_data: Dict) -> CypressTest:
        """Parse a single Cypress test."""
        test = CypressTest(
            title=test_data.get('title', [''])[0] if isinstance(test_data.get('title'), list) else test_data.get('title', ''),
            full_title=' '.join(test_data.get('title', [])) if isinstance(test_data.get('title'), list) else test_data.get('title', ''),
            state=test_data.get('state', 'unknown'),
            duration_ms=test_data.get('duration', 0)
        )
        
        # Parse error
        if test_data.get('displayError'):
            test.error = test_data['displayError']
        if test_data.get('err'):
            test.error = test_data['err'].get('message', str(test_data['err']))
            test.error_stack = test_data['err'].get('stack')
        
        # Parse attempts (for retries)
        attempts = test_data.get('attempts', [])
        if attempts:
            test.attempt = len(attempts)
        
        # Screenshots
        screenshots = run_data.get('screenshots', [])
        for screenshot in screenshots:
            if test.title in screenshot.get('name', ''):
                test.screenshot_path = screenshot.get('path')
                break
        
        # Videos
        if 'video' in run_data:
            test.video_path = run_data['video']
        
        return test
    
    def _parse_simple_format(self, data: Dict) -> CypressRunResult:
        """Parse simple Cypress JSON format."""
        result = CypressRunResult()
        
        # Create a default suite
        suite = CypressTestSuite(title='Default Suite')
        
        tests = data.get('tests', [])
        for test_data in tests:
            test = CypressTest(
                title=test_data.get('title', ''),
                full_title=test_data.get('fullTitle', test_data.get('title', '')),
                state=test_data.get('state', 'unknown'),
                duration_ms=test_data.get('duration', 0),
                error=test_data.get('error')
            )
            suite.tests.append(test)
        
        result.suites.append(suite)
        
        # Extract stats
        result.stats = data.get('stats', {
            'tests': len(tests),
            'passes': len([t for t in tests if t.get('state') == 'passed']),
            'failures': len([t for t in tests if t.get('state') == 'failed']),
        })
        
        return result
    
    def _parse_generic(self, data: Dict) -> CypressRunResult:
        """Parse unknown format - best effort."""
        result = CypressRunResult()
        
        # Try to extract any test-like data
        suite = CypressTestSuite(title='Parsed Tests')
        
        # Look for common keys
        for key in ['tests', 'test', 'results', 'testResults']:
            if key in data:
                items = data[key] if isinstance(data[key], list) else [data[key]]
                for item in items:
                    if isinstance(item, dict):
                        test = CypressTest(
                            title=item.get('title', item.get('name', 'Unknown')),
                            full_title=item.get('fullTitle', item.get('title', 'Unknown')),
                            state=item.get('state', item.get('status', 'unknown')),
                            duration_ms=item.get('duration', 0)
                        )
                        suite.tests.append(test)
        
        if suite.tests:
            result.suites.append(suite)
        
        return result
    
    def _parse_commands_from_context(self, context: str) -> List[CypressCommand]:
        """Parse Cypress commands from test context (if available)."""
        commands = []
        
        # Context might contain command logs as JSON or text
        # This is a simplified parser
        try:
            if context.startswith('{') or context.startswith('['):
                context_data = json.loads(context)
                if isinstance(context_data, list):
                    for cmd_data in context_data:
                        if isinstance(cmd_data, dict):
                            command = CypressCommand(
                                name=cmd_data.get('name', 'unknown'),
                                selector=cmd_data.get('selector'),
                                value=cmd_data.get('value'),
                                duration_ms=cmd_data.get('duration', 0),
                                error=cmd_data.get('error')
                            )
                            commands.append(command)
        except:
            # Context not parseable as JSON
            pass
        
        return commands
    
    def get_test_summary(self, result: CypressRunResult) -> Dict[str, Any]:
        """Get human-readable test summary."""
        all_tests = result.get_all_tests()
        
        return {
            'total_tests': len(all_tests),
            'passed': len([t for t in all_tests if t.state == 'passed']),
            'failed': len([t for t in all_tests if t.state == 'failed']),
            'pending': len([t for t in all_tests if t.state == 'pending']),
            'skipped': len([t for t in all_tests if t.state == 'skipped']),
            'duration_ms': result.duration_ms,
            'pass_rate': (len([t for t in all_tests if t.state == 'passed']) / len(all_tests) * 100) if all_tests else 0,
            'browser': result.browser,
            'cypress_version': result.cypress_version,
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def parse_cypress_results(results_path: Path) -> Optional[CypressRunResult]:
    """
    Convenience function to parse Cypress results.
    
    Args:
        results_path: Path to results JSON file
        
    Returns:
        CypressRunResult or None
    """
    parser = CypressResultsParser()
    return parser.parse_results(results_path)


def analyze_cypress_performance(results_path: Path) -> Dict[str, Any]:
    """
    Quick performance analysis of Cypress results.
    
    Args:
        results_path: Path to results JSON file
        
    Returns:
        Dict with performance insights
    """
    result = parse_cypress_results(results_path)
    if not result:
        return {}
    
    all_tests = result.get_all_tests()
    durations = [t.duration_ms for t in all_tests if t.duration_ms > 0]
    
    return {
        'total_tests': len(all_tests),
        'failed_tests': len(result.get_failed_tests()),
        'slow_tests': len(result.get_slow_tests()),
        'avg_test_duration_ms': sum(durations) / len(durations) if durations else 0,
        'max_test_duration_ms': max(durations) if durations else 0,
        'total_duration_ms': result.duration_ms,
        'pass_rate': (len([t for t in all_tests if t.state == 'passed']) / len(all_tests) * 100) if all_tests else 0,
    }


def find_flaky_tests(results_paths: List[Path]) -> Dict[str, List[str]]:
    """
    Find potentially flaky tests by analyzing multiple runs.
    
    Args:
        results_paths: List of result file paths from different runs
        
    Returns:
        Dict mapping test names to their states across runs
    """
    test_results = {}
    
    for path in results_paths:
        result = parse_cypress_results(path)
        if not result:
            continue
        
        for test in result.get_all_tests():
            if test.full_title not in test_results:
                test_results[test.full_title] = []
            test_results[test.full_title].append(test.state)
    
    # Find tests with inconsistent results
    flaky_tests = {}
    for test_name, states in test_results.items():
        unique_states = set(states)
        if len(unique_states) > 1:  # Test has different outcomes
            flaky_tests[test_name] = states
    
    return flaky_tests
