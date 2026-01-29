"""
Sample Playwright test file for testing adapter detection and extraction.
"""
import pytest
from playwright.sync_api import Page, expect


class TestLoginPage:
    """Test suite for login functionality."""
    
    @pytest.fixture
    def login_page(self, page: Page):
        """Navigate to login page."""
        page.goto("https://example.com/login")
        return page
    
    def test_successful_login(self, login_page: Page):
        """Test user can login with valid credentials."""
        # Arrange
        login_page.locator("#username").fill("test@example.com")
        login_page.locator("#password").fill("SecurePass123")
        
        # Act
        login_page.locator("button[type='submit']").click()
        
        # Assert
        expect(login_page.locator(".welcome-message")).to_be_visible()
        expect(login_page).to_have_url("https://example.com/dashboard")
    
    def test_failed_login_invalid_credentials(self, login_page: Page):
        """Test login fails with invalid credentials."""
        # Arrange
        login_page.locator("#username").fill("invalid@example.com")
        login_page.locator("#password").fill("WrongPassword")
        
        # Act
        login_page.locator("button[type='submit']").click()
        
        # Assert
        expect(login_page.locator(".error-message")).to_be_visible()
        expect(login_page.locator(".error-message")).to_contain_text("Invalid credentials")
    
    def test_empty_username_validation(self, login_page: Page):
        """Test validation for empty username field."""
        # Act
        login_page.locator("button[type='submit']").click()
        
        # Assert
        expect(login_page.locator("#username-error")).to_be_visible()


class TestShoppingCart:
    """Test suite for shopping cart functionality."""
    
    @pytest.fixture
    def cart_page(self, page: Page):
        """Navigate to cart page."""
        page.goto("https://example.com/cart")
        return page
    
    def test_add_item_to_cart(self, cart_page: Page):
        """Test adding item to shopping cart."""
        # Arrange
        cart_page.goto("https://example.com/products")
        
        # Act
        cart_page.locator(".product-card").first.locator("button.add-to-cart").click()
        cart_page.goto("https://example.com/cart")
        
        # Assert
        expect(cart_page.locator(".cart-items")).to_have_count(1)
    
    def test_remove_item_from_cart(self, cart_page: Page):
        """Test removing item from cart."""
        # Assume cart has items
        initial_count = cart_page.locator(".cart-item").count()
        
        # Act
        cart_page.locator(".cart-item").first.locator(".remove-button").click()
        
        # Assert
        expect(cart_page.locator(".cart-item")).to_have_count(initial_count - 1)


@pytest.mark.api
class TestAPIIntegration:
    """Test API integration in Playwright."""
    
    def test_api_response(self, page: Page):
        """Test API endpoint returns expected data."""
        response = page.request.get("https://api.example.com/users")
        assert response.status == 200
        assert response.json()["success"] is True
