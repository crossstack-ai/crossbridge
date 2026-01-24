"""
Unit tests for additional framework adapters (NUnit, TestNG, SpecFlow).
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from core.intelligence.adapters import (
    NUnitAdapter,
    TestNGAdapter,
    SpecFlowAdapter,
    AdapterFactory,
)
from core.intelligence.models import (
    UnifiedTestMemory,
    TestType,
    Priority,
)


class TestNUnitAdapter:
    """Test NUnit adapter for .NET."""
    
    def test_get_framework_name(self):
        """Test framework name."""
        adapter = NUnitAdapter()
        assert adapter.get_framework_name() == "nunit"
    
    def test_get_language(self):
        """Test language."""
        adapter = NUnitAdapter()
        assert adapter.get_language() == "csharp"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        """Test test discovery."""
        mock_rglob.side_effect = [
            [Path("Tests/UserTest.cs"), Path("Tests/ApiTest.cs")],
            [Path("Tests/AuthTests.cs")],
        ]
        
        adapter = NUnitAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 3
        assert any("UserTest.cs" in f for f in test_files)
        assert any("ApiTest.cs" in f for f in test_files)
        assert any("AuthTests.cs" in f for f in test_files)
    
    def test_infer_test_type_negative(self):
        """Test negative test type inference."""
        adapter = NUnitAdapter()
        
        test_type = adapter._infer_test_type("", "TestInvalidUser")
        assert test_type == TestType.NEGATIVE
        
        test_type = adapter._infer_test_type("", "TestErrorHandling")
        assert test_type == TestType.NEGATIVE
    
    def test_infer_test_type_integration(self):
        """Test integration test type inference."""
        adapter = NUnitAdapter()
        
        test_type = adapter._infer_test_type("", "TestIntegrationFlow")
        assert test_type == TestType.INTEGRATION
    
    def test_extract_priority_p0(self):
        """Test P0 priority extraction."""
        adapter = NUnitAdapter()
        
        content = '[Priority(0)]\npublic void TestCritical() {}'
        priority = adapter._extract_priority(content, "TestCritical")
        assert priority == Priority.P0
    
    def test_extract_priority_from_category(self):
        """Test priority from Category attribute."""
        adapter = NUnitAdapter()
        
        content = '[Category("Critical")]\npublic void TestImportant() {}'
        priority = adapter._extract_priority(content, "TestImportant")
        assert priority == Priority.P0
    
    def test_extract_nunit_categories(self):
        """Test NUnit category extraction."""
        adapter = NUnitAdapter()
        
        content = '''
[Category("Smoke")]
[Category("Regression")]
public void TestExample() {}
'''
        
        tags = adapter._extract_nunit_categories(content, "TestExample")
        
        assert "smoke" in tags
        assert "regression" in tags
    
    @patch("builtins.open", new_callable=mock_open, read_data='[Test]\npublic void TestExample() {}')
    def test_normalize_to_core_model(self, mock_file):
        """Test normalization to UnifiedTestMemory."""
        adapter = NUnitAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/project/Tests/UserTest.cs",
            test_name="TestExample",
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "nunit"
        assert unified.language == "csharp"
        assert "TestExample" in unified.test_id


class TestTestNGAdapter:
    """Test TestNG adapter for Java."""
    
    def test_get_framework_name(self):
        """Test framework name."""
        adapter = TestNGAdapter()
        assert adapter.get_framework_name() == "testng"
    
    def test_get_language(self):
        """Test language."""
        adapter = TestNGAdapter()
        assert adapter.get_language() == "java"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        """Test test discovery."""
        mock_rglob.side_effect = [
            [Path("src/test/UserTest.java")],
            [Path("src/test/ApiTests.java")],
        ]
        
        adapter = TestNGAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 2
        assert any("UserTest.java" in f for f in test_files)
    
    def test_infer_test_type_negative(self):
        """Test negative test type inference."""
        adapter = TestNGAdapter()
        
        test_type = adapter._infer_test_type("", "testInvalidInput")
        assert test_type == TestType.NEGATIVE
    
    def test_extract_priority_from_annotation(self):
        """Test priority from @Test annotation."""
        adapter = TestNGAdapter()
        
        content = '@Test(priority = 0)\npublic void testCritical() {}'
        priority = adapter._extract_priority(content, "testCritical")
        assert priority == Priority.P0
        
        content = '@Test(priority=1)\npublic void testHigh() {}'
        priority = adapter._extract_priority(content, "testHigh")
        assert priority == Priority.P1
    
    def test_extract_testng_groups(self):
        """Test TestNG groups extraction."""
        adapter = TestNGAdapter()
        
        content = '''
@Test(groups = "smoke")
public void testExample() {}
'''
        
        tags = adapter._extract_testng_groups(content, "testExample")
        assert "smoke" in tags
    
    @patch("builtins.open", new_callable=mock_open, read_data='@Test\npublic void testExample() {}')
    def test_normalize_to_core_model(self, mock_file):
        """Test normalization to UnifiedTestMemory."""
        adapter = TestNGAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/project/src/test/UserTest.java",
            test_name="testExample",
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "testng"
        assert unified.language == "java"


class TestSpecFlowAdapter:
    """Test SpecFlow adapter for .NET BDD."""
    
    def test_get_framework_name(self):
        """Test framework name."""
        adapter = SpecFlowAdapter()
        assert adapter.get_framework_name() == "specflow"
    
    def test_get_language(self):
        """Test language."""
        adapter = SpecFlowAdapter()
        assert adapter.get_language() == "csharp"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        """Test feature file discovery."""
        mock_rglob.return_value = [
            Path("Features/Login.feature"),
            Path("Features/Checkout.feature"),
        ]
        
        adapter = SpecFlowAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 2
        assert any("Login.feature" in f for f in test_files)
        assert any("Checkout.feature" in f for f in test_files)
    
    def test_infer_test_type_negative(self):
        """Test negative test type inference."""
        adapter = SpecFlowAdapter()
        
        test_type = adapter._infer_test_type("", "User login with invalid credentials")
        assert test_type == TestType.NEGATIVE
    
    def test_infer_test_type_e2e(self):
        """Test E2E test type inference."""
        adapter = SpecFlowAdapter()
        
        test_type = adapter._infer_test_type("", "Complete checkout flow end to end")
        assert test_type == TestType.E2E
    
    def test_extract_priority_from_tags(self):
        """Test priority from SpecFlow tags."""
        adapter = SpecFlowAdapter()
        
        content = '@critical\nScenario: Important test'
        priority = adapter._extract_priority(content, "Important test")
        assert priority == Priority.P0
        
        content = '@high\nScenario: High priority test'
        priority = adapter._extract_priority(content, "High priority test")
        assert priority == Priority.P1
    
    def test_extract_specflow_tags(self):
        """Test SpecFlow tag extraction."""
        adapter = SpecFlowAdapter()
        
        content = '''
@smoke @regression
Feature: User Management
'''
        
        tags = adapter._extract_specflow_tags(content, "scenario")
        assert "smoke" in tags
        assert "regression" in tags
    
    def test_extract_feature_from_content(self):
        """Test feature name extraction."""
        adapter = SpecFlowAdapter()
        
        content = '''
Feature: User Authentication
  As a user
  I want to login
'''
        
        feature = adapter._extract_feature_from_content(content)
        assert feature == "User Authentication"
    
    def test_parse_gherkin_steps_with_api(self):
        """Test parsing Gherkin steps with API calls."""
        adapter = SpecFlowAdapter()
        
        content = '''
Scenario: Get user details
  Given I am authenticated
  When I send a GET request to /api/users/123
  Then the response status should be 200
'''
        
        signals = adapter._parse_gherkin_steps(content, "Get user details")
        
        assert len(signals.api_calls) >= 1
        assert any(call.method == "GET" for call in signals.api_calls)
    
    def test_parse_gherkin_steps_with_assertions(self):
        """Test parsing Gherkin steps with assertions."""
        adapter = SpecFlowAdapter()
        
        content = '''
Scenario: Verify user creation
  Given I have user data
  When I create a user
  Then the user should be created successfully
  And the response should contain user ID
'''
        
        signals = adapter._parse_gherkin_steps(content, "Verify user creation")
        
        # Should detect assertion-like steps (Then, And with should/verify)
        assert len(signals.assertions) >= 1
    
    @patch("builtins.open", new_callable=mock_open, read_data='Feature: Test\nScenario: Example\n  When I test')
    def test_normalize_to_core_model(self, mock_file):
        """Test normalization to UnifiedTestMemory."""
        adapter = SpecFlowAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/project/Features/Test.feature",
            test_name="Example",
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "specflow"
        assert unified.language == "csharp"


class TestAdapterFactoryExtended:
    """Test adapter factory with all frameworks."""
    
    def test_get_nunit_adapter(self):
        """Test getting NUnit adapter."""
        adapter = AdapterFactory.get_adapter("nunit")
        
        assert adapter is not None
        assert isinstance(adapter, NUnitAdapter)
    
    def test_get_testng_adapter(self):
        """Test getting TestNG adapter."""
        adapter = AdapterFactory.get_adapter("testng")
        
        assert adapter is not None
        assert isinstance(adapter, TestNGAdapter)
    
    def test_get_specflow_adapter(self):
        """Test getting SpecFlow adapter."""
        adapter = AdapterFactory.get_adapter("specflow")
        
        assert adapter is not None
        assert isinstance(adapter, SpecFlowAdapter)
    
    def test_list_all_supported_frameworks(self):
        """Test listing all supported frameworks."""
        frameworks = AdapterFactory.list_supported_frameworks()
        
        assert "pytest" in frameworks
        assert "junit" in frameworks
        assert "testng" in frameworks
        assert "nunit" in frameworks
        assert "specflow" in frameworks
        assert "robot" in frameworks
    
    def test_case_insensitive_adapter_lookup(self):
        """Test case-insensitive framework lookup."""
        adapter1 = AdapterFactory.get_adapter("NUnit")
        adapter2 = AdapterFactory.get_adapter("NUNIT")
        
        assert adapter1 is not None
        assert adapter2 is not None


class TestCrossFrameworkIntegration:
    """Test cross-framework integration scenarios."""
    
    def test_all_adapters_have_consistent_interface(self):
        """Test all adapters implement the same interface."""
        adapters = [
            NUnitAdapter(),
            TestNGAdapter(),
            SpecFlowAdapter(),
        ]
        
        for adapter in adapters:
            # All should have these methods
            assert hasattr(adapter, "discover_tests")
            assert hasattr(adapter, "extract_metadata")
            assert hasattr(adapter, "extract_ast_signals")
            assert hasattr(adapter, "normalize_to_core_model")
            assert hasattr(adapter, "get_framework_name")
            assert hasattr(adapter, "get_language")
    
    def test_unified_memory_compatibility(self):
        """Test all adapters produce compatible UnifiedTestMemory objects."""
        adapters = [
            ("nunit", NUnitAdapter()),
            ("testng", TestNGAdapter()),
            ("specflow", SpecFlowAdapter()),
        ]
        
        for framework_name, adapter in adapters:
            unified = adapter.normalize_to_core_model(
                test_file=f"/test.{adapter.get_language()}",
                test_name="test_example",
            )
            
            assert isinstance(unified, UnifiedTestMemory)
            assert unified.framework == framework_name
            assert unified.test_id.startswith(f"{framework_name}::")
            assert unified.semantic is not None
            assert unified.structural is not None
            assert unified.metadata is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
