"""
Playwright Multi-Language Adapter for CrossBridge.

This adapter provides unified discovery and execution for Playwright tests
across all officially supported language bindings:
- JavaScript/TypeScript (@playwright/test)
- Python (pytest-playwright)
- Java (playwright-java)
- .NET (Microsoft.Playwright.NUnit or MSTest)

Key Features:
- Auto-detection of project language and test framework
- Unified test discovery across languages
- Execution support with result parsing
- Language-agnostic test metadata extraction
"""

import subprocess
import json
import time
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from ..common.base import BaseTestAdapter, TestResult, BaseTestExtractor
from ..common.models import TestMetadata


class PlaywrightLanguage(Enum):
    """Supported Playwright language bindings."""
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    JAVA = "java"
    DOTNET = "dotnet"


class PlaywrightTestFramework(Enum):
    """Test frameworks used with Playwright."""
    # JavaScript/TypeScript
    PLAYWRIGHT_TEST = "playwright-test"  # @playwright/test
    
    # Python
    PYTEST_PLAYWRIGHT = "pytest-playwright"
    
    # Java
    JUNIT_PLAYWRIGHT = "junit-playwright"
    TESTNG_PLAYWRIGHT = "testng-playwright"
    
    # .NET
    NUNIT_PLAYWRIGHT = "nunit-playwright"
    MSTEST_PLAYWRIGHT = "mstest-playwright"
    XUNIT_PLAYWRIGHT = "xunit-playwright"


@dataclass
class PlaywrightProjectConfig:
    """Configuration for detected Playwright project."""
    language: PlaywrightLanguage
    framework: PlaywrightTestFramework
    test_dir: Path
    config_file: Optional[Path] = None
    project_root: Path = None
    
    def __post_init__(self):
        if self.project_root is None:
            self.project_root = self.test_dir.parent


