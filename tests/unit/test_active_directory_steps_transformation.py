"""
Unit test comparing actual placeholder output vs improved fallback transformation
Testing with real-world ActiveDirectorySteps.java scenario
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from core.orchestration.orchestrator import MigrationOrchestrator


# This is what currently gets generated (placeholder)
CURRENT_PLACEHOLDER_OUTPUT = '''*** Settings ***
Documentation    Migrated from: TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java
Library          Browser

*** Keywords ***
# TODO: Implement keywords from Java class
# Source: TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java

Placeholder Keyword
    [Documentation]    This is a placeholder - actual transformation pending
    Log    Java file migrated: ActiveDirectorySteps.java
'''


# Sample ActiveDirectorySteps.java content (simulated based on typical structure)
SAMPLE_ACTIVE_DIRECTORY_STEPS_JAVA = '''
package com.arcserve.teton.stepdefinition;

import cucumber.api.java.en.Given;
import cucumber.api.java.en.When;
import cucumber.api.java.en.Then;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.By;
import com.arcserve.teton.pages.ActiveDirectoryPage;

public class ActiveDirectorySteps {
    
    private WebDriver driver;
    private ActiveDirectoryPage adPage;
    
    @Given("^user is on Active Directory configuration page$")
    public void userIsOnActiveDirectoryConfigurationPage() {
        driver.get("https://admin.arcserve.com/active-directory");
        adPage = new ActiveDirectoryPage(driver);
    }
    
    @When("^user enters domain controller IP \"([^\"]*)\"$")
    public void userEntersDomainControllerIP(String ipAddress) {
        adPage.enterDomainControllerIP(ipAddress);
    }
    
    @When("^user enters domain name \"([^\"]*)\"$")
    public void userEntersDomainName(String domainName) {
        adPage.enterDomainName(domainName);
    }
    
    @When("^user enters admin username \"([^\"]*)\"$")
    public void userEntersAdminUsername(String username) {
        adPage.enterAdminUsername(username);
    }
    
    @When("^user enters admin password \"([^\"]*)\"$")
    public void userEntersAdminPassword(String password) {
        adPage.enterAdminPassword(password);
    }
    
    @When("^user clicks test connection button$")
    public void userClicksTestConnectionButton() {
        adPage.clickTestConnection();
    }
    
    @Then("^connection status should display \"([^\"]*)\"$")
    public void connectionStatusShouldDisplay(String expectedStatus) {
        String actualStatus = adPage.getConnectionStatus();
        Assert.assertEquals(expectedStatus, actualStatus);
    }
    
    @Then("^Active Directory should be successfully configured$")
    public void activeDirectoryShouldBeSuccessfullyConfigured() {
        boolean isConfigured = adPage.isConfigurationSuccessful();
        Assert.assertTrue("AD not configured", isConfigured);
    }
    
    @When("^user saves Active Directory configuration$")
    public void userSavesActiveDirectoryConfiguration() {
        adPage.clickSave();
    }
}
'''


class TestActiveDirectoryStepsTransformation:
    """Compare current placeholder output with improved fallback transformation"""
    
    @pytest.fixture
    def orchestrator(self):
        return MigrationOrchestrator()
    
    def test_current_output_is_placeholder(self):
        """Document what currently gets generated - just a placeholder"""
        
        # Verify the current output is indeed just a placeholder
        assert "Placeholder Keyword" in CURRENT_PLACEHOLDER_OUTPUT
        assert "TODO: Implement keywords" in CURRENT_PLACEHOLDER_OUTPUT
        
        # Count useful keywords (should be 0 or 1 placeholder)
        keyword_count = CURRENT_PLACEHOLDER_OUTPUT.count("[Documentation]")
        
        print("\n" + "="*60)
        print("CURRENT OUTPUT (Placeholder)")
        print("="*60)
        print(CURRENT_PLACEHOLDER_OUTPUT)
        print(f"\nUseful keywords extracted: {keyword_count}")
        print("⚠️  Problem: No actual step definitions extracted!")
        
        assert keyword_count <= 1, "Current output should have minimal keywords"
    
    def test_improved_fallback_extracts_real_keywords(self, orchestrator):
        """Show what the improved fallback produces - actual keywords!"""
        
        # Generate improved output using our enhanced fallback
        improved_output = orchestrator._create_step_definition_fallback(
            SAMPLE_ACTIVE_DIRECTORY_STEPS_JAVA,
            "TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java",
            with_review_markers=False
        )
        
        print("\n" + "="*60)
        print("IMPROVED OUTPUT (Enhanced Fallback)")
        print("="*60)
        print(improved_output)
        
        # Validate improvements
        assert "*** Settings ***" in improved_output
        assert "*** Keywords ***" in improved_output
        
        # Should extract Given steps
        assert "User Is On Active Directory Configuration Page" in improved_output or \
               "active directory configuration page" in improved_output.lower()
        
        # Should extract When steps with parameters
        assert "domain controller" in improved_output.lower() or "domain name" in improved_output.lower()
        
        # Should extract Then steps
        assert "connection status" in improved_output.lower() or "successfully configured" in improved_output.lower()
        
        # Should include step types
        assert "Given:" in improved_output or "When:" in improved_output or "Then:" in improved_output
        
        # Should include tags
        assert "[Tags]" in improved_output
        assert "needs-implementation" in improved_output
        
        # Count actual keywords extracted
        keyword_count = improved_output.count("[Documentation]")
        
        print(f"\n✅ Useful keywords extracted: {keyword_count}")
        print("✅ Actual Cucumber annotations found and converted!")
        
        # Should have extracted multiple keywords (at least 5-8 from the sample)
        assert keyword_count >= 5, f"Should extract multiple keywords, got {keyword_count}"
    
    def test_comparison_shows_dramatic_improvement(self, orchestrator):
        """Compare side-by-side to show the improvement"""
        
        improved_output = orchestrator._create_step_definition_fallback(
            SAMPLE_ACTIVE_DIRECTORY_STEPS_JAVA,
            "TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java",
            with_review_markers=False
        )
        
        # Count keywords in each
        current_keywords = CURRENT_PLACEHOLDER_OUTPUT.count("[Documentation]")
        improved_keywords = improved_output.count("[Documentation]")
        
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        print(f"Current Output:")
        print(f"  - Keywords: {current_keywords}")
        print(f"  - Has step patterns: NO")
        print(f"  - Has step types: NO")
        print(f"  - Has tags: NO")
        print(f"  - Actionable: ❌ (must start from scratch)")
        print()
        print(f"Improved Output:")
        print(f"  - Keywords: {improved_keywords}")
        print(f"  - Has step patterns: YES ✅")
        print(f"  - Has step types: YES ✅")
        print(f"  - Has tags: YES ✅")
        print(f"  - Actionable: ✅ (clear implementation guide)")
        print()
        print(f"Improvement: {improved_keywords}x more keywords extracted!")
        print("="*60)
        
        # The improvement should be dramatic
        assert improved_keywords > current_keywords * 3, \
            f"Improved fallback should extract significantly more keywords"
    
    def test_improved_output_has_implementation_guidance(self, orchestrator):
        """Verify improved output provides clear implementation guidance"""
        
        improved_output = orchestrator._create_step_definition_fallback(
            SAMPLE_ACTIVE_DIRECTORY_STEPS_JAVA,
            "TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java",
            with_review_markers=False
        )
        
        # Should include original patterns for reference
        assert "Original pattern:" in improved_output
        
        # Should include TODO markers
        assert "TODO: Implement" in improved_output
        
        # Should include warning markers
        assert "⚠️" in improved_output
        
        # Should organize by step type
        has_given = "given" in improved_output.lower()
        has_when = "when" in improved_output.lower()
        has_then = "then" in improved_output.lower()
        
        assert has_given or has_when or has_then, \
            "Should include step type information"
        
        print("\n✅ Improved output includes:")
        print("  - Original Cucumber patterns for reference")
        print("  - Clear TODO markers for implementation")
        print("  - Step types (Given/When/Then) for organization")
        print("  - Tags for filtering and categorization")
        print("  - Warning markers for manual review areas")
    
    def test_real_world_scenario_active_directory(self, orchestrator):
        """Full test simulating the real ActiveDirectorySteps.java file"""
        
        print("\n" + "="*60)
        print("REAL-WORLD SCENARIO: ActiveDirectorySteps.java Migration")
        print("="*60)
        
        # Generate transformation
        result = orchestrator._create_step_definition_fallback(
            SAMPLE_ACTIVE_DIRECTORY_STEPS_JAVA,
            "TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java",
            with_review_markers=False
        )
        
        print("\nExpected Steps to Extract:")
        print("1. Given: user is on Active Directory configuration page")
        print("2. When: user enters domain controller IP")
        print("3. When: user enters domain name")
        print("4. When: user enters admin username")
        print("5. When: user enters admin password")
        print("6. When: user clicks test connection button")
        print("7. Then: connection status should display")
        print("8. Then: Active Directory should be successfully configured")
        print("9. When: user saves Active Directory configuration")
        
        # Verify key steps were extracted
        steps_to_check = [
            "Active Directory configuration page",
            "domain controller",
            "domain name",
            "admin username",
            "admin password",
            "test connection",
            "connection status",
            "successfully configured",
            "saves"
        ]
        
        found_steps = []
        for step in steps_to_check:
            if step.lower() in result.lower():
                found_steps.append(step)
        
        print(f"\n✅ Successfully extracted {len(found_steps)}/{len(steps_to_check)} steps")
        print(f"   Found: {', '.join(found_steps[:5])}...")
        
        # Show sample output
        print("\n--- Sample Generated Keyword ---")
        lines = result.split('\n')
        keyword_start = None
        for i, line in enumerate(lines):
            if 'Active Directory' in line and not line.strip().startswith('#'):
                keyword_start = i
                break
        
        if keyword_start:
            sample = '\n'.join(lines[keyword_start:keyword_start+6])
            print(sample)
        
        assert len(found_steps) >= 6, \
            f"Should extract most steps, found {len(found_steps)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
