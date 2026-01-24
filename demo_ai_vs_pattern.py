#!/usr/bin/env python3
"""
AI vs Pattern-Based Transformation Comparison Demo

This script demonstrates the difference between AI-powered and pattern-based
step definition transformation using CrossBridge.

Usage:
    python demo_ai_vs_pattern.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.orchestration.orchestrator import MigrationOrchestrator


# Sample Java Cucumber Step Definition
SAMPLE_JAVA_STEP_DEFINITION = '''
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
    
    @Then("user should see error message {string}")
    public void userShouldSeeErrorMessage(String expectedMessage) {
        WebElement errorMsg = driver.findElement(By.cssSelector(".error-message"));
        String actualMessage = errorMsg.getText();
        
        if (!actualMessage.equals(expectedMessage)) {
            throw new AssertionError(
                String.format("Expected: '%s', but got: '%s'", expectedMessage, actualMessage)
            );
        }
    }
}
'''


def run_pattern_based_transformation():
    """Run pattern-based transformation (no AI)"""
    print("=" * 80)
    print("🔧 PATTERN-BASED TRANSFORMATION")
    print("=" * 80)
    print()
    
    orchestrator = MigrationOrchestrator()
    
    # Transform without AI
    result = orchestrator._transform_java_to_robot_keywords(
        content=SAMPLE_JAVA_STEP_DEFINITION,
        source_path="src/test/java/com/example/steps/LoginSteps.java",
        with_review_markers=False,
        request=None  # No AI config
    )
    
    print(result)
    print()
    return result


def run_ai_transformation():
    """Run AI-powered transformation"""
    print("=" * 80)
    print("🤖 AI-POWERED TRANSFORMATION")
    print("=" * 80)
    print()
    
    # Check for API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set in environment")
        print("Please set it with:")
        print("  export OPENAI_API_KEY='sk-...'")
        print()
        return None
    
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
    
    # Transform with AI
    try:
        result = orchestrator._transform_java_to_robot_keywords(
            content=SAMPLE_JAVA_STEP_DEFINITION,
            source_path="src/test/java/com/example/steps/LoginSteps.java",
            with_review_markers=False,
            request=MockRequest()
        )
        
        print(result)
        print()
        return result
    except Exception as e:
        print(f"❌ AI transformation failed: {e}")
        print()
        return None


def compare_outputs(pattern_based, ai_powered):
    """Compare the two outputs"""
    print("=" * 80)
    print("📊 COMPARISON ANALYSIS")
    print("=" * 80)
    print()
    
    if not ai_powered:
        print("⚠️  Cannot compare - AI transformation failed or not available")
        return
    
    # Count keywords
    pattern_keywords = pattern_based.count("*** Keywords ***")
    pattern_keyword_defs = len([line for line in pattern_based.split('\n') 
                                 if line and not line.startswith(' ') and not line.startswith('***')])
    
    ai_keywords = ai_powered.count("*** Keywords ***")
    ai_keyword_defs = len([line for line in ai_powered.split('\n') 
                           if line and not line.startswith(' ') and not line.startswith('***')])
    
    # Count documentation
    pattern_docs = pattern_based.count("[Documentation]")
    ai_docs = ai_powered.count("[Documentation]")
    
    # Count Playwright actions
    pattern_actions = pattern_based.count("Click") + pattern_based.count("Fill") + pattern_based.count("Get Text")
    ai_actions = ai_powered.count("Click") + ai_powered.count("Fill") + ai_powered.count("Get Text")
    
    # Count TODOs/placeholders
    pattern_todos = pattern_based.count("TODO") + pattern_based.count("add implementation")
    ai_todos = ai_powered.count("TODO") + ai_powered.count("add implementation")
    
    print(f"Metric                      | Pattern-Based | AI-Powered")
    print(f"----------------------------+---------------+-----------")
    print(f"Total Lines                 | {len(pattern_based.split(chr(10))):>13} | {len(ai_powered.split(chr(10))):>10}")
    print(f"Keyword Definitions         | {pattern_keyword_defs:>13} | {ai_keyword_defs:>10}")
    print(f"[Documentation] Tags        | {pattern_docs:>13} | {ai_docs:>10}")
    print(f"Playwright Actions          | {pattern_actions:>13} | {ai_actions:>10}")
    print(f"TODO/Placeholder Comments   | {pattern_todos:>13} | {ai_todos:>10}")
    print()
    
    print("✅ Key Differences:")
    print()
    
    if ai_todos < pattern_todos:
        print("  • AI has fewer TODO/placeholder comments (more complete implementation)")
    
    if ai_actions > pattern_actions:
        print("  • AI generated more Playwright actions (better coverage)")
    
    if "[Tags]" in ai_powered and "[Tags]" not in pattern_based:
        print("  • AI added [Tags] for step categorization")
    
    if "Wait For" in ai_powered and "Wait For" not in pattern_based:
        print("  • AI included explicit wait strategies")
    
    if ai_docs > pattern_docs:
        print("  • AI provided more comprehensive documentation")
    
    print()


def main():
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                           ║")
    print("║   CrossBridge: AI vs Pattern-Based Transformation Comparison             ║")
    print("║                                                                           ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    print()
    
    print("📋 Sample Input: Java Cucumber Step Definitions")
    print("-" * 80)
    print(SAMPLE_JAVA_STEP_DEFINITION[:500] + "...")
    print("-" * 80)
    print()
    
    # Run pattern-based transformation
    pattern_result = run_pattern_based_transformation()
    
    # Run AI transformation
    ai_result = run_ai_transformation()
    
    # Compare results
    if pattern_result and ai_result:
        compare_outputs(pattern_result, ai_result)
    
    print("=" * 80)
    print("✅ Demo Complete")
    print("=" * 80)
    print()
    print("💡 To enable AI in your migrations:")
    print("   1. Set OPENAI_API_KEY environment variable")
    print("   2. Use transformation_mode='ENHANCED' or 'HYBRID'")
    print("   3. Set use_ai=True in MigrationRequest")
    print("   4. Provide ai_config with provider and model")
    print()
    print("📚 See docs/AI_TRANSFORMATION_USAGE.md for more details")
    print()


if __name__ == "__main__":
    main()
