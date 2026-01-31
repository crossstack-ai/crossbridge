"""
Selenium .NET Adapter for CrossBridge.

This adapter provides comprehensive support for pure Selenium .NET tests using:
- Selenium WebDriver for browser automation
- NUnit, MSTest, or xUnit as test runners
- .NET SDK for project management
- Page Object pattern support

Key Features:
- Auto-detection of Selenium .NET projects
- Support for NUnit, MSTest, xUnit test frameworks
- C# test class and method extraction
- Page Object pattern support
- Test discovery and execution
- Failure classification (Gap 5.2)

Note: This is separate from the selenium_specflow_dotnet adapter which handles BDD/SpecFlow tests.
"""

import subprocess
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from ..common.base import BaseTestAdapter, TestResult, BaseTestExtractor
from ..common.models import TestMetadata


class DotNetTestFramework(Enum):
    """Supported .NET test frameworks."""
    NUNIT = "nunit"
    MSTEST = "mstest"
    XUNIT = "xunit"


@dataclass
class SeleniumDotNetProjectConfig:
    """Configuration for detected Selenium .NET project."""
    project_file: Path
    test_framework: DotNetTestFramework
    project_root: Path
    tests_dir: Path
    page_objects_dir: Optional[Path] = None
    selenium_version: Optional[str] = None
    target_framework: Optional[str] = None


class SeleniumDotNetProjectDetector:
    """Detects Selenium .NET projects."""
    
    def __init__(self, project_root: str):
        """
        Initialize detector.
        
        Args:
            project_root: Root directory of the project to detect
        """
        self.project_root = Path(project_root)
    
    def detect(self) -> Optional[SeleniumDotNetProjectConfig]:
        """
        Auto-detect Selenium .NET project configuration.
        
        Returns:
            SeleniumDotNetProjectConfig if detected, None otherwise
        """
        # Find .csproj files
        csproj_files = list(self.project_root.rglob("*.csproj"))
        
        for csproj in csproj_files:
            config = self._analyze_csproj(csproj)
            if config:
                return config
        
        return None
    
    def _analyze_csproj(self, csproj: Path) -> Optional[SeleniumDotNetProjectConfig]:
        """Analyze a .csproj file for Selenium configuration."""
        try:
            content = csproj.read_text(encoding='utf-8')
            
            # Check for Selenium WebDriver
            if "Selenium.WebDriver" not in content:
                return None
            
            # Exclude SpecFlow projects (they have their own adapter)
            if "SpecFlow" in content:
                return None
            
            # Detect test framework
            test_framework = self._detect_test_framework(content)
            if not test_framework:
                return None
            
            # Extract Selenium version
            selenium_version = self._extract_selenium_version(content)
            
            # Extract target framework
            target_framework = self._extract_target_framework(content)
            
            # Find tests directory
            project_dir = csproj.parent
            tests_dir = self._find_tests_dir(project_dir)
            
            # Find page objects directory (optional)
            page_objects_dir = self._find_page_objects_dir(project_dir)
            
            return SeleniumDotNetProjectConfig(
                project_file=csproj,
                test_framework=test_framework,
                project_root=project_dir,
                tests_dir=tests_dir,
                page_objects_dir=page_objects_dir,
                selenium_version=selenium_version,
                target_framework=target_framework
            )
        
        except Exception as e:
            print(f"Warning: Error analyzing {csproj}: {e}")
            return None
    
    def _detect_test_framework(self, content: str) -> Optional[DotNetTestFramework]:
        """Detect which test framework is used."""
        content_lower = content.lower()
        
        if "nunit" in content_lower:
            return DotNetTestFramework.NUNIT
        elif "mstest" in content_lower:
            return DotNetTestFramework.MSTEST
        elif "xunit" in content_lower:
            return DotNetTestFramework.XUNIT
        
        return None
    
    def _extract_selenium_version(self, content: str) -> Optional[str]:
        """Extract Selenium version from project file."""
        match = re.search(r'<PackageReference\s+Include="Selenium\.WebDriver"\s+Version="([^"]+)"', content)
        if match:
            return match.group(1)
        return None
    
    def _extract_target_framework(self, content: str) -> Optional[str]:
        """Extract target framework (e.g., net6.0, net7.0, net8.0)."""
        match = re.search(r'<TargetFramework>([^<]+)</TargetFramework>', content)
        if match:
            return match.group(1)
        return None
    
    def _find_tests_dir(self, project_dir: Path) -> Path:
        """Find tests directory."""
        candidates = [
            project_dir / "Tests",
            project_dir / "tests",
            project_dir / "Test",
            project_dir / "test",
            project_dir,  # Tests might be in root
        ]
        
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                # Check if it contains .cs files with test attributes
                cs_files = list(candidate.glob("*.cs"))
                if cs_files:
                    for cs_file in cs_files:
                        content = cs_file.read_text(encoding='utf-8', errors='ignore')
                        if any(attr in content for attr in ["[Test]", "[TestMethod]", "[Fact]"]):
                            return candidate
        
        # Default to project root
        return project_dir
    
    def _find_page_objects_dir(self, project_dir: Path) -> Optional[Path]:
        """Find Page Objects directory."""
        candidates = [
            project_dir / "PageObjects",
            project_dir / "Pages",
            project_dir / "PageModels",
            project_dir / "page_objects",
            project_dir / "pages",
        ]
        
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate
        
        return None


