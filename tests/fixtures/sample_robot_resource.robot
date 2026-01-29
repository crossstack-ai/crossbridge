*** Settings ***
Documentation    Sample Robot Framework resource file (page object style) for testing adapter
Library          SeleniumLibrary


*** Variables ***
${LOGIN_URL}              https://example.com/login
${USERNAME_FIELD}         id=username
${PASSWORD_FIELD}         id=password
${SUBMIT_BUTTON}          css=button[type='submit']
${ERROR_MESSAGE}          class=error-message
${WELCOME_MESSAGE}        class=welcome-message


*** Keywords ***
#
# Login Page Keywords
#
Navigate To Login Page
    [Documentation]    Navigate to login page
    Go To    ${LOGIN_URL}
    Wait Until Page Contains Element    ${USERNAME_FIELD}


Enter Username
    [Documentation]    Enter username in login form
    [Arguments]    ${username}
    Input Text    ${USERNAME_FIELD}    ${username}


Enter Password
    [Documentation]    Enter password in login form
    [Arguments]    ${password}
    Input Password    ${PASSWORD_FIELD}    ${password}


Click Submit Button
    [Documentation]    Click the submit button
    Click Button    ${SUBMIT_BUTTON}


Login With Credentials
    [Documentation]    Complete login flow with provided credentials
    [Arguments]    ${username}    ${password}
    Navigate To Login Page
    Enter Username    ${username}
    Enter Password    ${password}
    Click Submit Button


Verify Login Success
    [Documentation]    Verify successful login
    Wait Until Page Contains Element    ${WELCOME_MESSAGE}    timeout=10s
    Location Should Contain    /dashboard


Verify Login Error
    [Documentation]    Verify login error is displayed
    [Arguments]    ${expected_message}
    Wait Until Page Contains Element    ${ERROR_MESSAGE}    timeout=10s
    ${actual_message}=    Get Text    ${ERROR_MESSAGE}
    Should Contain    ${actual_message}    ${expected_message}


#
# Shopping Cart Page Keywords
#
Navigate To Cart
    [Documentation]    Navigate to shopping cart page
    Go To    https://example.com/cart
    Wait Until Page Contains Element    class=cart-container


Get Cart Item Count
    [Documentation]    Get number of items in cart
    ${count}=    Get Element Count    class=cart-item
    [Return]    ${count}


Remove Item By Index
    [Documentation]    Remove cart item by index
    [Arguments]    ${index}=0
    ${items}=    Get WebElements    class=cart-item
    ${item}=    Set Variable    ${items}[${index}]
    ${remove_btn}=    Get WebElement    ${item}//*[@class='remove-button']
    Click Element    ${remove_btn}


Get Cart Total
    [Documentation]    Get cart total price
    ${total_text}=    Get Text    class=total-price
    ${total}=    Convert To Number    ${total_text[1:]}
    [Return]    ${total}


Verify Cart Is Empty
    [Documentation]    Verify cart has no items
    Element Should Be Visible    class=empty-cart-message
    ${count}=    Get Cart Item Count
    Should Be Equal As Integers    ${count}    0


#
# Product Page Keywords
#
Navigate To Products
    [Documentation]    Navigate to products page
    Go To    https://example.com/products
    Wait Until Page Contains Element    class=product-card


Add First Product To Cart
    [Documentation]    Add first product to cart
    Click Element    css=.product-card:first-child .add-to-cart
    Wait Until Page Contains    Added to cart    timeout=5s


Add Product By Index
    [Documentation]    Add product to cart by index
    [Arguments]    ${index}
    ${product}=    Get WebElements    class=product-card
    Click Element    ${product}[${index}]//*[@class='add-to-cart']


Get Product Title
    [Documentation]    Get product title by index
    [Arguments]    ${index}=0
    ${products}=    Get WebElements    class=product-card
    ${title}=    Get Text    ${products}[${index}]//*[@class='product-title']
    [Return]    ${title}


#
# Common Keywords
#
Wait For Page To Load
    [Documentation]    Wait for page to fully load
    Wait Until Page Contains Element    tag=body    timeout=10s
    Sleep    0.5s


Verify Element Contains Text
    [Documentation]    Verify element contains specific text
    [Arguments]    ${locator}    ${expected_text}
    ${actual_text}=    Get Text    ${locator}
    Should Contain    ${actual_text}    ${expected_text}


Take Screenshot On Failure
    [Documentation]    Take screenshot when test fails
    Run Keyword If Test Failed    Capture Page Screenshot
