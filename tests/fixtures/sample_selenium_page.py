"""
Sample Selenium page object for testing adapter extraction.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginPageObject:
    """Page object for login page."""
    
    def __init__(self, driver):
        self.driver = driver
        self.url = "https://example.com/login"
        
        # Locators
        self.username_field = (By.ID, "username")
        self.password_field = (By.ID, "password")
        self.submit_button = (By.CSS_SELECTOR, "button[type='submit']")
        self.error_message = (By.CLASS_NAME, "error-message")
        self.welcome_message = (By.CLASS_NAME, "welcome-message")
    
    def navigate(self):
        """Navigate to login page."""
        self.driver.get(self.url)
    
    def enter_username(self, username):
        """Enter username in the field."""
        element = self.driver.find_element(*self.username_field)
        element.clear()
        element.send_keys(username)
    
    def enter_password(self, password):
        """Enter password in the field."""
        element = self.driver.find_element(*self.password_field)
        element.clear()
        element.send_keys(password)
    
    def click_submit(self):
        """Click the submit button."""
        self.driver.find_element(*self.submit_button).click()
    
    def login(self, username, password):
        """Perform complete login action."""
        self.navigate()
        self.enter_username(username)
        self.enter_password(password)
        self.click_submit()
    
    def get_error_message(self):
        """Get error message text."""
        wait = WebDriverWait(self.driver, 10)
        element = wait.until(EC.presence_of_element_located(self.error_message))
        return element.text
    
    def is_welcome_message_displayed(self):
        """Check if welcome message is displayed."""
        try:
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located(self.welcome_message))
            return True
        except:
            return False


class ShoppingCartPage:
    """Page object for shopping cart page."""
    
    def __init__(self, driver):
        self.driver = driver
        self.url = "https://example.com/cart"
        
        # Locators
        self.cart_items = (By.CLASS_NAME, "cart-item")
        self.item_price = (By.CLASS_NAME, "item-price")
        self.remove_button = (By.CLASS_NAME, "remove-button")
        self.checkout_button = (By.ID, "checkout-btn")
        self.total_price = (By.CLASS_NAME, "total-price")
        self.empty_cart_message = (By.CLASS_NAME, "empty-cart")
    
    def navigate(self):
        """Navigate to cart page."""
        self.driver.get(self.url)
    
    def get_cart_items(self):
        """Get all cart items."""
        return self.driver.find_elements(*self.cart_items)
    
    def get_item_count(self):
        """Get number of items in cart."""
        return len(self.get_cart_items())
    
    def remove_item_by_index(self, index=0):
        """Remove item from cart by index."""
        items = self.get_cart_items()
        if index < len(items):
            remove_btn = items[index].find_element(*self.remove_button)
            remove_btn.click()
    
    def get_total_price(self):
        """Get total price as float."""
        element = self.driver.find_element(*self.total_price)
        price_text = element.text.replace("$", "")
        return float(price_text)
    
    def proceed_to_checkout(self):
        """Click checkout button."""
        self.driver.find_element(*self.checkout_button).click()
    
    def is_cart_empty(self):
        """Check if cart is empty."""
        try:
            self.driver.find_element(*self.empty_cart_message)
            return True
        except:
            return False


class ProductListPage:
    """Page object for product listing page."""
    
    def __init__(self, driver):
        self.driver = driver
        self.url = "https://example.com/products"
        
        # Locators
        self.product_cards = (By.CLASS_NAME, "product-card")
        self.add_to_cart_button = (By.CLASS_NAME, "add-to-cart")
        self.product_title = (By.CLASS_NAME, "product-title")
        self.product_price = (By.CLASS_NAME, "product-price")
    
    def navigate(self):
        """Navigate to products page."""
        self.driver.get(self.url)
    
    def get_all_products(self):
        """Get all product elements."""
        return self.driver.find_elements(*self.product_cards)
    
    def add_product_to_cart(self, product_index=0):
        """Add product to cart by index."""
        products = self.get_all_products()
        if product_index < len(products):
            product = products[product_index]
            add_btn = product.find_element(*self.add_to_cart_button)
            add_btn.click()
    
    def get_product_title(self, product_index=0):
        """Get product title by index."""
        products = self.get_all_products()
        if product_index < len(products):
            return products[product_index].find_element(*self.product_title).text
        return None
