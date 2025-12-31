"""
Unit tests for Selenium + SpecFlow + .NET adapter.

Tests cover:
- SpecFlow project detection
- Feature file parsing
- Step definition extraction
- Test discovery
- Test execution
- Page object detection
- Error handling
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from adapters.selenium_specflow_dotnet import (
    SeleniumSpecFlowAdapter,
    SeleniumSpecFlowExtractor,
    SpecFlowProjectDetector,
    SpecFlowProjectConfig,
    SpecFlowFeatureParser,
    SpecFlowStepDefinitionParser,
    DotNetTestFramework,
)


class TestSpecFlowProjectDetector:
    """Test SpecFlow project detection."""
    
    def test_detect_specflow_project_with_nunit(self, tmp_path):
        """Test detection of SpecFlow project with NUnit."""
        # Create .csproj file
        csproj = tmp_path / "TestProject.csproj"
        csproj.write_text("""<?xml version="1.0"?>
<Project Sdk="Microsoft.NET.Sdk">
    <ItemGroup>
        <PackageReference Include="SpecFlow" Version="3.9.0" />
        <PackageReference Include="SpecFlow.NUnit" Version="3.9.0" />
        <PackageReference Include="NUnit" Version="3.13.0" />
        <PackageReference Include="Selenium.WebDriver" Version="4.0.0" />
    </ItemGroup>
</Project>
""", encoding='utf-8')
        
        # Create features directory
        features_dir = tmp_path / "Features"
        features_dir.mkdir()
        (features_dir / "Login.feature").write_text("Feature: Login", encoding='utf-8')
        
        # Detect
        detector = SpecFlowProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.test_framework == DotNetTestFramework.NUNIT
        assert config.has_selenium is True
        assert config.specflow_version == "3.9.0"
        assert config.features_dir == features_dir
    
    def test_detect_specflow_project_with_mstest(self, tmp_path):
        """Test detection of SpecFlow project with MSTest."""
        csproj = tmp_path / "TestProject.csproj"
        csproj.write_text("""<?xml version="1.0"?>
<Project Sdk="Microsoft.NET.Sdk">
    <ItemGroup>
        <PackageReference Include="SpecFlow.Tools.MsBuild" Version="3.9.0" />
        <PackageReference Include="MSTest.TestFramework" Version="2.2.0" />
        <PackageReference Include="Selenium.WebDriver" Version="4.0.0" />
    </ItemGroup>
</Project>
""", encoding='utf-8')
        
        features_dir = tmp_path / "Features"
        features_dir.mkdir()
        
        detector = SpecFlowProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.test_framework == DotNetTestFramework.MSTEST
        assert config.has_selenium is True
    
    def test_detect_specflow_project_with_xunit(self, tmp_path):
        """Test detection of SpecFlow project with xUnit."""
        csproj = tmp_path / "TestProject.csproj"
        csproj.write_text("""<?xml version="1.0"?>
<Project Sdk="Microsoft.NET.Sdk">
    <ItemGroup>
        <PackageReference Include="SpecFlow.xUnit" Version="3.9.0" />
        <PackageReference Include="xunit" Version="2.4.0" />
    </ItemGroup>
</Project>
""", encoding='utf-8')
        
        detector = SpecFlowProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.test_framework == DotNetTestFramework.XUNIT
    
    def test_detect_no_specflow_project(self, tmp_path):
        """Test detection returns None for non-SpecFlow project."""
        csproj = tmp_path / "Regular.csproj"
        csproj.write_text("""<?xml version="1.0"?>
<Project Sdk="Microsoft.NET.Sdk">
    <ItemGroup>
        <PackageReference Include="NUnit" Version="3.13.0" />
    </ItemGroup>
</Project>
""", encoding='utf-8')
        
        detector = SpecFlowProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is None
    
    def test_detect_features_directory(self, tmp_path):
        """Test detection of various feature directory names."""
        csproj = tmp_path / "TestProject.csproj"
        csproj.write_text("""<?xml version="1.0"?>
<Project>
    <ItemGroup>
        <PackageReference Include="SpecFlow" />
        <PackageReference Include="NUnit" />
    </ItemGroup>
</Project>
""", encoding='utf-8')
        
        # Create features with lowercase name
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        (features_dir / "test.feature").write_text("Feature: Test", encoding='utf-8')
        
        detector = SpecFlowProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.features_dir.name.lower() == "features"


class TestSpecFlowFeatureParser:
    """Test feature file parsing."""
    
    def test_parse_simple_feature(self, tmp_path):
        """Test parsing a simple feature file."""
        feature_file = tmp_path / "Login.feature"
        feature_file.write_text("""Feature: User Login
    As a user
    I want to log in
    So that I can access my account

