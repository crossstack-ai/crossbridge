"""Login Page Object for test automation."""


class LoginPage:
    """Page Object for login functionality."""
    
    def __init__(self, driver):
        self.driver = driver
    
    def enter_username(self, username):
        """Enter username in the login form."""
        pass
    
    def enter_password(self, password):
        """Enter password in the login form."""
        pass
    
    def click_login_button(self):
        """Click the login button."""
        pass
    
    def login(self, username, password):
        """Perform complete login action."""
        self.enter_username(username)
        self.enter_password(password)
        self.click_login_button()
