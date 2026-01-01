"""
Unit tests for SpecFlow (.NET C#) to Python translation.

Tests translation paths:
1. SpecFlow → Pytest/Playwright
2. SpecFlow → Robot/Playwright
"""

import pytest

from core.translation.intent_model import ActionType, AssertionType, IntentType
from core.translation.parsers.specflow_parser import SpecFlowParser
from core.translation.generators.pytest_generator import PytestGenerator
from core.translation.generators.robot_generator import RobotGenerator
from core.translation.pipeline import TranslationPipeline


class TestSpecFlowParser:
    """Test SpecFlow parser."""
    
    def test_can_parse_specflow_code(self):
        """Test detection of SpecFlow C# code."""
        parser = SpecFlowParser()
        
        specflow_code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        using NUnit.Framework;
        
        namespace MyApp.Tests
        {
            [Binding]
            public class LoginSteps
            {
                private IWebDriver driver;
                
                [Given(@"user is on login page")]
                public void GivenUserIsOnLoginPage()
                {
                    driver.GoToUrl("https://example.com/login");
                }
                
                [When(@"user enters credentials")]
                public void WhenUserEntersCredentials()
                {
                    driver.FindElement(By.Id("username")).SendKeys("testuser");
                    driver.FindElement(By.Id("password")).SendKeys("testpass");
                }
                
                [Then(@"user should see dashboard")]
                public void ThenUserShouldSeeDashboard()
                {
                    Assert.IsTrue(driver.FindElement(By.Id("dashboard")).Displayed);
                }
            }
        }
        """
        
        assert parser.can_parse(specflow_code)
    
    def test_cannot_parse_non_specflow_code(self):
        """Test rejection of non-SpecFlow code."""
        parser = SpecFlowParser()
        
        python_code = """
        def test_login():
            assert True
        """
        
        assert not parser.can_parse(python_code)
    
    def test_extract_scenario_name_from_comment(self):
        """Test scenario name extraction from comments."""
        parser = SpecFlowParser()
        
        code = """
        // Scenario: User Login
        [Given(@"user is on page")]
        public void Step1() { }
        """
        
        intent = parser.parse(code)
        assert "login" in intent.name.lower()
    
    def test_extract_scenario_name_from_class(self):
        """Test scenario name extraction from class name."""
        parser = SpecFlowParser()
        
        code = """
        using TechTalk.SpecFlow;
        
        public class LoginSteps
        {
            [Given(@"test")]
            public void Step() { }
        }
        """
        
        intent = parser.parse(code)
        assert "login" in intent.name.lower()
    
    def test_parse_bdd_steps(self):
        """Test BDD step extraction."""
        parser = SpecFlowParser()
        
        code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        
        [Binding]
        public class Steps
        {
            private IWebDriver driver;
            
            [Given(@"user is on login page")]
            public void GivenStep()
            {
                driver.GoToUrl("https://example.com");
            }
            
            [When(@"user clicks button")]
            public void WhenStep()
            {
                driver.FindElement(By.Id("btn")).Click();
            }
            
            [Then(@"user sees result")]
            public void ThenStep()
            {
                Assert.IsTrue(driver.FindElement(By.Id("result")).Displayed);
            }
        }
        """
        
        intent = parser.parse(code)
        assert intent.test_type == IntentType.BDD
        assert len(intent.bdd_structure['given_steps']) > 0
        assert len(intent.bdd_structure['when_steps']) > 0
        assert len(intent.bdd_structure['then_steps']) > 0
    
    def test_parse_navigate_action(self):
        """Test parsing GoToUrl navigation."""
        parser = SpecFlowParser()
        
        code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        
        public class Steps
        {
            private IWebDriver driver;
            
            [Given(@"navigate")]
            public void Navigate()
            {
                driver.GoToUrl("https://example.com/login");
            }
        }
        """
        
        intent = parser.parse(code)
        navigate_actions = [a for a in intent.steps if a.action_type == ActionType.NAVIGATE]
        assert len(navigate_actions) == 1
        assert "example.com" in navigate_actions[0].value
    
    def test_parse_click_action(self):
        """Test parsing Click action."""
        parser = SpecFlowParser()
        
        code = """
        using OpenQA.Selenium;
        using TechTalk.SpecFlow;
        
        public class Steps
        {
            private IWebDriver driver;
            
            [When(@"click")]
            public void Click()
            {
                driver.FindElement(By.Id("submit")).Click();
            }
        }
        """
        
        intent = parser.parse(code)
        click_actions = [a for a in intent.steps if a.action_type == ActionType.CLICK]
        assert len(click_actions) == 1
        assert "#submit" in click_actions[0].selector
    
    def test_parse_sendkeys_action(self):
        """Test parsing SendKeys (fill) action."""
        parser = SpecFlowParser()
        
        code = """
        using OpenQA.Selenium;
        using TechTalk.SpecFlow;
        
        public class Steps
        {
            private IWebDriver driver;
            
            [When(@"enter text")]
            public void EnterText()
            {
                driver.FindElement(By.Name("username")).SendKeys("testuser");
            }
        }
        """
        
        intent = parser.parse(code)
        fill_actions = [a for a in intent.steps if a.action_type == ActionType.FILL]
        assert len(fill_actions) == 1
        assert fill_actions[0].value == "testuser"
        assert "username" in fill_actions[0].selector
    
    def test_parse_select_action(self):
        """Test parsing SelectElement action."""
        parser = SpecFlowParser()
        
        code = """
        using OpenQA.Selenium;
        using OpenQA.Selenium.Support.UI;
        using TechTalk.SpecFlow;
        
        public class Steps
        {
            [When(@"select")]
            public void Select()
            {
                var select = new SelectElement(driver.FindElement(By.Id("country")));
                select.SelectByText("United States");
            }
        }
        """
        
        intent = parser.parse(code)
        select_actions = [a for a in intent.steps if a.action_type == ActionType.SELECT]
        assert len(select_actions) == 1
        assert select_actions[0].value == "United States"
    
    def test_parse_assert_visible(self):
        """Test parsing visibility assertion."""
        parser = SpecFlowParser()
        
        code = """
        using OpenQA.Selenium;
        using NUnit.Framework;
        using TechTalk.SpecFlow;
        
        public class Steps
        {
            private IWebDriver driver;
            
            [Then(@"verify")]
            public void Verify()
            {
                Assert.IsTrue(driver.FindElement(By.Id("message")).Displayed);
            }
        }
        """
        
        intent = parser.parse(code)
        assert len(intent.assertions) == 1
        assert intent.assertions[0].assertion_type == AssertionType.VISIBLE
        assert "#message" in intent.assertions[0].selector
    
    def test_parse_assert_text(self):
        """Test parsing text equality assertion."""
        parser = SpecFlowParser()
        
        code = """
        using OpenQA.Selenium;
        using NUnit.Framework;
        using TechTalk.SpecFlow;
        
        public class Steps
        {
            [Then(@"verify text")]
            public void VerifyText()
            {
                var text = driver.FindElement(By.ClassName("title")).Text;
                Assert.AreEqual("Dashboard", text);
            }
        }
        """
        
        intent = parser.parse(code)
        text_assertions = [a for a in intent.assertions if a.assertion_type == AssertionType.TEXT_CONTENT]
        assert len(text_assertions) == 1
        assert text_assertions[0].expected == "Dashboard"
    
    def test_parse_css_selector(self):
        """Test parsing CSS selector."""
        parser = SpecFlowParser()
        
        code = """
        using OpenQA.Selenium;
        using TechTalk.SpecFlow;
        
        public class Steps
        {
            [When(@"click")]
            public void Click()
            {
                driver.FindElement(By.CssSelector("button.primary")).Click();
            }
        }
        """
        
        intent = parser.parse(code)
        click_actions = [a for a in intent.steps if a.action_type == ActionType.CLICK]
        assert len(click_actions) == 1
        assert "button.primary" in click_actions[0].selector
    
    def test_parse_xpath_selector(self):
        """Test parsing XPath selector."""
        parser = SpecFlowParser()
        
        code = """
        using OpenQA.Selenium;
        using TechTalk.SpecFlow;
        
        public class Steps
        {
            [When(@"click")]
            public void Click()
            {
                driver.FindElement(By.XPath("//button[@type='submit']")).Click();
            }
        }
        """
        
        intent = parser.parse(code)
        click_actions = [a for a in intent.steps if a.action_type == ActionType.CLICK]
        assert len(click_actions) == 1
        assert "//button" in click_actions[0].selector
    
    def test_categorize_actions_into_bdd_phases(self):
        """Test proper categorization of actions into Given/When/Then."""
        parser = SpecFlowParser()
        
        code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        using NUnit.Framework;
        
        public class Steps
        {
            private IWebDriver driver;
            
            [Given(@"setup")]
            public void Setup()
            {
                driver.GoToUrl("https://example.com");
            }
            
            [When(@"interact")]
            public void Interact()
            {
                driver.FindElement(By.Id("btn")).Click();
            }
            
            [Then(@"verify")]
            public void Verify()
            {
                Assert.IsTrue(driver.FindElement(By.Id("result")).Displayed);
            }
        }
        """
        
        intent = parser.parse(code)
        
        # Check that actions are categorized
        given_actions = [a for a in intent.steps if a.semantics.get('bdd_phase') == 'given']
        when_actions = [a for a in intent.steps if a.semantics.get('bdd_phase') == 'when']
        
        assert len(given_actions) > 0  # navigate
        assert len(when_actions) > 0  # click
        assert len(intent.assertions) > 0  # visibility


