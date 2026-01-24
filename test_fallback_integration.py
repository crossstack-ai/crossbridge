"""
Test to verify enhanced fallback works for step definitions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestration.orchestrator import MigrationOrchestrator

# Sample ActiveDirectorySteps.java content
JAVA_CONTENT = r'''
package com.arcserve.teton.stepdefinition;

import cucumber.api.java.en.Given;
import cucumber.api.java.en.When;
import cucumber.api.java.en.Then;

public class ActiveDirectorySteps {
    
    @Given("^user is on Active Directory configuration page$")
    public void userIsOnActiveDirectoryConfigurationPage() {
        driver.get("https://admin.arcserve.com/active-directory");
    }
    
    @When("^user enters domain controller IP \"([^\"]*)\"$")
    public void userEntersDomainControllerIP(String ipAddress) {
        adPage.enterDomainControllerIP(ipAddress);
    }
    
    @When("^user clicks test connection button$")
    public void userClicksTestConnectionButton() {
        adPage.clickTestConnection();
    }
    
    @Then("^connection status should display \"([^\"]*)\"$")
    public void connectionStatusShouldDisplay(String expectedStatus) {
        Assert.assertEquals(expectedStatus, actualStatus);
    }
}
'''

SOURCE_PATH = "TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java"

orchestrator = MigrationOrchestrator()

# Test _create_manual_placeholder with step definition file
print("="*80)
print("TESTING: _create_manual_placeholder with step definition file")
print("="*80)
result = orchestrator._create_manual_placeholder(SOURCE_PATH, 'java', JAVA_CONTENT)

print(result)
print("\n" + "="*80)

# Count keywords
keyword_count = result.count("[Documentation]")
print(f"Keywords extracted: {keyword_count}")

if keyword_count > 1:
    print("✅ SUCCESS: Enhanced fallback extracted multiple keywords!")
else:
    print("❌ FAILURE: Still showing placeholder only")
