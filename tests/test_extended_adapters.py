"""
Unit tests for extended framework adapters (RestAssured, Playwright, Selenium, BDD).
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from core.intelligence.adapters import (
    RestAssuredAdapter,
    PlaywrightAdapter,
    SeleniumPythonAdapter,
    SeleniumJavaAdapter,
    CucumberAdapter,
    BehaveAdapter,
    AdapterFactory,
)
from core.intelligence.models import (
    UnifiedTestMemory,
    TestType,
    Priority,
)


class TestRestAssuredAdapter:
    """Test RestAssured adapter for Java REST API testing."""
    
    def test_get_framework_name(self):
        adapter = RestAssuredAdapter()
        assert adapter.get_framework_name() == "restassured"
    
    def test_get_language(self):
        adapter = RestAssuredAdapter()
        assert adapter.get_language() == "java"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        mock_rglob.side_effect = [
            [Path("src/test/ApiTest.java")],
            [Path("src/test/UserTests.java")],
            [Path("src/test/IntegrationIT.java")],
        ]
        
        adapter = RestAssuredAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 3
        assert any("ApiTest.java" in f for f in test_files)
        assert any("IntegrationIT.java" in f for f in test_files)
    
    def test_infer_test_type_negative(self):
        adapter = RestAssuredAdapter()
        
        test_type = adapter._infer_test_type("", "testInvalidRequest")
        assert test_type == TestType.NEGATIVE
        
        test_type = adapter._infer_test_type("", "testUnauthorizedAccess")
        assert test_type == TestType.NEGATIVE
    
    def test_extract_priority(self):
        adapter = RestAssuredAdapter()
        
        content = "@Test(priority = 0)\npublic void testCritical() {}"
        priority = adapter._extract_priority(content, "testCritical")
        assert priority == Priority.P0
    
    @patch("builtins.open", new_callable=mock_open, read_data="@Test\npublic void testApi() {}")
    @patch("pathlib.Path.exists")
    def test_normalize_to_core_model(self, mock_exists, mock_file):
        mock_exists.return_value = True
        adapter = RestAssuredAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/src/test/ApiTest.java",
            test_name="testApi"
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "restassured"
        assert unified.language == "java"


class TestPlaywrightAdapter:
    """Test Playwright adapter for E2E testing."""
    
    def test_get_framework_name(self):
        adapter = PlaywrightAdapter()
        assert adapter.get_framework_name() == "playwright"
    
    def test_get_language(self):
        adapter = PlaywrightAdapter()
        assert adapter.get_language() == "javascript"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        mock_rglob.side_effect = [
            [Path("tests/login.spec.js")],
            [Path("tests/checkout.spec.ts")],
            [Path("tests/api.test.js")],
            [Path("tests/ui.test.ts")],
            [Path("tests/e2e.flow.js")],
            [Path("tests/e2e.flow.ts")],
        ]
        
        adapter = PlaywrightAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 6
        assert any("login.spec.js" in f for f in test_files)
        assert any("checkout.spec.ts" in f for f in test_files)
    
    def test_infer_test_type_e2e(self):
        adapter = PlaywrightAdapter()
        
        test_type = adapter._infer_test_type("", "test full e2e checkout flow")
        assert test_type == TestType.E2E
    
    def test_extract_playwright_tags(self):
        adapter = PlaywrightAdapter()
        
        content = "test('@smoke checkout flow', async () => {})"
        tags = adapter._extract_playwright_tags(content, "checkout flow")
        
        assert "smoke" in tags
    
    @patch("builtins.open", new_callable=mock_open, read_data="test('login', async () => {})")
    @patch("pathlib.Path.exists")
    def test_normalize_to_core_model(self, mock_exists, mock_file):
        mock_exists.return_value = True
        adapter = PlaywrightAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/tests/login.spec.js",
            test_name="login"
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "playwright"
        assert unified.language == "javascript"


class TestSeleniumPythonAdapter:
    """Test Selenium Python adapter."""
    
    def test_get_framework_name(self):
        adapter = SeleniumPythonAdapter()
        assert adapter.get_framework_name() == "selenium_python"
    
    def test_get_language(self):
        adapter = SeleniumPythonAdapter()
        assert adapter.get_language() == "python"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        mock_rglob.side_effect = [
            [Path("tests/test_login.py")],
            [Path("tests/checkout_test.py")],
            [Path("tests/testui.py")],
        ]
        
        adapter = SeleniumPythonAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 3
        assert any("test_login.py" in f for f in test_files)
    
    def test_infer_test_type_e2e(self):
        adapter = SeleniumPythonAdapter()
        
        test_type = adapter._infer_test_type("", "test_e2e_checkout_flow")
        assert test_type == TestType.E2E
    
    def test_extract_priority(self):
        adapter = SeleniumPythonAdapter()
        
        content = "@pytest.mark.p0\ndef test_critical(): pass"
        priority = adapter._extract_priority(content, "test_critical")
        assert priority == Priority.P0
    
    def test_extract_selenium_tags(self):
        adapter = SeleniumPythonAdapter()
        
        content = "@pytest.mark.smoke\n@pytest.mark.ui\ndef test_login(): pass"
        tags = adapter._extract_selenium_tags(content, "test_login")
        
        assert "smoke" in tags
        assert "ui" in tags
    
    @patch("builtins.open", new_callable=mock_open, read_data="def test_login(): pass")
    @patch("pathlib.Path.exists")
    def test_normalize_to_core_model(self, mock_exists, mock_file):
        mock_exists.return_value = True
        adapter = SeleniumPythonAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/tests/test_login.py",
            test_name="test_login"
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "selenium_python"
        assert unified.language == "python"


class TestSeleniumJavaAdapter:
    """Test Selenium Java adapter."""
    
    def test_get_framework_name(self):
        adapter = SeleniumJavaAdapter()
        assert adapter.get_framework_name() == "selenium_java"
    
    def test_get_language(self):
        adapter = SeleniumJavaAdapter()
        assert adapter.get_language() == "java"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        mock_rglob.side_effect = [
            [Path("src/test/LoginTest.java")],
            [Path("src/test/UITests.java")],
            [Path("src/test/IntegrationIT.java")],
        ]
        
        adapter = SeleniumJavaAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 3
    
    def test_infer_test_type_e2e(self):
        adapter = SeleniumJavaAdapter()
        
        test_type = adapter._infer_test_type("", "testE2ECheckout")
        assert test_type == TestType.E2E
    
    def test_extract_priority(self):
        adapter = SeleniumJavaAdapter()
        
        content = "@Test(priority = 0)\npublic void testCriticalUI() {}"
        priority = adapter._extract_priority(content, "testCriticalUI")
        assert priority == Priority.P0
    
    @patch("builtins.open", new_callable=mock_open, read_data="@Test\npublic void testLogin() {}")
    @patch("pathlib.Path.exists")
    def test_normalize_to_core_model(self, mock_exists, mock_file):
        mock_exists.return_value = True
        adapter = SeleniumJavaAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/src/test/LoginTest.java",
            test_name="testLogin"
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "selenium_java"
        assert unified.language == "java"


class TestCucumberAdapter:
    """Test Cucumber adapter for BDD."""
    
    def test_get_framework_name(self):
        adapter = CucumberAdapter()
        assert adapter.get_framework_name() == "cucumber"
    
    def test_get_language(self):
        adapter = CucumberAdapter()
        assert adapter.get_language() == "gherkin"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        mock_rglob.return_value = [
            Path("features/login.feature"),
            Path("features/checkout.feature"),
        ]
        
        adapter = CucumberAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 2
        assert any("login.feature" in f for f in test_files)
    
    def test_infer_test_type_negative(self):
        adapter = CucumberAdapter()
        
        test_type = adapter._infer_test_type("", "Login with invalid credentials")
        assert test_type == TestType.NEGATIVE
    
    def test_extract_priority_from_tags(self):
        adapter = CucumberAdapter()
        
        content = "@critical\nScenario: Important test"
        priority = adapter._extract_priority(content, "Important test")
        assert priority == Priority.P0
    
    def test_extract_cucumber_tags(self):
        adapter = CucumberAdapter()
        
        content = "@smoke @regression\nScenario: Test scenario"
        tags = adapter._extract_cucumber_tags(content, "Test scenario")
        
        assert "smoke" in tags
        assert "regression" in tags
    
    def test_extract_feature_from_content(self):
        adapter = CucumberAdapter()
        
        content = "Feature: User Authentication\n  As a user"
        feature = adapter._extract_feature_from_content(content)
        
        assert feature == "User Authentication"
    
    def test_parse_gherkin_steps_with_api(self):
        adapter = CucumberAdapter()
        
        content = """
