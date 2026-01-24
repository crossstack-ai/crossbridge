"""
Unit tests for assisted test generation engine.
"""

import pytest
from unittest.mock import Mock
from core.intelligence.generator import (
    AssistedTestGenerator,
    TestTemplate,
    GenerationResult,
    generate_test_template,
)
from core.intelligence.models import (
    UnifiedTestMemory,
    SemanticSignals,
    StructuralSignals,
    TestMetadata,
    APICall,
    Assertion,
    TestType,
)


class TestAssistedTestGenerator:
    """Test assisted test generation engine."""
    
    def test_generate_pytest_template(self):
        """Test pytest template generation."""
        search_engine = Mock()
        search_engine.search.return_value = []
        
        generator = AssistedTestGenerator(search_engine)
        
        result = generator.generate_test(
            user_intent="Test checkout with invalid credit card",
            framework="pytest",
            language="python",
        )
        
        assert isinstance(result, GenerationResult)
        assert len(result.templates) == 1
        
        template = result.templates[0]
        assert "def test_" in template.template_code
        assert "TODO" in template.template_code
        assert template.framework == "pytest"
        assert template.language == "python"
    
    def test_generate_junit_template(self):
        """Test JUnit template generation."""
        search_engine = Mock()
        search_engine.search.return_value = []
        
        generator = AssistedTestGenerator(search_engine)
        
        result = generator.generate_test(
            user_intent="Test user registration",
            framework="junit",
            language="java",
        )
        
        assert len(result.templates) == 1
        
        template = result.templates[0]
        assert "@Test" in template.template_code
        assert "public void" in template.template_code
        assert "TODO" in template.template_code
        assert template.framework == "junit"
        assert template.language == "java"
    
    def test_generate_test_name(self):
        """Test test name generation from intent."""
        search_engine = Mock()
        generator = AssistedTestGenerator(search_engine)
        
        name = generator._generate_test_name(
            "Test checkout with valid credit card",
            TestType.POSITIVE,
        )
        
        assert name.startswith("test_")
        assert "checkout" in name
        assert "valid" in name
        assert "credit" in name
        assert "card" in name
    
    def test_generate_test_name_special_chars(self):
        """Test test name generation with special characters."""
        search_engine = Mock()
        generator = AssistedTestGenerator(search_engine)
        
        name = generator._generate_test_name(
            "Test: User's Profile (With Special Chars!)",
            None,
        )
        
        assert name.startswith("test_")
        # Special characters should be removed
        assert ":" not in name
        assert "(" not in name
        assert ")" not in name
        assert "!" not in name
    
    def test_extract_patterns(self):
        """Test pattern extraction from similar tests."""
        search_engine = Mock()
        generator = AssistedTestGenerator(search_engine)
        
        similar_tests = [
            UnifiedTestMemory(
                test_id="test_1",
                framework="pytest",
                language="python",
                file_path="/test.py",
                test_name="test_1",
                semantic=SemanticSignals(),
                structural=StructuralSignals(
                    api_calls=[APICall(method="GET", endpoint="/api/users")],
                    assertions=[Assertion(type="assertEqual", target="status")],
                    fixtures=["db_session", "api_client"],
                ),
                metadata=TestMetadata(),
            ),
            UnifiedTestMemory(
                test_id="test_2",
                framework="pytest",
                language="python",
                file_path="/test.py",
                test_name="test_2",
                semantic=SemanticSignals(),
                structural=StructuralSignals(
                    api_calls=[APICall(method="POST", endpoint="/api/users")],
                    assertions=[Assertion(type="assertTrue", target="result")],
                    fixtures=["db_session"],
                ),
                metadata=TestMetadata(),
            ),
        ]
        
        patterns = generator._extract_patterns(similar_tests)
        
        assert len(patterns["common_api_calls"]) == 2
        assert len(patterns["common_assertions"]) == 2
        assert "db_session" in patterns["common_fixtures"]
        assert "api_client" in patterns["common_fixtures"]
    
    def test_extract_todos(self):
        """Test TODO extraction from template."""
        search_engine = Mock()
        generator = AssistedTestGenerator(search_engine)
        
        template_code = """
def test_example():
    # TODO: Setup test data
    # TODO: Make API call
    result = None
    # TODO: Add assertions
    assert False, 'TODO: Complete implementation'
"""
        
        todos = generator._extract_todos(template_code)
        
        assert len(todos) == 4
        assert "Setup test data" in todos
        assert "Make API call" in todos
        assert "Add assertions" in todos
        assert "Complete implementation" in todos
    
    def test_pytest_template_with_fixtures(self):
        """Test pytest template with fixtures."""
        search_engine = Mock()
        generator = AssistedTestGenerator(search_engine)
        
        patterns = {
            "common_fixtures": ["db_session", "api_client"],
            "common_api_calls": ["GET /api/users"],
            "common_assertions": ["assertEqual"],
            "common_setup": [],
            "common_teardown": [],
        }
        
        template_code = generator._generate_pytest_template(
            test_name="test_user_api",
            user_intent="Test user API",
            patterns=patterns,
        )
        
        assert "db_session" in template_code
        assert "api_client" in template_code
        assert "GET /api/users" in template_code
    
    def test_junit_template_with_api_calls(self):
        """Test JUnit template with API call patterns."""
        search_engine = Mock()
        generator = AssistedTestGenerator(search_engine)
        
        patterns = {
            "common_fixtures": [],
            "common_api_calls": ["POST /api/users", "GET /api/users"],
            "common_assertions": ["assertEquals"],
            "common_setup": [],
            "common_teardown": [],
        }
        
        template_code = generator._generate_junit_template(
            test_name="testUserApi",
            user_intent="Test user API",
            patterns=patterns,
        )
        
        assert "POST /api/users" in template_code
        assert "GET /api/users" in template_code
        assert "@Test" in template_code
    
    def test_build_reasoning(self):
        """Test reasoning summary generation."""
        search_engine = Mock()
        generator = AssistedTestGenerator(search_engine)
        
        similar_tests = [
            UnifiedTestMemory(
                test_id="test_1",
                framework="pytest",
                language="python",
                file_path="/test.py",
                test_name="test_1",
                semantic=SemanticSignals(),
                structural=StructuralSignals(),
                metadata=TestMetadata(),
            ),
        ]
        
        patterns = {
            "common_api_calls": ["GET /api/test"],
            "common_assertions": ["assert"],
            "common_fixtures": [],
            "common_setup": [],
            "common_teardown": [],
        }
        
        reasoning = generator._build_reasoning(
            "Test API endpoint",
            similar_tests,
            patterns,
        )
        
        assert "Test API endpoint" in reasoning
        assert "test_1" in reasoning
        assert "GET /api/test" in reasoning
    
    def test_generic_template_fallback(self):
        """Test generic template for unsupported framework."""
        search_engine = Mock()
        generator = AssistedTestGenerator(search_engine)
        
        template_code = generator._generate_generic_template(
            test_name="test_custom",
            user_intent="Test custom framework",
            framework="custom_framework",
            language="ruby",
        )
        
        assert "custom_framework" in template_code
        assert "ruby" in template_code
        assert "TODO" in template_code


