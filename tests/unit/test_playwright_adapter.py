"""
Unit tests for Playwright multi-language adapter.

Tests cover:
- Auto-detection for all language bindings
- Test discovery
- Test execution
- Result parsing
- Error handling
- Edge cases
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from adapters.playwright import (
    PlaywrightAdapter,
    PlaywrightExtractor,
    PlaywrightProjectDetector,
    PlaywrightProjectConfig,
    PlaywrightLanguage,
    PlaywrightTestFramework,
)


class TestPlaywrightProjectDetector:
    """Test auto-detection of Playwright projects."""
    
    def test_detect_playwright_test_javascript(self, tmp_path):
        """Test detection of @playwright/test with JavaScript."""
        # Create package.json
        package_json = {
            "name": "test-project",
            "devDependencies": {
                "@playwright/test": "^1.40.0"
            }
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))
        
        # Create test directory
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "example.spec.js").write_text("test('example', () => {});")
        
        # Detect
        detector = PlaywrightProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.language == PlaywrightLanguage.JAVASCRIPT
        assert config.framework == PlaywrightTestFramework.PLAYWRIGHT_TEST
        assert config.test_dir.exists()
    
    def test_detect_playwright_test_typescript(self, tmp_path):
        """Test detection of @playwright/test with TypeScript."""
        # Create package.json
        package_json = {
            "name": "test-project",
            "devDependencies": {
                "@playwright/test": "^1.40.0",
                "typescript": "^5.0.0"
            }
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))
        (tmp_path / "tsconfig.json").write_text("{}")
        
        # Create test directory
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "example.spec.ts").write_text("test('example', () => {});")
        
        # Create config file
        (tmp_path / "playwright.config.ts").write_text("export default {};")
        
        # Detect
        detector = PlaywrightProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.language == PlaywrightLanguage.TYPESCRIPT
        assert config.framework == PlaywrightTestFramework.PLAYWRIGHT_TEST
        assert config.config_file is not None
        assert config.config_file.exists()
    
    def test_detect_python_playwright(self, tmp_path):
        """Test detection of pytest-playwright (Python)."""
        # Create pytest.ini
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        
        # Create test directory
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "test_example.py"
        test_file.write_text("""
import pytest
from playwright.sync_api import Page

def test_example(page: Page):
    page.goto("https://example.com")
""")
        
        # Detect
        detector = PlaywrightProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.language == PlaywrightLanguage.PYTHON
        assert config.framework == PlaywrightTestFramework.PYTEST_PLAYWRIGHT
    
    def test_detect_java_playwright_junit(self, tmp_path):
        """Test detection of Java Playwright with JUnit."""
        # Create pom.xml
        pom_xml = """<?xml version="1.0"?>
<project>
    <dependencies>
        <dependency>
            <groupId>com.microsoft.playwright</groupId>
            <artifactId>playwright</artifactId>
        </dependency>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
        </dependency>
    </dependencies>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_xml)
        
        # Create test directory
        test_dir = tmp_path / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        (test_dir / "LoginTest.java").write_text("@Test void test() {}")
        
        # Detect
        detector = PlaywrightProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.language == PlaywrightLanguage.JAVA
        assert config.framework == PlaywrightTestFramework.JUNIT_PLAYWRIGHT
        assert config.config_file == tmp_path / "pom.xml"
    
    def test_detect_java_playwright_testng(self, tmp_path):
        """Test detection of Java Playwright with TestNG."""
        # Create pom.xml with TestNG
        pom_xml = """<?xml version="1.0"?>
<project>
    <dependencies>
        <dependency>
            <groupId>com.microsoft.playwright</groupId>
            <artifactId>playwright</artifactId>
        </dependency>
        <dependency>
            <groupId>org.testng</groupId>
            <artifactId>testng</artifactId>
        </dependency>
    </dependencies>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_xml)
        
        test_dir = tmp_path / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        (test_dir / "LoginTest.java").write_text("@Test void test() {}")
        
        # Detect
        detector = PlaywrightProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.language == PlaywrightLanguage.JAVA
        assert config.framework == PlaywrightTestFramework.TESTNG_PLAYWRIGHT
    
    def test_detect_dotnet_playwright_nunit(self, tmp_path):
        """Test detection of .NET Playwright with NUnit."""
        # Create .csproj
        csproj = """<?xml version="1.0"?>
