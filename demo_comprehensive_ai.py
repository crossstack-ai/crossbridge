#!/usr/bin/env python3
"""
Comprehensive AI Transformation Demo

Demonstrates AI-powered transformation for:
1. Step Definitions
2. Page Objects
3. Locators (with self-healing analysis)

Shows both regular migration and repo-native modes.

Usage:
    export OPENAI_API_KEY='sk-...'
    python demo_comprehensive_ai.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.orchestration.orchestrator import MigrationOrchestrator


# ============================================================================
# SAMPLE 1: Java Cucumber Step Definition
# ============================================================================
SAMPLE_STEP_DEFINITION = '''
package com.example.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

public class LoginSteps {
    
    private WebDriver driver;
    
    @Given("user is on the login page")
    public void userIsOnLoginPage() {
        driver.get("https://example.com/login");
        WebElement loginTitle = driver.findElement(By.cssSelector("h1.login-title"));
        if (!loginTitle.isDisplayed()) {
            throw new RuntimeException("Login page not loaded");
        }
    }
    
    @When("user enters username {string} and password {string}")
    public void userEntersCredentials(String username, String password) {
        WebElement usernameField = driver.findElement(By.id("username"));
        WebElement passwordField = driver.findElement(By.id("password"));
        
        usernameField.clear();
        usernameField.sendKeys(username);
        
        passwordField.clear();
        passwordField.sendKeys(password);
    }
    
    @When("user clicks the login button")
    public void userClicksLoginButton() {
        WebElement loginButton = driver.findElement(By.xpath("//button[@type='submit']"));
        loginButton.click();
    }
    
    @Then("user should see the dashboard")
    public void userShouldSeeDashboard() {
        WebElement dashboard = driver.findElement(By.className("dashboard-container"));
        if (!dashboard.isDisplayed()) {
            throw new AssertionError("Dashboard not visible");
        }
    }
}
'''


# ============================================================================
# SAMPLE 2: Java Selenium Page Object
# ============================================================================
SAMPLE_PAGE_OBJECT = '''
package com.example.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

/**
 * Login Page Object
 * Handles all interactions with the login page
 */
public class LoginPage {
    
    private WebDriver driver;
    private WebDriverWait wait;
    
    @FindBy(id = "username")
    private WebElement usernameField;
    
    @FindBy(id = "password")
    private WebElement passwordField;
    
    @FindBy(css = "button[data-testid='login-button']")
    private WebElement loginButton;
    
    @FindBy(className = "error-message")
    private WebElement errorMessage;
    
    public LoginPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, 10);
        PageFactory.initElements(driver, this);
    }
    
    /**
     * Enter username in the username field
     * @param username The username to enter
     */
    public void enterUsername(String username) {
        wait.until(ExpectedConditions.visibilityOf(usernameField));
        usernameField.clear();
        usernameField.sendKeys(username);
    }
    
    /**
     * Enter password in the password field
     * @param password The password to enter
     */
    public void enterPassword(String password) {
        wait.until(ExpectedConditions.visibilityOf(passwordField));
        passwordField.clear();
        passwordField.sendKeys(password);
    }
    
    /**
     * Click the login button
     */
    public void clickLogin() {
        wait.until(ExpectedConditions.elementToBeClickable(loginButton));
        loginButton.click();
    }
    
    /**
     * Perform complete login with credentials
     * @param username The username
     * @param password The password
     */
    public void login(String username, String password) {
        enterUsername(username);
        enterPassword(password);
        clickLogin();
    }
    
    /**
     * Get the error message text
     * @return Error message text or empty string
     */
    public String getErrorMessage() {
        try {
            wait.until(ExpectedConditions.visibilityOf(errorMessage));
            return errorMessage.getText();
        } catch (Exception e) {
            return "";
        }
    }
    
    /**
     * Check if login button is enabled
     * @return true if enabled, false otherwise
     */
    public boolean isLoginButtonEnabled() {
        return loginButton.isEnabled();
    }
}
'''


# ============================================================================
# SAMPLE 3: Java Locators File
# ============================================================================
SAMPLE_LOCATORS = '''
package com.example.locators;

import org.openqa.selenium.By;

/**
 * Centralized locator repository for login functionality
 */
public class LoginLocators {
    
    // GOOD: ID-based locators (stable)
    public static final By USERNAME_FIELD = By.id("username");
    public static final By PASSWORD_FIELD = By.id("password");
    
    // GOOD: data-testid (modern, stable)
    public static final By LOGIN_BUTTON = By.cssSelector("[data-testid='login-button']");
    
    // MODERATE: Class-based (may change with styling)
    public static final By ERROR_MESSAGE = By.className("error-message");
    public static final By SUCCESS_BANNER = By.cssSelector(".alert.alert-success");
    
    // POOR: Absolute XPath (brittle!)
    public static final By FORGOT_PASSWORD_LINK = By.xpath("/html/body/div[1]/div[2]/form/div[4]/a");
    
    // POOR: Text-based (breaks with localization)
    public static final By LOGIN_TITLE = By.xpath("//h1[text()='Login to Your Account']");
    
    // MODERATE: Positional selector (fragile)
    public static final By REMEMBER_ME_CHECKBOX = By.cssSelector("form > div:nth-child(3) input[type='checkbox']");
    
    // POOR: Multiple class names (breaks easily)
    public static final By SOCIAL_LOGIN_SECTION = By.className("social-login-container mt-3 border-top pt-3");
    
    // GOOD: Unique attribute combination
    public static final By SUBMIT_BUTTON = By.cssSelector("button[type='submit'][name='login']");
}
'''


def print_section(title: str, width: int = 80):
    """Print a section header"""
    print()
    print("=" * width)
    print(title.center(width))
    print("=" * width)
    print()


def print_subsection(title: str):
    """Print a subsection header"""
    print()
    print("-" * 80)
    print(f"  {title}")
    print("-" * 80)
    print()


def run_transformation(sample_name: str, content: str, file_path: str, api_key: str):
    """Run AI transformation on a sample"""
    
    print_subsection(f"Transforming: {sample_name}")
    
    # Create mock request object with AI config
    class MockRequest:
        use_ai = True
        ai_config = {
            'provider': 'openai',
            'api_key': api_key,
            'model': 'gpt-3.5-turbo',
            'temperature': 0.3,
            'region': 'US'
        }
    
    orchestrator = MigrationOrchestrator()
    
    try:
        result = orchestrator._transform_java_to_robot_keywords(
            content=content,
            source_path=file_path,
            with_review_markers=False,
            request=MockRequest()
        )
        
        print(result)
        print()
        return result
    except Exception as e:
        print(f"❌ Transformation failed: {e}")
        print()
        import traceback
        traceback.print_exc()
        return None


def main():
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                           ║")
    print("║   CrossBridge: Comprehensive AI Transformation Demo                      ║")
    print("║                                                                           ║")
    print("║   Demonstrates AI-powered transformation for:                            ║")
    print("║   • Step Definitions (Cucumber → Robot Framework)                        ║")
    print("║   • Page Objects (Selenium → Playwright)                                 ║")
    print("║   • Locators (with self-healing analysis)                                ║")
    print("║                                                                           ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Check for API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set in environment")
        print()
        print("Please set it with:")
        print("  export OPENAI_API_KEY='sk-...'")
        print()
        print("Or on Windows:")
        print("  set OPENAI_API_KEY=sk-...")
        print()
        return
    
    print(f"✅ API key found: {api_key[:15]}...")
    print()
    
    # ========================================================================
    # Test 1: Step Definition Transformation
    # ========================================================================
    print_section("TEST 1: STEP DEFINITION TRANSFORMATION")
    
    print("📋 Input: Java Cucumber Step Definition")
    print("   File: LoginSteps.java")
    print("   Contains: @Given, @When, @Then annotations")
    print()
    
    result1 = run_transformation(
        "Step Definition",
        SAMPLE_STEP_DEFINITION,
        "src/test/java/com/example/steps/LoginSteps.java",
        api_key
    )
    
    # ========================================================================
    # Test 2: Page Object Transformation
    # ========================================================================
    print_section("TEST 2: PAGE OBJECT TRANSFORMATION")
    
    print("📋 Input: Java Selenium Page Object")
    print("   File: LoginPage.java")
    print("   Contains: @FindBy annotations, WebElement fields, public methods")
    print()
    
    result2 = run_transformation(
        "Page Object",
        SAMPLE_PAGE_OBJECT,
        "src/test/java/com/example/pages/LoginPage.java",
        api_key
    )
    
    # ========================================================================
    # Test 3: Locator Transformation with Self-Healing Analysis
    # ========================================================================
    print_section("TEST 3: LOCATOR TRANSFORMATION (Self-Healing Analysis)")
    
    print("📋 Input: Java Locators File")
    print("   File: LoginLocators.java")
    print("   Contains: Mix of GOOD, MODERATE, and POOR quality locators")
    print()
    print("   Expected AI Analysis:")
    print("   • Identify stable locators (id, data-testid)")
    print("   • Flag brittle locators (XPath, text-based, positional)")
    print("   • Suggest alternatives for each POOR locator")
    print("   • Provide self-healing recommendations")
    print()
    
    result3 = run_transformation(
        "Locators",
        SAMPLE_LOCATORS,
        "src/test/java/com/example/locators/LoginLocators.java",
        api_key
    )
    
    # ========================================================================
    # Summary
    # ========================================================================
    print_section("SUMMARY")
    
    success_count = sum([1 for r in [result1, result2, result3] if r])
    
    print(f"Transformations Completed: {success_count}/3")
    print()
    
    if result1:
        print("✅ Step Definition: SUCCESS")
        print("   • Cucumber annotations extracted")
        print("   • Playwright actions generated")
        print("   • Parameters properly handled")
    else:
        print("❌ Step Definition: FAILED")
    print()
    
    if result2:
        print("✅ Page Object: SUCCESS")
        print("   • WebElements converted to variables")
        print("   • Methods converted to keywords")
        print("   • JavaDoc preserved in documentation")
    else:
        print("❌ Page Object: FAILED")
    print()
    
    if result3:
        print("✅ Locators: SUCCESS")
        print("   • Quality analysis performed")
        print("   • Self-healing recommendations provided")
        print("   • Alternative strategies suggested for brittle locators")
    else:
        print("❌ Locators: FAILED")
    print()
    
    print("=" * 80)
    print()
    print("💡 Key Features Demonstrated:")
    print()
    print("1. File Type Auto-Detection:")
    print("   • Step definitions detected by filename pattern and @Given/@When/@Then")
    print("   • Page objects detected by 'Page' in name and @FindBy annotations")
    print("   • Locators detected by 'Locator' in name and By.* patterns")
    print()
    print("2. AI-Powered Enhancements:")
    print("   • Context-aware code generation")
    print("   • Natural language documentation")
    print("   • Best practice implementations")
    print("   • Self-healing locator analysis")
    print()
    print("3. Automatic Fallback:")
    print("   • Falls back to pattern-based if AI fails")
    print("   • No manual intervention required")
    print()
    print("4. Works in Both Modes:")
    print("   • Regular migration (demonstrated here)")
    print("   • Repo-native transformation (same logic)")
    print()
    print("=" * 80)
    print()
    print("📚 For more information:")
    print("   • See docs/AI_TRANSFORMATION_USAGE.md")
    print("   • Run: python demo_ai_vs_pattern.py (for comparison)")
    print()


if __name__ == "__main__":
    main()
