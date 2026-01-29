"""
Framework integration adapters for flaky detection.

Converts framework-specific test results to normalized TestExecutionRecord
for flaky detection analysis.
"""

from typing import List, Optional
from datetime import datetime
from pathlib import Path

from ..flaky_detection.models import (
    TestExecutionRecord,
    TestFramework,
    TestStatus
)
from ..flaky_detection.feature_engineering import normalize_error_signature


class CucumberIntegration:
    """Integration adapter for Cucumber/BDD frameworks."""
    
    @staticmethod
    def from_cucumber_json(
        cucumber_json_path: Path,
        git_commit: Optional[str] = None,
        environment: str = "unknown",
        build_id: Optional[str] = None
    ) -> List[TestExecutionRecord]:
        """
        Convert Cucumber JSON results to normalized execution records.
        
        Args:
            cucumber_json_path: Path to cucumber-report.json
            git_commit: Git commit SHA
            environment: Execution environment
            build_id: CI build identifier
        
        Returns:
            List of TestExecutionRecord objects
        """
        from adapters.selenium_bdd_java import parse_cucumber_json
        
        features = parse_cucumber_json(cucumber_json_path)
        records = []
        
        for feature in features:
            for scenario in feature.scenarios:
                # Create stable test ID
                test_id = f"{feature.uri}::{scenario.scenario}"
                
                # Determine status
                if scenario.status == "passed":
                    status = TestStatus.PASSED
                elif scenario.status == "failed":
                    status = TestStatus.FAILED
                elif scenario.status == "skipped":
                    status = TestStatus.SKIPPED
                else:
                    status = TestStatus.ERROR
                
                # Extract error information
                error_signature = None
                error_full = None
                
                if scenario.failed_steps:
                    failed_step = scenario.failed_steps[0]
                    if failed_step.error_message:
                        error_signature = normalize_error_signature(
                            failed_step.error_message
                        )
                        error_full = failed_step.error_message
                
                # Create execution record
                record = TestExecutionRecord(
                    test_id=test_id,
                    framework=TestFramework.CUCUMBER,
                    status=status,
                    duration_ms=scenario.total_duration_ns / 1_000_000,
                    executed_at=datetime.now(),  # Cucumber JSON doesn't include timestamp
                    error_signature=error_signature,
                    error_full=error_full,
                    retry_count=0,  # Cucumber doesn't track this in JSON
                    git_commit=git_commit,
                    environment=environment,
                    build_id=build_id,
                    test_name=scenario.scenario,
                    test_file=feature.uri,
                    test_line=scenario.line,
                    tags=scenario.tags,
                    metadata={
                        "feature_name": feature.name,
                        "scenario_type": scenario.scenario_type,
                        "step_count": len(scenario.steps)
                    }
                )
                
                records.append(record)
        
        return records