class PlaywrightProjectDetector:
    """Detects Playwright project language and framework."""
    
    def __init__(self, project_root: str):
        """
        Initialize detector.
        
        Args:
            project_root: Root directory of the project to detect
        """
        self.project_root = Path(project_root)
    
    def detect(self) -> Optional[PlaywrightProjectConfig]:
        """
        Auto-detect Playwright project configuration.
        
        Returns:
            PlaywrightProjectConfig if detected, None otherwise
        """
        # Try each detection method in order of specificity (TypeScript before JavaScript)
        detectors = [
            self._detect_playwright_test_ts,
            self._detect_playwright_test_js,
            self._detect_python_playwright,
            self._detect_java_playwright,
            self._detect_dotnet_playwright,
        ]
        
        for detector in detectors:
            config = detector()
            if config:
                return config
        
        return None
    
    def _detect_playwright_test_js(self) -> Optional[PlaywrightProjectConfig]:
        """Detect @playwright/test with JavaScript."""
        # Look for playwright.config.js or package.json with @playwright/test
        config_files = [
            self.project_root / "playwright.config.js",
            self.project_root / "playwright.config.mjs",
        ]
        
        config_file = next((f for f in config_files if f.exists()), None)
        
        # Check package.json
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    if "@playwright/test" in deps:
                        test_dir = self._find_test_directory(["tests", "e2e", "test"])
                        return PlaywrightProjectConfig(
                            language=PlaywrightLanguage.JAVASCRIPT,
                            framework=PlaywrightTestFramework.PLAYWRIGHT_TEST,
                            test_dir=test_dir,
                            config_file=config_file,
                            project_root=self.project_root
                        )
            except (OSError, json.JSONDecodeError) as e:
                # Skip files that can't be read or parsed
                pass
        
        return None
    
    def _detect_playwright_test_ts(self) -> Optional[PlaywrightProjectConfig]:
        """Detect @playwright/test with TypeScript."""
        config_files = [
            self.project_root / "playwright.config.ts",
            self.project_root / "playwright.config.mts",
        ]
        
        config_file = next((f for f in config_files if f.exists()), None)
        
        # Check for TypeScript config
        has_typescript = (self.project_root / "tsconfig.json").exists()
        
        # Check package.json
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    if "@playwright/test" in deps and (has_typescript or "typescript" in deps):
                        test_dir = self._find_test_directory(["tests", "e2e", "test"])
                        return PlaywrightProjectConfig(
                            language=PlaywrightLanguage.TYPESCRIPT,
                            framework=PlaywrightTestFramework.PLAYWRIGHT_TEST,
                            test_dir=test_dir,
                            config_file=config_file,
                            project_root=self.project_root
                        )
            except (IOError, UnicodeDecodeError, json.JSONDecodeError) as e:
                logger.debug(f"Failed to parse playwright config: {e}")
        
        return None
    
    def _detect_python_playwright(self) -> Optional[PlaywrightProjectConfig]:
        """Detect Python with pytest-playwright."""
        # Look for pytest.ini, pyproject.toml, or requirements.txt
        indicators = [
            self.project_root / "pytest.ini",
            self.project_root / "pyproject.toml",
            self.project_root / "requirements.txt",
            self.project_root / "setup.py",
        ]
        
        has_pytest_config = any(f.exists() for f in indicators)
        
        # Check for pytest-playwright installation
        try:
            result = subprocess.run(
                ["pip", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            has_playwright = "pytest-playwright" in result.stdout or "playwright" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"Failed to check pip packages: {e}")
            has_playwright = False
        
        # Look for Python test files with Playwright
        test_files = list(self.project_root.rglob("test_*.py")) + list(self.project_root.rglob("*_test.py"))
        
        for test_file in test_files[:5]:  # Check first few files
            try:
                content = test_file.read_text()
                if "playwright" in content.lower() or "from playwright" in content:
                    test_dir = test_file.parent
                    return PlaywrightProjectConfig(
                        language=PlaywrightLanguage.PYTHON,
                        framework=PlaywrightTestFramework.PYTEST_PLAYWRIGHT,
                        test_dir=test_dir,
                        config_file=None,
                        project_root=self.project_root
                    )
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to read Python test file: {e}")
                continue
        
        return None
    
    def _detect_java_playwright(self) -> Optional[PlaywrightProjectConfig]:
        """Detect Java with playwright-java."""
        # Look for Maven or Gradle
        pom_xml = self.project_root / "pom.xml"
        build_gradle = self.project_root / "build.gradle"
        
        if pom_xml.exists():
            try:
                content = pom_xml.read_text()
                if "com.microsoft.playwright" in content:
                    # Detect framework (JUnit vs TestNG)
                    if "junit-jupiter" in content or "junit" in content:
                        framework = PlaywrightTestFramework.JUNIT_PLAYWRIGHT
                    elif "testng" in content:
                        framework = PlaywrightTestFramework.TESTNG_PLAYWRIGHT
                    else:
                        framework = PlaywrightTestFramework.JUNIT_PLAYWRIGHT  # default
                    
                    test_dir = self._find_test_directory([
                        "src/test/java",
                        "src/it/java",
                        "test"
                    ])
                    
                    return PlaywrightProjectConfig(
                        language=PlaywrightLanguage.JAVA,
                        framework=framework,
                        test_dir=test_dir,
                        config_file=pom_xml,
                        project_root=self.project_root
                    )
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to read pom.xml: {e}")
        
        if build_gradle.exists():
            try:
                content = build_gradle.read_text()
                if "com.microsoft.playwright" in content or "playwright" in content:
                    # Detect framework
                    if "junit" in content.lower():
                        framework = PlaywrightTestFramework.JUNIT_PLAYWRIGHT
                    elif "testng" in content.lower():
                        framework = PlaywrightTestFramework.TESTNG_PLAYWRIGHT
                    else:
                        framework = PlaywrightTestFramework.JUNIT_PLAYWRIGHT
                    
                    test_dir = self._find_test_directory([
                        "src/test/java",
                        "test"
                    ])
                    
                    return PlaywrightProjectConfig(
                        language=PlaywrightLanguage.JAVA,
                        framework=framework,
                        test_dir=test_dir,
                        config_file=build.gradle,
                        project_root=self.project_root
                    )
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to read build.gradle: {e}")
        
        return None
    
    def _detect_dotnet_playwright(self) -> Optional[PlaywrightProjectConfig]:
        """Detect .NET with Microsoft.Playwright."""
        # Look for .csproj files
        csproj_files = list(self.project_root.rglob("*.csproj"))
        
        for csproj in csproj_files:
            try:
                content = csproj.read_text()
                if "Microsoft.Playwright" in content:
                    # Detect test framework
                    if "NUnit" in content:
                        framework = PlaywrightTestFramework.NUNIT_PLAYWRIGHT
                    elif "MSTest" in content:
                        framework = PlaywrightTestFramework.MSTEST_PLAYWRIGHT
                    elif "xunit" in content.lower():
                        framework = PlaywrightTestFramework.XUNIT_PLAYWRIGHT
                    else:
                        framework = PlaywrightTestFramework.NUNIT_PLAYWRIGHT  # default
                    
                    test_dir = csproj.parent
                    
                    return PlaywrightProjectConfig(
                        language=PlaywrightLanguage.DOTNET,
                        framework=framework,
                        test_dir=test_dir,
                        config_file=csproj,
                        project_root=self.project_root
                    )
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to read .csproj file: {e}")
                continue
        
        return None
    
    def _find_test_directory(self, candidates: List[str]) -> Path:
        """Find first existing test directory from candidates."""
        for candidate in candidates:
            test_dir = self.project_root / candidate
            if test_dir.exists() and test_dir.is_dir():
                return test_dir
        
        # Fallback to project root
        return self.project_root


class PlaywrightAdapter(BaseTestAdapter):
    """
    Unified Playwright adapter supporting all language bindings.
    
    Automatically detects project language and framework, then provides
    unified test discovery and execution.
    """
    
    def __init__(self, project_root: str, config: Optional[PlaywrightProjectConfig] = None):
        """
        Initialize Playwright adapter.
        
        Args:
            project_root: Root directory of the Playwright project
            config: Pre-detected configuration (optional, will auto-detect if None)
        """
        self.project_root = Path(project_root)
        
        if config is None:
            detector = PlaywrightProjectDetector(str(self.project_root))
            config = detector.detect()
            
            if config is None:
                raise ValueError(
                    f"Could not detect Playwright project in {project_root}. "
                    "Ensure Playwright is configured and dependencies are installed."
                )
        
        self.config = config
        self._executor = self._get_executor()
    
    def _get_executor(self):
        """Get language-specific executor."""
        if self.config.framework == PlaywrightTestFramework.PLAYWRIGHT_TEST:
            return PlaywrightTestExecutor(self.config)
        elif self.config.framework == PlaywrightTestFramework.PYTEST_PLAYWRIGHT:
            return PytestPlaywrightExecutor(self.config)
        elif self.config.framework in [
            PlaywrightTestFramework.JUNIT_PLAYWRIGHT,
            PlaywrightTestFramework.TESTNG_PLAYWRIGHT
        ]:
            return JavaPlaywrightExecutor(self.config)
        elif self.config.framework in [
            PlaywrightTestFramework.NUNIT_PLAYWRIGHT,
            PlaywrightTestFramework.MSTEST_PLAYWRIGHT,
            PlaywrightTestFramework.XUNIT_PLAYWRIGHT
        ]:
            return DotNetPlaywrightExecutor(self.config)
        else:
            raise ValueError(f"Unsupported framework: {self.config.framework}")
    
    def discover_tests(self) -> List[str]:
        """
        Discover all Playwright tests.
        
        Returns:
            List of test identifiers
        """
        return self._executor.discover_tests()
    
    def run_tests(
        self,
        tests: List[str] = None,
        tags: List[str] = None
    ) -> List[TestResult]:
        """
        Execute Playwright tests.
        
        Args:
            tests: List of test identifiers to run (None = all tests)
            tags: List of tags/markers to filter by
            
        Returns:
            List of test results
        """
        return self._executor.run_tests(tests, tags)
    
    def get_config_info(self) -> Dict[str, str]:
        """Get configuration information for debugging."""
        return {
            "language": self.config.language.value,
            "framework": self.config.framework.value,
            "test_dir": str(self.config.test_dir),
            "config_file": str(self.config.config_file) if self.config.config_file else None,
            "project_root": str(self.config.project_root)
        }


class PlaywrightTestExecutor:
    """Executor for @playwright/test (JavaScript/TypeScript)."""
    
    def __init__(self, config: PlaywrightProjectConfig):
        self.config = config
    
    def discover_tests(self) -> List[str]:
        """Discover tests using playwright test --list."""
        tests = []
        
        try:
            cmd = ["npx", "playwright", "test", "--list"]
            
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse test list output
            for line in result.stdout.split('\n'):
                line = line.strip()
                # Format: [chromium] › path/to/test.spec.ts:10:5 › Test Name
                if '›' in line:
                    # Extract test name (after last ›)
                    parts = line.split('›')
                    if len(parts) >= 2:
                        test_name = parts[-1].strip()
                        tests.append(test_name)
        
        except Exception as e:
            print(f"Warning: Error discovering Playwright tests: {e}")
        
        return tests
    
    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestResult]:
        """Run tests using playwright test."""
        results = []
        
        try:
            cmd = ["npx", "playwright", "test", "--reporter=json"]
            
            # Add grep filter for specific tests
            if tests:
                # Use grep to filter test names
                cmd.extend(["--grep", "|".join(tests)])
            
            # Add tag filtering
            if tags:
                for tag in tags:
                    cmd.extend(["--grep", f"@{tag}"])
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse JSON output
            try:
                report = json.loads(result.stdout)
                for suite in report.get("suites", []):
                    for spec in suite.get("specs", []):
                        test_name = spec.get("title", "unknown")
                        for test in spec.get("tests", []):
                            for result_item in test.get("results", []):
                                status_map = {
                                    "passed": "pass",
                                    "failed": "fail",
                                    "skipped": "skip",
                                    "timedOut": "fail"
                                }
                                status = status_map.get(result_item.get("status", ""), "fail")
                                
                                results.append(TestResult(
                                    name=test_name,
                                    status=status,
                                    duration_ms=result_item.get("duration", 0),
                                    message=result_item.get("error", {}).get("message", "")
                                ))
            except json.JSONDecodeError:
                # Fallback: overall status
                status = "pass" if result.returncode == 0 else "fail"
                results.append(TestResult(
                    name="playwright suite",
                    status=status,
                    duration_ms=duration_ms,
                    message=""
                ))
        
        except Exception as e:
            print(f"Warning: Error running Playwright tests: {e}")
        
        return results


