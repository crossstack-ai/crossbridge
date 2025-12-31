*** Settings ***
Documentation    Migrated from Java Selenium BDD
Library    Browser
Resource    ../resources/LoginPage.robot
Resource    ../resources/HomePage.robot

*** Test Cases ***
User Is On The Login Page
    [Documentation]    Given: user is on the login page
    # TODO: Implement step - user is on the login page

User Enters Username {String}
    [Documentation]    When: user enters username {string}
    Enter Username    username

User Enters Password {String}
    [Documentation]    When: user enters password {string}
    Enter Password    password

User Clicks Login Button
    [Documentation]    When: user clicks login button
    Click Login Button

User Should See Welcome Message
    [Documentation]    Then: user should see welcome message
    Verify Welcome Message

User Should Be On Home Page
    [Documentation]    Then: user should be on home page
    # TODO: Implement step - user should be on home page
