"""
Selenium + C# (.NET) + SpecFlow + NUnit Adapter for CrossBridge.

This adapter provides comprehensive support for C# BDD tests using:
- Selenium WebDriver for browser automation
- SpecFlow for BDD/Gherkin scenarios
- NUnit (or MSTest/xUnit) as test runner
- .NET SDK for project management

Key Features:
- Auto-detection of SpecFlow projects
- Gherkin feature file parsing
- C# step definition extraction
- NUnit test execution integration
- Page Object pattern support
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
class SpecFlowProjectConfig:
    """Configuration for detected SpecFlow project."""
    project_file: Path
    test_framework: DotNetTestFramework
    features_dir: Path
    step_definitions_dir: Path
    project_root: Path
    has_selenium: bool = True
    specflow_version: Optional[str] = None


class SpecFlowProjectDetector:
    """Detects SpecFlow projects in .NET solutions."""
    
    def __init__(self, project_root: str):
        """
        Initialize detector.
        
        Args:
            project_root: Root directory of the project to detect
        """
        self.project_root = Path(project_root)
    
    def detect(self) -> Optional[SpecFlowProjectConfig]:
        """
        Auto-detect SpecFlow project configuration.
        
        Returns:
            SpecFlowProjectConfig if detected, None otherwise
        """
        # Find .csproj files
        csproj_files = list(self.project_root.rglob("*.csproj"))
        
        for csproj in csproj_files:
            config = self._analyze_csproj(csproj)
            if config:
                return config
        
        return None
    
    def _analyze_csproj(self, csproj: Path) -> Optional[SpecFlowProjectConfig]:
        """Analyze a .csproj file for SpecFlow configuration."""
        try:
            content = csproj.read_text(encoding='utf-8')
            
            # Check for SpecFlow package
            if "SpecFlow" not in content:
                return None
            
            # Check for Selenium
            has_selenium = "Selenium.WebDriver" in content or "Selenium.Support" in content
            
            # Detect test framework
            test_framework = self._detect_test_framework(content)
            if not test_framework:
                return None
            
            # Extract SpecFlow version
            specflow_version = self._extract_specflow_version(content)
            
            # Find features directory
            project_dir = csproj.parent
            features_dir = self._find_features_dir(project_dir)
            
            # Find step definitions directory
            step_defs_dir = self._find_step_definitions_dir(project_dir)
            
            return SpecFlowProjectConfig(
                project_file=csproj,
                test_framework=test_framework,
                features_dir=features_dir,
                step_definitions_dir=step_defs_dir,
                project_root=project_dir,
                has_selenium=has_selenium,
                specflow_version=specflow_version
            )
        
        except Exception as e:
            print(f"Warning: Error analyzing {csproj}: {e}")
            return None
    
    def _detect_test_framework(self, content: str) -> Optional[DotNetTestFramework]:
        """Detect which test framework is used."""
        if "nunit" in content.lower():
            return DotNetTestFramework.NUNIT
        elif "mstest" in content.lower():
            return DotNetTestFramework.MSTEST
        elif "xunit" in content.lower():
            return DotNetTestFramework.XUNIT
        return None
    
    def _extract_specflow_version(self, content: str) -> Optional[str]:
        """Extract SpecFlow version from project file."""
        # Look for PackageReference with SpecFlow
        match = re.search(r'<PackageReference\s+Include="SpecFlow[^"]*"\s+Version="([^"]+)"', content)
        if match:
            return match.group(1)
        return None
    
    def _find_features_dir(self, project_dir: Path) -> Path:
        """Find features directory."""
        candidates = [
            project_dir / "Features",
            project_dir / "features",
            project_dir / "Specs",
            project_dir / "specs",
        ]
        
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate
        
        # Check for any .feature files
        feature_files = list(project_dir.rglob("*.feature"))
        if feature_files:
            return feature_files[0].parent
        
        # Default to Features subdirectory
        return project_dir / "Features"
    
    def _find_step_definitions_dir(self, project_dir: Path) -> Path:
        """Find step definitions directory."""
        candidates = [
            project_dir / "StepDefinitions",
            project_dir / "Steps",
            project_dir / "step_definitions",
        ]
        
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate
        
        # Check for files with [Binding] attribute
        cs_files = list(project_dir.rglob("*Steps.cs"))
        if cs_files:
            return cs_files[0].parent
        
        # Default to StepDefinitions subdirectory
        return project_dir / "StepDefinitions"


class SpecFlowFeatureParser:
    """Parse SpecFlow/Gherkin feature files."""
    
    def parse_feature(self, feature_file: Path) -> Dict:
        """
        Parse a feature file.
        
        Args:
            feature_file: Path to .feature file
            
        Returns:
            Dictionary with feature metadata
        """
        try:
            content = feature_file.read_text(encoding='utf-8')
            
            feature_name = self._extract_feature_name(content)
            scenarios = self._extract_scenarios(content)
            tags = self._extract_tags(content)
            
            return {
                'file': str(feature_file),
                'feature': feature_name,
                'scenarios': scenarios,
                'tags': tags
            }
        
        except Exception as e:
            print(f"Warning: Error parsing {feature_file}: {e}")
            return {
                'file': str(feature_file),
                'feature': feature_file.stem,
                'scenarios': [],
                'tags': []
            }
    
    def _extract_feature_name(self, content: str) -> str:
        """Extract feature name from content."""
        match = re.search(r'^Feature:\s*(.+)$', content, re.MULTILINE)
        return match.group(1).strip() if match else "Unknown Feature"
    
    def _extract_scenarios(self, content: str) -> List[Dict]:
        """Extract scenarios from content."""
        scenarios = []
        
        # Match Scenario or Scenario Outline
        pattern = r'^\s*(Scenario|Scenario Outline):\s*(.+)$'
        
        for match in re.finditer(pattern, content, re.MULTILINE):
            scenario_type = match.group(1)
            scenario_name = match.group(2).strip()
            
            scenarios.append({
                'type': scenario_type,
                'name': scenario_name
            })
        
        return scenarios
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content."""
        tags = []
        
        # Match @tag patterns
        for match in re.finditer(r'@(\w+)', content):
            tag = match.group(1)
            if tag not in tags:
                tags.append(tag)
        
        return tags


