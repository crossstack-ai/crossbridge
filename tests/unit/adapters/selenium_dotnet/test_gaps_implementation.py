"""
Tests for Selenium .NET Gap Implementations.

Tests Gap 5.1 (Adapter Implementation) and Gap 5.2 (Failure Classification).
"""

import pytest
from pathlib import Path
from adapters.selenium_dotnet.failure_classifier import (
    SeleniumDotNetFailureType,
    classify_selenium_dotnet_failure,
)
from adapters.selenium_dotnet.adapter import (
    SeleniumDotNetProjectDetector,
    SeleniumDotNetExtractor,
    DotNetTestFramework,
)


class TestSeleniumDotNetFailureClassification:
    """Tests for Gap 5.2: Selenium .NET Failure Classification."""
    
    def test_no_such_element_exception(self):
        """Test classification of NoSuchElementException."""
        error = "OpenQA.Selenium.NoSuchElementException: no such element: Unable to locate element: {\"method\":\"id\",\"selector\":\"submit-btn\"}"
        
        classification = classify_selenium_dotnet_failure(
            error,
            "",
            "TestUserLogin",
            "NoSuchElementException"
        )
        
        assert classification.failure_type == SeleniumDotNetFailureType.NO_SUCH_ELEMENT
        assert classification.confidence > 0.7
        assert classification.is_intermittent is False
    
    def test_stale_element_exception(self):
        """Test classification of StaleElementReferenceException."""
        error = "OpenQA.Selenium.StaleElementReferenceException: stale element reference: element is no longer attached to the DOM"
        stack = """at MyProject.Tests.LoginTests.TestLogin() in C:\\Project\\Tests\\LoginTests.cs:line 42
at NUnit.Framework.Internal.TaskAwaitAdapter.GenericAdapter`1.GetResult()"""
        
        classification = classify_selenium_dotnet_failure(
            error,
            stack,
            "TestLogin",
            "StaleElementReferenceException"
        )
        
        assert classification.failure_type == SeleniumDotNetFailureType.STALE_ELEMENT
        assert classification.is_intermittent is True
        assert classification.location is not None
        assert classification.location.file_path.endswith("LoginTests.cs")
        assert classification.location.line_number == 42
    
    def test_element_not_interactable(self):
        """Test classification of element not interactable error."""
        error = "OpenQA.Selenium.ElementNotInteractableException: element click intercepted"
        
        classification = classify_selenium_dotnet_failure(error)
        
        assert classification.failure_type == SeleniumDotNetFailureType.ELEMENT_NOT_INTERACTABLE
        assert classification.is_intermittent is True
    
    def test_timeout_exception(self):
        """Test classification of timeout exception."""
        error = "OpenQA.Selenium.WebDriverTimeoutException: Timed out after 30 seconds"
        
        classification = classify_selenium_dotnet_failure(
            error,
            "",
            "TestWaitForElement",
            "WebDriverTimeoutException"
        )
        
        assert classification.failure_type == SeleniumDotNetFailureType.TIMEOUT
        assert classification.is_intermittent is True
    
    def test_locator_extraction_by_id(self):
        """Test extraction of By.Id locator."""
        error = "Element not found"
        stack = """at MyProject.Pages.LoginPage.get_SubmitButton() in C:\\Project\\Pages\\LoginPage.cs:line 25
    driver.FindElement(By.Id("submit-button"))
at MyProject.Tests.LoginTests.TestLogin() in C:\\Project\\Tests\\LoginTests.cs:line 42"""
        
        classification = classify_selenium_dotnet_failure(error, stack)
        
        assert classification.locator == "submit-button"
        assert classification.locator_strategy == "Id"
    
    def test_locator_extraction_by_xpath(self):
        """Test extraction of By.XPath locator."""
        error = "Element not found"
        stack = """driver.FindElement(By.XPath("//button[@id='submit']"))"""
        
        classification = classify_selenium_dotnet_failure(error, stack)
        
        assert classification.locator == "//button[@id='submit']"
        assert classification.locator_strategy == "XPath"
    
    def test_locator_extraction_by_css(self):
        """Test extraction of By.CssSelector locator."""
        error = "Element not found"
        stack = """driver.FindElement(By.CssSelector("#modal .close-button"))"""
        
        classification = classify_selenium_dotnet_failure(error, stack)
        
        assert classification.locator == "#modal .close-button"
        assert classification.locator_strategy == "CssSelector"
    
    def test_page_object_detection(self):
        """Test detection of Page Object from stack trace."""
        error = "Element not found"
        stack = """at MyProject.Pages.LoginPage.UsernameField.get() in C:\\Project\\Pages\\LoginPage.cs:line 15
at MyProject.Tests.LoginTests.TestLogin() in C:\\Project\\Tests\\LoginTests.cs:line 42"""
        
        classification = classify_selenium_dotnet_failure(error, stack)
        
        assert classification.page_object == "LoginPage"
        assert classification.element_name == "UsernameField"
        assert classification.component.value == "page_object"
    
    def test_browser_name_extraction(self):
        """Test extraction of browser name from error."""
        error = "Chrome not reachable"
        
        classification = classify_selenium_dotnet_failure(error)
        
        assert classification.browser_name == "Chrome"
    
    def test_session_not_created(self):
        """Test classification of session not created error."""
        error = "OpenQA.Selenium.SessionNotCreatedException: Could not start a new session"
        
        classification = classify_selenium_dotnet_failure(
            error,
            exception_type="SessionNotCreatedException"
        )
        
        assert classification.failure_type == SeleniumDotNetFailureType.SESSION_NOT_CREATED
    
    def test_browser_crash(self):
        """Test classification of browser crash."""
        error = "session deleted because of page crash from tab crashed"
        
        classification = classify_selenium_dotnet_failure(error)
        
        assert classification.failure_type == SeleniumDotNetFailureType.BROWSER_CRASH
        assert classification.is_intermittent is True
    
    def test_network_error(self):
        """Test classification of network error."""
        error = "Connection refused when trying to connect to remote server"
        
        classification = classify_selenium_dotnet_failure(error)
        
        assert classification.failure_type == SeleniumDotNetFailureType.NETWORK_ERROR
        assert classification.is_intermittent is True
    
    def test_assertion_failure(self):
        """Test classification of assertion failure."""
        error = "NUnit.Framework.AssertionException: Expected: True\nBut was: False"
        
        classification = classify_selenium_dotnet_failure(
            error,
            exception_type="AssertionException"
        )
        
        assert classification.failure_type == SeleniumDotNetFailureType.ASSERTION
        assert classification.is_intermittent is False
    
    def test_csharp_stack_trace_parsing(self):
        """Test C# stack trace parsing."""
        error = "Test error"
        stack = """at MyProject.Pages.HomePage.ClickButton() in C:\\Project\\Pages\\HomePage.cs:line 30
at MyProject.Tests.HomeTests.TestNavigation() in C:\\Project\\Tests\\HomeTests.cs:line 15
at NUnit.Framework.Internal.TaskAwaitAdapter.GenericAdapter`1.GetResult()
at System.Threading.Tasks.Task.Execute()"""
        
        classification = classify_selenium_dotnet_failure(error, stack)
        
        assert len(classification.stack_trace) >= 2
        
        # First frame should be from user code
        frame1 = classification.stack_trace[0]
        assert frame1.class_name == "HomePage"
        assert frame1.function_name == "ClickButton"
        assert frame1.line_number == 30
        assert frame1.is_framework_code is False
        
        # Later frames should be framework code
        assert any(f.is_framework_code for f in classification.stack_trace)
    
    def test_no_such_window_exception(self):
        """Test classification of NoSuchWindowException."""
        error = "OpenQA.Selenium.NoSuchWindowException: no such window: window was already closed"
        
        classification = classify_selenium_dotnet_failure(
            error,
            exception_type="NoSuchWindowException"
        )
        
        assert classification.failure_type == SeleniumDotNetFailureType.NO_SUCH_WINDOW
    
    def test_javascript_error(self):
        """Test classification of JavaScript execution error."""
        error = "OpenQA.Selenium.JavaScriptException: javascript error: Cannot read property 'click' of undefined"
        
        classification = classify_selenium_dotnet_failure(
            error,
            exception_type="JavaScriptException"
        )
        
        assert classification.failure_type == SeleniumDotNetFailureType.JAVASCRIPT_ERROR


