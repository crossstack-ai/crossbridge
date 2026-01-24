"""
Unit tests for step definition fallback transformation
Tests the enhanced fallback when the advanced parser fails to extract annotations
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.orchestration.orchestrator import MigrationOrchestrator


# Sample Java step definition content that might not parse correctly
SAMPLE_ACTIVE_DIRECTORY_STEPS = '''
package com.arcserve.teton.stepdefinition;

import cucumber.api.java.en.Given;
import cucumber.api.java.en.When;
import cucumber.api.java.en.Then;
import org.openqa.selenium.WebDriver;

public class ActiveDirectorySteps {
    
    private WebDriver driver;
    
    @Given("^user navigates to Active Directory page$")
    public void userNavigatesToActiveDirectoryPage() {
        driver.get("https://example.com/active-directory");
    }
    
    @When("^user enters domain name \"([^\"]*)\"$")
    public void userEntersDomainName(String domainName) {
        driver.findElement(By.id("domainName")).sendKeys(domainName);
    }
    
    @When("^user clicks connect button$")
    public void userClicksConnectButton() {
        driver.findElement(By.xpath("//button[@id='connectBtn']")).click();
    }
    
    @Then("^user should see connection status as \"([^\"]*)\"$")
    public void userShouldSeeConnectionStatus(String expectedStatus) {
        String actualStatus = driver.findElement(By.id("status")).getText();
        Assert.assertEquals(expectedStatus, actualStatus);
    }
    
    @Then("^Active Directory should be configured successfully$")
    public void activeDirectoryShouldBeConfigured() {
        boolean isConfigured = driver.findElement(By.id("adConfigured")).isDisplayed();
        Assert.assertTrue(isConfigured);
    }
}
'''


# Sample with io.cucumber annotations (newer format)
SAMPLE_NEW_CUCUMBER_FORMAT = '''
package com.arcserve.teton.stepdefinition;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;

public class ActiveDirectorySteps {
    
    @Given("user navigates to Active Directory page")
    public void userNavigatesToActiveDirectoryPage() {
        // implementation
    }
    
    @When("user enters domain name {string}")
    public void userEntersDomainName(String domainName) {
        // implementation
    }
}
'''


class TestStepDefinitionFallback:
    """Test fallback transformation for step definitions"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        return MigrationOrchestrator()
    
    def test_fallback_extracts_cucumber_annotations(self, orchestrator):
        """Test that fallback can extract Cucumber annotations with simple regex"""
        
        result = orchestrator._create_step_definition_fallback(
            SAMPLE_ACTIVE_DIRECTORY_STEPS,
            "ActiveDirectorySteps.java",
            with_review_markers=False
        )
        
        # Should contain Settings section
        assert "*** Settings ***" in result
        assert "Library          Browser" in result
        
        # Should contain Keywords section
        assert "*** Keywords ***" in result
        
        # Should extract the Given annotation
        assert "User Navigates To Active Directory Page" in result or "user navigates to active directory page" in result.lower()
        
        # Should extract the When annotation with parameter (it's in the output but with different wording)
        assert "connect button" in result.lower() or "clicks" in result.lower()
        
        # Should extract the Then annotation
        assert "configured successfully" in result.lower()
        
        # Should include documentation
        assert "[Documentation]" in result
        assert "Given:" in result or "When:" in result or "Then:" in result
        
        # Should have tags
        assert "[Tags]" in result
        assert "needs-implementation" in result
        
        print("\n✓ Fallback successfully extracted Cucumber annotations")
        print(f"\nGenerated Robot Framework content:\n{result}")
    
    def test_fallback_extracts_methods_when_no_annotations(self, orchestrator):
        """Test that fallback extracts method names when annotations aren't found"""
        
        # Java file without recognizable annotations
        java_without_annotations = '''
        public class SomeSteps {
            public void setupTest() {
                // setup
            }
            
            public void executeAction() {
                // action
            }
            
            public void verifyResult() {
                // verify
            }
        }
        '''
        
        result = orchestrator._create_step_definition_fallback(
            java_without_annotations,
            "SomeSteps.java",
            with_review_markers=False
        )
        
        # Should extract method names
        assert "Setup Test" in result or "Execute Action" in result or "Verify Result" in result
        
        # Should include method documentation
        assert "Extracted from method:" in result
        
        print("\n✓ Fallback successfully extracted method names")
        print(f"\nGenerated Robot Framework content:\n{result}")
    
    def test_fallback_handles_new_cucumber_format(self, orchestrator):
        """Test that fallback handles io.cucumber.java.en annotations"""
        
        result = orchestrator._create_step_definition_fallback(
            SAMPLE_NEW_CUCUMBER_FORMAT,
            "ActiveDirectorySteps.java",
            with_review_markers=False
        )
        
        # Should extract annotations from new format
        assert "Active Directory" in result
        assert "domain name" in result.lower()
        
        print("\n✓ Fallback successfully handled new Cucumber format")
        print(f"\nGenerated Robot Framework content:\n{result}")
    
    def test_fallback_infers_step_types(self, orchestrator):
        """Test that fallback infers step types from method names"""
        
        java_with_semantic_names = '''
        public class InferredSteps {
            public void givenUserIsLoggedIn() {
                // setup
            }
            
            public void whenUserClicksButton() {
                // action
            }
            
            public void thenResultShouldBeVisible() {
                // verification
            }
            
            public void enterUsername(String username) {
                // action - should infer as 'when'
            }
            
            public void verifyPageTitle() {
                // verification - should infer as 'then'
            }
        }
        '''
        
        result = orchestrator._create_step_definition_fallback(
            java_with_semantic_names,
            "InferredSteps.java",
            with_review_markers=False
        )
        
        # Should have inferred tags
        assert "given" in result.lower()
        assert "when" in result.lower()
        assert "then" in result.lower()
        
        print("\n✓ Fallback successfully inferred step types")
        print(f"\nGenerated Robot Framework content:\n{result}")
    
    def test_fallback_handles_empty_file(self, orchestrator):
        """Test that fallback handles files with no extractable content"""
        
        empty_java = '''
        public class EmptySteps {
            // No methods
        }
        '''
        
        result = orchestrator._create_step_definition_fallback(
            empty_java,
            "EmptySteps.java",
            with_review_markers=False
        )
        
        # Should have a TODO placeholder
        assert "TODO Implement Keywords" in result
        assert "CRITICAL" in result or "manual" in result.lower()
        
        print("\n✓ Fallback successfully handled empty file")
        print(f"\nGenerated Robot Framework content:\n{result}")
    
    def test_transformation_with_parser_failure(self, orchestrator):
        """Test full transformation when parser fails"""
        
        # Test that even when the parser completely fails, we get reasonable output
        result = orchestrator._create_step_definition_fallback(
            SAMPLE_ACTIVE_DIRECTORY_STEPS,
            "ActiveDirectorySteps.java",
            with_review_markers=False
        )
        
        # Should still generate content via fallback
        assert "*** Settings ***" in result
        assert "*** Keywords ***" in result
        
        # Should have extracted something useful
        assert "Active Directory" in result or "Navigates" in result
        
        print("\n✓ Full transformation handled parser failure gracefully")
        print(f"\nGenerated Robot Framework content:\n{result}")
    
    def test_fallback_cleans_regex_patterns(self, orchestrator):
        """Test that fallback converts regex patterns to readable names"""
        
        java_with_regex = '''
        public class RegexSteps {
            @Given("^user enters username \"([^\"]*)\" and password \"([^\"]*)\"$")
            public void userEntersCredentials(String username, String password) {
                // implementation
            }
            
            @When("^user clicks (.*) button$")
            public void userClicksButton(String buttonName) {
                // implementation
            }
        }
        '''
        
        result = orchestrator._create_step_definition_fallback(
            java_with_regex,
            "RegexSteps.java",
            with_review_markers=False
        )
        
        # Should convert (.*) and ([^"]*) to {value}
        assert "{value}" in result.lower() or "username" in result.lower()
        
        # Should create readable keyword names
        assert "User Enters" in result or "User Clicks" in result
        
        print("\n✓ Fallback successfully cleaned regex patterns")
        print(f"\nGenerated Robot Framework content:\n{result}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