class SpecFlowStepDefinitionParser:
    """Parse C# step definition files."""
    
    def parse_step_definitions(self, cs_file: Path) -> List[Dict]:
        """
        Parse step definitions from C# file.
        
        Args:
            cs_file: Path to .cs file
            
        Returns:
            List of step definitions
        """
        try:
            content = cs_file.read_text(encoding='utf-8')
            
            step_defs = []
            
            # Match [Given], [When], [Then] attributes - handle escaped quotes with \\ 
            pattern = r'\[(Given|When|Then)\(@"((?:[^"\\]|\\.)*)"\)\]\s*public\s+(?:void|Task|async\s+Task)\s+(\w+)\('
            
            for match in re.finditer(pattern, content, re.DOTALL):
                keyword = match.group(1)
                pattern_text = match.group(2)
                method_name = match.group(3)
                
                step_defs.append({
                    'keyword': keyword,
                    'pattern': pattern_text,
                    'method': method_name,
                    'file': str(cs_file)
                })
            
            return step_defs
        
        except Exception as e:
            print(f"Warning: Error parsing {cs_file}: {e}")
            return []


class SeleniumSpecFlowAdapter(BaseTestAdapter):
    """
    Adapter for Selenium + SpecFlow + NUnit (.NET) tests.
    
    Provides unified discovery and execution for C# BDD tests.
    """
    
    def __init__(self, project_root: str, config: Optional[SpecFlowProjectConfig] = None):
        """
        Initialize adapter.
        
        Args:
            project_root: Root directory of the project
            config: Pre-detected configuration (optional)
        """
        self.project_root = Path(project_root)
        
        if config is None:
            detector = SpecFlowProjectDetector(str(self.project_root))
            config = detector.detect()
            
            if config is None:
                raise ValueError(
                    f"Could not detect SpecFlow project in {project_root}. "
                    "Ensure SpecFlow and a test framework (NUnit/MSTest/xUnit) are configured."
                )
        
        self.config = config
    
    def discover_tests(self) -> List[str]:
        """
        Discover all SpecFlow tests.
        
        Returns:
            List of test identifiers (scenario names)
        """
        tests = []
        
        try:
            # Parse all feature files
            feature_files = list(self.config.features_dir.rglob("*.feature"))
            
            parser = SpecFlowFeatureParser()
            
            for feature_file in feature_files:
                feature_data = parser.parse_feature(feature_file)
                
                for scenario in feature_data['scenarios']:
                    # Create test identifier
                    test_id = f"{feature_data['feature']}.{scenario['name']}"
                    tests.append(test_id)
        
        except Exception as e:
            print(f"Warning: Error discovering tests: {e}")
        
        return tests
    
    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestResult]:
        """
        Execute SpecFlow tests using dotnet test.
        
        Args:
            tests: List of test names to run (None = all tests)
            tags: List of SpecFlow tags to filter by
            
        Returns:
            List of test results
        """
        results = []
        
        try:
            # Build dotnet test command
            cmd = ["dotnet", "test", str(self.config.project_file)]
            
            # Add filter for specific tests
            if tests:
                # Convert test names to filter format
                test_filter = " | ".join([f"FullyQualifiedName~{test}" for test in tests])
                cmd.extend(["--filter", test_filter])
            
            # Add tag filtering
            if tags:
                # SpecFlow uses Category for tags
                tag_filter = " | ".join([f"Category={tag}" for tag in tags])
                if tests:
                    cmd[-1] = f"({cmd[-1]}) & ({tag_filter})"
                else:
                    cmd.extend(["--filter", tag_filter])
            
            # Add logger for structured output
            cmd.extend(["--logger", "trx"])
            
            # Execute tests
            import time
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse results
            results = self._parse_trx_results(self.config.project_root)
            
            # If no TRX found, create summary result
            if not results:
                status = "pass" if result.returncode == 0 else "fail"
                results.append(TestResult(
                    name="SpecFlow test suite",
                    status=status,
                    duration_ms=duration_ms,
                    message=result.stdout[:200] if result.stdout else ""
                ))
        
        except subprocess.TimeoutExpired:
            results.append(TestResult(
                name="SpecFlow tests",
                status="fail",
                duration_ms=300000,
                message="Test execution timed out"
            ))
        except Exception as e:
            print(f"Warning: Error running tests: {e}")
            results.append(TestResult(
                name="SpecFlow tests",
                status="fail",
                duration_ms=0,
                message=str(e)
            ))
        
        return results
    
    def _parse_trx_results(self, project_dir: Path) -> List[TestResult]:
        """Parse TRX (Visual Studio Test Results) file."""
        results = []
        
        try:
            # Find TRX files in TestResults directory
            trx_files = list(project_dir.rglob("TestResults/*.trx"))
            
            if not trx_files:
                return []
            
            # Parse most recent TRX
            trx_file = max(trx_files, key=lambda p: p.stat().st_mtime)
            
            tree = ET.parse(trx_file)
            root = tree.getroot()
            
            # Parse namespace
            ns = {'': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
            
            # Find all test results
            for test_result in root.findall('.//UnitTestResult', ns):
                name = test_result.get('testName', 'Unknown')
                outcome = test_result.get('outcome', 'Failed')
                duration = test_result.get('duration', '00:00:00')
                
                # Parse duration
                duration_ms = self._parse_duration(duration)
                
                # Map outcome to status
                status_map = {
                    'Passed': 'pass',
                    'Failed': 'fail',
                    'NotExecuted': 'skip',
                    'Inconclusive': 'skip'
                }
                status = status_map.get(outcome, 'fail')
                
                # Get error message if failed
                message = ""
                error_info = test_result.find('.//ErrorInfo', ns)
                if error_info is not None:
                    msg_elem = error_info.find('.//Message', ns)
                    if msg_elem is not None:
                        message = msg_elem.text or ""
                
                results.append(TestResult(
                    name=name,
                    status=status,
                    duration_ms=duration_ms,
                    message=message
                ))
        
        except Exception as e:
            print(f"Warning: Error parsing TRX results: {e}")
        
        return results
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string like '00:00:01.234' to milliseconds."""
        try:
            parts = duration_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
            return int(total_ms)
        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse duration: {e}")
            return 0
    
    def get_config_info(self) -> Dict[str, str]:
        """Get configuration information."""
        return {
            'project_file': str(self.config.project_file),
            'test_framework': self.config.test_framework.value,
            'features_dir': str(self.config.features_dir),
            'step_definitions_dir': str(self.config.step_definitions_dir),
            'has_selenium': str(self.config.has_selenium),
            'specflow_version': self.config.specflow_version or 'Unknown'
        }


class SeleniumSpecFlowExtractor(BaseTestExtractor):
    """
    Extract test metadata from SpecFlow projects.
    
    This is the read-only extractor for static analysis without execution.
    """
    
    def __init__(self, project_root: str):
        """
        Initialize extractor.
        
        Args:
            project_root: Root directory of SpecFlow project
        """
        self.project_root = Path(project_root)
        detector = SpecFlowProjectDetector(str(self.project_root))
        self.config = detector.detect()
        
        if self.config is None:
            raise ValueError(f"Could not detect SpecFlow project in {project_root}")
    
    def extract_tests(self) -> List[TestMetadata]:
        """
        Extract test metadata from SpecFlow feature files.
        
        Returns:
            List of TestMetadata objects
        """
        tests = []
        
        try:
            # Parse all feature files
            feature_files = list(self.config.features_dir.rglob("*.feature"))
            
            parser = SpecFlowFeatureParser()
            
            for feature_file in feature_files:
                feature_data = parser.parse_feature(feature_file)
                
                for scenario in feature_data['scenarios']:
                    test_name = f"{feature_data['feature']}.{scenario['name']}"
                    
                    tests.append(TestMetadata(
                        test_name=test_name,
                        file_path=str(feature_file),
                        tags=feature_data['tags'],
                        framework=f"specflow-{self.config.test_framework.value}",
                        test_type="bdd",
                        language="csharp"
                    ))
        
        except Exception as e:
            print(f"Warning: Error extracting tests: {e}")
        
        return tests
    
    def extract_step_definitions(self) -> List[Dict]:
        """
        Extract step definitions from C# files.
        
        Returns:
            List of step definition metadata
        """
        step_defs = []
        
        try:
            # Find all C# files with step definitions
            cs_files = list(self.config.step_definitions_dir.rglob("*Steps.cs"))
            cs_files += list(self.config.step_definitions_dir.rglob("*StepDefinitions.cs"))
            
            parser = SpecFlowStepDefinitionParser()
            
            for cs_file in cs_files:
                defs = parser.parse_step_definitions(cs_file)
                step_defs.extend(defs)
        
        except Exception as e:
            print(f"Warning: Error extracting step definitions: {e}")
        
        return step_defs
    
    def extract_page_objects(self) -> List[Dict]:
        """
        Extract page object classes from C# files.
        
        Returns:
            List of page object metadata
        """
        page_objects = []
        
        try:
            # Find C# files with typical page object names
            patterns = ["*Page.cs", "*PageObject.cs", "*PO.cs"]
            
            for pattern in patterns:
                files = list(self.config.project_root.rglob(pattern))
                
                for cs_file in files:
                    content = cs_file.read_text(encoding='utf-8')
                    
                    # Extract class name
                    match = re.search(r'class\s+(\w+)', content)
                    if match:
                        class_name = match.group(1)
                        
                        # Check if it has Selenium imports
                        has_selenium = (
                            "using OpenQA.Selenium" in content or
                            "IWebDriver" in content or
                            "IWebElement" in content
                        )
                        
                        if has_selenium:
                            page_objects.append({
                                'class_name': class_name,
                                'file': str(cs_file),
                                'has_selenium': True
                            })
        
        except Exception as e:
            print(f"Warning: Error extracting page objects: {e}")
        
        return page_objects