class TestSeleniumDotNetProjectDetection:
    """Tests for Gap 5.1: Selenium .NET Project Detection."""
    
    def test_detect_nunit_project(self, tmp_path):
        """Test detection of NUnit Selenium project."""
        csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Selenium.WebDriver" Version="4.15.0" />
    <PackageReference Include="NUnit" Version="3.14.0" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.5.0" />
  </ItemGroup>
</Project>"""
        
        project_file = tmp_path / "SeleniumTests.csproj"
        project_file.write_text(csproj_content)
        
        # Create a test file
        tests_dir = tmp_path / "Tests"
        tests_dir.mkdir()
        test_file = tests_dir / "LoginTests.cs"
        test_file.write_text("""
using NUnit.Framework;
using OpenQA.Selenium;

namespace SeleniumTests
{
    [TestFixture]
    public class LoginTests
    {
        [Test]
        public void TestLogin()
        {
            // Test code
        }
    }
}
""")
        
        detector = SeleniumDotNetProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.test_framework == DotNetTestFramework.NUNIT
        assert config.selenium_version == "4.15.0"
        assert config.target_framework == "net8.0"
    
    def test_detect_mstest_project(self, tmp_path):
        """Test detection of MSTest Selenium project."""
        csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Selenium.WebDriver" Version="4.10.0" />
    <PackageReference Include="MSTest.TestFramework" Version="3.0.0" />
    <PackageReference Include="MSTest.TestAdapter" Version="3.0.0" />
  </ItemGroup>
</Project>"""
        
        project_file = tmp_path / "Tests.csproj"
        project_file.write_text(csproj_content)
        
        detector = SeleniumDotNetProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.test_framework == DotNetTestFramework.MSTEST
    
    def test_detect_xunit_project(self, tmp_path):
        """Test detection of xUnit Selenium project."""
        csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Selenium.WebDriver" Version="4.12.0" />
    <PackageReference Include="xunit" Version="2.5.0" />
  </ItemGroup>
