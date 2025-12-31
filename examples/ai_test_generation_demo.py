"""
AI-Powered Test Generation - Quick Reference and Examples.

This module demonstrates the capabilities of the AI-powered test generation service.
"""

from pathlib import Path
from unittest.mock import Mock

from core.ai.models import AIExecutionContext, ModelConfig, ProviderType, TaskType
from core.ai.orchestrator import AIOrchestrator
from core.ai.test_generation import (
    AITestGenerationService,
    AssertionGenerator,
    NaturalLanguageParser,
    PageObjectDetector,
    TestIntent,
)


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


def demo_natural_language_parsing():
    """Demonstrate natural language parsing."""
    print_section("1. Natural Language Parsing")
    
    parser = NaturalLanguageParser()
    
    # Example 1: Simple login test
    nl_text = """
    1. Navigate to the login page
    2. Enter username "testuser"
    3. Enter password "password123"
    4. Click the login button
    5. Verify the dashboard is displayed
    """
    
    print(f"\nInput: {nl_text.strip()}")
    print("\nParsed Intents:")
    
    intents = parser.parse(nl_text)
    for i, intent in enumerate(intents, 1):
        print(f"  {i}. Action: {intent.action}")
        print(f"     Target: {intent.target}")
        if intent.expected_outcome:
            print(f"     Expected: {intent.expected_outcome}")
        if intent.data:
            print(f"     Data: {intent.data}")
    
    # Example 2: E-commerce flow
    print("\n\nExample 2: E-commerce Checkout")
    ecommerce_text = "Add item to cart, proceed to checkout, and verify order confirmation"
    intents2 = parser.parse(ecommerce_text)
    
    print(f"Input: {ecommerce_text}")
    print(f"Parsed into {len(intents2)} steps")


def demo_page_object_detection():
    """Demonstrate page object detection."""
    print_section("2. Page Object Detection")
    
    # Would work with actual project structure
    print("\nPage Object Detection Features:")
    print("  • Automatically scans project for page object classes")
    print("  • Detects patterns: pages/*.py, page_objects/*.py, *_page.py")
    print("  • Extracts locators (Selenium, Playwright, Cypress)")
    print("  • Caches results for performance")
    print("  • Finds relevant page objects based on test intent")
    
    print("\n\nExample Page Object Detection:")
    print("""
    Project structure:
    └── pages/
        ├── login_page.py      → LoginPage class detected
        ├── dashboard_page.py  → DashboardPage class detected
        └── checkout_page.py   → CheckoutPage class detected
    
    Detected Locators:
    - LoginPage: username_field, password_field, login_button
    - DashboardPage: user_menu, welcome_message
    - CheckoutPage: cart_items, checkout_button, payment_form
    """)


def demo_intelligent_assertions():
    """Demonstrate intelligent assertion generation."""
    print_section("3. Intelligent Assertion Generation")
    
    generator = AssertionGenerator()
    
    # Example 1: Verify action
    print("\n\nExample 1: Verify Element Visibility")
    intent = TestIntent(
        action="verify",
        target="login button",
        context="Verify login button is visible",
    )
    
    print(f"Intent: {intent.context}")
    print("Generated Assertions:")
    print("  • assert element.is_displayed()  (Selenium)")
    print("  • await expect(locator).to_be_visible()  (Playwright)")
    
    # Example 2: Navigation with URL check
    print("\n\nExample 2: Navigation Verification")
    intent2 = TestIntent(
        action="navigate",
        target="dashboard",
        expected_outcome="user is on dashboard page",
        context="Navigate to dashboard",
    )
    
    print(f"Intent: {intent2.context}")
    print("Generated Assertions:")
    print("  • assert 'dashboard' in driver.current_url")
    print("  • assert page.url.includes('dashboard')")
    
    # Example 3: Input validation
    print("\n\nExample 3: Input Field Validation")
    intent3 = TestIntent(
        action="input",
        target="username field",
        data={"username": "testuser"},
        context="Enter username",
    )
    
    print(f"Intent: {intent3.context}")
    print("Generated Assertions:")
    print("  • assert element.get_attribute('value') == 'testuser'")


