package stepdefinitions;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import org.openqa.selenium.WebDriver;
import pages.LoginPage;
import pages.HomePage;

public class LoginSteps {
    
    private WebDriver driver;
    private LoginPage loginPage;
    private HomePage homePage;
    
    public LoginSteps(WebDriver driver) {
        this.driver = driver;
        this.loginPage = new LoginPage(driver);
        this.homePage = new HomePage(driver);
    }
    
    @Given("user is on the login page")
    public void userIsOnLoginPage() {
        driver.get("https://example.com/login");
    }
    
    @When("user enters username {string}")
    public void userEntersUsername(String username) {
        loginPage.enterUsername(username);
    }
    
    @When("user enters password {string}")
    public void userEntersPassword(String password) {
        loginPage.enterPassword(password);
    }
    
    @When("user clicks login button")
    public void userClicksLoginButton() {
        loginPage.clickLoginButton();
    }
    
    @Then("user should see welcome message")
    public void userShouldSeeWelcomeMessage() {
        homePage.verifyWelcomeMessage();
    }
    
    @Then("user should be on home page")
    public void userShouldBeOnHomePage() {
        String currentUrl = driver.getCurrentUrl();
        if (!currentUrl.contains("/home")) {
            throw new AssertionError("Not on home page");
        }
    }
}
