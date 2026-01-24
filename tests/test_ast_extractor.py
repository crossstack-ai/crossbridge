"""
Unit tests for AST extraction layer.
"""

import pytest
from core.intelligence.ast_extractor import (
    PythonASTExtractor,
    ASTExtractorFactory,
    extract_from_file,
)
from core.intelligence.models import APICall, Assertion


class TestPythonASTExtractor:
    """Test Python AST extractor."""
    
    def test_extract_api_calls(self):
        """Test extraction of API calls."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_checkout():
    response = requests.get('/api/checkout')
    assert response.status_code == 200
"""
        
        signals = extractor.extract(source_code, "test_checkout")
        
        assert len(signals.api_calls) == 1
        assert signals.api_calls[0].method == "GET"
        assert signals.api_calls[0].endpoint == "/api/checkout"
    
    def test_extract_multiple_api_calls(self):
        """Test extraction of multiple API calls."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_user_flow():
    response1 = requests.post('/api/users', json={'name': 'test'})
    user_id = response1.json()['id']
    response2 = requests.get('/api/users/123')
    response3 = requests.delete('/api/users/123')
"""
        
        signals = extractor.extract(source_code, "test_user_flow")
        
        assert len(signals.api_calls) >= 2  # Should detect POST and at least one more
        methods = [call.method for call in signals.api_calls]
        assert "POST" in methods
    
    def test_extract_assertions(self):
        """Test extraction of assertions."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_validation():
    result = process_data()
    assert result == 42
    assert result > 0
    assert result in [40, 41, 42]
"""
        
        signals = extractor.extract(source_code, "test_validation")
        
        assert len(signals.assertions) >= 3
    
    def test_extract_unittest_assertions(self):
        """Test extraction of unittest-style assertions."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_validation(self):
    result = process_data()
    self.assertEqual(result, 42)
    self.assertTrue(result > 0)
    self.assertIn(result, [40, 41, 42])
"""
        
        signals = extractor.extract(source_code, "test_validation")
        
        assert len(signals.assertions) >= 3
        types = [a.type for a in signals.assertions]
        assert any("assertEqual" in t for t in types)
    
    def test_extract_status_codes(self):
        """Test extraction of expected status codes."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_status_codes():
    response = requests.get('/api/test')
    assert response.status_code == 200
    
    response2 = requests.post('/api/invalid')
    assert response2.status_code == 404
"""
        
        signals = extractor.extract(source_code, "test_status_codes")
        
        assert 200 in signals.expected_status_codes
        assert 404 in signals.expected_status_codes
    
    def test_extract_exceptions(self):
        """Test extraction of expected exceptions."""
        extractor = PythonASTExtractor()
        
        source_code = """
import pytest

def test_invalid_input():
    with pytest.raises(ValueError):
        process_invalid_data()
"""
        
        signals = extractor.extract(source_code, "test_invalid_input")
        
        assert "ValueError" in signals.expected_exceptions
    
    def test_detect_retry_logic(self):
        """Test detection of retry logic."""
        extractor = PythonASTExtractor()
        
        source_code = """
@retry(max_attempts=3)
def test_flaky_service():
    response = call_external_service()
    assert response.ok
"""
        
        signals = extractor.extract(source_code, "test_flaky_service")
        
        assert signals.has_retry_logic is True
    
    def test_detect_timeout(self):
        """Test detection of timeout."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_slow_service():
    response = requests.get('/api/slow', timeout=5)
    assert response.ok
"""
        
        signals = extractor.extract(source_code, "test_slow_service")
        
        assert signals.has_timeout is True
    
    def test_detect_async(self):
        """Test detection of async/await."""
        extractor = PythonASTExtractor()
        
        source_code = """
async def test_async_operation():
    result = await async_function()
    assert result is not None
"""
        
        signals = extractor.extract(source_code, "test_async_operation")
        
        assert signals.has_async_await is True
    
    def test_detect_loops(self):
        """Test detection of loops."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_batch_processing():
    items = [1, 2, 3]
    for item in items:
        process(item)
    assert True
"""
        
        signals = extractor.extract(source_code, "test_batch_processing")
        
        assert signals.has_loop is True
    
    def test_detect_conditionals(self):
        """Test detection of conditional logic."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_conditional_logic():
    result = get_result()
    if result > 0:
        assert result == 42
    else:
        assert result == 0
"""
        
        signals = extractor.extract(source_code, "test_conditional_logic")
        
        assert signals.has_conditional is True
    
    def test_extract_fixtures(self):
        """Test extraction of pytest fixtures."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_with_fixtures(db_session, api_client, mock_user):
    user = mock_user()
    db_session.add(user)
    response = api_client.get('/api/users')
    assert response.ok
"""
        
        signals = extractor.extract(source_code, "test_with_fixtures")
        
        assert "db_session" in signals.fixtures
        assert "api_client" in signals.fixtures
        assert "mock_user" in signals.fixtures
    
    def test_extract_from_empty_test(self):
        """Test extraction from empty test."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_empty():
    pass
"""
        
        signals = extractor.extract(source_code, "test_empty")
        
        assert len(signals.api_calls) == 0
        assert len(signals.assertions) == 0
    
    def test_extract_with_syntax_error(self):
        """Test extraction with syntax error."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_invalid_syntax(
    # Missing closing paren
"""
        
        signals = extractor.extract(source_code, "test_invalid_syntax")
        
        # Should return empty signals, not crash
        assert len(signals.api_calls) == 0
    
    def test_test_function_not_found(self):
        """Test when test function not found."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_actual():
    assert True
"""
        
        signals = extractor.extract(source_code, "test_nonexistent")
        
        # Should return empty signals
        assert len(signals.api_calls) == 0


