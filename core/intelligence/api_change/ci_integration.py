"""
CI Integration - Selective test execution based on API changes.

This module provides integration with CI/CD systems to enable smart test selection.
Instead of running all tests, only run tests affected by API changes.
"""

from typing import List, Dict, Set, Optional, Any
from pathlib import Path
from enum import Enum
import json
import logging

from core.intelligence.api_change.models.api_change import APIChangeEvent
from core.intelligence.api_change.models.test_impact import TestImpact


logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    """Output formats for test lists."""
    PYTEST = "pytest"           # pytest test1.py::test_func test2.py
    ROBOT = "robot"             # robot test1.robot test2.robot
    JSON = "json"               # {"tests": ["test1", "test2"]}
    TEXT = "text"               # One test per line
    GITHUB_ACTIONS = "github"   # GitHub Actions output format
    JENKINS = "jenkins"         # Jenkins format


class CIIntegration:
    """
    Handles CI/CD integration for selective test execution.
    
    Features:
    - Convert test impacts to CI-friendly format
    - Filter tests by confidence level
    - Group tests by framework
    - Generate CI system outputs
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CI integration.
        
        Args:
            config: Optional configuration with:
                - min_confidence: Minimum confidence for test selection (default: 0.5)
                - max_tests: Maximum number of tests to run (default: unlimited)
                - frameworks: List of test frameworks to include
                - exclude_patterns: Test patterns to exclude
        """
        self.config = config or {}
        self.min_confidence = self.config.get('min_confidence', 0.5)
        self.max_tests = self.config.get('max_tests', 0)  # 0 = unlimited
        self.frameworks = self.config.get('frameworks', [])
        self.exclude_patterns = self.config.get('exclude_patterns', [])
    
    def select_tests(
        self,
        impacts: List[TestImpact],
        changes: Optional[List[APIChangeEvent]] = None
    ) -> List[TestImpact]:
        """
        Select tests to run based on impacts and configuration.
        
        Args:
            impacts: List of test impacts from impact analyzer
            changes: Optional list of API changes for additional filtering
        
        Returns:
            Filtered list of test impacts to run
        """
        # Filter by confidence
        selected = [
            impact for impact in impacts
            if impact.confidence >= self.min_confidence
        ]
        
        # Filter by framework if specified
        if self.frameworks:
            selected = [
                impact for impact in selected
                if self._matches_framework(impact.test_file)
            ]
        
        # Filter out excluded patterns
        if self.exclude_patterns:
            selected = [
                impact for impact in selected
                if not self._matches_exclude_pattern(impact.test_file)
            ]
        
        # Sort by confidence (highest first)
        selected.sort(key=lambda x: x.confidence, reverse=True)
        
        # Limit number of tests if configured
        if self.max_tests > 0:
            selected = selected[:self.max_tests]
        
        return selected
    
    def generate_test_command(
        self,
        impacts: List[TestImpact],
        output_format: OutputFormat = OutputFormat.PYTEST,
        framework: Optional[str] = None
    ) -> str:
        """
        Generate test execution command for CI.
        
        Args:
            impacts: Selected test impacts
            output_format: Desired output format
            framework: Optional framework override
        
        Returns:
            Test execution command string
        """
        if not impacts:
            return ""
        
        if output_format == OutputFormat.PYTEST:
            return self._generate_pytest_command(impacts)
        elif output_format == OutputFormat.ROBOT:
            return self._generate_robot_command(impacts)
        elif output_format == OutputFormat.JSON:
            return self._generate_json_output(impacts)
        elif output_format == OutputFormat.TEXT:
            return self._generate_text_output(impacts)
        elif output_format == OutputFormat.GITHUB_ACTIONS:
            return self._generate_github_output(impacts)
        elif output_format == OutputFormat.JENKINS:
            return self._generate_jenkins_output(impacts)
        else:
            return self._generate_text_output(impacts)
    
    def generate_test_plan(
        self,
        impacts: List[TestImpact],
        changes: List[APIChangeEvent]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive test plan with metadata.
        
        Args:
            impacts: Test impacts
            changes: API changes
        
        Returns:
            Test plan dictionary with execution details
        """
        breaking_changes = [c for c in changes if c.breaking]
        high_confidence_tests = [i for i in impacts if i.confidence >= 0.75]
        
        # Group tests by framework
        by_framework = self._group_by_framework(impacts)
        
        plan = {
            'summary': {
                'total_changes': len(changes),
                'breaking_changes': len(breaking_changes),
                'total_tests': len(impacts),
                'high_confidence_tests': len(high_confidence_tests),
                'frameworks': list(by_framework.keys())
            },
            'execution': {
                'min_confidence': self.min_confidence,
                'max_tests': self.max_tests if self.max_tests > 0 else 'unlimited',
                'estimated_duration': self._estimate_duration(impacts)
            },
            'tests_by_framework': {
                framework: [
                    {
                        'file': impact.test_file,
                        'name': impact.test_name,
                        'confidence': impact.confidence,
                        'endpoint': impact.endpoint,
                        'method': impact.method
                    }
                    for impact in tests
                ]
                for framework, tests in by_framework.items()
            },
            'breaking_changes': [
                {
                    'path': change.path,
                    'method': change.method,
                    'type': change.change_type,
                    'risk': change.risk_level.value if change.risk_level else 'unknown'
                }
                for change in breaking_changes
            ]
        }
        
        return plan
    
    def _generate_pytest_command(self, impacts: List[TestImpact]) -> str:
        """Generate pytest command."""
        # Group by test file
        test_specs = []
        
        for impact in impacts:
            if impact.test_name:
                # Specific test: file.py::test_name
                test_specs.append(f"{impact.test_file}::{impact.test_name}")
            else:
                # Whole file
                test_specs.append(impact.test_file)
        
        # Deduplicate
        test_specs = list(set(test_specs))
        
        return f"pytest {' '.join(test_specs)}"
    
    def _generate_robot_command(self, impacts: List[TestImpact]) -> str:
        """Generate Robot Framework command."""
        # Group by test file
        test_files = list(set([impact.test_file for impact in impacts]))
        
        # If specific tests, use --test option
        specific_tests = [impact.test_name for impact in impacts if impact.test_name]
        
        cmd_parts = ["robot"]
        
        if specific_tests:
            for test in specific_tests:
                cmd_parts.append(f"--test '{test}'")
        
        cmd_parts.extend(test_files)
        
        return ' '.join(cmd_parts)
    
    def _generate_json_output(self, impacts: List[TestImpact]) -> str:
        """Generate JSON output."""
        data = {
            'total': len(impacts),
            'tests': [
                {
                    'file': impact.test_file,
                    'name': impact.test_name,
                    'confidence': impact.confidence,
                    'endpoint': impact.endpoint,
                    'method': impact.method,
                    'reason': impact.reason
                }
                for impact in impacts
            ]
        }
        return json.dumps(data, indent=2)
    
    def _generate_text_output(self, impacts: List[TestImpact]) -> str:
        """Generate plain text output (one test per line)."""
        lines = []
        for impact in impacts:
            if impact.test_name:
                lines.append(f"{impact.test_file}::{impact.test_name}")
            else:
                lines.append(impact.test_file)
        return '\n'.join(lines)
    
    def _generate_github_output(self, impacts: List[TestImpact]) -> str:
        """Generate GitHub Actions output format."""
        test_list = []
        for impact in impacts:
            if impact.test_name:
                test_list.append(f"{impact.test_file}::{impact.test_name}")
            else:
                test_list.append(impact.test_file)
        
        # GitHub Actions output format
        tests_json = json.dumps(test_list)
        return f"::set-output name=tests::{tests_json}"
    
    def _generate_jenkins_output(self, impacts: List[TestImpact]) -> str:
        """Generate Jenkins-friendly output."""
        # Jenkins can read from a file or environment variable
        test_files = list(set([impact.test_file for impact in impacts]))
        return ','.join(test_files)
    
    def _group_by_framework(self, impacts: List[TestImpact]) -> Dict[str, List[TestImpact]]:
        """Group test impacts by framework."""
        by_framework: Dict[str, List[TestImpact]] = {}
        
        for impact in impacts:
            framework = self._detect_framework(impact.test_file)
            if framework not in by_framework:
                by_framework[framework] = []
            by_framework[framework].append(impact)
        
        return by_framework
    
    def _detect_framework(self, test_file: str) -> str:
        """Detect test framework from file path."""
        test_file_lower = test_file.lower()
        
        if test_file_lower.endswith('.robot'):
            return 'robot'
        elif 'pytest' in test_file_lower or test_file_lower.startswith('test_'):
            return 'pytest'
        elif 'selenium' in test_file_lower:
            return 'selenium'
        elif 'playwright' in test_file_lower:
            return 'playwright'
        elif 'cypress' in test_file_lower:
            return 'cypress'
        elif test_file_lower.endswith(('.spec.js', '.spec.ts')):
            return 'jest'
        else:
            return 'unknown'
    
    def _matches_framework(self, test_file: str) -> bool:
        """Check if test file matches configured frameworks."""
        framework = self._detect_framework(test_file)
        return framework in self.frameworks
    
    def _matches_exclude_pattern(self, test_file: str) -> bool:
        """Check if test file matches any exclude pattern."""
        for pattern in self.exclude_patterns:
            if pattern in test_file:
                return True
        return False
    
    def _estimate_duration(self, impacts: List[TestImpact]) -> str:
        """Estimate test execution duration."""
        # Rough estimate: 2 seconds per test
        total_tests = len(impacts)
        estimated_seconds = total_tests * 2
        
        if estimated_seconds < 60:
            return f"{estimated_seconds}s"
        else:
            minutes = estimated_seconds // 60
            return f"{minutes}m"
    
    def create_ci_config(
        self,
        impacts: List[TestImpact],
        ci_system: str = 'github'
    ) -> Dict[str, Any]:
        """
        Create CI configuration snippet for running selected tests.
        
        Args:
            impacts: Test impacts
            ci_system: CI system (github, jenkins, gitlab)
        
        Returns:
            CI configuration dictionary
        """
        if ci_system == 'github':
            return self._create_github_config(impacts)
        elif ci_system == 'jenkins':
            return self._create_jenkins_config(impacts)
        elif ci_system == 'gitlab':
            return self._create_gitlab_config(impacts)
        else:
            return {}
    
    def _create_github_config(self, impacts: List[TestImpact]) -> Dict[str, Any]:
        """Create GitHub Actions workflow snippet."""
        pytest_tests = [i for i in impacts if self._detect_framework(i.test_file) == 'pytest']
        
        config = {
            'name': 'API Change Tests',
            'on': {
                'push': {
                    'branches': ['main', 'develop']
                }
            },
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {'uses': 'actions/checkout@v3'},
                        {
                            'name': 'Set up Python',
                            'uses': 'actions/setup-python@v4',
                            'with': {'python-version': '3.11'}
                        },
                        {
                            'name': 'Install dependencies',
                            'run': 'pip install -r requirements.txt'
                        },
                        {
                            'name': 'Run affected tests',
                            'run': self._generate_pytest_command(pytest_tests)
                        }
                    ]
                }
            }
        }
        
        return config
    
    def _create_jenkins_config(self, impacts: List[TestImpact]) -> Dict[str, Any]:
        """Create Jenkins pipeline snippet."""
        test_files = list(set([i.test_file for i in impacts]))
        
        config = {
            'pipeline': {
                'agent': 'any',
                'stages': [
                    {
                        'stage': 'Test',
                        'steps': {
                            'sh': f"pytest {' '.join(test_files)}"
                        }
                    }
                ]
            }
        }
        
        return config
    
    def _create_gitlab_config(self, impacts: List[TestImpact]) -> Dict[str, Any]:
        """Create GitLab CI snippet."""
        config = {
            'test': {
                'stage': 'test',
                'script': [
                    'pip install -r requirements.txt',
                    self._generate_pytest_command(impacts)
                ]
            }
        }
        
        return config
    
    def save_test_plan(
        self,
        plan: Dict[str, Any],
        output_file: Path
    ) -> None:
        """
        Save test plan to file.
        
        Args:
            plan: Test plan dictionary
            output_file: Output file path
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(plan, f, indent=2)
            logger.info(f"Test plan saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save test plan: {str(e)}")
