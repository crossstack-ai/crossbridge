"""
Unit tests for framework adapters.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from core.intelligence.adapters import (
    PytestAdapter,
    JUnitAdapter,
    RobotFrameworkAdapter,
    AdapterFactory,
    normalize_test,
)
from core.intelligence.models import (
    UnifiedTestMemory,
    SemanticSignals,
    TestType,
    Priority,
)


class TestPytestAdapter:
    """Test pytest adapter."""
    
    def test_get_framework_name(self):
        """Test framework name."""
        adapter = PytestAdapter()
        assert adapter.get_framework_name() == "pytest"
    
    def test_get_language(self):
        """Test language."""
        adapter = PytestAdapter()
        assert adapter.get_language() == "python"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        """Test test discovery."""
        # Mock test file discovery
        mock_rglob.side_effect = [
            [Path("tests/test_user.py"), Path("tests/test_api.py")],
            [Path("tests/integration_test.py")],
        ]
        
        adapter = PytestAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 3
        assert any("test_user.py" in f for f in test_files)
        assert any("test_api.py" in f for f in test_files)
        assert any("integration_test.py" in f for f in test_files)
    
    def test_infer_test_type_negative(self):
        """Test negative test type inference."""
        adapter = PytestAdapter()
        
        test_type = adapter._infer_test_type("", "test_invalid_user")
        assert test_type == TestType.NEGATIVE
        
        test_type = adapter._infer_test_type("", "test_error_handling")
        assert test_type == TestType.NEGATIVE
    
    def test_infer_test_type_boundary(self):
        """Test boundary test type inference."""
        adapter = PytestAdapter()
        
        test_type = adapter._infer_test_type("", "test_boundary_conditions")
        assert test_type == TestType.BOUNDARY
        
        test_type = adapter._infer_test_type("", "test_edge_case")
        assert test_type == TestType.BOUNDARY
    
    def test_infer_test_type_integration(self):
        """Test integration test type inference."""
        adapter = PytestAdapter()
        
        test_type = adapter._infer_test_type("", "test_integration_flow")
        assert test_type == TestType.INTEGRATION
    
    def test_infer_test_type_positive(self):
        """Test positive test type inference (default)."""
        adapter = PytestAdapter()
        
        test_type = adapter._infer_test_type("", "test_user_registration")
        assert test_type == TestType.POSITIVE
    
    def test_extract_priority_p0(self):
        """Test P0 priority extraction."""
        adapter = PytestAdapter()
        
        content = "@pytest.mark.p0\ndef test_critical(): pass"
        priority = adapter._extract_priority(content, "test_critical")
        assert priority == Priority.P0
    
    def test_extract_priority_p1(self):
        """Test P1 priority extraction."""
        adapter = PytestAdapter()
        
        content = "@pytest.mark.high\ndef test_important(): pass"
        priority = adapter._extract_priority(content, "test_important")
        assert priority == Priority.P1
    
    def test_extract_priority_default(self):
        """Test default priority."""
        adapter = PytestAdapter()
        
        content = "def test_normal(): pass"
        priority = adapter._extract_priority(content, "test_normal")
        assert priority == Priority.P2
    
    def test_extract_pytest_marks(self):
        """Test pytest marks extraction."""
        adapter = PytestAdapter()
        
        content = """
@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.slow
def test_example():
    pass