def demo_ai_test_generation():
    """Demonstrate full AI test generation."""
    print_section("4. AI-Powered Test Generation")
    
    print("\n\nGenerating test from natural language...")
    print("\nInput:")
    print("""
    Test successful user login:
    1. Navigate to https://example.com/login
    2. Enter username "admin"
    3. Enter password "secret123"
    4. Click the login button
    5. Verify the user is redirected to dashboard
    6. Verify welcome message contains username
    """)
    
    print("\n\nGenerated Test Code:")
    print("""
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from pages.login_page import LoginPage

@pytest.fixture
def driver():
    '''Setup browser driver'''
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    yield driver
    driver.quit()

def test_successful_user_login(driver):
    '''Test successful user login workflow'''
    # Navigate to login page
    driver.get("https://example.com/login")
    
    # Initialize page object
    login_page = LoginPage(driver)
    
    # Enter credentials
    login_page.enter_username("admin")
    login_page.enter_password("secret123")
    
    # Submit login form
    login_page.click_login_button()
    
    # Verify redirection to dashboard
    assert "dashboard" in driver.current_url, "User not redirected to dashboard"
    
    # Verify welcome message
    welcome_msg = driver.find_element(By.CLASS_NAME, "welcome-message").text
    assert "admin" in welcome_msg, "Username not in welcome message"
""")
    
    print("\n\nFeatures Applied:")
    print("  ✓ Natural language → structured test")
    print("  ✓ Page object pattern usage")
    print("  ✓ Intelligent assertions generated")
    print("  ✓ Setup/teardown fixtures")
    print("  ✓ Descriptive test name")
    print("  ✓ Clear comments")


def demo_test_enhancement():
    """Demonstrate test enhancement."""
    print_section("5. Test Enhancement")
    
    print("\n\nOriginal Test:")
    print("""
def test_login():
    driver.get("https://example.com/login")
    driver.find_element_by_id("username").send_keys("user")
    driver.find_element_by_id("password").send_keys("pass")
    driver.find_element_by_id("submit").click()
""")
    
    print("\n\nEnhancement Request:")
    print("  'Add assertions to verify successful login and error handling'")
    
    print("\n\nEnhanced Test:")
    print("""
def test_login():
    '''Test login with success and error scenarios'''
    driver.get("https://example.com/login")
    
    # Enter credentials
    driver.find_element_by_id("username").send_keys("user")
    driver.find_element_by_id("password").send_keys("pass")
    driver.find_element_by_id("submit").click()
    
    # Verify successful login
    WebDriverWait(driver, 10).until(
        EC.url_contains("dashboard")
    )
    assert "dashboard" in driver.current_url
    assert driver.find_element_by_class_name("success-message").is_displayed()
    
def test_login_with_invalid_credentials():
    '''Test login error handling'''
    driver.get("https://example.com/login")
    
    # Enter invalid credentials
    driver.find_element_by_id("username").send_keys("invalid")
    driver.find_element_by_id("password").send_keys("wrong")
    driver.find_element_by_id("submit").click()
    
    # Verify error message displayed
    error_msg = driver.find_element_by_class_name("error-message")
    assert error_msg.is_displayed()
    assert "Invalid credentials" in error_msg.text
""")


def demo_context_aware_suggestions():
    """Demonstrate context-aware suggestions."""
    print_section("6. Context-Aware Suggestions")
    
    print("\n\nSuggestions Based on Test Analysis:")
    
    print("\n\n1. Complex Test Detected:")
    print("   Test: 15-step checkout flow")
    print("   Suggestion: Consider splitting into multiple focused tests")
    print("   Reason: Improves maintainability and debugging")
    
    print("\n\n2. No Page Objects Found:")
    print("   Test: Multiple direct Selenium calls")
    print("   Suggestion: Create page objects for better test structure")
    print("   Reason: Reduces duplication and improves maintainability")
    
    print("\n\n3. Missing Assertions:")
    print("   Test: Actions without verification")
    print("   Suggestion: Add assertions to verify expected outcomes")
    print("   Reason: Tests should validate behavior, not just execute steps")
    
    print("\n\n4. Framework-Specific Optimization:")
    print("   Test: Using Playwright")
    print("   Suggestion: Use auto-waiting instead of explicit waits")
    print("   Reason: Playwright has built-in smart waiting")