Scenario: Successful login with valid credentials
    Given I am on the login page
    When I enter valid credentials
    And I click the login button
    Then I should see the dashboard
""", encoding='utf-8')
        
        parser = SpecFlowFeatureParser()
        result = parser.parse_feature(feature_file)
        
        assert result['feature'] == "User Login"
        assert len(result['scenarios']) == 1
        assert result['scenarios'][0]['name'] == "Successful login with valid credentials"
        assert result['scenarios'][0]['type'] == "Scenario"
    
    def test_parse_feature_with_tags(self, tmp_path):
        """Test parsing feature with tags."""
        feature_file = tmp_path / "Login.feature"
        feature_file.write_text("""@smoke @login
Feature: User Login

@positive
Scenario: Successful login
    Given I am on the login page
    When I enter valid credentials
    Then I should see the dashboard

@negative
Scenario: Failed login
    Given I am on the login page
    When I enter invalid credentials
    Then I should see an error message
""", encoding='utf-8')
        
        parser = SpecFlowFeatureParser()
        result = parser.parse_feature(feature_file)
        
        assert 'smoke' in result['tags']
        assert 'login' in result['tags']
        assert 'positive' in result['tags']
        assert 'negative' in result['tags']
        assert len(result['scenarios']) == 2
    
    def test_parse_scenario_outline(self, tmp_path):
        """Test parsing scenario outline."""
        feature_file = tmp_path / "Login.feature"
        feature_file.write_text("""Feature: Login

Scenario Outline: Login with different credentials
    Given I am on the login page
    When I enter username "<username>" and password "<password>"
    Then I should see "<result>"

    Examples:
    | username | password | result |
    | admin    | pass123  | success |
    | user     | wrong    | error   |
""", encoding='utf-8')
        
        parser = SpecFlowFeatureParser()
        result = parser.parse_feature(feature_file)
        
        assert len(result['scenarios']) == 1
        assert result['scenarios'][0]['type'] == "Scenario Outline"


class TestSpecFlowStepDefinitionParser:
    """Test step definition parsing."""
    
    def test_parse_step_definitions(self, tmp_path):
        """Test parsing C# step definition file."""
        cs_file = tmp_path / "LoginSteps.cs"
        cs_file.write_text("""using TechTalk.SpecFlow;

[Binding]
public class LoginSteps
{
    [Given(@"I am on the login page")]
    public void GivenIAmOnTheLoginPage()
    {
        // code
    }

    [When(@"I enter username \\"(.*)\\" and password \\"(.*)\\"")]
    public void WhenIEnterCredentials(string username, string password)
    {
        // code
    }

    [Then(@"I should see the dashboard")]
    public async Task ThenIShouldSeeDashboard()
    {
        // code
    }
}
""", encoding='utf-8')
        
        parser = SpecFlowStepDefinitionParser()
        step_defs = parser.parse_step_definitions(cs_file)
        
        assert len(step_defs) == 3
        assert step_defs[0]['keyword'] == 'Given'
        assert step_defs[0]['pattern'] == 'I am on the login page'
        assert step_defs[0]['method'] == 'GivenIAmOnTheLoginPage'
        
        assert step_defs[1]['keyword'] == 'When'
        assert step_defs[1]['method'] == 'WhenIEnterCredentials'
        
        assert step_defs[2]['keyword'] == 'Then'
        assert step_defs[2]['method'] == 'ThenIShouldSeeDashboard'