class SeleniumDotNetAdapter(BaseTestAdapter):
    """
    Adapter for Selenium .NET tests (non-BDD).
    
    Supports NUnit, MSTest, and xUnit test frameworks with Selenium WebDriver.
    """
    
    def __init__(self, project_root: str, config: Optional[SeleniumDotNetProjectConfig] = None):
        """
        Initialize Selenium .NET adapter.
        
        Args:
            project_root: Root directory of the project
            config: Optional SeleniumDotNetProjectConfig, auto-detected if not provided
        """
        self.project_root = Path(project_root)
        
        if config:
            self.config = config
        else:
            detector = SeleniumDotNetProjectDetector(str(self.project_root))
            detected = detector.detect()
            if not detected:
                raise ValueError(f"No Selenium .NET project detected in {project_root}")
            self.config = detected
    
    def discover_tests(self) -> List[str]:
        """
        Discover all tests in the project using dotnet test --list-tests.
        
        Returns:
            List of fully qualified test names
        """
        try:
            # Use dotnet test --list-tests
            result = subprocess.run(
                ["dotnet", "test", str(self.config.project_file), "--list-tests"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"Warning: Test discovery failed: {result.stderr}")
                return []
            
            # Parse output for test names
            tests = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                # Test names are typically indented and fully qualified
                if line and not line.startswith('The following') and '.' in line:
                    # Remove leading/trailing whitespace and filter valid test names
                    if '(' not in line or line.endswith(')'):  # Valid test method
                        tests.append(line)
            
            return tests
        
        except subprocess.TimeoutExpired:
            print("Warning: Test discovery timed out")
            return []
        except FileNotFoundError:
            print("Warning: dotnet CLI not found. Please ensure .NET SDK is installed")
            return []
        except Exception as e:
            print(f"Warning: Error discovering tests: {e}")
            return []
    
    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestResult]:
        """
        Run tests using dotnet test.
        
        Args:
            tests: Optional list of specific test names to run
            tags: Optional list of test categories/tags to filter
            
        Returns:
            List of TestResult objects
        """
        # Build command
        cmd = [
            "dotnet", "test",
            str(self.config.project_file),
            "--logger", "trx",
            "--results-directory", str(self.project_root / "TestResults")
        ]
        
        # Filter by specific tests
        if tests:
            for test in tests:
                cmd.extend(["--filter", f"FullyQualifiedName={test}"])
        
        # Filter by categories/tags
        if tags:
            tag_filter = "|".join([f"Category={tag}" for tag in tags])
            cmd.extend(["--filter", tag_filter])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse TRX results
            return self._parse_trx_results()
        
        except subprocess.TimeoutExpired:
            print("Warning: Test execution timed out")
            return []
        except Exception as e:
            print(f"Warning: Error running tests: {e}")
            return []
    
    def _parse_trx_results(self) -> List[TestResult]:
        """Parse .trx (Visual Studio Test Results) files."""
        results = []
        test_results_dir = self.project_root / "TestResults"
        
        if not test_results_dir.exists():
            return results
        
        # Find most recent .trx file
        trx_files = list(test_results_dir.glob("*.trx"))
        if not trx_files:
            return results
        
        latest_trx = max(trx_files, key=lambda p: p.stat().st_mtime)
        
        try:
            tree = ET.parse(latest_trx)
            root = tree.getroot()
            
            # Define namespace
            ns = {'': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
            
            # Parse test results
            for unit_test_result in root.findall('.//UnitTestResult', ns):
                test_name = unit_test_result.get('testName')
                outcome = unit_test_result.get('outcome')  # Passed, Failed, etc.
                duration = unit_test_result.get('duration')
                
                # Get error message if failed
                error_message = None
                stack_trace = None
                
                output_elem = unit_test_result.find('.//Output', ns)
                if output_elem is not None:
                    error_info = output_elem.find('.//ErrorInfo', ns)
                    if error_info is not None:
                        message_elem = error_info.find('.//Message', ns)
                        if message_elem is not None and message_elem.text:
                            error_message = message_elem.text
                        
                        stack_elem = error_info.find('.//StackTrace', ns)
                        if stack_elem is not None and stack_elem.text:
                            stack_trace = stack_elem.text
                
                # Convert outcome to status
                status = "passed" if outcome == "Passed" else "failed" if outcome == "Failed" else "skipped"
                
                results.append(TestResult(
                    name=test_name,
                    status=status,
                    duration=self._parse_duration(duration),
                    error_message=error_message,
                    stack_trace=stack_trace,
                    metadata=TestMetadata()
                ))
        
        except Exception as e:
            print(f"Warning: Error parsing TRX file: {e}")
        
        return results
    
    def _parse_duration(self, duration_str: Optional[str]) -> float:
        """Parse duration string (HH:MM:SS.mmm) to seconds."""
        if not duration_str:
            return 0.0
        
        try:
            # Format: HH:MM:SS.mmm
            parts = duration_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            return 0.0


class SeleniumDotNetExtractor(BaseTestExtractor):
    """Extracts test information from Selenium .NET projects."""
    
    def __init__(self, project_root: str):
        """Initialize extractor."""
        self.project_root = Path(project_root)
    
    def extract_tests(self) -> List[Dict]:
        """Extract test metadata from C# source files."""
        tests = []
        
        # Find all .cs files
        for cs_file in self.project_root.rglob("*.cs"):
            file_tests = self._extract_tests_from_file(cs_file)
            tests.extend(file_tests)
        
        return tests
    
    def _extract_tests_from_file(self, cs_file: Path) -> List[Dict]:
        """Extract tests from a single C# file."""
        tests = []
        
        try:
            content = cs_file.read_text(encoding='utf-8', errors='ignore')
            
            # Extract namespace
            namespace_match = re.search(r'namespace\s+([\w.]+)', content)
            namespace = namespace_match.group(1) if namespace_match else None
            
            # Extract class name
            class_match = re.search(r'class\s+(\w+)', content)
            if not class_match:
                return tests
            
            class_name = class_match.group(1)
            
            # Find test methods
            # NUnit: [Test], [TestCase]
            # MSTest: [TestMethod]
            # xUnit: [Fact], [Theory]
            test_patterns = [
                (r'\[Test(?:Case)?\][\s\S]*?public\s+(?:async\s+)?(?:void|Task)\s+(\w+)', 'nunit'),
                (r'\[TestMethod\][\s\S]*?public\s+(?:async\s+)?(?:void|Task)\s+(\w+)', 'mstest'),
                (r'\[Fact\][\s\S]*?public\s+(?:async\s+)?(?:void|Task)\s+(\w+)', 'xunit'),
                (r'\[Theory\][\s\S]*?public\s+(?:async\s+)?(?:void|Task)\s+(\w+)', 'xunit'),
            ]
            
            for pattern, framework in test_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    method_name = match.group(1)
                    
                    # Build fully qualified name
                    fqn = f"{namespace}.{class_name}.{method_name}" if namespace else f"{class_name}.{method_name}"
                    
                    tests.append({
                        "name": method_name,
                        "fully_qualified_name": fqn,
                        "class_name": class_name,
                        "namespace": namespace,
                        "file": str(cs_file),
                        "framework": framework,
                    })
        
        except Exception as e:
            print(f"Warning: Error extracting tests from {cs_file}: {e}")
        
        return tests


__all__ = [
    'SeleniumDotNetAdapter',
    'SeleniumDotNetExtractor',
    'SeleniumDotNetProjectDetector',
    'SeleniumDotNetProjectConfig',
    'DotNetTestFramework',
]
