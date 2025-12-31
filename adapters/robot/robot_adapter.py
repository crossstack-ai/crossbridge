"""
Robot Framework adapter implementation for CrossBridge.

This adapter translates between Robot Framework test structure and the
framework-agnostic internal model.
"""

import subprocess
import time
import json
import tempfile
import re
from pathlib import Path
from typing import List, Optional
from xml.etree import ElementTree as ET

from adapters.common.base import BaseTestAdapter, TestResult
from adapters.common.models import TestMetadata
from .config import RobotConfig


class RobotAdapter(BaseTestAdapter):
    """
    Adapter for Robot Framework.
    
    Translates Robot Framework tests to and from the framework-agnostic internal model.
    """

    def __init__(self, project_root: str, config: Optional[RobotConfig] = None):
        """
        Initialize Robot Framework adapter.
        
        Args:
            project_root: Root directory of the project
            config: Optional RobotConfig, defaults to sensible values
        """
        self.project_root = Path(project_root)
        self.config = config or RobotConfig(
            tests_path=str(self.project_root / "tests"),
            pythonpath=str(self.project_root)
        )

    def discover_tests(self) -> List[str]:
        """
        Robot does not have a native 'list tests' command,
        so we rely on --dryrun + output.xml parsing.
        """
        output_dir = tempfile.mkdtemp()

        cmd = [
            "robot",
            "--dryrun",
            "--output", f"{output_dir}/output.xml",
            "--log", "NONE",
            "--report", "NONE",
            "--pythonpath", self.config.pythonpath,
            self.config.tests_path
        ]

        try:
            subprocess.run(cmd, check=False, capture_output=True, timeout=30)
            
            output_xml = Path(output_dir) / "output.xml"
            if output_xml.exists():
                return self._parse_test_names(output_xml)
            else:
                print(f"Warning: No output.xml generated. Robot may not have found any test files in {self.config.tests_path}")
                return []
                
        except subprocess.TimeoutExpired:
            print("Warning: Robot Framework test discovery timed out")
            return []
        except FileNotFoundError:
            print("Warning: Robot Framework not found. Please ensure robot is installed (pip install robotframework)")
            return []
        except Exception as e:
            print(f"Warning: Error discovering Robot tests: {e}")
            return []

    def run_tests(
        self,
        tests: List[str] = None,
        tags: List[str] = None
    ) -> List[TestResult]:

        output_dir = tempfile.mkdtemp()
        start = time.time()

        cmd = [
            "robot",
            "--output", f"{output_dir}/output.xml",
            "--log", f"{output_dir}/log.html",
            "--report", "NONE",
            "--pythonpath", self.config.pythonpath,
        ]

        if tests:
            for test in tests:
                cmd += ["--test", test]

        if tags:
            for tag in tags:
                cmd += ["--include", tag]

        cmd.append(self.config.tests_path)

        try:
            subprocess.run(cmd, check=False, capture_output=True, timeout=300)
            
            output_xml = Path(output_dir) / "output.xml"
            if output_xml.exists():
                return self._parse_results(output_xml)
            else:
                duration_ms = int((time.time() - start) * 1000)
                print(f"Warning: No output.xml generated. Robot may not have found any test files in {self.config.tests_path}")
                return [TestResult(
                    name="Robot Suite",
                    status="fail",
                    duration_ms=duration_ms,
                    message=f"No tests found in {self.config.tests_path}"
                )]
                
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start) * 1000)
            return [TestResult(
                name="Robot Suite",
                status="fail",
                duration_ms=duration_ms,
                message="Test execution timed out"
            )]
        except FileNotFoundError:
            return [TestResult(
                name="Robot Suite",
                status="fail",
                duration_ms=0,
                message="Robot Framework not found. Please ensure robot is installed."
            )]
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            return [TestResult(
                name="Robot Suite",
                status="fail",
                duration_ms=duration_ms,
                message=f"Error executing tests: {str(e)}"
            )]

    def _parse_test_names(self, output_xml: Path) -> List[str]:
        tree = ET.parse(output_xml)
        root = tree.getroot()

        tests = []
        for test in root.iter("test"):
            tests.append(test.attrib.get("name"))

        return tests

    def _parse_results(self, output_xml: Path) -> List[TestResult]:
        tree = ET.parse(output_xml)
        root = tree.getroot()

        results = []

        for test in root.iter("test"):
            name = test.attrib.get("name")
            status_node = test.find("status")

            status = status_node.attrib.get("status").lower()
            elapsed = int(float(status_node.attrib.get("elapsedtime", 0)))

            message = status_node.text or ""

            results.append(
                TestResult(
                    name=name,
                    status=status,
                    duration_ms=elapsed,
                    message=message.strip()
                )
            )

        return results


