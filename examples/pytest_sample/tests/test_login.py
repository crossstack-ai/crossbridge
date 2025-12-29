"""Login tests using Page Objects."""


def test_valid_login(login_page, dashboard_page):
    """Test successful login with valid credentials."""
    login_page.login("user@example.com", "password123")
    assert dashboard_page.get_welcome_message() == "Welcome!"


def test_invalid_login(login_page):
    """Test login with invalid credentials."""
    login_page.login("invalid@example.com", "wrongpass")
    # Assert error message shown


def test_empty_credentials(login_page):
    """Test login with empty credentials."""
    login_page.click_login_button()
    # Assert validation error
