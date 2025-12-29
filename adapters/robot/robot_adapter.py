"""
Robot Framework adapter implementation for CrossBridge AI.

This adapter translates between Robot Framework test structure and the
framework-agnostic internal model.
"""

import subprocess
import time
import json
import tempfile
from pathlib import Path
from typing import List
from xml.etree import ElementTree as ET

from adapters.common.base import BaseTestAdapter, TestResult


class RobotAdapter(BaseTestAdapter):
    """
    Adapter for Robot Framework.
    
    Translates Robot Framework tests to and from the framework-agnostic internal model.
    """

    def __init__(self, config):
        self.config = config

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
