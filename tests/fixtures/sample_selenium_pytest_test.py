"""
Sample Selenium pytest test file for testing adapter detection and extraction.
"""
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.fixture(scope="function")
def driver():
    """Create Chrome WebDriver instance."""
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


class TestLoginFeature:
    """Test suite for login feature."""
    
    def test_successful_login_with_valid_credentials(self, driver):
        """Test user can login with valid credentials."""
        # Arrange
        driver.get("https://example.com/login")
        
        # Act
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        username_field.send_keys("test@example.com")
        password_field.send_keys("SecurePass123")
        submit_button.click()
        
        # Assert
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "welcome-message"))
        )
        assert driver.current_url == "https://example.com/dashboard"
    
    def test_login_fails_with_invalid_password(self, driver):
        """Test login fails when wrong password provided."""
        driver.get("https://example.com/login")
        
        driver.find_element(By.ID, "username").send_keys("test@example.com")
        driver.find_element(By.ID, "password").send_keys("WrongPassword")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        error_msg = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
        )
        assert "Invalid credentials" in error_msg.text
    
    def test_login_form_validation_empty_username(self, driver):
        """Test validation message appears for empty username."""
        driver.get("https://example.com/login")
        
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        error = driver.find_element(By.ID, "username-error")
        assert error.is_displayed()
        assert "required" in error.text.lower()


class TestShoppingCartFeature:
    """Test suite for shopping cart functionality."""
    
    @pytest.fixture
    def cart_page(self, driver):
        """Navigate to cart page and return driver."""
        driver.get("https://example.com/cart")
        return driver
    
    def test_add_product_to_cart(self, driver):
        """Test adding a product to shopping cart."""
        driver.get("https://example.com/products")
        
        # Add first product to cart
        add_button = driver.find_element(By.CSS_SELECTOR, ".product-card .add-to-cart")
        add_button.click()
        
        # Navigate to cart
        driver.get("https://example.com/cart")
        
        # Verify cart has item
        cart_items = driver.find_elements(By.CLASS_NAME, "cart-item")
        assert len(cart_items) == 1
    
    def test_remove_product_from_cart(self, cart_page):
        """Test removing a product from cart."""
        initial_items = cart_page.find_elements(By.CLASS_NAME, "cart-item")
        initial_count = len(initial_items)
        
        if initial_count > 0:
            remove_button = initial_items[0].find_element(By.CLASS_NAME, "remove-button")
            remove_button.click()
            
            # Wait for item to be removed
            WebDriverWait(cart_page, 10).until(
                lambda d: len(d.find_elements(By.CLASS_NAME, "cart-item")) == initial_count - 1
            )
    
    def test_cart_total_calculation(self, cart_page):
        """Test cart total is calculated correctly."""
        items = cart_page.find_elements(By.CLASS_NAME, "cart-item")
        
        expected_total = 0
        for item in items:
            price_text = item.find_element(By.CLASS_NAME, "item-price").text
            price = float(price_text.replace("$", ""))
            expected_total += price
        
        actual_total_text = cart_page.find_element(By.CLASS_NAME, "total-price").text
        actual_total = float(actual_total_text.replace("$", ""))
        
        assert abs(actual_total - expected_total) < 0.01  # Account for floating point


@pytest.mark.parametrize("browser", ["chrome", "firefox"])
def test_cross_browser_compatibility(browser):
    """Test application works across different browsers."""
    if browser == "chrome":
        driver = webdriver.Chrome()
    elif browser == "firefox":
        driver = webdriver.Firefox()
    
    try:
        driver.get("https://example.com")
        title = driver.title
        assert "Example" in title
    finally:
        driver.quit()


def test_wait_for_element_with_explicit_wait(driver):
    """Test explicit wait for element to be clickable."""
    driver.get("https://example.com/dynamic")
    
    # Wait for dynamic element
    wait = WebDriverWait(driver, 15)
    element = wait.until(
        EC.element_to_be_clickable((By.ID, "dynamic-button"))
    )
    
    element.click()
    assert driver.find_element(By.ID, "result").text == "Clicked"