<Project Sdk="Microsoft.NET.Sdk">
    <ItemGroup>
        <PackageReference Include="Microsoft.Playwright" />
        <PackageReference Include="NUnit" />
    </ItemGroup>
</Project>
"""
        (tmp_path / "Tests.csproj").write_text(csproj)
        (tmp_path / "LoginTests.cs").write_text("[Test] void Test() {}")
        
        # Detect
        detector = PlaywrightProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.language == PlaywrightLanguage.DOTNET
        assert config.framework == PlaywrightTestFramework.NUNIT_PLAYWRIGHT
    
    def test_detect_dotnet_playwright_mstest(self, tmp_path):
        """Test detection of .NET Playwright with MSTest."""
        csproj = """<?xml version="1.0"?>
<Project Sdk="Microsoft.NET.Sdk">
    <ItemGroup>
        <PackageReference Include="Microsoft.Playwright" />
        <PackageReference Include="MSTest.TestFramework" />
    </ItemGroup>
</Project>
"""
        (tmp_path / "Tests.csproj").write_text(csproj)
        
        detector = PlaywrightProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.language == PlaywrightLanguage.DOTNET
        assert config.framework == PlaywrightTestFramework.MSTEST_PLAYWRIGHT
    
    def test_detect_no_playwright_project(self, tmp_path):
        """Test detection returns None for non-Playwright project."""
        # Create empty directory
        (tmp_path / "README.md").write_text("# Not a Playwright project")
        
        detector = PlaywrightProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is None


class TestPlaywrightAdapter:
    """Test PlaywrightAdapter unified interface."""
    
    def test_adapter_requires_valid_project(self, tmp_path):
        """Test adapter raises error for invalid project."""
        with pytest.raises(ValueError, match="Could not detect Playwright project"):
            PlaywrightAdapter(str(tmp_path))
    
    def test_adapter_with_manual_config(self, tmp_path):
        """Test adapter accepts manual configuration."""
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.PYTHON,
            framework=PlaywrightTestFramework.PYTEST_PLAYWRIGHT,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        adapter = PlaywrightAdapter(str(tmp_path), config=config)
        
        assert adapter.config == config
        assert adapter._executor is not None
    
    def test_get_config_info(self, tmp_path):
        """Test getting configuration information."""
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.TYPESCRIPT,
            framework=PlaywrightTestFramework.PLAYWRIGHT_TEST,
            test_dir=tmp_path / "tests",
            config_file=tmp_path / "playwright.config.ts",
            project_root=tmp_path
        )
        
        adapter = PlaywrightAdapter(str(tmp_path), config=config)
        info = adapter.get_config_info()
        
        assert info["language"] == "typescript"
        assert info["framework"] == "playwright-test"
        assert "tests" in info["test_dir"]
        assert "playwright.config.ts" in info["config_file"]
    
    @patch("subprocess.run")
    def test_discover_tests_delegates_to_executor(self, mock_run, tmp_path):
        """Test discover_tests delegates to language-specific executor."""
        # Setup mock
        mock_result = Mock()
        mock_result.stdout = "test 1\ntest 2"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.PYTHON,
            framework=PlaywrightTestFramework.PYTEST_PLAYWRIGHT,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        adapter = PlaywrightAdapter(str(tmp_path), config=config)
        tests = adapter.discover_tests()
        
        # Should call subprocess
        assert mock_run.called
        assert isinstance(tests, list)
    
    @patch("subprocess.run")
    def test_run_tests_delegates_to_executor(self, mock_run, tmp_path):
        """Test run_tests delegates to language-specific executor."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.PYTHON,
            framework=PlaywrightTestFramework.PYTEST_PLAYWRIGHT,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        adapter = PlaywrightAdapter(str(tmp_path), config=config)
        results = adapter.run_tests()
        
        assert mock_run.called
        assert isinstance(results, list)


