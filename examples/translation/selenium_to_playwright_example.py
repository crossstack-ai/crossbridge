"""
End-to-end translation example: Selenium Java → Playwright Python.

This example demonstrates the complete translation workflow.
"""

from core.translation.pipeline import TranslationPipeline, TranslationConfig, TranslationMode


# Sample Selenium Java test
SELENIUM_LOGIN_TEST = """
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;

public class LoginTest {
    private WebDriver driver;
    private WebDriverWait wait;
    
    @Before
    public void setUp() {
        driver = new ChromeDriver();
        wait = new WebDriverWait(driver, 10);
    }
    
    @Test
    public void testSuccessfulLogin() {
        // Navigate to login page
        driver.get("https://example.com/login");
        
        // Wait for login form
        wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("login-form")));
        
        // Fill in credentials
        driver.findElement(By.id("username")).sendKeys("testuser");
        driver.findElement(By.id("password")).sendKeys("TestPass123!");
        
        // Click login button
        driver.findElement(By.id("login-btn")).click();
        
        // Wait for dashboard
        wait.until(ExpectedConditions.urlContains("/dashboard"));
        
        // Verify welcome message
        WebElement welcomeMsg = driver.findElement(By.className("welcome-message"));
        assertTrue(welcomeMsg.isDisplayed());
        assertEquals("Welcome, Test User", welcomeMsg.getText());
        
        // Verify user profile link
        assertTrue(driver.findElement(By.linkText("Profile")).isDisplayed());
    }
    
    @Test
    public void testInvalidLogin() {
        driver.get("https://example.com/login");
        
        driver.findElement(By.id("username")).sendKeys("invalid");
        driver.findElement(By.id("password")).sendKeys("wrong");
        driver.findElement(By.id("login-btn")).click();
        
        // Should stay on login page
        Thread.sleep(1000);  // Bad practice - will be removed in translation
        
        // Verify error message
        WebElement errorMsg = driver.findElement(By.className("error-message"));
        assertTrue(errorMsg.isDisplayed());
        assertEquals("Invalid credentials", errorMsg.getText());
    }
    
    @After
    public void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }
}
"""


def run_translation_example():
    """Run complete translation example."""
    print("=" * 80)
    print("CrossBridge Framework Translation Example")
    print("Selenium Java → Playwright Python")
    print("=" * 80)
    print()
    
    # Create pipeline
    pipeline = TranslationPipeline()
    
    # Configure translation
    config = TranslationConfig(
        source_framework="selenium-java",
        target_framework="playwright-python",
        mode=TranslationMode.ASSISTIVE,
        use_ai=False,  # Rule-based only for this example
        confidence_threshold=0.7,
    )
    
    # Translate
    print("🔄 Translating Selenium Java test...")
    print()
    
    result = pipeline.translate(
        source_code=SELENIUM_LOGIN_TEST,
        source_framework="selenium-java",
        target_framework="playwright-python",
        source_file="LoginTest.java",
    )
    
    # Show results
    print("=" * 80)
    print("Translation Results")
    print("=" * 80)
    print()
    
    if result.success:
        print("✅ Translation successful!")
        print()
        print(f"📊 Statistics:")
        print(f"   • Confidence: {result.confidence:.1%}")
        print(f"   • Actions: {result.statistics.get('actions', 0)}")
        print(f"   • Assertions: {result.statistics.get('assertions', 0)}")
        print(f"   • Idioms applied: {result.statistics.get('idioms_applied', 0)}")
        print()
        
        if result.warnings:
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"   • {warning}")
            print()
        
        if result.todos:
            print("📝 TODOs (manual review needed):")
            for todo in result.todos:
                print(f"   • {todo}")
            print()
        
        print("=" * 80)
        print("Generated Playwright Python Code")
        print("=" * 80)
        print()
        print(result.target_code)
        print()
        
        # Show key improvements
        print("=" * 80)
        print("Key Improvements from Translation")
        print("=" * 80)
        print()
        print("✅ Explicit waits removed - Playwright auto-waits")
        print("✅ Thread.sleep removed - not needed")
        print("✅ Browser setup/teardown handled by Playwright fixtures")
        print("✅ Cleaner assertions with expect() API")
        print("✅ Role-based selectors preferred")
        print("✅ More idiomatic Python code")
        print()
        
    else:
        print("❌ Translation failed:")
        for error in result.errors:
            print(f"   • {error}")
        print()
    
    return result


if __name__ == "__main__":
    run_translation_example()