class JUnitIntegration:
    """Integration adapter for JUnit/TestNG frameworks."""
    
    @staticmethod
    def from_junit_xml(
        junit_xml_path: Path,
        git_commit: Optional[str] = None,
        environment: str = "unknown",
        build_id: Optional[str] = None
    ) -> List[TestExecutionRecord]:
        """
        Convert JUnit XML results to normalized execution records.
        
        Args:
            junit_xml_path: Path to JUnit XML file
            git_commit: Git commit SHA
            environment: Execution environment
            build_id: CI build identifier
        
        Returns:
            List of TestExecutionRecord objects
        """
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(junit_xml_path)
        root = tree.getroot()
        
        records = []
        
        # Handle both <testsuite> and <testsuites> root elements
        testsuites = root.findall('.//testsuite')
        if not testsuites:
            testsuites = [root] if root.tag == 'testsuite' else []
        
        for testsuite in testsuites:
            suite_name = testsuite.get('name', 'UnknownSuite')
            
            for testcase in testsuite.findall('testcase'):
                class_name = testcase.get('classname', suite_name)
                test_name = testcase.get('name', 'UnknownTest')
                duration = float(testcase.get('time', '0'))
                
                # Create stable test ID
                test_id = f"{class_name}.{test_name}"
                
                # Determine status
                failure = testcase.find('failure')
                error = testcase.find('error')
                skipped = testcase.find('skipped')
                
                if skipped is not None:
                    status = TestStatus.SKIPPED
                    error_signature = None
                    error_full = None
                elif error is not None:
                    status = TestStatus.ERROR
                    error_signature = normalize_error_signature(error.get('message', ''))
                    error_full = error.text
                elif failure is not None:
                    status = TestStatus.FAILED
                    error_signature = normalize_error_signature(failure.get('message', ''))
                    error_full = failure.text
                else:
                    status = TestStatus.PASSED
                    error_signature = None
                    error_full = None
                
                record = TestExecutionRecord(
                    test_id=test_id,
                    framework=TestFramework.JUNIT,
                    status=status,
                    duration_ms=duration * 1000,  # Convert seconds to ms
                    executed_at=datetime.now(),
                    error_signature=error_signature,
                    error_full=error_full,
                    retry_count=0,
                    git_commit=git_commit,
                    environment=environment,
                    build_id=build_id,
                    test_name=test_name,
                    test_file=class_name.replace('.', '/') + '.java',
                    tags=[],
                    metadata={
                        "suite_name": suite_name,
                        "class_name": class_name
                    }
                )
                
                records.append(record)
        
        return records


class PytestIntegration:
    """Integration adapter for Pytest framework."""
    
    @staticmethod
    def from_pytest_json(
        pytest_json_path: Path,
        git_commit: Optional[str] = None,
        environment: str = "unknown",
        build_id: Optional[str] = None
    ) -> List[TestExecutionRecord]:
        """
        Convert Pytest JSON results to normalized execution records.
        
        Requires pytest-json-report plugin.
        
        Args:
            pytest_json_path: Path to pytest .report.json file
            git_commit: Git commit SHA
            environment: Execution environment
            build_id: CI build identifier
        
        Returns:
            List of TestExecutionRecord objects
        """
        import json
        
        with open(pytest_json_path, 'r') as f:
            data = json.load(f)
        
        records = []
        
        for test_id, test_data in data.get('tests', {}).items():
            # Parse test info
            nodeid = test_data.get('nodeid', test_id)
            outcome = test_data.get('outcome', 'unknown')
            duration = test_data.get('call', {}).get('duration', 0)
            
            # Determine status
            if outcome == 'passed':
                status = TestStatus.PASSED
            elif outcome == 'failed':
                status = TestStatus.FAILED
            elif outcome == 'skipped':
                status = TestStatus.SKIPPED
            elif outcome == 'error':
                status = TestStatus.ERROR
            else:
                status = TestStatus.ERROR
            
            # Extract error information
            error_signature = None
            error_full = None
            
            if outcome in ('failed', 'error'):
                call_info = test_data.get('call', {})
                if 'longrepr' in call_info:
                    error_full = call_info['longrepr']
                    error_signature = normalize_error_signature(error_full)
            
            # Parse file and line from nodeid
            # Format: path/to/file.py::TestClass::test_method
            parts = nodeid.split('::')
            test_file = parts[0] if parts else None
            test_name = parts[-1] if parts else nodeid
            
            record = TestExecutionRecord(
                test_id=nodeid,
                framework=TestFramework.PYTEST,
                status=status,
                duration_ms=duration * 1000,
                executed_at=datetime.now(),
                error_signature=error_signature,
                error_full=error_full,
                retry_count=0,
                git_commit=git_commit,
                environment=environment,
                build_id=build_id,
                test_name=test_name,
                test_file=test_file,
                tags=test_data.get('markers', []),
                metadata={
                    "outcome": outcome,
                    "keywords": test_data.get('keywords', [])
                }
            )
            
            records.append(record)
        
        return records