class TestPlaywrightTestExecutor:
    """Test @playwright/test executor (JavaScript/TypeScript)."""
    
    @patch("subprocess.run")
    def test_discover_tests_parses_output(self, mock_run, tmp_path):
        """Test discovery parses playwright test --list output."""
        from adapters.playwright.adapter import PlaywrightTestExecutor
        
        mock_result = Mock()
        mock_result.stdout = """
[chromium] › tests/login.spec.ts:5:1 › user can login
[chromium] › tests/checkout.spec.ts:10:1 › user can checkout
"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.TYPESCRIPT,
            framework=PlaywrightTestFramework.PLAYWRIGHT_TEST,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        executor = PlaywrightTestExecutor(config)
        tests = executor.discover_tests()
        
        assert len(tests) == 2
        assert "user can login" in tests
        assert "user can checkout" in tests
    
    @patch("subprocess.run")
    def test_run_tests_with_json_reporter(self, mock_run, tmp_path):
        """Test execution with JSON reporter."""
        from adapters.playwright.adapter import PlaywrightTestExecutor
        
        report = {
            "suites": [{
                "specs": [{
                    "title": "login test",
                    "tests": [{
                        "results": [{
                            "status": "passed",
                            "duration": 1500
                        }]
                    }]
                }]
            }]
        }
        
        mock_result = Mock()
        mock_result.stdout = json.dumps(report)
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.TYPESCRIPT,
            framework=PlaywrightTestFramework.PLAYWRIGHT_TEST,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        executor = PlaywrightTestExecutor(config)
        results = executor.run_tests()
        
        assert len(results) == 1
        assert results[0].name == "login test"
        assert results[0].status == "pass"
        assert results[0].duration_ms == 1500


class TestPytestPlaywrightExecutor:
    """Test pytest-playwright executor (Python)."""
    
    @patch("subprocess.run")
    def test_discover_tests_parses_pytest_output(self, mock_run, tmp_path):
        """Test discovery parses pytest --collect-only output."""
        from adapters.playwright.adapter import PytestPlaywrightExecutor
        
        mock_result = Mock()
        mock_result.stdout = """
tests/test_login.py::test_user_can_login
tests/test_checkout.py::test_user_can_checkout
"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.PYTHON,
            framework=PlaywrightTestFramework.PYTEST_PLAYWRIGHT,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        executor = PytestPlaywrightExecutor(config)
        tests = executor.discover_tests()
        
        assert len(tests) == 2
        assert "test_user_can_login" in tests
        assert "test_user_can_checkout" in tests
    
    @patch("subprocess.run")
    def test_run_tests_parses_results(self, mock_run, tmp_path):
        """Test execution parses pytest output."""
        from adapters.playwright.adapter import PytestPlaywrightExecutor
        
        mock_result = Mock()
        mock_result.stdout = """
tests/test_login.py::test_user_can_login PASSED
tests/test_checkout.py::test_user_can_checkout FAILED
"""
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.PYTHON,
            framework=PlaywrightTestFramework.PYTEST_PLAYWRIGHT,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        executor = PytestPlaywrightExecutor(config)
        results = executor.run_tests()
        
        assert len(results) == 2
        assert results[0].status == "pass"
        assert results[1].status == "fail"


class TestPlaywrightExtractor:
    """Test PlaywrightExtractor metadata extraction."""
    
    def test_extractor_requires_valid_project(self, tmp_path):
        """Test extractor raises error for invalid project."""
        with pytest.raises(ValueError, match="Could not detect Playwright project"):
            PlaywrightExtractor(str(tmp_path))
    
    def test_extract_javascript_tests(self, tmp_path):
        """Test extraction from JavaScript test files."""
        # Setup project
        package_json = {
            "devDependencies": {"@playwright/test": "^1.40.0"}
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))
        
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "login.spec.js"
        test_file.write_text("""
test('user can login', async ({ page }) => {
  await page.goto('https://example.com');
});

test('user can logout', async ({ page }) => {
  await page.click('#logout');
});
""")
        
        extractor = PlaywrightExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        assert any(t.name == "user can login" for t in tests)
        assert any(t.name == "user can logout" for t in tests)
        assert all(t.framework == "playwright-test" for t in tests)
    
    def test_extract_python_tests(self, tmp_path):
        """Test extraction from Python test files."""
        # Setup project
        (tmp_path / "pytest.ini").write_text("[pytest]")
        
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        test_file = tests_dir / "test_login.py"
        test_file.write_text("""
from playwright.sync_api import Page

def test_user_can_login(page: Page):
    page.goto("https://example.com")

def test_user_can_logout(page: Page):
    page.click("#logout")
""")
        
        extractor = PlaywrightExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        assert any(t.name == "test_user_can_login" for t in tests)
        assert any(t.name == "test_user_can_logout" for t in tests)
        assert all(t.framework == "pytest-playwright" for t in tests)
    
    def test_extract_java_tests(self, tmp_path):
        """Test extraction from Java test files."""
        # Setup project
        pom_xml = """<?xml version="1.0"?>
<project>
    <dependencies>
        <dependency>
            <groupId>com.microsoft.playwright</groupId>
            <artifactId>playwright</artifactId>
        </dependency>
    </dependencies>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_xml)
        
        test_dir = tmp_path / "src" / "test" / "java"
        test_dir.mkdir(parents=True)
        
        test_file = test_dir / "LoginTest.java"
        test_file.write_text("""
