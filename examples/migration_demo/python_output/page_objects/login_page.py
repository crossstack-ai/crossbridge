from playwright.sync_api import Page


class LoginPage:
    """Generated Playwright Page Object"""

    def __init__(self, page: Page):
        self.page = page
        self.username_input = self.page.locator("input[name='username']")
        self.password_input = self.page.locator("input[type='password']")
        self.login_button_locator = self.page.locator("button:has-text('Login')")

    def enter_username(self, username: str):
        self.username_input.fill(username)

    def enter_password(self, password: str):
        self.password_input.fill(password)

    def click_login_button(self):
        self.login_button_locator.click()