"""
        
        tags = adapter._extract_pytest_marks(content, "test_example")
        
        assert "smoke" in tags
        assert "regression" in tags
        assert "slow" in tags
    
    def test_extract_feature_from_path(self):
        """Test feature extraction from path."""
        adapter = PytestAdapter()
        
        feature = adapter._extract_feature_from_path("/project/tests/checkout/test_payment.py")
        assert feature == "checkout"
        
        feature = adapter._extract_feature_from_path("/project/tests/test_user.py")
        assert feature == "general"
    
    @patch("builtins.open", new_callable=mock_open, read_data="def test_example(): pass")
    def test_normalize_to_core_model(self, mock_file):
        """Test normalization to UnifiedTestMemory."""
        adapter = PytestAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/project/tests/test_user.py",
            test_name="test_example",
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "pytest"
        assert unified.language == "python"
        assert "test_example" in unified.test_id
        assert unified.test_name == "test_example"


class TestJUnitAdapter:
    """Test JUnit adapter."""
    
    def test_get_framework_name(self):
        """Test framework name."""
        adapter = JUnitAdapter()
        assert adapter.get_framework_name() == "junit"
    
    def test_get_language(self):
        """Test language."""
        adapter = JUnitAdapter()
        assert adapter.get_language() == "java"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        """Test test discovery."""
        mock_rglob.side_effect = [
            [Path("src/test/UserTest.java")],
            [Path("src/test/TestApi.java")],
        ]
        
        adapter = JUnitAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 2
        assert any("UserTest.java" in f for f in test_files)
        assert any("TestApi.java" in f for f in test_files)
    
    def test_normalize_to_core_model(self):
        """Test normalization to UnifiedTestMemory."""
        adapter = JUnitAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/project/src/test/UserTest.java",
            test_name="testUserRegistration",
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "junit"
        assert unified.language == "java"
        assert "testUserRegistration" in unified.test_id


class TestRobotFrameworkAdapter:
    """Test Robot Framework adapter."""
    
    def test_get_framework_name(self):
        """Test framework name."""
        adapter = RobotFrameworkAdapter()
        assert adapter.get_framework_name() == "robot"
    
    def test_get_language(self):
        """Test language."""
        adapter = RobotFrameworkAdapter()
        assert adapter.get_language() == "robot"
    
    @patch("pathlib.Path.rglob")
    def test_discover_tests(self, mock_rglob):
        """Test test discovery."""
        mock_rglob.return_value = [
            Path("tests/user.robot"),
            Path("tests/api.robot"),
        ]
        
        adapter = RobotFrameworkAdapter()
        test_files = adapter.discover_tests("/project")
        
        assert len(test_files) == 2
        assert any("user.robot" in f for f in test_files)
        assert any("api.robot" in f for f in test_files)
    
    def test_normalize_to_core_model(self):
        """Test normalization to UnifiedTestMemory."""
        adapter = RobotFrameworkAdapter()
        
        unified = adapter.normalize_to_core_model(
            test_file="/project/tests/user.robot",
            test_name="User Registration Test",
        )
        
        assert isinstance(unified, UnifiedTestMemory)
        assert unified.framework == "robot"
        assert unified.language == "robot"


class TestAdapterFactory:
    """Test adapter factory."""
    
    def test_get_pytest_adapter(self):
        """Test getting pytest adapter."""
        adapter = AdapterFactory.get_adapter("pytest")
        
        assert adapter is not None
        assert isinstance(adapter, PytestAdapter)
    
    def test_get_junit_adapter(self):
        """Test getting JUnit adapter."""
        adapter = AdapterFactory.get_adapter("junit")
        
        assert adapter is not None
        assert isinstance(adapter, JUnitAdapter)
    
    def test_get_robot_adapter(self):
        """Test getting Robot Framework adapter."""
        adapter = AdapterFactory.get_adapter("robot")
        
        assert adapter is not None
        assert isinstance(adapter, RobotFrameworkAdapter)
    
    def test_get_unsupported_adapter(self):
        """Test getting unsupported adapter."""
        adapter = AdapterFactory.get_adapter("unsupported")
        
        assert adapter is None
    
    def test_list_supported_frameworks(self):
        """Test listing supported frameworks."""
        frameworks = AdapterFactory.list_supported_frameworks()
        
        assert "pytest" in frameworks
        assert "junit" in frameworks
        assert "robot" in frameworks
    
    def test_register_custom_adapter(self):
        """Test registering custom adapter."""
        
        class CustomAdapter(PytestAdapter):
            def get_framework_name(self):
                return "custom"
        
        AdapterFactory.register_adapter("custom", CustomAdapter)
        
        adapter = AdapterFactory.get_adapter("custom")
        assert adapter is not None
        assert isinstance(adapter, CustomAdapter)


class TestNormalizeTestFunction:
    """Test normalize_test convenience function."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="def test_example(): pass")
    def test_normalize_test_pytest(self, mock_file):
        """Test normalizing pytest test."""
        unified = normalize_test(
            test_file="/test.py",
            test_name="test_example",
            framework="pytest",
        )
        
        assert unified is not None
        assert unified.framework == "pytest"
    
    def test_normalize_test_unsupported(self):
        """Test normalizing unsupported framework."""
        unified = normalize_test(
            test_file="/test.rb",
            test_name="test_example",
            framework="rspec",
        )
        
        assert unified is None
    
    @patch("builtins.open", new_callable=mock_open, read_data="def test_example(): pass")
    def test_normalize_test_with_semantic_signals(self, mock_file):
        """Test normalizing with semantic signals."""
        semantic = SemanticSignals(
            intent_text="Test user registration",
            embedding=[0.1] * 1536,
            keywords=["user", "registration"],
        )
        
        unified = normalize_test(
            test_file="/test.py",
            test_name="test_example",
            framework="pytest",
            semantic_signals=semantic,
        )
        
        assert unified is not None
        assert unified.semantic == semantic


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