class TestASTExtractorFactory:
    """Test AST extractor factory."""
    
    def test_get_python_extractor(self):
        """Test getting Python extractor."""
        extractor = ASTExtractorFactory.get_extractor("python")
        
        assert extractor is not None
        assert isinstance(extractor, PythonASTExtractor)
    
    def test_get_unsupported_language(self):
        """Test getting extractor for unsupported language."""
        extractor = ASTExtractorFactory.get_extractor("ruby")
        
        assert extractor is None
    
    def test_register_custom_extractor(self):
        """Test registering custom extractor."""
        
        class CustomExtractor(PythonASTExtractor):
            def supports_language(self):
                return "custom"
        
        ASTExtractorFactory.register_extractor("custom", CustomExtractor)
        
        extractor = ASTExtractorFactory.get_extractor("custom")
        assert extractor is not None
        assert isinstance(extractor, CustomExtractor)


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_rest_assured_style_test(self):
        """Test REST Assured style API test."""
        extractor = PythonASTExtractor()
        
        source_code = """
def test_api_chain():
    # Create user
    response1 = requests.post('/api/users', json={
        'name': 'Test User',
        'email': 'test@example.com'
    })
    assert response1.status_code == 201
    user_id = response1.json()['id']
    
    # Get user
    response2 = requests.get('/api/users/123')
    assert response2.status_code == 200
    assert response2.json()['name'] == 'Test User'
    
    # Update user
    response3 = requests.put('/api/users/123', json={
        'name': 'Updated User'
    })
    assert response3.status_code == 200
    
    # Delete user
    response4 = requests.delete('/api/users/123')
    assert response4.status_code == 204
"""
        
        signals = extractor.extract(source_code, "test_api_chain")
        
        # Should detect multiple API calls (at least POST, GET, PUT, DELETE with static endpoints)
        assert len(signals.api_calls) >= 2
        
        # Should detect multiple assertions
        assert len(signals.assertions) >= 4
        
        # Should detect status codes
        assert 201 in signals.expected_status_codes
        assert 200 in signals.expected_status_codes
        assert 204 in signals.expected_status_codes
    
    def test_parametrized_test(self):
        """Test parametrized test."""
        extractor = PythonASTExtractor()
        
        source_code = """
@pytest.mark.parametrize('input,expected', [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    result = double(input)
    assert result == expected
"""
        
        signals = extractor.extract(source_code, "test_double")
        
        assert len(signals.assertions) >= 1
        assert "input" in signals.fixtures
        assert "expected" in signals.fixtures


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
