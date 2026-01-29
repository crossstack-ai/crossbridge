"""
Selenium + Behave adapter implementation.

Handles Selenium WebDriver tests written with Behave (Python BDD framework).
Supports:
- Gherkin feature files (.feature)
- Step definitions in Python
- Environment hooks (before_all, before_scenario, etc.)
- Tags for scenario filtering
- Context sharing between steps
- Page Object Model integration
"""

import subprocess
import json
import re
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..common.base import BaseTestAdapter, TestResult
from ..common.models import TestMetadata


class SeleniumBehaveAdapter(BaseTestAdapter):
    """
    Adapter for Selenium tests using Behave BDD framework.
    
    Handles discovery and execution of Gherkin scenarios with Selenium steps.
    """

    def __init__(self, project_root: str, driver_type: str = "chrome"):
        """
        Initialize the Selenium Behave adapter.
        
        Args:
            project_root: Root directory of the project
            driver_type: WebDriver type (chrome, firefox, edge, safari)
        """
        self.project_root = Path(project_root)
        self.driver_type = driver_type
        self.features_dir = self.project_root / "features"
        self._verify_behave_installed()

    def _verify_behave_installed(self):
        """Verify Behave is installed."""
        try:
            result = subprocess.run(
                ["behave", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Behave is not properly installed")
        except FileNotFoundError:
            raise RuntimeError("Behave is not installed. Install with: pip install behave selenium")

    def discover_tests(self) -> List[str]:
        """
        Discover Behave scenarios using behave --dry-run.
        
        Returns:
            List of scenario identifiers (feature:scenario format)
        """
        tests = []
        
        if not self.features_dir.exists():
            return tests
        
        try:
            # Use behave dry-run to list scenarios
            result = subprocess.run(
                ["behave", "--dry-run", "--no-summary", "--format", "json", "-o", "scenarios.json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse JSON output
            json_path = self.project_root / "scenarios.json"
            if json_path.exists():
                with open(json_path, 'r') as f:
                    features = json.load(f)
                    
                for feature in features:
                    feature_name = feature.get('name', 'Unknown Feature')
                    feature_file = feature.get('location', '')
                    
                    for element in feature.get('elements', []):
                        if element.get('type') == 'scenario':
                            scenario_name = element.get('name', 'Unknown Scenario')
                            scenario_line = element.get('line', 0)
                            
                            # Format: feature_file:line or feature:scenario
                            test_id = f"{feature_file}:{scenario_line}"
                            tests.append(test_id)
                
                # Cleanup
                json_path.unlink()
            else:
                # Fallback: parse feature files directly
                tests = self._discover_from_files()
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("Test discovery timed out")
        except Exception as e:
            # Fallback to file parsing
            tests = self._discover_from_files()
        
        return tests

    def _discover_from_files(self) -> List[str]:
        """Discover scenarios by parsing .feature files directly."""
        tests = []
        
        feature_files = list(self.features_dir.rglob("*.feature"))
        
        for feature_file in feature_files:
            try:
                with open(feature_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find all scenarios
                scenario_pattern = r'^\s*(?:Scenario|Scenario Outline):\s*(.+)$'
                line_num = 0
                
                for line in content.split('\n'):
                    line_num += 1
                    match = re.match(scenario_pattern, line)
                    if match:
                        scenario_name = match.group(1).strip()
                        relative_path = feature_file.relative_to(self.project_root)
                        test_id = f"{relative_path}:{line_num}"
                        tests.append(test_id)
            
            except Exception as e:
                continue
        
        return tests

    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestResult]:
        """
        Run Behave scenarios.
        
        Args:
            tests: Specific scenarios to run (feature:line format)
            tags: Behave tags to filter by (e.g., @smoke, @critical)
        
        Returns:
            List of TestResult objects
        """
        cmd = ["behave", "--format", "json", "--outfile", "results.json", "--no-capture"]
        
        # Add tag filtering
        if tags:
            for tag in tags:
                tag_expr = tag if tag.startswith('@') else f'@{tag}'
                cmd.extend(["--tags", tag_expr])
        
        # Add specific scenarios
        if tests:
            # Behave accepts feature files or feature:line
            for test in tests:
                if ':' in test:
                    cmd.append(test)
                else:
                    cmd.append(test)
        
        try:
            # Set driver type via environment
            import os
            env = os.environ.copy()
            env['DRIVER_TYPE'] = self.driver_type
            
            # Run Behave
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            # Parse JSON results
            results_path = self.project_root / "results.json"
            if results_path.exists():
                with open(results_path, 'r') as f:
                    behave_results = json.load(f)
                    parsed_results = self._parse_behave_results(behave_results)
                
                # Cleanup
                results_path.unlink()
                return parsed_results
            
            # Fallback to stdout parsing
            return self._parse_behave_output(result.stdout)
        
        except subprocess.TimeoutExpired:
            return [TestResult(
                name="execution_timeout",
                status="fail",
                duration_ms=300000,
                message="Test execution timed out"
            )]
        except Exception as e:
            return [TestResult(
                name="execution_error",
                status="fail",
                duration_ms=0,
                message=f"Execution failed: {e}"
            )]

    def _parse_behave_results(self, results: List[Dict[str, Any]]) -> List[TestResult]:
        """Parse Behave JSON results."""
        test_results = []
        
        for feature in results:
            feature_name = feature.get('name', 'Unknown Feature')
            
            for element in feature.get('elements', []):
                if element.get('type') != 'scenario':
                    continue
                
                scenario_name = element.get('name', 'Unknown Scenario')
                location = element.get('location', '')
                
                # Calculate scenario status (all steps must pass)
                all_steps = element.get('steps', [])
                failed_steps = [s for s in all_steps if s.get('result', {}).get('status') != 'passed']
                skipped_steps = [s for s in all_steps if s.get('result', {}).get('status') == 'skipped']
                
                if failed_steps:
                    status = 'fail'
                    # Get first failure message
                    first_failure = failed_steps[0].get('result', {})
                    message = first_failure.get('error_message', 'Step failed')
                elif skipped_steps:
                    status = 'skip'
                    message = 'Scenario skipped'
                else:
                    status = 'pass'
                    message = ''
                
                # Calculate total duration
                duration_ms = 0
                for step in all_steps:
                    step_duration = step.get('result', {}).get('duration', 0)
                    # Behave durations are in seconds (float)
                    duration_ms += int(step_duration * 1000)
                
                test_results.append(TestResult(
                    name=f"{feature_name}: {scenario_name}",
                    status=status,
                    duration_ms=duration_ms,
                    message=message
                ))
        
        return test_results

    def _parse_behave_output(self, output: str) -> List[TestResult]:
        """Parse Behave stdout as fallback."""
        results = []
        
        # Parse behave output
        # Format: "Scenario: scenario_name ... passed/failed"
        lines = output.split('\n')
        
        for line in lines:
            # Match scenario results
            match = re.match(r'\s*Scenario:\s*(.+?)\s+\.\.\.\s+(passed|failed|skipped)', line, re.IGNORECASE)
            if match:
                scenario_name = match.group(1).strip()
                outcome = match.group(2).strip().lower()
                
                status_map = {
                    'passed': 'pass',
                    'failed': 'fail',
                    'skipped': 'skip'
                }
                status = status_map.get(outcome, 'fail')
                
                results.append(TestResult(
                    name=scenario_name,
                    status=status,
                    duration_ms=0,
                    message=""
                ))
        
        return results

    def get_driver_info(self) -> Dict[str, str]:
        """Get WebDriver information."""
        return {
            'driver_type': self.driver_type,
            'framework': 'selenium',
            'runner': 'behave',
            'bdd': True
        }


class SeleniumBehaveExtractor:
    """
    Extractor for Selenium + Behave tests.
    
    Parses Gherkin feature files to extract metadata without execution.
    """
    
    def __init__(self, project_root: str):
        """
        Initialize extractor.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.features_dir = self.project_root / "features"
    
    def extract_tests(self) -> List[TestMetadata]:
        """
        Extract test metadata from feature files.
        
        Returns:
            List of TestMetadata objects
        """
        tests = []
        
        if not self.features_dir.exists():
            return tests
        
        feature_files = list(self.features_dir.rglob("*.feature"))
        
        for feature_file in feature_files:
            try:
                file_tests = self._parse_feature_file(feature_file)
                tests.extend(file_tests)
            except Exception as e:
                print(f"Warning: Failed to parse {feature_file}: {e}")
                continue
        
        return tests
    
    def _parse_feature_file(self, file_path: Path) -> List[TestMetadata]:
        """Parse a Gherkin feature file."""
        tests = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        feature_name = None
        feature_tags = []
        current_scenario = None
        current_tags = []
        line_num = 0
        
        for line in lines:
            line_num += 1
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Extract tags
            if stripped.startswith('@'):
                tags = [tag.strip() for tag in stripped.split() if tag.startswith('@')]
                current_tags.extend(tags)
                continue
            
            # Extract feature name
            if stripped.startswith('Feature:'):
                feature_name = stripped[8:].strip()
                feature_tags = current_tags.copy()
                current_tags = []
                continue
            
            # Extract scenarios
            if stripped.startswith('Scenario:') or stripped.startswith('Scenario Outline:'):
                is_outline = stripped.startswith('Scenario Outline:')
                prefix_len = 17 if is_outline else 9
                scenario_name = stripped[prefix_len:].strip()
                
                # Combine feature tags and scenario tags
                all_tags = list(set(feature_tags + current_tags))
                
                # Remove @ prefix from tags
                clean_tags = [tag[1:] if tag.startswith('@') else tag for tag in all_tags]
                
                test_id = f"{file_path.name}:{line_num}"
                
                tests.append(TestMetadata(
                    framework="selenium-behave",
                    test_name=f"{feature_name}: {scenario_name}" if feature_name else scenario_name,
                    file_path=str(file_path),
                    tags=clean_tags,
                    test_type="bdd",
                    language="gherkin"
                ))
                
                current_tags = []
        
        return tests
    
    def extract_steps(self, feature_file: Path) -> Dict[str, List[str]]:
        """
        Extract steps from a feature file grouped by scenario.
        
        Args:
            feature_file: Path to .feature file
        
        Returns:
            Dict mapping scenario names to their steps
        """
        scenario_steps = {}
        
        with open(feature_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_scenario = None
        steps = []
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped or stripped.startswith('#') or stripped.startswith('@'):
                continue
            
            # New scenario
            if stripped.startswith('Scenario:') or stripped.startswith('Scenario Outline:'):
                # Save previous scenario
                if current_scenario:
                    scenario_steps[current_scenario] = steps
                
                # Start new scenario
                is_outline = stripped.startswith('Scenario Outline:')
                prefix_len = 17 if is_outline else 9
                current_scenario = stripped[prefix_len:].strip()
                steps = []
                continue
            
            # Extract steps (Given, When, Then, And, But)
            step_keywords = ['Given', 'When', 'Then', 'And', 'But']
            for keyword in step_keywords:
                if stripped.startswith(keyword):
                    step_text = stripped[len(keyword):].strip()
                    steps.append(f"{keyword} {step_text}")
                    break
        
        # Save last scenario
        if current_scenario:
            scenario_steps[current_scenario] = steps
        
        return scenario_steps


class SeleniumBehaveDetector:
    """
    Detector for Selenium + Behave projects.
    
    Identifies if a project uses Selenium with Behave BDD framework.
    """
    
    @staticmethod
    def detect(project_root: str) -> bool:
        """
        Detect if project uses Selenium + Behave.
        
        Args:
            project_root: Root directory to check
        
        Returns:
            True if Selenium + Behave project detected
        """
        root = Path(project_root)
        
        # Check for features directory (Behave convention)
        features_dir = root / "features"
        has_features = features_dir.exists() and features_dir.is_dir()
        
        # Check for .feature files
        has_feature_files = False
        if has_features:
            feature_files = list(features_dir.rglob("*.feature"))
            has_feature_files = len(feature_files) > 0
        
        # Check for steps directory
        has_steps = (features_dir / "steps").exists() if has_features else False
        
        # Check for environment.py (Behave hooks)
        has_environment = (features_dir / "environment.py").exists() if has_features else False
        
        # Check for Selenium in steps or environment
        has_selenium = False
        if has_steps or has_environment:
            files_to_check = []
            
            if has_steps:
                steps_dir = features_dir / "steps"
                files_to_check.extend(list(steps_dir.rglob("*.py")))
            
            if has_environment:
                files_to_check.append(features_dir / "environment.py")
            
            for file_path in files_to_check[:5]:  # Check first 5 files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'from selenium' in content or 'import selenium' in content:
                            has_selenium = True
                            break
                except (IOError, UnicodeDecodeError) as e:
                    logger.debug(f"Failed to read step file: {e}")
                    continue
        
        # Check requirements
        if not has_selenium:
            for req_file in ['requirements.txt', 'requirements-test.txt']:
                req_path = root / req_file
                if req_path.exists():
                    try:
                        with open(req_path, 'r') as f:
                            content = f.read().lower()
                            if 'selenium' in content and 'behave' in content:
                                has_selenium = True
                                break
                    except (IOError, UnicodeDecodeError) as e:
                        logger.debug(f"Failed to read requirements file: {e}")
                        continue
        
        return (has_features or has_feature_files) and (has_steps or has_environment or has_selenium)
