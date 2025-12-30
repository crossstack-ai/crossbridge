@regression @e2e
Feature: Shopping Cart

  @cart @positive
  Scenario: Add single item to cart
    Given user is logged in
    And user is on products page
    When user clicks "Add to Cart" for "Laptop"
    Then cart icon should show "1" item
    And cart total should be "$999.00"

  @cart @positive
  Scenario: Add multiple items to cart
    Given user is logged in
    And user is on products page
    When user adds the following items:
      | Product  | Quantity |
      | Laptop   | 1        |
      | Mouse    | 2        |
      | Keyboard | 1        |
    Then cart should contain 4 items total
    And cart subtotal should be calculated correctly

  @cart @negative
  Scenario: Remove item from cart
    Given user has items in cart
    When user clicks "Remove" for "Mouse"
    Then cart should not contain "Mouse"
    And cart total should be updated