import org.junit.jupiter.api.Test;

public class LoginTest {
    @Test
    public void userCanLogin() {
        // test code
    }
    
    @Test
    public void userCanLogout() {
        // test code
    }
}
""")
        
        extractor = PlaywrightExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        assert any(t.name == "userCanLogin" for t in tests)
        assert any(t.name == "userCanLogout" for t in tests)
        assert all(t.framework == "junit-playwright" for t in tests)
    
    def test_extract_dotnet_tests(self, tmp_path):
        """Test extraction from .NET test files."""
        # Setup project
        csproj = """<?xml version="1.0"?>
<Project Sdk="Microsoft.NET.Sdk">
    <ItemGroup>
        <PackageReference Include="Microsoft.Playwright" />
        <PackageReference Include="NUnit" />
    </ItemGroup>
</Project>
"""
        (tmp_path / "Tests.csproj").write_text(csproj)
        
        test_file = tmp_path / "LoginTests.cs"
        test_file.write_text("""
using NUnit.Framework;

public class LoginTests
{
    [Test]
    public void UserCanLogin()
    {
        // test code
    }
    
    [Test]
    public void UserCanLogout()
    {
        // test code
    }
}
""")
        
        extractor = PlaywrightExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 2
        assert any(t.name == "UserCanLogin" for t in tests)
        assert any(t.name == "UserCanLogout" for t in tests)
        assert all(t.framework == "nunit-playwright" for t in tests)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_adapter_handles_missing_executor(self, tmp_path):
        """Test adapter handles unsupported framework gracefully."""
        # Create invalid config
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.PYTHON,
            framework=None,  # Invalid
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        with pytest.raises(ValueError, match="Unsupported framework"):
            PlaywrightAdapter(str(tmp_path), config=config)
    
    @patch("subprocess.run")
    def test_executor_handles_timeout(self, mock_run, tmp_path):
        """Test executor handles subprocess timeout."""
        from adapters.playwright.adapter import PytestPlaywrightExecutor
        import subprocess
        
        mock_run.side_effect = subprocess.TimeoutExpired("pytest", 30)
        
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.PYTHON,
            framework=PlaywrightTestFramework.PYTEST_PLAYWRIGHT,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        executor = PytestPlaywrightExecutor(config)
        tests = executor.discover_tests()
        
        # Should return empty list, not crash
        assert tests == []
    
    @patch("subprocess.run")
    def test_executor_handles_command_not_found(self, mock_run, tmp_path):
        """Test executor handles missing command."""
        from adapters.playwright.adapter import PytestPlaywrightExecutor
        
        mock_run.side_effect = FileNotFoundError("pytest not found")
        
        config = PlaywrightProjectConfig(
            language=PlaywrightLanguage.PYTHON,
            framework=PlaywrightTestFramework.PYTEST_PLAYWRIGHT,
            test_dir=tmp_path,
            project_root=tmp_path
        )
        
        executor = PytestPlaywrightExecutor(config)
        tests = executor.discover_tests()
        
        assert tests == []
    
    def test_extractor_handles_parse_errors(self, tmp_path):
        """Test extractor handles malformed test files."""
        package_json = {
            "devDependencies": {"@playwright/test": "^1.40.0"}
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))
        
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        # Create malformed test file
        test_file = tests_dir / "bad.spec.js"
        test_file.write_text("this is not valid javascript {{{")
        
        extractor = PlaywrightExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        # Should not crash, returns empty or partial results
        assert isinstance(tests, list)
