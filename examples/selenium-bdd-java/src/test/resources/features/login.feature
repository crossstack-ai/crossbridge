@auth @smoke
Feature: Login Feature

  Background:
    Given the application is running
    And user is on home page

  @positive @critical
  Scenario: Valid login with correct credentials
    Given user is on login page
    When user enters username "testuser"
    And user enters password "testpass"
    And user clicks login button
    Then user should be redirected to dashboard
    And welcome message should be displayed

  @negative
  Scenario: Invalid login with wrong password
    Given user is on login page
    When user enters username "testuser"
    And user enters password "wrongpass"
    And user clicks login button
    Then error message "Invalid credentials" should be displayed
    And user should remain on login page

  @positive
  Scenario Outline: Login with different valid users
    Given user is on login page
    When user enters username "<username>"
    And user enters password "<password>"
    And user clicks login button
    Then user should be redirected to "<landing_page>"

    Examples:
      | username | password  | landing_page |
      | admin    | admin123  | admin_panel  |
      | user     | user123   | dashboard    |
      | guest    | guest123  | home         |