</Project>"""
        
        project_file = tmp_path / "Tests.csproj"
        project_file.write_text(csproj_content)
        
        detector = SeleniumDotNetProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.test_framework == DotNetTestFramework.XUNIT
    
    def test_exclude_specflow_project(self, tmp_path):
        """Test that SpecFlow projects are excluded."""
        csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Selenium.WebDriver" Version="4.15.0" />
    <PackageReference Include="SpecFlow" Version="3.9.0" />
    <PackageReference Include="NUnit" Version="3.14.0" />
  </ItemGroup>
</Project>"""
        
        project_file = tmp_path / "SpecFlowTests.csproj"
        project_file.write_text(csproj_content)
        
        detector = SeleniumDotNetProjectDetector(str(tmp_path))
        config = detector.detect()
        
        # Should be None because SpecFlow projects use separate adapter
        assert config is None
    
    def test_no_selenium_project(self, tmp_path):
        """Test that non-Selenium projects are not detected."""
        csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="NUnit" Version="3.14.0" />
  </ItemGroup>
</Project>"""
        
        project_file = tmp_path / "Tests.csproj"
        project_file.write_text(csproj_content)
        
        detector = SeleniumDotNetProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is None


class TestSeleniumDotNetExtractor:
    """Tests for test extraction from C# files."""
    
    def test_extract_nunit_tests(self, tmp_path):
        """Test extraction of NUnit test methods."""
        cs_file = tmp_path / "LoginTests.cs"
        cs_file.write_text("""
using NUnit.Framework;

namespace MyTests
{
    [TestFixture]
    public class LoginTests
    {
        [Test]
        public void TestValidLogin()
        {
            // Test code
        }
        
        [TestCase("user1", "pass1")]
        [TestCase("user2", "pass2")]
        public void TestLoginWithCredentials(string username, string password)
        {
            // Test code
        }
    }
}
""")
        
        extractor = SeleniumDotNetExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) >= 2
        
        test_names = [t['name'] for t in tests]
        assert "TestValidLogin" in test_names
        assert "TestLoginWithCredentials" in test_names
        
        # Check fully qualified names
        fqns = [t['fully_qualified_name'] for t in tests]
        assert any("MyTests.LoginTests.TestValidLogin" in fqn for fqn in fqns)
    
    def test_extract_mstest_tests(self, tmp_path):
        """Test extraction of MSTest test methods."""
        cs_file = tmp_path / "HomeTests.cs"
        cs_file.write_text("""
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace MyTests
{
    [TestClass]
    public class HomeTests
    {
        [TestMethod]
        public void TestHomePage()
        {
            // Test code
        }
    }
}
""")
        
        extractor = SeleniumDotNetExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) >= 1
        assert tests[0]['name'] == "TestHomePage"
        assert tests[0]['framework'] == "mstest"
    
    def test_extract_xunit_tests(self, tmp_path):
        """Test extraction of xUnit test methods."""
        cs_file = tmp_path / "SearchTests.cs"
        cs_file.write_text("""
using Xunit;

namespace MyTests
{
    public class SearchTests
    {
        [Fact]
        public void TestSearch()
        {
            // Test code
        }
        
        [Theory]
        [InlineData("keyword1")]
        [InlineData("keyword2")]
        public void TestSearchWithKeyword(string keyword)
        {
            // Test code
        }
    }
}
""")
        
        extractor = SeleniumDotNetExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) >= 2
        test_names = [t['name'] for t in tests]
        assert "TestSearch" in test_names
        assert "TestSearchWithKeyword" in test_names
    
    def test_extract_async_tests(self, tmp_path):
        """Test extraction of async test methods."""
        cs_file = tmp_path / "AsyncTests.cs"
        cs_file.write_text("""
using NUnit.Framework;
using System.Threading.Tasks;

namespace MyTests
{
    public class AsyncTests
    {
        [Test]
        public async Task TestAsyncOperation()
        {
            await Task.Delay(100);
        }
    }
}
""")
        
        extractor = SeleniumDotNetExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) >= 1
        assert tests[0]['name'] == "TestAsyncOperation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
