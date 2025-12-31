*** Settings ***
Library    Browser

*** Variables ***
${WELCOME_MESSAGE_LOCATOR}    id=verify_welcome_message

*** Keywords ***
Verify Welcome Message
    [Documentation]    Verify verify welcome message
    Get Element States    ${WELCOME_MESSAGE_LOCATOR}    validate    value & visible
