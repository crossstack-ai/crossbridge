"""
Tests for xUnit integration.
"""

import pytest
from pathlib import Path
from adapters.selenium_specflow_dotnet.xunit_integration import (
    SpecFlowXUnitIntegration,
    XUnitTestInfo
)


@pytest.fixture
def integration():
    return SpecFlowXUnitIntegration()


@pytest.fixture
def sample_xunit_file(tmp_path):
    """Create a sample xUnit test file."""
    cs_file = tmp_path / "LoginTests.cs"
    cs_file.write_text("""
using Xunit;
using TechTalk.SpecFlow;

namespace MyApp.Tests
{
    [Binding]
    public class LoginSteps
    {
        [Fact]
        public void TestValidLogin()
        {
            // Arrange
            var loginPage = new LoginPage();
            
            // Act
            var result = loginPage.Login("admin", "password");
            
            // Assert
            Assert.True(result);
        }
        
        [Theory]
        [InlineData("user1", "pass1")]
        [InlineData("user2", "pass2")]
        [InlineData("admin", "admin123")]
        public void TestMultipleLogins(string username, string password)
        {
            var loginPage = new LoginPage();
            var result = loginPage.Login(username, password);
            Assert.True(result);
        }
        
        [Fact]
        [Trait("Category", "Smoke")]
        [Trait("Priority", "High")]
        public void TestSmokeLogin()
        {
            Assert.True(true);
        }
    }
}
    """)
    return cs_file


def test_detect_xunit(integration, sample_xunit_file):
    """Test xUnit detection."""
    result = integration.detect_xunit(sample_xunit_file)
    assert result is True


def test_extract_xunit_tests(integration, sample_xunit_file):
    """Test extraction of xUnit tests."""
    tests = integration.extract_xunit_tests(sample_xunit_file)
    
    assert len(tests) >= 2  # TestValidLogin, TestMultipleLogins, TestSmokeLogin
    
    # Check Fact test
    fact_test = next((t for t in tests if t.test_name == "TestValidLogin"), None)
    assert fact_test is not None
    assert fact_test.test_type == "Fact"
    assert fact_test.is_theory is False
    
    # Check Theory test
    theory_test = next((t for t in tests if t.test_name == "TestMultipleLogins"), None)
    assert theory_test is not None
    assert theory_test.is_theory is True
    assert len(theory_test.theory_data) == 3


def test_extract_traits(integration, sample_xunit_file):
    """Test extraction of trait attributes."""
    tests = integration.extract_xunit_tests(sample_xunit_file)
    
    smoke_test = next((t for t in tests if t.test_name == "TestSmokeLogin"), None)
    assert smoke_test is not None
    assert "Category" in smoke_test.traits
    assert smoke_test.traits["Category"] == "Smoke"
    assert "Priority" in smoke_test.traits
    assert smoke_test.traits["Priority"] == "High"


def test_convert_to_pytest(integration, sample_xunit_file):
    """Test conversion to pytest format."""
    tests = integration.extract_xunit_tests(sample_xunit_file)
    
    # Convert first test
    fact_test = next((t for t in tests if t.test_type == "Fact"), None)
    pytest_code = integration.convert_to_pytest(fact_test)
    
    assert "def test_" in pytest_code
    assert pytest_code.strip().startswith("def test_")


def test_convert_theory_to_parametrize(integration, sample_xunit_file):
    """Test conversion of Theory to parametrize."""
    tests = integration.extract_xunit_tests(sample_xunit_file)
    
    theory_test = next((t for t in tests if t.is_theory), None)
    assert theory_test is not None
    
    pytest_code = integration.convert_to_pytest(theory_test)
    
    assert "@pytest.mark.parametrize" in pytest_code
    assert '"username"' in pytest_code or "'username'" in pytest_code
    assert '"password"' in pytest_code or "'password'" in pytest_code


def test_non_xunit_file(integration, tmp_path):
    """Test file without xUnit."""
    cs_file = tmp_path / "RegularClass.cs"
    cs_file.write_text("""
namespace MyApp
{
    public class MyClass
    {
        public void DoSomething() { }
    }
}
    """)
    
    result = integration.detect_xunit(cs_file)
    assert result is False


def test_get_required_imports(integration):
    """Test getting required imports."""
    imports = integration.get_required_imports()
    
    assert "pytest" in imports
    assert "unittest" in imports or "pytest" in imports