class RobotIntegration:
    """Integration adapter for Robot Framework."""
    
    @staticmethod
    def from_robot_output(
        robot_output_path: Path,
        git_commit: Optional[str] = None,
        environment: str = "unknown",
        build_id: Optional[str] = None
    ) -> List[TestExecutionRecord]:
        """
        Convert Robot Framework output.xml to normalized execution records.
        
        Args:
            robot_output_path: Path to output.xml
            git_commit: Git commit SHA
            environment: Execution environment
            build_id: CI build identifier
        
        Returns:
            List of TestExecutionRecord objects
        """
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(robot_output_path)
        root = tree.getroot()
        
        records = []
        
        for suite in root.findall('.//suite'):
            suite_name = suite.get('name', 'UnknownSuite')
            suite_source = suite.get('source', '')
            
            for test in suite.findall('test'):
                test_name = test.get('name', 'UnknownTest')
                test_id = f"{suite_name}::{test_name}"
                
                # Get status
                status_elem = test.find('status')
                if status_elem is not None:
                    outcome = status_elem.get('status', 'FAIL')
                    
                    if outcome == 'PASS':
                        status = TestStatus.PASSED
                    elif outcome == 'FAIL':
                        status = TestStatus.FAILED
                    elif outcome == 'SKIP':
                        status = TestStatus.SKIPPED
                    else:
                        status = TestStatus.ERROR
                    
                    # Calculate duration
                    start_time = status_elem.get('starttime', '')
                    end_time = status_elem.get('endtime', '')
                    
                    # Parse Robot timestamps (yyyymmdd HH:MM:SS.mmm)
                    try:
                        from datetime import datetime as dt
                        start_dt = dt.strptime(start_time, '%Y%m%d %H:%M:%S.%f')
                        end_dt = dt.strptime(end_time, '%Y%m%d %H:%M:%S.%f')
                        duration_ms = (end_dt - start_dt).total_seconds() * 1000
                        executed_at = start_dt
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Failed to parse Robot Framework timestamps: {e}")
                        duration_ms = 0.0
                        executed_at = datetime.now()
                    
                    # Get error message
                    error_full = status_elem.text
                    error_signature = normalize_error_signature(error_full) if error_full else None
                else:
                    status = TestStatus.ERROR
                    duration_ms = 0.0
                    executed_at = datetime.now()
                    error_signature = None
                    error_full = None
                
                # Get tags
                tags = [tag.text for tag in test.findall('tag') if tag.text]
                
                record = TestExecutionRecord(
                    test_id=test_id,
                    framework=TestFramework.ROBOT,
                    status=status,
                    duration_ms=duration_ms,
                    executed_at=executed_at,
                    error_signature=error_signature,
                    error_full=error_full,
                    retry_count=0,
                    git_commit=git_commit,
                    environment=environment,
                    build_id=build_id,
                    test_name=test_name,
                    test_file=suite_source,
                    tags=tags,
                    metadata={
                        "suite_name": suite_name
                    }
                )
                
                records.append(record)
        
        return records


def convert_test_results(
    result_file: Path,
    framework: TestFramework,
    git_commit: Optional[str] = None,
    environment: str = "unknown",
    build_id: Optional[str] = None
) -> List[TestExecutionRecord]:
    """
    Convert test results from any framework to normalized records.
    
    Args:
        result_file: Path to test result file
        framework: Test framework type
        git_commit: Git commit SHA
        environment: Execution environment
        build_id: CI build identifier
    
    Returns:
        List of TestExecutionRecord objects
    
    Raises:
        ValueError: If framework is not supported
    """
    if framework in (TestFramework.CUCUMBER, TestFramework.SELENIUM_BDD):
        return CucumberIntegration.from_cucumber_json(
            result_file, git_commit, environment, build_id
        )
    elif framework in (TestFramework.JUNIT, TestFramework.TESTNG, TestFramework.SELENIUM_JAVA):
        return JUnitIntegration.from_junit_xml(
            result_file, git_commit, environment, build_id
        )
    elif framework == TestFramework.PYTEST:
        return PytestIntegration.from_pytest_json(
            result_file, git_commit, environment, build_id
        )
    elif framework == TestFramework.ROBOT:
        return RobotIntegration.from_robot_output(
            result_file, git_commit, environment, build_id
        )
    else:
        raise ValueError(f"Unsupported framework: {framework}")