Scenario: Get user data
  When I send a GET request to /api/users
  Then the response status should be 200
"""
        
        signals = adapter._parse_gherkin_steps(content, "Get user data")
        
        assert len(signals.api_calls) >= 1
        assert any(call.method == "GET" for call in signals.api_calls)
    
    def test_parse_gherkin_steps_with_assertions(self):
        adapter = CucumberAdapter()
        
        content = """
Scenario: Verify user creation
  When I create a user
  Then the user should be created successfully
  And the response must contain user ID
"""
        
        signals = adapter._parse_gherkin_steps(content, "Verify user creation")
        
        assert len(signals.assertions) >= 1
    
    @patch("builtins.open", new_callable=mock_open, read_data="Feature: Test\nScenario: Example\n  When I test")
    @patch("pathlib.Path.exists")
    def test_normalize_to_core_model(self, mock_exists, mock_file):
        mock_exists.return_value = True
        adapter = CucumberAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/features/test.feature",
            test_name="Example"
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "cucumber"
        assert unified.language == "gherkin"


class TestBehaveAdapter:
    """Test Behave adapter for Python BDD."""
    
    def test_get_framework_name(self):
        adapter = BehaveAdapter()
        assert adapter.get_framework_name() == "behave"
    
    def test_get_language(self):
        adapter = BehaveAdapter()
        assert adapter.get_language() == "python"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        mock_rglob.return_value = [
            Path("features/login.feature"),
            Path("features/api.feature"),
        ]
        
        adapter = BehaveAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 2
    
    def test_infer_test_type_negative(self):
        adapter = BehaveAdapter()
        
        test_type = adapter._infer_test_type("", "Login with invalid password")
        assert test_type == TestType.NEGATIVE
    
    def test_extract_priority_from_tags(self):
        adapter = BehaveAdapter()
        
        content = "@critical @p0\nScenario: Critical test"
        priority = adapter._extract_priority(content, "Critical test")
        assert priority == Priority.P0
    
    def test_extract_behave_tags(self):
        adapter = BehaveAdapter()
        
        content = "@smoke @api\nScenario: API test"
        tags = adapter._extract_behave_tags(content, "API test")
        
        assert "smoke" in tags
        assert "api" in tags
    
    def test_parse_gherkin_steps_with_api(self):
        adapter = BehaveAdapter()
        
        content = """