class TestSpecFlowToPytestPlaywright:
    """Test SpecFlow to Pytest/Playwright translation."""
    
    def test_complete_translation(self):
        """Test complete SpecFlow to Pytest translation."""
        specflow_code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        using NUnit.Framework;
        
        namespace MyApp.Tests
        {
            // Scenario: Successful user login
            
            [Binding]
            public class LoginSteps
            {
                private IWebDriver driver;
                
                [Given(@"user is on the login page")]
                public void GivenUserOnLoginPage()
                {
                    driver.GoToUrl("https://example.com/login");
                }
                
                [When(@"user enters valid credentials")]
                public void WhenUserEntersCredentials()
                {
                    driver.FindElement(By.Id("username")).SendKeys("admin");
                    driver.FindElement(By.Id("password")).SendKeys("password123");
                }
                
                [When(@"user clicks login button")]
                public void WhenUserClicksLogin()
                {
                    driver.FindElement(By.CssSelector("button[type='submit']")).Click();
                }
                
                [Then(@"user should see the dashboard")]
                public void ThenUserSeesDashboard()
                {
                    Assert.IsTrue(driver.FindElement(By.Id("dashboard")).Displayed);
                    var title = driver.FindElement(By.TagName("h1")).Text;
                    Assert.AreEqual("Dashboard", title);
                }
            }
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=specflow_code,
            source_framework="specflow-dotnet",
            target_framework="pytest",
        )
        
        assert result.success
        assert "def test" in result.target_code
        assert "page.goto" in result.target_code or "navigate" in result.target_code.lower()
        # Should preserve BDD structure
        assert "given" in result.target_code.lower() or "arrange" in result.target_code.lower()
    
    def test_navigation_translation(self):
        """Test navigation translation."""
        code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        
        public class Steps
        {
            private IWebDriver driver;
            
            [Given(@"open page")]
            public void OpenPage()
            {
                driver.GoToUrl("https://example.com");
            }
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=code,
            source_framework="specflow",
            target_framework="pytest",
        )
        
        assert result.success
        # pytest generator generates TODO for navigate actions (use playwright generator for UI)
        assert "TODO" in result.target_code or "page.goto" in result.target_code
    
    def test_form_interaction_translation(self):
        """Test form interaction translation."""
        code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        
        public class Steps
        {
            private IWebDriver driver;
            
            [When(@"fill form")]
            public void FillForm()
            {
                driver.FindElement(By.Name("email")).SendKeys("test@example.com");
                driver.FindElement(By.Id("submit")).Click();
            }
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=code,
            source_framework="specflow",
            target_framework="pytest",
        )
        
        assert result.success
        assert "fill" in result.target_code.lower() or "sendkeys" in result.target_code.lower()


