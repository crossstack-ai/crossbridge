"""
Demo: SpecFlow (.NET C#) to Python translation.

Demonstrates translation paths:
1. SpecFlow → Pytest/Playwright
2. SpecFlow → Robot Framework/Playwright
"""

from core.translation.pipeline import TranslationPipeline


def demo_specflow_to_pytest_playwright():
    """Demo SpecFlow to Pytest/Playwright translation."""
    print("\n" + "="*80)
    print("DEMO 1: SpecFlow (.NET C#) → Pytest/Playwright")
    print("="*80)
    
    specflow_code = """
    using TechTalk.SpecFlow;
    using OpenQA.Selenium;
    using NUnit.Framework;
    
    namespace MyApp.Tests
    {
        // Scenario: Successful user login
        // Feature: User Authentication
        
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
                driver.FindElement(By.Id("password")).SendKeys("SecurePass123");
            }
            
            [When(@"user clicks the login button")]
            public void WhenUserClicksLogin()
            {
                driver.FindElement(By.CssSelector("button[type='submit']")).Click();
            }
            
            [Then(@"user should see the dashboard")]
            public void ThenUserSeesDashboard()
            {
                Assert.IsTrue(driver.FindElement(By.Id("dashboard")).Displayed);
                
                var welcomeText = driver.FindElement(By.ClassName("welcome-message")).Text;
                Assert.AreEqual("Welcome, Admin!", welcomeText);
            }
        }
    }
    """
    
    print("\nSource (SpecFlow C#):")
    print(specflow_code)
    
    pipeline = TranslationPipeline()
    result = pipeline.translate(
        source_code=specflow_code,
        source_framework="specflow-dotnet",
        target_framework="pytest",
    )
    
    if result.success:
        print("\nGenerated Pytest/Playwright code:")
        print(result.target_code)
        print(f"\nConfidence: {result.confidence:.2%}")
        print(f"Actions translated: {result.actions_translated}")
        print(f"Assertions translated: {result.assertions_translated}")
        print(f"Warnings: {len(result.warnings)}")
        if result.warnings:
            for warning in result.warnings:
                print(f"  ⚠️  {warning}")
    else:
        print(f"\nTranslation failed: {result.error_message}")


def demo_specflow_to_robot_playwright():
    """Demo SpecFlow to Robot Framework/Playwright translation."""
    print("\n" + "="*80)
    print("DEMO 2: SpecFlow (.NET C#) → Robot Framework/Playwright")
    print("="*80)
    
    specflow_code = """
    using TechTalk.SpecFlow;
    using OpenQA.Selenium;
    using OpenQA.Selenium.Support.UI;
    using NUnit.Framework;
    
    namespace MyApp.Tests
    {
        // Scenario: User completes registration
        
        [Binding]
        public class RegistrationSteps
        {
            private IWebDriver driver;
            
            [Given(@"user opens the registration page")]
            public void GivenOpenRegistration()
            {
                driver.GoToUrl("https://example.com/register");
            }
            
            [When(@"user fills the registration form")]
            public void WhenFillsForm()
            {
                driver.FindElement(By.Name("firstName")).SendKeys("John");
                driver.FindElement(By.Name("lastName")).SendKeys("Doe");
                driver.FindElement(By.Name("email")).SendKeys("john.doe@example.com");
                
                var countryDropdown = new SelectElement(driver.FindElement(By.Id("country")));
                countryDropdown.SelectByText("United States");
            }
            
            [When(@"user accepts terms and submits")]
            public void WhenSubmitsForm()
            {
                driver.FindElement(By.Id("terms-checkbox")).Click();
                driver.FindElement(By.Id("submit-button")).Click();
            }
            
            [Then(@"user should see success confirmation")]
            public void ThenSeeConfirmation()
            {
                Assert.IsTrue(driver.FindElement(By.ClassName("success-message")).Displayed);
                
                var confirmText = driver.FindElement(By.ClassName("confirmation-text")).Text;
                Assert.That(confirmText, Does.Contain("successfully registered"));
            }
        }
    }
    """
    
    print("\nSource (SpecFlow C#):")
    print(specflow_code)
    
    pipeline = TranslationPipeline()
    result = pipeline.translate(
        source_code=specflow_code,
        source_framework="specflow",
        target_framework="robot",
    )
    
    if result.success:
        print("\nGenerated Robot Framework/Playwright code:")
        print(result.target_code)
        print(f"\nConfidence: {result.confidence:.2%}")
        print(f"Actions translated: {result.actions_translated}")
    else:
        print(f"\nTranslation failed: {result.error_message}")


