"""Generated pytest-bdd step definitions"""
from page_objects.home_page import HomePage
from page_objects.login_page import LoginPage
from pytest_bdd import given, when, then, parsers


@given("user is on the login page")
def user_is_on_login_page(page):
    """Step: given user is on the login page"""
    # TODO: Implement step logic
        pass


@when(parsers.parse("user enters username {username}"))
def user_enters_username(page, login_page, username):
    """Step: when user enters username {username}"""
    login_page.enter_username(username)


@when(parsers.parse("user enters password {password}"))
def user_enters_password(page, login_page, password):
    """Step: when user enters password {password}"""
    login_page.enter_password(password)


@when("user clicks login button")
def user_clicks_login_button(page, login_page):
    """Step: when user clicks login button"""
    login_page.click_login_button()


@then("user should see welcome message")
def user_should_see_welcome_message(page, home_page):
    """Step: then user should see welcome message"""
    home_page.verify_welcome_message()


@then("user should be on home page")
def user_should_be_on_home_page(page):
    """Step: then user should be on home page"""
    # TODO: Implement step logic
        pass