class TestSeleniumSpecFlowAdapter:
    """Test SeleniumSpecFlowAdapter."""
    
    def test_adapter_requires_valid_project(self, tmp_path):
        """Test adapter raises error for invalid project."""
        with pytest.raises(ValueError, match="Could not detect SpecFlow project"):
            SeleniumSpecFlowAdapter(str(tmp_path))
    
    def test_adapter_with_manual_config(self, tmp_path):
        """Test adapter accepts manual configuration."""
        config = SpecFlowProjectConfig(
            project_file=tmp_path / "Test.csproj",
            test_framework=DotNetTestFramework.NUNIT,
            features_dir=tmp_path / "Features",
            step_definitions_dir=tmp_path / "Steps",
            project_root=tmp_path,
            has_selenium=True
        )
        
        adapter = SeleniumSpecFlowAdapter(str(tmp_path), config=config)
        
        assert adapter.config == config
    
    def test_discover_tests(self, tmp_path):
        """Test discovering tests from feature files."""
        # Setup
        features_dir = tmp_path / "Features"
        features_dir.mkdir()
        
        feature1 = features_dir / "Login.feature"
        feature1.write_text("""Feature: User Login

Scenario: Successful login
    Given I am on the login page

Scenario: Failed login
    Given I am on the login page
""", encoding='utf-8')
        
        feature2 = features_dir / "Checkout.feature"
        feature2.write_text("""Feature: Checkout

Scenario: Complete checkout
    Given I have items in cart
""", encoding='utf-8')
        
        config = SpecFlowProjectConfig(
            project_file=tmp_path / "Test.csproj",
            test_framework=DotNetTestFramework.NUNIT,
            features_dir=features_dir,
            step_definitions_dir=tmp_path / "Steps",
            project_root=tmp_path
        )
        
        adapter = SeleniumSpecFlowAdapter(str(tmp_path), config=config)
        tests = adapter.discover_tests()
        
        assert len(tests) == 3
        assert "User Login.Successful login" in tests
        assert "User Login.Failed login" in tests
        assert "Checkout.Complete checkout" in tests
    
    @patch("subprocess.run")
    def test_run_tests(self, mock_run, tmp_path):
        """Test running tests with dotnet test."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Tests passed"
        mock_run.return_value = mock_result
        
        config = SpecFlowProjectConfig(
            project_file=tmp_path / "Test.csproj",
            test_framework=DotNetTestFramework.NUNIT,
            features_dir=tmp_path / "Features",
            step_definitions_dir=tmp_path / "Steps",
            project_root=tmp_path
        )
        
        adapter = SeleniumSpecFlowAdapter(str(tmp_path), config=config)
        results = adapter.run_tests()
        
        assert mock_run.called
        assert len(results) >= 1
        
        # Verify command structure
        call_args = mock_run.call_args[0][0]
        assert "dotnet" in call_args
        assert "test" in call_args
    
    @patch("subprocess.run")
    def test_run_tests_with_tags(self, mock_run, tmp_path):
        """Test running tests with tag filtering."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        config = SpecFlowProjectConfig(
            project_file=tmp_path / "Test.csproj",
            test_framework=DotNetTestFramework.NUNIT,
            features_dir=tmp_path / "Features",
            step_definitions_dir=tmp_path / "Steps",
            project_root=tmp_path
        )
        
        adapter = SeleniumSpecFlowAdapter(str(tmp_path), config=config)
        results = adapter.run_tests(tags=["smoke"])
        
        # Verify tag filter was applied
        call_args = mock_run.call_args[0][0]
        assert "--filter" in call_args
        assert any("smoke" in arg for arg in call_args)
    
    def test_get_config_info(self, tmp_path):
        """Test getting configuration information."""
        config = SpecFlowProjectConfig(
            project_file=tmp_path / "Test.csproj",
            test_framework=DotNetTestFramework.NUNIT,
            features_dir=tmp_path / "Features",
            step_definitions_dir=tmp_path / "Steps",
            project_root=tmp_path,
            has_selenium=True,
            specflow_version="3.9.0"
        )
        
        adapter = SeleniumSpecFlowAdapter(str(tmp_path), config=config)
        info = adapter.get_config_info()
        
        assert info['test_framework'] == 'nunit'
        assert info['has_selenium'] == 'True'
        assert info['specflow_version'] == '3.9.0'