def demo_specflow_with_fluent_assertions():
    """Demo SpecFlow with FluentAssertions library."""
    print("\n" + "="*80)
    print("DEMO 3: SpecFlow with FluentAssertions → Pytest")
    print("="*80)
    
    specflow_code = """
    using TechTalk.SpecFlow;
    using OpenQA.Selenium;
    using FluentAssertions;
    
    namespace MyApp.Tests
    {
        [Binding]
        public class SearchSteps
        {
            private IWebDriver driver;
            
            [Given(@"user is on search page")]
            public void GivenOnSearchPage()
            {
                driver.GoToUrl("https://example.com/search");
            }
            
            [When(@"user searches for product")]
            public void WhenSearches()
            {
                driver.FindElement(By.Name("query")).SendKeys("laptop");
                driver.FindElement(By.Id("search-btn")).Click();
            }
            
            [Then(@"user should see search results")]
            public void ThenSeeResults()
            {
                driver.FindElement(By.ClassName("results")).Displayed.Should().BeTrue();
                
                var resultCount = driver.FindElement(By.Id("result-count")).Text;
                resultCount.Should().Contain("results found");
                
                var firstResult = driver.FindElement(By.CssSelector(".result-item:first-child h3")).Text;
                firstResult.Should().NotBeEmpty();
            }
        }
    }
    """
    
    print("\nSource (SpecFlow with FluentAssertions):")
    print(specflow_code)
    
    pipeline = TranslationPipeline()
    result = pipeline.translate(
        source_code=specflow_code,
        source_framework="specflow-dotnet",
        target_framework="pytest",
    )
    
    if result.success:
        print("\nGenerated Pytest code:")
        print(result.target_code)
        print(f"\nConfidence: {result.confidence:.2%}")
    else:
        print(f"\nTranslation failed: {result.error_message}")


def main():
    """Run all SpecFlow translation demos."""
    print("\n" + "="*80)
    print(" CROSSBRIDGE - SpecFlow (.NET C#) Translation Demos")
    print(" Framework-to-Framework Translation")
    print("="*80)
    
    # Run all demos
    demo_specflow_to_pytest_playwright()
    demo_specflow_to_robot_playwright()
    demo_specflow_with_fluent_assertions()
    
    print("\n" + "="*80)
    print(" SpecFlow Translation Summary:")
    print("="*80)
    print("\nNEW Translation Paths (Phase 3):")
    print("  1. SpecFlow (.NET C#) → Pytest/Playwright")
    print("  2. SpecFlow (.NET C#) → Robot Framework/Playwright")
    print("\nSupported SpecFlow Features:")
    print("  ✅ [Given], [When], [Then], [And] attributes")
    print("  ✅ Selenium WebDriver (IWebDriver)")
    print("  ✅ NUnit assertions (Assert.IsTrue, Assert.AreEqual, etc.)")
    print("  ✅ FluentAssertions (.Should().Be(), .Should().Contain(), etc.)")
    print("  ✅ Selector types: Id, Name, ClassName, CssSelector, XPath")
    print("  ✅ Actions: Navigate, Click, SendKeys, Select")
    print("  ✅ BDD structure preservation")
    print("\nPrevious Translation Paths (Phase 1 & 2):")
    print("  3. Selenium Java → Playwright Python")
    print("  4. RestAssured → Pytest")
    print("  5. RestAssured → Robot Framework")
    print("  6. Selenium BDD Java → Pytest")
    print("  7. Selenium BDD Java → Robot Framework")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