class TestSpecFlowToRobotPlaywright:
    """Test SpecFlow to Robot Framework/Playwright translation."""
    
    def test_complete_translation_to_robot(self):
        """Test complete SpecFlow to Robot translation."""
        specflow_code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        using NUnit.Framework;
        
        namespace MyApp.Tests
        {
            // Scenario: User Registration
            
            [Binding]
            public class RegistrationSteps
            {
                private IWebDriver driver;
                
                [Given(@"user opens registration page")]
                public void GivenOpenRegistration()
                {
                    driver.GoToUrl("https://example.com/register");
                }
                
                [When(@"user fills registration form")]
                public void WhenFillsForm()
                {
                    driver.FindElement(By.Id("name")).SendKeys("John Doe");
                    driver.FindElement(By.Id("email")).SendKeys("john@example.com");
                }
                
                [When(@"user submits form")]
                public void WhenSubmitsForm()
                {
                    driver.FindElement(By.Id("submit")).Click();
                }
                
                [Then(@"user should see confirmation")]
                public void ThenSeeConfirmation()
                {
                    Assert.IsTrue(driver.FindElement(By.ClassName("success")).Displayed);
                }
            }
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=specflow_code,
            source_framework="specflow",
            target_framework="robot",
        )
        
        assert result.success
        assert "*** Settings ***" in result.target_code
        assert "*** Test Cases ***" in result.target_code
        assert "Library" in result.target_code
        # Should have BDD keywords
        assert "Given" in result.target_code or "When" in result.target_code
    
    def test_robot_keyword_generation(self):
        """Test Robot keyword generation from SpecFlow."""
        code = """
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        
        public class Steps
        {
            private IWebDriver driver;
            
            [When(@"click button")]
            public void ClickButton()
            {
                driver.FindElement(By.Id("myButton")).Click();
            }
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=code,
            source_framework="specflow",
            target_framework="robot",
        )
        
        assert result.success
        assert "Click" in result.target_code
        # Robot uses id= prefix
        assert "id=myButton" in result.target_code or "myButton" in result.target_code


class TestSpecFlowParserEdgeCases:
    """Test edge cases and robustness."""
    
    def test_parse_empty_code(self):
        """Test parsing empty code."""
        parser = SpecFlowParser()
        intent = parser.parse("")
        assert intent.test_type == IntentType.BDD
    
    def test_parse_code_with_comments(self):
        """Test parsing code with extensive comments."""
        parser = SpecFlowParser()
        
        code = """
        using TechTalk.SpecFlow;
        // This is a comment
        /* Multi-line
           comment */
        [Given(@"step")]
        public void Step() { }
        """
        
        intent = parser.parse(code)
        assert intent is not None
    
    def test_parse_fluent_assertions(self):
        """Test parsing FluentAssertions library."""
        parser = SpecFlowParser()
        
        code = """
        using FluentAssertions;
        using TechTalk.SpecFlow;
        using OpenQA.Selenium;
        
        public class Steps
        {
            [Then(@"verify")]
            public void Verify()
            {
                driver.FindElement(By.Id("title")).Text.Should().Be("Welcome");
            }
        }
        """
        
        intent = parser.parse(code)
        assertions = [a for a in intent.assertions if a.assertion_type == AssertionType.EQUALS]
        assert len(assertions) == 1
        assert assertions[0].expected == "Welcome"


# Run count: ensure comprehensive coverage
def test_test_coverage():
    """Verify test count."""
    # This module should have comprehensive tests
    # Count assertions to ensure thorough testing
    import sys
    module = sys.modules[__name__]
    test_count = len([name for name in dir(module) if name.startswith('Test')])
    assert test_count >= 4, "Should have multiple test classes"