Scenario: API call test
  When I POST to /api/users
  Then I should receive a 201 response
"""
        
        signals = adapter._parse_gherkin_steps(content, "API call test")
        
        assert len(signals.api_calls) >= 1
        assert any(call.method == "POST" for call in signals.api_calls)
    
    @patch("builtins.open", new_callable=mock_open, read_data="Feature: Test\nScenario: Example\n  When I test")
    @patch("pathlib.Path.exists")
    def test_normalize_to_core_model(self, mock_exists, mock_file):
        mock_exists.return_value = True
        adapter = BehaveAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/features/test.feature",
            test_name="Example"
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "behave"
        assert unified.language == "python"


class TestExtendedAdapterFactory:
    """Test adapter factory with all extended frameworks."""
    
    def test_get_restassured_adapter(self):
        adapter = AdapterFactory.get_adapter("restassured")
        
        assert adapter is not None
        assert isinstance(adapter, RestAssuredAdapter)
    
    def test_get_playwright_adapter(self):
        adapter = AdapterFactory.get_adapter("playwright")
        
        assert adapter is not None
        assert isinstance(adapter, PlaywrightAdapter)
    
    def test_get_selenium_python_adapter(self):
        adapter = AdapterFactory.get_adapter("selenium_python")
        
        assert adapter is not None
        assert isinstance(adapter, SeleniumPythonAdapter)
    
    def test_get_selenium_java_adapter(self):
        adapter = AdapterFactory.get_adapter("selenium_java")
        
        assert adapter is not None
        assert isinstance(adapter, SeleniumJavaAdapter)
    
    def test_get_cucumber_adapter(self):
        adapter = AdapterFactory.get_adapter("cucumber")
        
        assert adapter is not None
        assert isinstance(adapter, CucumberAdapter)
    
    def test_get_behave_adapter(self):
        adapter = AdapterFactory.get_adapter("behave")
        
        assert adapter is not None
        assert isinstance(adapter, BehaveAdapter)
    
    def test_list_all_frameworks(self):
        frameworks = AdapterFactory.list_supported_frameworks()
        
        # Original frameworks
        assert "pytest" in frameworks
        assert "junit" in frameworks
        assert "testng" in frameworks
        assert "nunit" in frameworks
        assert "specflow" in frameworks
        assert "robot" in frameworks
        
        # Extended frameworks
        assert "restassured" in frameworks
        assert "playwright" in frameworks
        assert "selenium_python" in frameworks
        assert "selenium_java" in frameworks
        assert "cucumber" in frameworks
        assert "behave" in frameworks
        
        # Total should be 12
        assert len(frameworks) == 12
    
    def test_case_insensitive_lookup(self):
        adapter1 = AdapterFactory.get_adapter("RestAssured")
        adapter2 = AdapterFactory.get_adapter("PLAYWRIGHT")
        adapter3 = AdapterFactory.get_adapter("Selenium_Python")
        
        assert adapter1 is not None
        assert adapter2 is not None
        assert adapter3 is not None


class TestCrossFrameworkCompatibility:
    """Test cross-framework compatibility."""
    
    def test_all_adapters_consistent_interface(self):
        """Test all adapters implement consistent interface."""
        adapters = [
            RestAssuredAdapter(),
            PlaywrightAdapter(),
            SeleniumPythonAdapter(),
            SeleniumJavaAdapter(),
            CucumberAdapter(),
            BehaveAdapter(),
        ]
        
        for adapter in adapters:
            assert hasattr(adapter, "discover_tests")
            assert hasattr(adapter, "extract_metadata")
            assert hasattr(adapter, "extract_ast_signals")
            assert hasattr(adapter, "normalize_to_core_model")
            assert hasattr(adapter, "get_framework_name")
            assert hasattr(adapter, "get_language")
    
    @patch("builtins.open", new_callable=mock_open, read_data="test code")
    @patch("pathlib.Path.exists")
    def test_unified_memory_compatibility(self, mock_exists, mock_file):
        """Test all adapters produce compatible UnifiedTestMemory."""
        mock_exists.return_value = True
        
        adapters_config = [
            ("restassured", RestAssuredAdapter(), "java"),
            ("playwright", PlaywrightAdapter(), "javascript"),
            ("selenium_python", SeleniumPythonAdapter(), "python"),
            ("selenium_java", SeleniumJavaAdapter(), "java"),
            ("cucumber", CucumberAdapter(), "gherkin"),
            ("behave", BehaveAdapter(), "python"),
        ]
        
        for framework_name, adapter, expected_lang in adapters_config:
            unified = adapter.normalize_to_core_model(
                test_file=f"/test.{expected_lang}",
                test_name="test_example"
            )
            
            assert isinstance(unified, UnifiedTestMemory)
            assert unified.framework == framework_name
            assert unified.test_id.startswith(f"{framework_name}::")
            assert unified.semantic is not None
            assert unified.structural is not None
            assert unified.metadata is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