class PytestPlaywrightExecutor:
    """Executor for pytest-playwright (Python)."""
    
    def __init__(self, config: PlaywrightProjectConfig):
        self.config = config
    
    def discover_tests(self) -> List[str]:
        """Discover tests using pytest --collect-only."""
        tests = []
        
        try:
            cmd = ["pytest", "--collect-only", "-q", str(self.config.test_dir)]
            
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if '::' in line and not line.startswith('='):
                    # Extract test name
                    test_name = line.split('::')[-1]
                    tests.append(test_name)
        
        except Exception as e:
            print(f"Warning: Error discovering pytest-playwright tests: {e}")
        
        return tests
    
    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestResult]:
        """Run tests using pytest."""
        results = []
        
        try:
            cmd = ["pytest", "-v", "--json-report", "--json-report-file=/tmp/report.json"]
            
            if tests:
                cmd.extend(["-k", " or ".join(tests)])
            
            if tags:
                for tag in tags:
                    cmd.extend(["-m", tag])
            
            cmd.append(str(self.config.test_dir))
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse output
            for line in result.stdout.split('\n'):
                if 'PASSED' in line or 'FAILED' in line or 'SKIPPED' in line:
                    if 'PASSED' in line:
                        status = 'pass'
                    elif 'FAILED' in line:
                        status = 'fail'
                    else:
                        status = 'skip'
                    
                    test_name = line.split('::')[-1].split()[0] if '::' in line else 'unknown'
                    
                    results.append(TestResult(
                        name=test_name,
                        status=status,
                        duration_ms=duration_ms // max(len(results) + 1, 1),
                        message=line.strip()
                    ))
        
        except Exception as e:
            print(f"Warning: Error running pytest-playwright tests: {e}")
        
        return results


