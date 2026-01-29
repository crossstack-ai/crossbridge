#!/usr/bin/env python3
"""
Quick test of AI transformation capability
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.orchestration.orchestrator import MigrationOrchestrator

# Sample Java step definition
SAMPLE_JAVA = '''
package com.example.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public class LoginSteps {
    
    private WebDriver driver;
    
    @Given("user is on the login page")
    public void userIsOnLoginPage() {
        driver.get("https://example.com/login");
    }
    
    @When("user enters username {string}")
    public void userEntersUsername(String username) {
        driver.findElement(By.id("username")).sendKeys(username);
    }
}
'''

def main():
    print("Testing AI transformation...")
    print()
    
    # Check for API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='sk-...'")
        return
    
    print(f"✅ API key found: {api_key[:10]}...")
    print()
    
    # Create mock request
    class MockRequest:
        use_ai = True
        ai_config = {
            'provider': 'openai',
            'api_key': api_key,
            'model': 'gpt-3.5-turbo',
            'temperature': 0.3
        }
    
    orchestrator = MigrationOrchestrator()
    
    print("Calling AI transformation...")
    try:
        result = orchestrator._transform_java_to_robot_keywords(
            content=SAMPLE_JAVA,
            source_path="src/test/java/steps/LoginSteps.java",
            with_review_markers=False,
            request=MockRequest()
        )
        
        print("✅ AI transformation successful!")
        print()
        print("=" * 80)
        print("ROBOT FRAMEWORK OUTPUT:")
        print("=" * 80)
        print(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
