"""
Unit tests for AI-powered transformation file type detection.
Tests the enhanced detection logic that ensures all Java files go through AI transformation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import MigrationRequest, AIConfig


class TestAITransformationDetection:
    """Test suite for AI transformation file type detection and routing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MigrationOrchestrator()
        
        # Create a base request with AI enabled
        self.ai_config = AIConfig(
            provider="openai",
            api_key="test-key",
            model="gpt-4"
        )
        
        self.request = MigrationRequest(
            repo_url="https://github.com/test/repo",
            branch="main",
            target_branch="robot-migration",
            use_ai=True,
            ai_config=self.ai_config
        )
    
    @patch('core.orchestration.orchestrator.logger')
    def test_ai_detection_step_definition_by_content(self, mock_logger):
        """Test AI detection for step definition identified by @Given/@When/@Then."""
        java_content = """
        package com.test;
        
        import io.cucumber.java.en.Given;
        import io.cucumber.java.en.When;
        import io.cucumber.java.en.Then;
        
        public class LoginSteps {
            @Given("user is on login page")
            public void userOnLoginPage() {
                driver.get("https://example.com/login");
            }
            
            @When("user enters credentials")
            public void userEntersCredentials() {
                driver.findElement(By.id("username")).sendKeys("test");
            }
        }
        """
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***\nTest Keyword\n    Log    AI Generated"
            
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/LoginSteps.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Verify AI method was called
            mock_ai.assert_called_once()
            assert mock_ai.call_args[1]['content'] == java_content
            assert mock_ai.call_args[1]['ai_config'] == self.ai_config
            
            # Verify correct detection logging
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('AI-Powered transformation enabled' in str(call) for call in info_calls)
            assert any('Step Definition' in str(call) and '@Given/@When/@Then' in str(call) for call in info_calls)
            assert any('AI transformation successful' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_ai_detection_page_object_by_content(self, mock_logger):
        """Test AI detection for page object identified by @FindBy/WebElement."""
        java_content = """
        package com.test;
        
        import org.openqa.selenium.WebElement;
        import org.openqa.selenium.support.FindBy;
        
        public class LoginPage {
            @FindBy(id = "username")
            private WebElement usernameField;
            
            @FindBy(id = "password")
            private WebElement passwordField;
            
            public void login(String user, String pass) {
                usernameField.sendKeys(user);
                passwordField.sendKeys(pass);
            }
        }
        """
        
        with patch.object(self.orchestrator, '_convert_page_object_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***\nLogin\n    Log    AI Generated"
            
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/LoginPage.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Verify AI method was called
            mock_ai.assert_called_once()
            assert mock_ai.call_args[1]['java_content'] == java_content
            assert mock_ai.call_args[1]['ai_config'] == self.ai_config
            
            # Verify correct detection logging
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('Page Object' in str(call) and '@FindBy/WebElement' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_ai_detection_step_definition_by_filename(self, mock_logger):
        """Test AI detection for step definition identified by filename pattern."""
        java_content = """
        package com.test;
        
        public class SomeSteps {
            public void someMethod() {
                // No specific annotations
            }
        }
        """
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***\nTest Keyword\n    Log    AI Generated"
            
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/stepdefinitions/SomeSteps.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Verify AI method was called
            mock_ai.assert_called_once()
            
            # Verify correct detection logging
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('Step Definition' in str(call) and 'filename pattern' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_ai_detection_generic_test_file(self, mock_logger):
        """Test AI detection for generic test file with @Test methods."""
        java_content = """
        package com.test;
        
        import org.junit.Test;
        
        public class LoginTest {
            @Test
            public void testLogin() {
                // Test code
            }
            
            @Test
            public void testLogout() {
                // Test code
            }
        }
        """
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***\nTest Login\n    Log    AI Generated"
            
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/LoginTest.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Verify AI method was called (this is the key fix - generic test files now use AI)
            mock_ai.assert_called_once()
            
            # Verify correct detection logging
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('Generic Test File' in str(call) and '@Test' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_ai_detection_unknown_java_file(self, mock_logger):
        """Test AI detection for unknown Java file - should still attempt AI transformation."""
        java_content = """
        package com.test;
        
        public class RandomClass {
            public void someMethod() {
                // Generic Java code
                System.out.println("Hello");
            }
        }
        """
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***\nSome Method\n    Log    AI Generated"
            
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/RandomClass.java",
                with_review_markers=False,
                request=self.request
            )
            
            # THIS IS THE MAIN FIX: Unknown files should now go through AI transformation
            mock_ai.assert_called_once()
            
            # Verify correct detection logging
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('Unknown file type' in str(call) and 'attempt AI transformation anyway' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_ai_detection_locator_file(self, mock_logger):
        """Test AI detection for locator file by filename pattern."""
        java_content = """
        package com.test;
        
        public class LoginLocators {
            public static final String USERNAME = "//input[@id='username']";
            public static final String PASSWORD = "//input[@id='password']";
        }
        """
        
        with patch.object(self.orchestrator, '_convert_locators_with_ai') as mock_ai:
            mock_ai.return_value = "*** Variables ***\n${USERNAME}    xpath=//input[@id='username']"
            
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/locators/LoginLocators.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Verify AI method was called
            mock_ai.assert_called_once()
            
            # Verify correct detection logging
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('Locator File' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_ai_transformation_fallback_to_pattern_based(self, mock_logger):
        """Test fallback to pattern-based transformation when AI returns None."""
        java_content = """
        package com.test;
        
        public class TestClass {
            public void method() {}
        }
        """
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = None  # Simulate AI failure
            
            # This should fall back to pattern-based transformation
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/TestClass.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Verify AI was attempted
            mock_ai.assert_called_once()
            
            # Verify fallback happened
            assert "*** Keywords ***" in result or "*** Settings ***" in result
            
            # Verify warning about fallback
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any('AI transformation returned None' in str(call) for call in warning_calls)
            assert any('Falling back to pattern-based' in str(call) for call in warning_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_no_ai_when_disabled(self, mock_logger):
        """Test that AI is not used when disabled in request."""
        java_content = """
        package com.test;
        
        public class TestClass {
            public void method() {}
        }
        """
        
        # Create request with AI disabled
        request_no_ai = MigrationRequest(
            repo_url="https://github.com/test/repo",
            branch="main",
            target_branch="robot-migration",
            use_ai=False
        )
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/TestClass.java",
                with_review_markers=False,
                request=request_no_ai
            )
            
            # Verify AI was NOT called
            mock_ai.assert_not_called()
            
            # Should go directly to pattern-based transformation
            assert "*** Keywords ***" in result or "*** Settings ***" in result
    
    @patch('core.orchestration.orchestrator.logger')
    def test_no_ai_when_no_config(self, mock_logger):
        """Test that AI is not used when ai_config is None."""
        java_content = """
        package com.test;
        
        public class TestClass {
            public void method() {}
        }
        """
        
        # Create request with use_ai=True but no ai_config
        request_no_config = MigrationRequest(
            repo_url="https://github.com/test/repo",
            branch="main",
            target_branch="robot-migration",
            use_ai=True,
            ai_config=None
        )
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/TestClass.java",
                with_review_markers=False,
                request=request_no_config
            )
            
            # Verify AI was NOT called (no config provided)
            mock_ai.assert_not_called()
    
    @patch('core.orchestration.orchestrator.logger')
    def test_content_detection_takes_precedence_over_filename(self, mock_logger):
        """Test that content markers take precedence over filename patterns."""
        # File named like a page object but contains step definitions
        java_content = """
        package com.test;
        
        import io.cucumber.java.en.Given;
        
        public class LoginPage {
            @Given("user is on login page")
            public void userOnLoginPage() {
                // Step definition in a file named *Page.java
            }
        }
        """
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_step_ai, \
             patch.object(self.orchestrator, '_convert_page_object_with_ai') as mock_page_ai:
            
            mock_step_ai.return_value = "*** Keywords ***\nStep Keyword\n    Log    AI Generated"
            
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/LoginPage.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Should call step definition AI (content markers), not page object AI (filename)
            mock_step_ai.assert_called_once()
            mock_page_ai.assert_not_called()
            
            # Verify detection logged correctly (content detection, not filename)
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('Step Definition' in str(call) and '@Given/@When/@Then' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_review_markers_passed_to_ai(self, mock_logger):
        """Test that review markers flag is correctly passed to AI methods."""
        java_content = """
        package com.test;
        
        import io.cucumber.java.en.Given;
        
        public class Steps {
            @Given("step")
            public void step() {}
        }
        """
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***\nStep\n    Log    AI Generated"
            
            # Call with review markers enabled
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/Steps.java",
                with_review_markers=True,  # Hybrid mode
                request=self.request
            )
            
            # Verify review markers flag was passed to AI method
            mock_ai.assert_called_once()
            assert mock_ai.call_args[1]['with_review_markers'] == True
    
    @patch('core.orchestration.orchestrator.logger')
    def test_multiple_content_markers_step_definition_wins(self, mock_logger):
        """Test that Cucumber annotations take precedence when multiple markers present."""
        # File with both @Given and @FindBy - step definition should win
        java_content = """
        package com.test;
        
        import io.cucumber.java.en.Given;
        import org.openqa.selenium.WebElement;
        import org.openqa.selenium.support.FindBy;
        
        public class HybridClass {
            @FindBy(id = "test")
            private WebElement element;
            
            @Given("step")
            public void step() {
                element.click();
            }
        }
        """
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_step_ai, \
             patch.object(self.orchestrator, '_convert_page_object_with_ai') as mock_page_ai:
            
            mock_step_ai.return_value = "*** Keywords ***\nStep\n    Log    AI Generated"
            
            result = self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="com/test/HybridClass.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Should detect as step definition (first in priority order)
            mock_step_ai.assert_called_once()
            mock_page_ai.assert_not_called()


class TestAITransformationLogging:
    """Test suite for AI transformation logging and visibility."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MigrationOrchestrator()
        
        self.ai_config = AIConfig(
            provider="openai",
            api_key="test-key",
            model="gpt-4"
        )
        
        self.request = MigrationRequest(
            repo_url="https://github.com/test/repo",
            branch="main",
            target_branch="robot-migration",
            use_ai=True,
            ai_config=self.ai_config
        )
    
    @patch('core.orchestration.orchestrator.logger')
    def test_logging_ai_enabled(self, mock_logger):
        """Test that AI enabled is logged at file level."""
        java_content = "public class Test {}"
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***\nTest\n    Log    AI"
            
            self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="Test.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Check for AI enabled log
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('AI-Powered transformation enabled' in str(call) for call in info_calls)
            assert any('Test.java' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_logging_detection_type(self, mock_logger):
        """Test that detected file type is logged."""
        java_content = "@Given('step') public void step() {}"
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***"
            
            self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="Steps.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Check for detection type log
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('Detected:' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_logging_ai_attempt(self, mock_logger):
        """Test that AI transformation attempt is logged."""
        java_content = "public class Test {}"
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***"
            
            self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="Test.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Check for AI attempt log
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('Attempting AI' in str(call) and 'transformation' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_logging_ai_success(self, mock_logger):
        """Test that AI success is logged."""
        java_content = "public class Test {}"
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = "*** Keywords ***"
            
            self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="Test.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Check for success log
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any('AI transformation successful' in str(call) and 'Test.java' in str(call) for call in info_calls)
    
    @patch('core.orchestration.orchestrator.logger')
    def test_logging_ai_fallback(self, mock_logger):
        """Test that AI fallback is logged when AI returns None."""
        java_content = "public class Test {}"
        
        with patch.object(self.orchestrator, '_transform_step_definitions_with_ai') as mock_ai:
            mock_ai.return_value = None
            
            self.orchestrator._transform_java_to_robot_keywords(
                content=java_content,
                source_path="Test.java",
                with_review_markers=False,
                request=self.request
            )
            
            # Check for fallback warning
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any('AI transformation returned None' in str(call) for call in warning_calls)
            assert any('Falling back to pattern-based' in str(call) for call in warning_calls)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
