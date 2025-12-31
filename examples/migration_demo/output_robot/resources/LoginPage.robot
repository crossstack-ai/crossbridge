*** Settings ***
Library    Browser

*** Variables ***
${USERNAME_LOCATOR}    id=username
${PASSWORD_LOCATOR}    id=password
${LOGIN_BUTTON_LOCATOR}    css=button[type='submit']

*** Keywords ***
Enter Username
    [Arguments]    ${username}
    [Documentation]    Enter username into enter username
    Fill Text    ${USERNAME_LOCATOR}    ${username}

Enter Password
    [Arguments]    ${password}
    [Documentation]    Enter password into enter password
    Fill Text    ${PASSWORD_LOCATOR}    ${password}

Click Login Button
    [Documentation]    Click on click login button
    Click    ${LOGIN_BUTTON_LOCATOR}