class TestGenerationStructures:
    """Test generation data structures."""
    
    def test_test_template_creation(self):
        """Test creation of test template."""
        template = TestTemplate(
            test_name="test_checkout",
            framework="pytest",
            language="python",
            template_code="def test_checkout():\n    pass",
            similar_tests=["test_1", "test_2"],
            todo_items=["Complete implementation"],
            reasoning="Based on similar tests",
        )
        
        assert template.test_name == "test_checkout"
        assert template.framework == "pytest"
        assert len(template.similar_tests) == 2
        assert len(template.todo_items) == 1
    
    def test_generation_result_creation(self):
        """Test creation of generation result."""
        templates = [
            TestTemplate(
                test_name="test_1",
                framework="pytest",
                language="python",
                template_code="code",
                similar_tests=[],
                todo_items=[],
                reasoning="reason",
            ),
        ]
        
        result = GenerationResult(
            templates=templates,
            reasoning_summary="Generated 1 template",
            reference_tests=["ref_1", "ref_2"],
        )
        
        assert len(result.templates) == 1
        assert "1 template" in result.reasoning_summary
        assert len(result.reference_tests) == 2


class TestConvenienceFunction:
    """Test convenience function."""
    
    def test_generate_test_template_function(self):
        """Test generate_test_template convenience function."""
        search_engine = Mock()
        search_engine.search.return_value = []
        
        result = generate_test_template(
            user_intent="Test user login",
            search_engine=search_engine,
            framework="pytest",
            language="python",
        )
        
        assert isinstance(result, GenerationResult)
        assert len(result.templates) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