class RobotExtractor:
    """
    Extractor for Robot Framework tests.
    
    Parses .robot files to extract metadata without execution.
    """
    
    def __init__(self, project_root: str):
        """
        Initialize extractor.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
    
    def extract_tests(self) -> List[TestMetadata]:
        """
        Extract test metadata from .robot files.
        
        Returns:
            List of TestMetadata objects
        """
        tests = []
        
        # Find all .robot files
        robot_files = list(self.project_root.rglob("*.robot"))
        
        for robot_file in robot_files:
            # Skip files in output directories
            if any(part.startswith('.') or part in ['output', 'results', 'logs'] 
                   for part in robot_file.parts):
                continue
            
            try:
                file_tests = self._parse_robot_file(robot_file)
                tests.extend(file_tests)
            except Exception as e:
                print(f"Warning: Failed to parse {robot_file}: {e}")
                continue
        
        return tests
    
    def _parse_robot_file(self, file_path: Path) -> List[TestMetadata]:
        """Parse a single .robot file."""
        tests = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse test cases
        in_test_cases = False
        in_test = False
        current_test = None
        current_tags = []
        suite_tags = []
        
        for line in content.split('\n'):
            stripped = line.strip()
            
            # Check for Force Tags (suite-level tags)
            if stripped.startswith('Force Tags'):
                tags_str = stripped[10:].strip()
                suite_tags = [t.strip() for t in tags_str.split() if t.strip()]
                continue
            
            # Check for Test Cases section
            if stripped.startswith('*** Test Cases ***'):
                in_test_cases = True
                continue
            
            # Check for other sections (end of Test Cases)
            if stripped.startswith('***') and 'Test Cases' not in stripped:
                in_test_cases = False
                # Save current test if any
                if current_test:
                    all_tags = list(set(suite_tags + current_tags))
                    tests.append(TestMetadata(
                        framework="robot",
                        test_name=current_test,
                        file_path=str(file_path),
                        tags=all_tags,
                        test_type="robot",
                        language="robot"
                    ))
                    current_test = None
                    current_tags = []
                continue
            
            if not in_test_cases or not stripped:
                continue
            
            # Check if line starts a new test (not indented)
            if not line.startswith(' ') and not line.startswith('\t') and stripped:
                # Save previous test
                if current_test:
                    all_tags = list(set(suite_tags + current_tags))
                    tests.append(TestMetadata(
                        framework="robot",
                        test_name=current_test,
                        file_path=str(file_path),
                        tags=all_tags,
                        test_type="robot",
                        language="robot"
                    ))
                
                # Start new test
                current_test = stripped
                current_tags = []
                in_test = True
                continue
            
            # Check for tags within test
            if in_test and stripped.startswith('[Tags]'):
                tags_str = stripped[6:].strip()
                current_tags = [t.strip() for t in tags_str.split() if t.strip()]
        
        # Save last test
        if current_test:
            all_tags = list(set(suite_tags + current_tags))
            tests.append(TestMetadata(
                framework="robot",
                test_name=current_test,
                file_path=str(file_path),
                tags=all_tags,
                test_type="robot",
                language="robot"
            ))
        
        return tests


class RobotDetector:
    """
    Detector for Robot Framework projects.
    
    Identifies if a project uses Robot Framework.
    """
    
    @staticmethod
    def detect(project_root: str) -> bool:
        """
        Detect if project uses Robot Framework.
        
        Args:
            project_root: Root directory to check
        
        Returns:
            True if Robot Framework project detected
        """
        root = Path(project_root)
        
        # Check for .robot files
        robot_files = list(root.rglob("*.robot"))
        has_robot_files = len(robot_files) > 0
        
        # Check for requirements
        has_robot_requirement = False
        for req_file in ['requirements.txt', 'requirements-test.txt', 'test-requirements.txt']:
            req_path = root / req_file
            if req_path.exists():
                try:
                    with open(req_path, 'r') as f:
                        content = f.read().lower()
                        if 'robotframework' in content or 'robot-framework' in content:
                            has_robot_requirement = True
                            break
                except:
                    continue
        
        # Check for robot configuration files
        has_robot_config = any([
            (root / "robot.yaml").exists(),
            (root / "robot.yml").exists(),
            (root / ".robot").exists(),
        ])
        
        return has_robot_files or (has_robot_requirement and has_robot_config)