class TestSeleniumSpecFlowExtractor:
    """Test SeleniumSpecFlowExtractor."""
    
    def test_extractor_requires_valid_project(self, tmp_path):
        """Test extractor raises error for invalid project."""
        with pytest.raises(ValueError, match="Could not detect SpecFlow project"):
            SeleniumSpecFlowExtractor(str(tmp_path))
    
    def test_extract_tests(self, tmp_path):
        """Test extracting test metadata."""
        # Setup project
        csproj = tmp_path / "Test.csproj"
        csproj.write_text("""<?xml version="1.0"?>
<Project>
    <ItemGroup>
        <PackageReference Include="SpecFlow" />
        <PackageReference Include="NUnit" />
    </ItemGroup>
</Project>
""", encoding='utf-8')
        
        features_dir = tmp_path / "Features"
        features_dir.mkdir()
        
        feature = features_dir / "Login.feature"
        feature.write_text("""@smoke
Feature: Login

@positive
Scenario: Successful login
    Given I am on the login page
""", encoding='utf-8')
        
        extractor = SeleniumSpecFlowExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].test_name == "Login.Successful login"
        assert "smoke" in tests[0].tags
        assert "positive" in tests[0].tags
        assert tests[0].framework == "specflow-nunit"
        assert tests[0].test_type == "bdd"
        assert tests[0].language == "csharp"
    
    def test_extract_step_definitions(self, tmp_path):
        """Test extracting step definitions."""
        # Setup project
        csproj = tmp_path / "Test.csproj"
        csproj.write_text("""<?xml version="1.0"?>
<Project>
    <ItemGroup>
        <PackageReference Include="SpecFlow" />
        <PackageReference Include="NUnit" />
    </ItemGroup>
</Project>
""", encoding='utf-8')
        
        steps_dir = tmp_path / "StepDefinitions"
        steps_dir.mkdir()
        
        steps_file = steps_dir / "LoginSteps.cs"
        steps_file.write_text("""
[Binding]
public class LoginSteps
{
    [Given(@"I am on the login page")]
    public void GivenIAmOnLoginPage()
    {
    }
}
""", encoding='utf-8')
        
        extractor = SeleniumSpecFlowExtractor(str(tmp_path))
        step_defs = extractor.extract_step_definitions()
        
        assert len(step_defs) == 1
        assert step_defs[0]['keyword'] == 'Given'
        assert step_defs[0]['pattern'] == 'I am on the login page'
    
    def test_extract_page_objects(self, tmp_path):
        """Test extracting page objects."""
        # Setup project
        csproj = tmp_path / "Test.csproj"
        csproj.write_text("""<?xml version="1.0"?>
<Project>
    <ItemGroup>
        <PackageReference Include="SpecFlow" />
        <PackageReference Include="NUnit" />
        <PackageReference Include="Selenium.WebDriver" />
    </ItemGroup>
</Project>
""", encoding='utf-8')
        
        pages_dir = tmp_path / "Pages"
        pages_dir.mkdir()
        
        page_file = pages_dir / "LoginPage.cs"
        page_file.write_text("""using OpenQA.Selenium;

public class LoginPage
{
    private IWebDriver driver;
    
    public IWebElement UsernameField => driver.FindElement(By.Id("username"));
}
""", encoding='utf-8')
        
        extractor = SeleniumSpecFlowExtractor(str(tmp_path))
        page_objects = extractor.extract_page_objects()
        
        assert len(page_objects) == 1
        assert page_objects[0]['class_name'] == 'LoginPage'
        assert page_objects[0]['has_selenium'] is True


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_parse_malformed_feature_file(self, tmp_path):
        """Test parsing handles malformed feature files."""
        feature_file = tmp_path / "Bad.feature"
        feature_file.write_text("This is not a valid feature file", encoding='utf-8')
        
        parser = SpecFlowFeatureParser()
        result = parser.parse_feature(feature_file)
        
        # Should not crash, returns basic info
        assert 'feature' in result
        assert 'scenarios' in result
    
    def test_parse_empty_step_definition_file(self, tmp_path):
        """Test parsing handles empty step definition files."""
        cs_file = tmp_path / "Empty.cs"
        cs_file.write_text("", encoding='utf-8')
        
        parser = SpecFlowStepDefinitionParser()
        step_defs = parser.parse_step_definitions(cs_file)
        
        assert step_defs == []
    
    @patch("subprocess.run")
    def test_adapter_handles_timeout(self, mock_run, tmp_path):
        """Test adapter handles subprocess timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("dotnet", 300)
        
        config = SpecFlowProjectConfig(
            project_file=tmp_path / "Test.csproj",
            test_framework=DotNetTestFramework.NUNIT,
            features_dir=tmp_path / "Features",
            step_definitions_dir=tmp_path / "Steps",
            project_root=tmp_path
        )
        
        adapter = SeleniumSpecFlowAdapter(str(tmp_path), config=config)
        results = adapter.run_tests()
        
        # Should return error result, not crash
        assert len(results) == 1
        assert results[0].status == "fail"
        assert "timed out" in results[0].message.lower()
    
    def test_detector_handles_invalid_xml(self, tmp_path):
        """Test detector handles malformed csproj files."""
        csproj = tmp_path / "Bad.csproj"
        csproj.write_text("<<This is invalid XML>>", encoding='utf-8')
        
        detector = SpecFlowProjectDetector(str(tmp_path))
        config = detector.detect()
        
        # Should return None, not crash
        assert config is None
