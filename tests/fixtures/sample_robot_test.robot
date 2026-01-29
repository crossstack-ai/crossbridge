*** Settings ***
Documentation    Sample Robot Framework test suite for testing adapter detection
Library          SeleniumLibrary
Library          Collections
Suite Setup      Open Browser To Login Page
Suite Teardown   Close Browser
Test Setup       Go To Login Page


*** Variables ***
${SERVER}         https://example.com
${BROWSER}        Chrome
${DELAY}          0.5 seconds
${LOGIN URL}      ${SERVER}/login
${WELCOME URL}    ${SERVER}/dashboard
${USERNAME}       test@example.com
${PASSWORD}       SecurePass123
${INVALID_PASS}   WrongPassword


*** Test Cases ***
Valid Login
    [Documentation]    Test user can login with valid credentials
    [Tags]             smoke    critical    login
    Input Text         id=username    ${USERNAME}
    Input Password     id=password    ${PASSWORD}
    Click Button       css=button[type='submit']
    Wait Until Page Contains Element    class=welcome-message    timeout=10s
    Location Should Be    ${WELCOME URL}


Invalid Password Login
    [Documentation]    Test login fails with wrong password
    [Tags]             negative    login
    Input Text         id=username    ${USERNAME}
    Input Password     id=password    ${INVALID_PASS}
    Click Button       css=button[type='submit']
    Wait Until Page Contains Element    class=error-message    timeout=10s
    Element Should Contain    class=error-message    Invalid credentials


Empty Username Validation
    [Documentation]    Test validation for empty username field
    [Tags]             validation    negative
    Click Button       css=button[type='submit']
    Element Should Be Visible    id=username-error
    ${error_text}=     Get Text    id=username-error
    Should Contain     ${error_text}    required    ignore_case=True


Logout Functionality
    [Documentation]    Test user can logout successfully
    [Tags]             smoke    logout
    Perform Valid Login
    Click Element      id=logout-btn
    Wait Until Page Contains Element    id=login-form    timeout=10s
    Location Should Be    ${LOGIN URL}


Shopping Cart Add Item
    [Documentation]    Test adding product to shopping cart
    [Tags]             cart    critical
    Perform Valid Login
    Go To    ${SERVER}/products
    Click Element    css=.product-card:first-child .add-to-cart
    Go To    ${SERVER}/cart
    ${items}=    Get Element Count    class=cart-item
    Should Be Equal As Integers    ${items}    1


Shopping Cart Remove Item
    [Documentation]    Test removing item from shopping cart
    [Tags]             cart
    Perform Valid Login
    Setup Cart With One Item
    ${initial_count}=    Get Element Count    class=cart-item
    Click Element    css=.cart-item:first-child .remove-button
    Wait Until Keyword Succeeds    5s    0.5s    
    ...    Cart Item Count Should Be    ${initial_count - 1}


Cart Total Calculation
    [Documentation]    Test cart total is calculated correctly
    [Tags]             cart    calculation
    Perform Valid Login
    Setup Cart With Multiple Items
    ${items}=    Get WebElements    class=cart-item
    ${expected_total}=    Calculate Items Total    ${items}
    ${actual_total_text}=    Get Text    class=total-price
    ${actual_total}=    Convert To Number    ${actual_total_text[1:]}
    Should Be Equal As Numbers    ${actual_total}    ${expected_total}    precision=2


Cross Browser Test Chrome
    [Documentation]    Test application works in Chrome
    [Tags]             cross-browser    smoke
    Open Browser    ${SERVER}    Chrome
    Title Should Contain    Example
    [Teardown]    Close Browser


Cross Browser Test Firefox
    [Documentation]    Test application works in Firefox
    [Tags]             cross-browser
    Open Browser    ${SERVER}    Firefox
    Title Should Contain    Example
    [Teardown]    Close Browser


Dynamic Element Wait
    [Documentation]    Test explicit wait for dynamic elements
    [Tags]             wait    dynamic
    Perform Valid Login
    Go To    ${SERVER}/dynamic
    Wait Until Element Is Visible    id=dynamic-button    timeout=15s
    Click Element    id=dynamic-button
    ${result}=    Get Text    id=result
    Should Be Equal    ${result}    Clicked


Form Submission With Multiple Inputs
    [Documentation]    Test complex form with multiple fields
    [Tags]             form    integration
    Perform Valid Login
    Go To    ${SERVER}/profile
    Input Text    id=first-name    John
    Input Text    id=last-name     Doe
    Input Text    id=email         john.doe@example.com
    Select From List By Value    id=country    US
    Click Button    id=submit-btn
    Wait Until Page Contains    Profile updated    timeout=10s


*** Keywords ***
Open Browser To Login Page
    [Documentation]    Open browser and navigate to login page
    Open Browser    ${LOGIN URL}    ${BROWSER}
    Maximize Browser Window
    Set Selenium Speed    ${DELAY}


Go To Login Page
    [Documentation]    Navigate to login page
    Go To    ${LOGIN URL}
    Title Should Be    Login Page


Perform Valid Login
    [Documentation]    Login with valid credentials
    Go To Login Page
    Input Text         id=username    ${USERNAME}
    Input Password     id=password    ${PASSWORD}
    Click Button       css=button[type='submit']
    Wait Until Page Contains Element    class=welcome-message    timeout=10s


Setup Cart With One Item
    [Documentation]    Add one item to cart
    Go To    ${SERVER}/products
    Click Element    css=.product-card:first-child .add-to-cart
    Go To    ${SERVER}/cart


Setup Cart With Multiple Items
    [Documentation]    Add multiple items to cart
    Go To    ${SERVER}/products
    Click Element    css=.product-card:nth-child(1) .add-to-cart
    Sleep    0.5s
    Click Element    css=.product-card:nth-child(2) .add-to-cart
    Sleep    0.5s
    Click Element    css=.product-card:nth-child(3) .add-to-cart
    Go To    ${SERVER}/cart


Cart Item Count Should Be
    [Documentation]    Verify cart has specific number of items
    [Arguments]    ${expected_count}
    ${actual_count}=    Get Element Count    class=cart-item
    Should Be Equal As Integers    ${actual_count}    ${expected_count}


Calculate Items Total
    [Documentation]    Calculate total price of cart items
    [Arguments]    ${items}
    ${total}=    Set Variable    0.0
    FOR    ${item}    IN    @{items}
        ${price_text}=    Get Text    ${item}//*[@class='item-price']
        ${price}=    Convert To Number    ${price_text[1:]}
        ${total}=    Evaluate    ${total} + ${price}
    END
    [Return]    ${total}
