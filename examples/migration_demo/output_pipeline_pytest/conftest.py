from page_objects.home_page import HomePage
from page_objects.login_page import LoginPage
from playwright.sync_api import sync_playwright
import pytest

@pytest.fixture(scope="session")
def browser():
    """Playwright browser instance"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    """Playwright page instance"""
    page = browser.new_page()
    yield page
    page.close()

@pytest.fixture
def login_page(page):
    """Fixture for LoginPage"""
    return LoginPage(page)

@pytest.fixture
def home_page(page):
    """Fixture for HomePage"""
    return HomePage(page)