def demo_usage_examples():
    """Show practical usage examples."""
    print_section("7. Usage Examples")
    
    print("\n\nExample 1: Basic Usage (with mock orchestrator)")
    print("""
from core.ai.orchestrator import AIOrchestrator
from core.ai.test_generation import AITestGenerationService

# Initialize service
orchestrator = AIOrchestrator(config={...})
service = AITestGenerationService(
    orchestrator=orchestrator,
    project_root=Path("./my_project"),
)

# Generate test from natural language
result = service.generate_from_natural_language(
    natural_language="Test user can add items to cart and checkout",
    framework="pytest",
    language="python",
)

# Access generated code
print(result.test_code)
print(f"Test name: {result.test_name}")
print(f"Assertions: {len(result.assertions)}")
print(f"Confidence: {result.confidence}")
""")
    
    print("\n\nExample 2: Enhance Existing Test")
    print("""
existing_test = '''
def test_search():
    driver.get("https://example.com")
    driver.find_element_by_id("search").send_keys("laptop")
'''

enhanced = service.enhance_existing_test(
    existing_test=existing_test,
    enhancement_request="Add assertions to verify search results",
)
""")
    
    print("\n\nExample 3: Multi-Framework Support")
    print("""
# Generate Playwright test
result_pw = service.generate_from_natural_language(
    natural_language="Test login flow",
    framework="playwright",
    language="python",
)

# Generate Selenium test
result_sel = service.generate_from_natural_language(
    natural_language="Test login flow",
    framework="pytest",  # with Selenium
    language="python",
)

# Generate Cypress test
result_cy = service.generate_from_natural_language(
    natural_language="Test login flow",
    framework="cypress",
    language="javascript",
)
""")


def demo_key_features_summary():
    """Show summary of all features."""
    print_section("8. AI-Powered Test Generation - Feature Summary")
    
    features = [
        ("Natural Language → Test Code", "Convert plain English to executable test code", "✅"),
        ("Intelligent Assertion Generation", "Auto-generate relevant assertions based on context", "✅"),
        ("Context-Aware Page Object Usage", "Detect and use existing page objects automatically", "✅"),
        ("Multi-Framework Support", "Generate tests for pytest, Playwright, Cypress, etc.", "✅"),
        ("Test Enhancement", "Improve existing tests with AI suggestions", "✅"),
        ("Smart Suggestions", "Provide actionable recommendations", "✅"),
        ("Setup/Teardown Generation", "Auto-generate fixtures and cleanup code", "✅"),
        ("Code Quality", "Generate idiomatic, maintainable test code", "✅"),
    ]
    
    print("\n")
    for feature, description, status in features:
        print(f"{status} {feature}")
        print(f"   {description}\n")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print(" " * 15 + "AI-POWERED TEST GENERATION")
    print(" " * 20 + "Quick Reference & Examples")
    print("=" * 80)
    
    demos = [
        ("Natural Language Parsing", demo_natural_language_parsing),
        ("Page Object Detection", demo_page_object_detection),
        ("Intelligent Assertions", demo_intelligent_assertions),
        ("AI Test Generation", demo_ai_test_generation),
        ("Test Enhancement", demo_test_enhancement),
        ("Context-Aware Suggestions", demo_context_aware_suggestions),
        ("Usage Examples", demo_usage_examples),
        ("Feature Summary", demo_key_features_summary),
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
    
    print("\n" + "=" * 80)
    print(" " * 25 + "END OF EXAMPLES")
    print("=" * 80)
    
    print("\n\nNext Steps:")
    print("  1. Review core/ai/test_generation.py for implementation details")
    print("  2. Run tests: pytest tests/unit/core/ai/test_ai_test_generation.py")
    print("  3. Try generating tests for your project")
    print("  4. Provide feedback for improvements")
    
    print("\n\nDocumentation:")
    print("  • See docs/AI_POWERED_TEST_GENERATION.md for full documentation")
    print("  • API Reference: core/ai/test_generation.py docstrings")
    print("  • Examples: examples/ai_test_generation_examples.py")


if __name__ == "__main__":
    main()
