*** Settings ***
Documentation    testGetUserById
...              Translated from: restassured
...              Confidence: 1.00

Library    RequestsLibrary
Library    Collections
Library    String
Library    BuiltIn
Suite Setup    Create Session    api    ${{BASE_URL}}
Suite Teardown    Delete All Sessions

*** Test Cases ***
Get User By Id

    # Source line: 20
    ${response}=    GET On Session    api    /api/users/{id}    headers=&{Content-Type=application/json}
    # Source line: 38
    ${response}=    POST On Session    api    /api/users    data=${newUser}    headers=&{Content-Type=application/json}
    # Source line: 52
    ${response}=    PUT On Session    api    /api/users/{id}    json={\"email\": \"newemail@example.com\"}    headers=&{Content-Type=application/json}
    # Source line: 63
    ${response}=    DELETE On Session    api    /api/users/{id}    json={\"email\": \"newemail@example.com\"}    headers=&{Content-Type=application/json}
    # Source line: 74
    ${response}=    GET On Session    api    /api/users/search    json={\"email\": \"newemail@example.com\"}    headers=&{Content-Type=application/json}
    # Source line: 22
    Status Should Be    200    ${response}
    # Source line: 23
    Dictionary Should Contain Item    ${response.json()}    id    123
    # Source line: 40
    Status Should Be    201    ${response}
    # Source line: 42
    Dictionary Should Contain Item    ${response.json()}    username    johndoe
    # Source line: 54
    Status Should Be    200    ${response}
    # Source line: 55
    Dictionary Should Contain Item    ${response.json()}    email    newemail@example.com
    # Source line: 65
    Status Should Be    204    ${response}
    # Source line: 76
    Status Should Be    200    ${response}