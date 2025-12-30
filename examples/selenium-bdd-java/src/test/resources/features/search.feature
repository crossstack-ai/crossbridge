@search
Feature: Search Functionality

  @positive @smoke
  Scenario: Search with valid keyword
    Given user is on home page
    When user enters "laptop" in search box
    And user clicks search button
    Then search results should display products matching "laptop"
    And results count should be greater than 0

  @negative
  Scenario: Search with no results
    Given user is on home page
    When user enters "xyzabc123" in search box
    And user clicks search button
    Then "No results found" message should be displayed
    And suggested alternatives should be shown