class JavaPlaywrightExecutor:
    """Executor for Java Playwright (JUnit/TestNG)."""
    
    def __init__(self, config: PlaywrightProjectConfig):
        self.config = config
    
    def discover_tests(self) -> List[str]:
        """Discover tests using Maven or Gradle."""
        tests = []
        
        # Use Maven or Gradle depending on config
        if self.config.config_file and self.config.config_file.name == "pom.xml":
            tests = self._discover_maven()
        elif self.config.config_file and "gradle" in self.config.config_file.name:
            tests = self._discover_gradle()
        
        return tests
    
    def _discover_maven(self) -> List[str]:
        """Discover tests using Maven."""
        tests = []
        
        try:
            cmd = ["mvn", "test", "-DskipTests"]
            
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse test files from output or scan directory
            test_files = list(self.config.test_dir.rglob("*Test.java"))
            for test_file in test_files:
                # Extract class name
                class_name = test_file.stem
                tests.append(class_name)
        
        except Exception as e:
            print(f"Warning: Error discovering Maven tests: {e}")
        
        return tests
    
    def _discover_gradle(self) -> List[str]:
        """Discover tests using Gradle."""
        tests = []
        
        try:
            # Scan test directory
            test_files = list(self.config.test_dir.rglob("*Test.java"))
            for test_file in test_files:
                class_name = test_file.stem
                tests.append(class_name)
        
        except Exception as e:
            print(f"Warning: Error discovering Gradle tests: {e}")
        
        return tests
    
    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestResult]:
        """Run tests using Maven or Gradle."""
        if self.config.config_file and self.config.config_file.name == "pom.xml":
            return self._run_maven(tests, tags)
        elif self.config.config_file and "gradle" in self.config.config_file.name:
            return self._run_gradle(tests, tags)
        return []
    
    def _run_maven(
        self,
        tests: Optional[List[str]],
        tags: Optional[List[str]]
    ) -> List[TestResult]:
        """Run tests using Maven."""
        results = []
        
        try:
            cmd = ["mvn", "test"]
            
            if tests:
                # Filter by test class
                cmd.append(f"-Dtest={','.join(tests)}")
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse Maven output
            status = "pass" if result.returncode == 0 else "fail"
            results.append(TestResult(
                name="maven test suite",
                status=status,
                duration_ms=duration_ms,
                message=""
            ))
        
        except Exception as e:
            print(f"Warning: Error running Maven tests: {e}")
        
        return results
    
    def _run_gradle(
        self,
        tests: Optional[List[str]],
        tags: Optional[List[str]]
    ) -> List[TestResult]:
        """Run tests using Gradle."""
        results = []
        
        try:
            cmd = ["gradle", "test"]
            
            if tests:
                cmd.append(f"--tests={tests[0]}")
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            status = "pass" if result.returncode == 0 else "fail"
            results.append(TestResult(
                name="gradle test suite",
                status=status,
                duration_ms=duration_ms,
                message=""
            ))
        
        except Exception as e:
            print(f"Warning: Error running Gradle tests: {e}")
        
        return results


