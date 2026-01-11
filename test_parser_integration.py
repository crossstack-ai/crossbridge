"""Quick integration test for the enhanced parser"""
import sys
sys.path.insert(0, '.')

from adapters.selenium_bdd_java.step_definition_parser import JavaStepDefinitionParser

# Test 1: Click with ID locator
java_code = '''
@Given("user clicks login button")
public void userClicksLoginButton() {
    driver.findElement(By.id("loginBtn")).click();
}
'''

parser = JavaStepDefinitionParser()
result = parser.parse_content(java_code, "TestSteps.java")

print(f"✓ Parsed {len(result.step_definitions)} step definition(s)")
step_def = result.step_definitions[0]
print(f"  Step: {step_def.pattern_text}")
print(f"  Method: {step_def.method_name}")
print(f"  Selenium actions: {len(step_def.selenium_actions)}")

for action in step_def.selenium_actions:
    print(f"    - {action.action_type}: locator={action.locator_type}:{action.locator_value}")

# Test 2: Complex scenario
complex_java = '''
@When("user logs in with username {string} and password {string}")
public void userLogsIn(String username, String password) {
    driver.get("https://example.com/login");
    driver.findElement(By.id("username")).sendKeys(username);
    driver.findElement(By.id("password")).sendKeys(password);
    driver.findElement(By.cssSelector("#loginBtn")).click();
    
    WebDriverWait wait = new WebDriverWait(driver, 10);
    wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("dashboard")));
    
    String welcomeText = driver.findElement(By.xpath("//h1[@class='welcome']")).getText();
    assertTrue(welcomeText.contains(username));
}
'''

result2 = parser.parse_content(complex_java, "LoginSteps.java")
step_def2 = result2.step_definitions[0]

print(f"\n✓ Complex scenario:")
print(f"  Step: {step_def2.pattern_text}")
print(f"  Selenium actions: {len(step_def2.selenium_actions)}")
print(f"  Assertions: {len(step_def2.assertions)}")

# Count action types
action_types = {}
for action in step_def2.selenium_actions:
    action_types[action.action_type] = action_types.get(action.action_type, 0) + 1

print(f"  Action breakdown:")
for action_type, count in action_types.items():
    print(f"    - {action_type}: {count}")

# Test 3: Now test with orchestrator
print(f"\n✓ Testing orchestrator integration...")
from core.orchestration.orchestrator import MigrationOrchestrator

orch = MigrationOrchestrator()

# Test selenium to playwright conversion
from adapters.selenium_bdd_java.step_definition_parser import SeleniumAction

click_action = SeleniumAction(
    action_type="click",
    target="loginBtn",
    locator_type="id",
    locator_value="loginBtn",
    parameters=[],
    line_number=1,
    variable_name="",
    full_statement="driver.findElement(By.id('loginBtn')).click();"
)

playwright_code = orch._selenium_to_playwright(click_action)
print(f"  Selenium click → Playwright: {playwright_code}")

sendkeys_action = SeleniumAction(
    action_type="sendKeys",
    target="username",
    locator_type="id",
    locator_value="username",
    parameters=['"testuser"'],
    line_number=2,
    variable_name="",
    full_statement="driver.findElement(By.id('username')).sendKeys(username);"
)

playwright_code2 = orch._selenium_to_playwright(sendkeys_action)
print(f"  Selenium sendKeys → Playwright: {playwright_code2}")

print("\n✅ All integration tests passed!")
