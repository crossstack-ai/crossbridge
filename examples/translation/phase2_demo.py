"""
Quick demo of Phase 2 translation paths.

Demonstrates:
1. RestAssured → Pytest
2. RestAssured → Robot Framework
3. Selenium BDD → Pytest
4. Selenium BDD → Robot Framework
"""

from core.translation.pipeline import TranslationPipeline


def demo_restassured_to_pytest():
    """Demo RestAssured to pytest translation."""
    print("\n" + "="*80)
    print("DEMO 1: RestAssured → Pytest")
    print("="*80)
    
    restassured_code = """
    import io.restassured.RestAssured;
    import static io.restassured.RestAssured.*;
    import static org.hamcrest.Matchers.*;
    
    @Test
    public void testGetUser() {
        given()
            .auth().basic("admin", "password123")
            .header("Accept", "application/json")
        .when()
            .get("/api/users/1")
        .then()
            .statusCode(200)
            .body("username", equalTo("admin"))
            .body("email", equalTo("admin@example.com"));
    }
    """
    
    print("\nSource (RestAssured):")
    print(restassured_code)
    
    pipeline = TranslationPipeline()
    result = pipeline.translate(
        source_code=restassured_code,
        source_framework="restassured",
        target_framework="pytest",
    )
    
    if result.success:
        print("\nGenerated pytest code:")
        print(result.target_code)
        print(f"\nConfidence: {result.confidence:.2%}")
        print(f"Warnings: {len(result.warnings)}")
    else:
        print(f"\nTranslation failed: {result.error_message}")


def demo_restassured_to_robot():
    """Demo RestAssured to Robot Framework translation."""
    print("\n" + "="*80)
    print("DEMO 2: RestAssured → Robot Framework")
    print("="*80)
    
    restassured_code = """
    @Test
    public void testCreateUser() {
        given()
            .contentType("application/json")
            .body("{\\"username\\":\\"john\\",\\"email\\":\\"john@example.com\\"}")
        .when()
            .post("/api/users")
        .then()
            .statusCode(201)
            .body("id", notNullValue());
    }
    """
    
    print("\nSource (RestAssured):")
    print(restassured_code)
    
    pipeline = TranslationPipeline()
    result = pipeline.translate(
        source_code=restassured_code,
        source_framework="restassured",
        target_framework="robot",
    )
    
    if result.success:
        print("\nGenerated Robot Framework code:")
        print(result.target_code)
        print(f"\nConfidence: {result.confidence:.2%}")
    else:
        print(f"\nTranslation failed: {result.error_message}")


def demo_selenium_bdd_to_pytest():
    """Demo Selenium BDD to pytest translation."""
    print("\n" + "="*80)
    print("DEMO 3: Selenium BDD → Pytest")
    print("="*80)
    
    selenium_bdd_code = """
    import org.openqa.selenium.WebDriver;
    import org.openqa.selenium.By;
    import cucumber.api.java.en.Given;
    import cucumber.api.java.en.When;
    import cucumber.api.java.en.Then;
    import static org.junit.Assert.*;
    
    // Scenario: Successful user login
    
    @Given("user is on the login page")
    public void userOnLoginPage() {
        driver.get("https://example.com/login");
    }
    
    @When("user enters valid credentials")
    public void userEntersCredentials() {
        driver.findElement(By.id("username")).sendKeys("testuser");
        driver.findElement(By.id("password")).sendKeys("testpass");
    }
    
    @When("user clicks the login button")
    public void userClicksLogin() {
        driver.findElement(By.id("login-button")).click();
    }
    
    @Then("user should see the dashboard")
    public void userSeesDashboard() {
        assertTrue(driver.findElement(By.id("dashboard")).isDisplayed());
        assertEquals("Dashboard", driver.findElement(By.tagName("h1")).getText());
    }
    """
    
    print("\nSource (Selenium BDD):")
    print(selenium_bdd_code)
    
    pipeline = TranslationPipeline()
    result = pipeline.translate(
        source_code=selenium_bdd_code,
        source_framework="selenium-java-bdd",
        target_framework="pytest",
    )
    
    if result.success:
        print("\nGenerated pytest code:")
        print(result.target_code)
        print(f"\nConfidence: {result.confidence:.2%}")
    else:
        print(f"\nTranslation failed: {result.error_message}")


def demo_selenium_bdd_to_robot():
    """Demo Selenium BDD to Robot Framework translation."""
    print("\n" + "="*80)
    print("DEMO 4: Selenium BDD → Robot Framework")
    print("="*80)
    
    selenium_bdd_code = """
    import org.openqa.selenium.WebDriver;
    import org.openqa.selenium.By;
    import cucumber.api.java.en.Given;
    import cucumber.api.java.en.When;
    import cucumber.api.java.en.Then;
    
    // Scenario: User completes registration form
    
    @Given("user opens the registration page")
    public void openRegistration() {
        driver.get("https://example.com/register");
    }
    
    @When("user fills the registration form")
    public void fillForm() {
        driver.findElement(By.id("name")).sendKeys("John Doe");
        driver.findElement(By.id("email")).sendKeys("john@example.com");
        driver.findElement(By.id("password")).sendKeys("SecurePass123");
    }
    
    @When("user submits the form")
    public void submitForm() {
        driver.findElement(By.id("submit-button")).click();
    }
    
    @Then("user should see confirmation message")
    public void seeConfirmation() {
        assertTrue(driver.findElement(By.className("success-message")).isDisplayed());
    }
    """
    
    print("\nSource (Selenium BDD):")
    print(selenium_bdd_code)
    
    pipeline = TranslationPipeline()
    result = pipeline.translate(
        source_code=selenium_bdd_code,
        source_framework="selenium-java-bdd",
        target_framework="robot",
    )
    
    if result.success:
        print("\nGenerated Robot Framework code:")
        print(result.target_code)
        print(f"\nConfidence: {result.confidence:.2%}")
    else:
        print(f"\nTranslation failed: {result.error_message}")


def main():
    """Run all Phase 2 demos."""
    print("\n" + "="*80)
    print(" CROSSBRIDGE - Phase 2 Translation Demos")
    print(" Framework-to-Framework Translation")
    print("="*80)
    
    # Run all demos
    demo_restassured_to_pytest()
    demo_restassured_to_robot()
    demo_selenium_bdd_to_pytest()
    demo_selenium_bdd_to_robot()
    
    print("\n" + "="*80)
    print(" Phase 2 Translation Paths Summary:")
    print("="*80)
    print("\nAPI Testing:")
    print("  1. RestAssured → Pytest (requests library)")
    print("  2. RestAssured → Robot Framework (RequestsLibrary)")
    print("\nBDD UI Testing:")
    print("  3. Selenium BDD → Pytest (Playwright)")
    print("  4. Selenium BDD → Robot Framework (Browser library)")
    print("\nPhase 1 (still available):")
    print("  5. Selenium Java → Playwright Python")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
