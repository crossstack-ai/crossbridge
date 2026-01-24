"""
Simple demonstration showing the difference between placeholder and improved extraction
"""
import re

# What you're currently getting from Bitbucket
CURRENT_OUTPUT = """*** Settings ***
Documentation    Migrated from: TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java
Library          Browser

*** Keywords ***
# TODO: Implement keywords from Java class
# Source: TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java

Placeholder Keyword
    [Documentation]    This is a placeholder - actual transformation pending
    Log    Java file migrated: ActiveDirectorySteps.java"""

# Sample Java source
JAVA_SOURCE = """
package com.arcserve.teton.stepdefinition;

import cucumber.api.java.en.Given;
import cucumber.api.java.en.When;
import cucumber.api.java.en.Then;

public class ActiveDirectorySteps {
    
    @Given("^user is on Active Directory configuration page$")
    public void userIsOnActiveDirectoryConfigurationPage() {
        driver.get("https://admin.arcserve.com/active-directory");
    }
    
    @When("^user enters domain controller IP \\\\"([^\\\\"]*)\\\\"$")
    public void userEntersDomainControllerIP(String ipAddress) {
        adPage.enterDomainControllerIP(ipAddress);
    }
    
    @When("^user clicks test connection button$")
    public void userClicksTestConnectionButton() {
        adPage.clickTestConnection();
    }
    
    @Then("^connection status should display \\\\"([^\\\\"]*)\\\\"$")
    public void connectionStatusShouldDisplay(String expectedStatus) {
        Assert.assertEquals(expectedStatus, actualStatus);
    }
}
"""

def extract_annotations_improved(content):
    """Improved extraction using simple regex"""
    # Extract Cucumber annotations - handle both simple and complex patterns
    annotation_pattern = r'@(Given|When|Then|And|But)\s*\(["\'](.+?)["\']\s*\)'
    annotations_found = re.findall(annotation_pattern, content, re.IGNORECASE | re.DOTALL)
    
    keywords = []
    for step_type, pattern in annotations_found:
        # Clean up pattern
        pattern_clean = pattern.replace('^', '').replace('$', '').replace('\\"', '')
        pattern_clean = re.sub(r'\([^)]*\)', '{value}', pattern_clean)
        pattern_clean = pattern_clean.strip()
        
        # Create keyword name
        keyword_name = ' '.join(word.capitalize() for word in pattern_clean.split())
        
        keywords.append({
            'name': keyword_name,
            'type': step_type.capitalize(),
            'original_pattern': pattern
        })
    
    return keywords

def generate_improved_output(java_content, source_file):
    """Generate improved Robot Framework output"""
    keywords = extract_annotations_improved(java_content)
    
    output = f"""*** Settings ***
Documentation    Migrated from: {source_file}
...              Contains {len(keywords)} step definitions extracted from Cucumber annotations
...              ⚠️ Manual implementation required - these are scaffolds based on the original patterns
Library          Browser

*** Keywords ***
"""
    
    for kw in keywords:
        output += f"\n{kw['name']}\n"
        output += f"    [Documentation]    Original Cucumber pattern: {kw['original_pattern']}\n"
        output += f"    [Tags]    {kw['type']}    TODO\n"
        output += f"    # TODO: Implement this keyword based on the original Java implementation\n"
        output += f"    Log    TODO: {kw['name']}\n"
    
    return output

# Main comparison
print("="*80)
print("CURRENT OUTPUT FROM BITBUCKET")
print("="*80)
print(CURRENT_OUTPUT)
print("\n")
print(f"Keywords extracted: 1 (placeholder only)")
print(f"Useful information: ❌ None")

print("\n\n")
print("="*80)
print("IMPROVED OUTPUT (with enhanced fallback)")
print("="*80)
improved = generate_improved_output(JAVA_SOURCE, "TetonUIAutomation/src/main/java/com/arcserve/teton/stepdefinition/ActiveDirectorySteps.java")
print(improved)

keywords = extract_annotations_improved(JAVA_SOURCE)
print("\n")
print(f"Keywords extracted: {len(keywords)}")
print(f"Useful information: ✅ Step patterns, types, and structure preserved")

print("\n\n")
print("="*80)
print("SUMMARY")
print("="*80)
print(f"📊 Improvement: {len(keywords)}x more keywords!")
print(f"⏱️  Time saved: ~{len(keywords) * 15} minutes of manual extraction")
print(f"✅ Each keyword includes:")
print(f"   • Original Cucumber pattern")
print(f"   • Step type (Given/When/Then)")
print(f"   • Clear TODO markers")
print(f"   • Meaningful keyword names")
print("\n🎯 Result: Actionable starting point instead of empty placeholder!")
