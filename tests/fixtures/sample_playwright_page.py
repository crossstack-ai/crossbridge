"""
Sample Playwright page object for testing adapter extraction.
"""
from playwright.sync_api import Page


class LoginPage:
    """Page object for login page."""
    
    def __init__(self, page: Page):
        self.page = page
        self.username_input = page.locator("#username")
        self.password_input = page.locator("#password")
        self.submit_button = page.locator("button[type='submit']")
        self.error_message = page.locator(".error-message")
        self.welcome_message = page.locator(".welcome-message")
    
    def navigate(self):
        """Navigate to login page."""
        self.page.goto("https://example.com/login")
    
    def login(self, username: str, password: str):
        """Perform login with given credentials."""
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.submit_button.click()
    
    def get_error_message(self) -> str:
        """Get error message text."""
        return self.error_message.text_content()


class CartPage:
    """Page object for shopping cart."""
    
    def __init__(self, page: Page):
        self.page = page
        self.cart_items = page.locator(".cart-item")
        self.checkout_button = page.locator("#checkout-btn")
        self.total_price = page.locator(".total-price")
    
    def navigate(self):
        """Navigate to cart page."""
        self.page.goto("https://example.com/cart")
    
    def remove_item(self, index: int = 0):
        """Remove item from cart by index."""
        self.cart_items.nth(index).locator(".remove-button").click()
    
    def get_item_count(self) -> int:
        """Get number of items in cart."""
        return self.cart_items.count()
    
    def proceed_to_checkout(self):
        """Click checkout button."""
        self.checkout_button.click()