class DotNetPlaywrightExecutor:
    """Executor for .NET Playwright (NUnit/MSTest/xUnit)."""
    
    def __init__(self, config: PlaywrightProjectConfig):
        self.config = config
    
    def discover_tests(self) -> List[str]:
        """Discover tests using dotnet test --list-tests."""
        tests = []
        
        try:
            cmd = ["dotnet", "test", "--list-tests"]
            
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse test list
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('The following Tests'):
                    tests.append(line)
        
        except Exception as e:
            print(f"Warning: Error discovering .NET tests: {e}")
        
        return tests
    
    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestResult]:
        """Run tests using dotnet test."""
        results = []
        
        try:
            cmd = ["dotnet", "test"]
            
            if tests:
                cmd.extend(["--filter", f"FullyQualifiedName~{tests[0]}"])
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse output
            status = "pass" if result.returncode == 0 else "fail"
            results.append(TestResult(
                name="dotnet test suite",
                status=status,
                duration_ms=duration_ms,
                message=""
            ))
        
        except Exception as e:
            print(f"Warning: Error running .NET tests: {e}")
        
        return results


class PlaywrightExtractor(BaseTestExtractor):
    """
    Extract test metadata from Playwright tests across all languages.
    
    This is the read-only extractor for static analysis without execution.
    """
    
    def __init__(self, project_root: str):
        """
        Initialize extractor.
        
        Args:
            project_root: Root directory of Playwright project
        """
        self.project_root = Path(project_root)
        detector = PlaywrightProjectDetector(str(self.project_root))
        self.config = detector.detect()
        
        if self.config is None:
            raise ValueError(f"Could not detect Playwright project in {project_root}")
    
    def extract_tests(self) -> List[TestMetadata]:
        """
        Extract test metadata from Playwright test files.
        
        Returns:
            List of TestMetadata objects
        """
        tests = []
        
        # Get test files based on language
        test_files = self._get_test_files()
        
        for test_file in test_files:
            try:
                test_metadata = self._parse_test_file(test_file)
                tests.extend(test_metadata)
            except Exception as e:
                print(f"Warning: Error parsing {test_file}: {e}")
        
        return tests
    
    def _get_test_files(self) -> List[Path]:
        """Get test files based on detected language."""
        patterns = {
            PlaywrightLanguage.JAVASCRIPT: ["*.spec.js", "*.test.js"],
            PlaywrightLanguage.TYPESCRIPT: ["*.spec.ts", "*.test.ts"],
            PlaywrightLanguage.PYTHON: ["test_*.py", "*_test.py"],
            PlaywrightLanguage.JAVA: ["*Test.java"],
            PlaywrightLanguage.DOTNET: ["*Tests.cs", "*Test.cs"],
        }
        
        files = []
        for pattern in patterns.get(self.config.language, []):
            files.extend(self.config.test_dir.rglob(pattern))
        
        return files
    
    def _parse_test_file(self, test_file: Path) -> List[TestMetadata]:
        """Parse individual test file for test metadata."""
        tests = []
        
        try:
            content = test_file.read_text()
            
            # Language-specific parsing
            if self.config.language in [PlaywrightLanguage.JAVASCRIPT, PlaywrightLanguage.TYPESCRIPT]:
                tests = self._parse_js_ts_file(test_file, content)
            elif self.config.language == PlaywrightLanguage.PYTHON:
                tests = self._parse_python_file(test_file, content)
            elif self.config.language == PlaywrightLanguage.JAVA:
                tests = self._parse_java_file(test_file, content)
            elif self.config.language == PlaywrightLanguage.DOTNET:
                tests = self._parse_dotnet_file(test_file, content)
        
        except Exception as e:
            print(f"Warning: Error parsing {test_file}: {e}")
        
        return tests
    
    def _parse_js_ts_file(self, test_file: Path, content: str) -> List[TestMetadata]:
        """Parse JavaScript/TypeScript test file."""
        tests = []
        
        # Find test() or it() calls
        test_pattern = r"(?:test|it)\s*\(\s*['\"]([^'\"]+)['\"]"
        
        for match in re.finditer(test_pattern, content):
            test_name = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            
            tests.append(TestMetadata(
                test_name=test_name,
                file_path=str(test_file),
                tags=[],
                framework="playwright-test"
            ))
        
        return tests
    
    def _parse_python_file(self, test_file: Path, content: str) -> List[TestMetadata]:
        """Parse Python test file."""
        tests = []
        
        # Find test functions
        test_pattern = r"def\s+(test_\w+)\s*\("
        
        for match in re.finditer(test_pattern, content):
            test_name = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            
            tests.append(TestMetadata(
                test_name=test_name,
                file_path=str(test_file),
                tags=[],
                framework="pytest-playwright"
            ))
        
        return tests
    
    def _parse_java_file(self, test_file: Path, content: str) -> List[TestMetadata]:
        """Parse Java test file."""
        tests = []
        
        # Find @Test methods
        test_pattern = r"@Test.*?(?:public|private|protected)\s+void\s+(\w+)\s*\("
        
        for match in re.finditer(test_pattern, content, re.DOTALL):
            test_name = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            
            tests.append(TestMetadata(
                test_name=test_name,
                file_path=str(test_file),
                tags=[],
                framework="junit-playwright"
            ))
        
        return tests
    
    def _parse_dotnet_file(self, test_file: Path, content: str) -> List[TestMetadata]:
        """Parse .NET test file."""
        tests = []
        
        # Find [Test] or [Fact] methods
        test_pattern = r"\[(?:Test|Fact|TestMethod)\].*?public\s+(?:void|Task)\s+(\w+)\s*\("
        
        for match in re.finditer(test_pattern, content, re.DOTALL):
            test_name = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            
            tests.append(TestMetadata(
                test_name=test_name,
                file_path=str(test_file),
                tags=[],
                framework="nunit-playwright"
            ))
        
        return tests
