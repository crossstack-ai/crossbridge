"""
Quick demo of framework translation.
"""

# Sample Selenium Java test
SELENIUM_CODE = """
@Test
public void testLogin() {
    driver.get("https://example.com/login");
    driver.findElement(By.id("username")).sendKeys("admin");
    driver.findElement(By.id("password")).sendKeys("secret");
    driver.findElement(By.id("login-btn")).click();
    
    WebDriverWait wait = new WebDriverWait(driver, 10);
    wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("dashboard")));
    
    assertTrue(driver.findElement(By.id("welcome")).isDisplayed());
    assertEquals("Welcome, Admin", driver.findElement(By.id("welcome")).getText());
}
"""

print("=" * 80)
print("CrossBridge Framework Translation Demo")
print("=" * 80)
print()
print("Input: Selenium Java")
print("-" * 80)
print(SELENIUM_CODE)
print()

# Import translation components
from core.translation.parsers.selenium_parser import SeleniumParser
from core.translation.generators.playwright_generator import PlaywrightGenerator

# Parse Selenium code
print("🔄 Step 1: Parsing Selenium Java code...")
parser = SeleniumParser()
intent = parser.parse(SELENIUM_CODE, "LoginTest.java")

print(f"   ✅ Extracted {len(intent.steps)} actions")
print(f"   ✅ Extracted {len(intent.assertions)} assertions")
print()

# Show intent model
print("📊 Step 2: Neutral Intent Model")
print("-" * 80)
for i, step in enumerate(intent.steps, 1):
    print(f"   {i}. {step.action_type.value}: {step.description}")
for i, assertion in enumerate(intent.assertions, 1):
    print(f"   A{i}. {assertion.assertion_type.value}: {assertion.description}")
print()

# Generate Playwright code
print("🔄 Step 3: Generating Playwright Python code...")
generator = PlaywrightGenerator()
playwright_code = generator.generate(intent)

print("   ✅ Generated Playwright test")
print()
print("Output: Playwright Python")
print("=" * 80)
print(playwright_code)
print("=" * 80)
print()

# Show improvements
print("✨ Key Improvements:")
print("   ✅ Removed WebDriverWait - Playwright auto-waits")
print("   ✅ Cleaner assertions with expect() API")
print("   ✅ More Pythonic code style")
print("   ✅ Role-based selectors preferred")
print()
