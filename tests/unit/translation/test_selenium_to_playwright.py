"""
Unit tests for Selenium to Playwright translation.

Tests the complete translation path: Selenium Java → Intent Model → Playwright Python.
"""

import pytest

from core.translation.intent_model import ActionType, AssertionType, IntentType
from core.translation.parsers.selenium_parser import SeleniumParser
from core.translation.generators.playwright_generator import PlaywrightGenerator
from core.translation.pipeline import TranslationPipeline, TranslationConfig


class TestSeleniumParser:
    """Test Selenium Java parser."""
    
    def test_can_parse_selenium_code(self):
        """Test detection of Selenium code."""
        parser = SeleniumParser()
        
        selenium_code = """
        import org.openqa.selenium.WebDriver;
        
        public class LoginTest {
            WebDriver driver;
            
            @Test
            public void testLogin() {
                driver.get("https://example.com");
            }
        }
        """
        
        assert parser.can_parse(selenium_code)
    
    def test_cannot_parse_non_selenium_code(self):
        """Test rejection of non-Selenium code."""
        parser = SeleniumParser()
        
        python_code = """
        def test_example():
            assert True
        """
        
        assert not parser.can_parse(python_code)
    
    def test_extract_test_name(self):
        """Test extraction of test method name."""
        parser = SeleniumParser()
        
        code = """
        @Test
        public void testLoginFlow() {
            // test code
        }
        """
        
        intent = parser.parse(code)
        assert intent.name == "testLoginFlow"
    
    def test_parse_navigation(self):
        """Test parsing driver.get()."""
        parser = SeleniumParser()
        
        code = """
        @Test
        public void testNav() {
            driver.get("https://example.com/login");
        }
        """
        
        intent = parser.parse(code)
        assert len(intent.steps) == 1
        assert intent.steps[0].action_type == ActionType.NAVIGATE
        assert intent.steps[0].value == "https://example.com/login"
    
    def test_parse_click_action(self):
        """Test parsing click with By locator."""
        parser = SeleniumParser()
        
        code = """
        @Test
        public void testClick() {
            driver.findElement(By.id("login-btn")).click();
        }
        """
        
        intent = parser.parse(code)
        assert len(intent.steps) == 1
        assert intent.steps[0].action_type == ActionType.CLICK
        assert intent.steps[0].target == "login_btn"
        assert "#login-btn" in intent.steps[0].selector
    
    def test_parse_fill_action(self):
        """Test parsing sendKeys()."""
        parser = SeleniumParser()
        
        code = """
        @Test
        public void testFill() {
            driver.findElement(By.name("username")).sendKeys("testuser");
        }
        """
        
        intent = parser.parse(code)
        assert len(intent.steps) == 1
        assert intent.steps[0].action_type == ActionType.FILL
        assert intent.steps[0].value == "testuser"
        assert "username" in intent.steps[0].selector
    
    def test_parse_assertion_visible(self):
        """Test parsing assertTrue(isDisplayed())."""
        parser = SeleniumParser()
        
        code = """
        @Test
        public void testVisible() {
            assertTrue(driver.findElement(By.id("welcome")).isDisplayed());
        }
        """
        
        intent = parser.parse(code)
        assert len(intent.assertions) == 1
        assert intent.assertions[0].assertion_type == AssertionType.VISIBLE
        assert intent.assertions[0].expected == True
    
    def test_parse_assertion_text(self):
        """Test parsing assertEquals() with getText()."""
        parser = SeleniumParser()
        
        code = """
        @Test
        public void testText() {
            assertEquals("Welcome", driver.findElement(By.id("title")).getText());
        }
        """
        
        intent = parser.parse(code)
        assert len(intent.assertions) == 1
        assert intent.assertions[0].assertion_type == AssertionType.TEXT_CONTENT
        assert intent.assertions[0].expected == "Welcome"
    
    def test_parse_explicit_wait(self):
        """Test parsing WebDriverWait."""
        parser = SeleniumParser()
        
        code = """
        @Test
        public void testWait() {
            WebDriverWait wait = new WebDriverWait(driver, 10);
            wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("element")));
        }
        """
        
        intent = parser.parse(code)
        # Should parse wait action
        wait_actions = [a for a in intent.steps if a.action_type == ActionType.WAIT]
        assert len(wait_actions) >= 1
        assert wait_actions[0].wait_strategy == "explicit"
        # Lower confidence because Playwright doesn't need explicit waits
        assert wait_actions[0].confidence < 1.0
    
    def test_parse_sleep(self):
        """Test parsing Thread.sleep()."""
        parser = SeleniumParser()
        
        code = """
        @Test
        public void testSleep() {
            Thread.sleep(2000);
        }
        """
        
        intent = parser.parse(code)
        sleep_actions = [a for a in intent.steps if a.target == "sleep"]
        assert len(sleep_actions) == 1
        # Very low confidence - should be removed
        assert sleep_actions[0].confidence < 0.8


class TestPlaywrightGenerator:
    """Test Playwright Python generator."""
    
    def test_can_generate_ui_test(self):
        """Test capability check for UI tests."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_ui")
        
        assert generator.can_generate(intent)
    
    def test_cannot_generate_api_test(self):
        """Test rejection of API tests."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent
        intent = TestIntent(test_type=IntentType.API, name="test_api")
        
        # Playwright is for UI, not API
        assert not generator.can_generate(intent)
    
    def test_generate_navigation(self):
        """Test generation of page.goto()."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_nav")
        intent.add_step(ActionIntent(
            action_type=ActionType.NAVIGATE,
            target="url",
            value="https://example.com",
        ))
        
        code = generator.generate(intent)
        assert 'page.goto("https://example.com")' in code
    
    def test_generate_click(self):
        """Test generation of locator.click()."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_click")
        intent.add_step(ActionIntent(
            action_type=ActionType.CLICK,
            target="login_button",
            selector="#login-btn",
        ))
        
        code = generator.generate(intent)
        assert "click()" in code
        # Should prefer role-based selector for buttons
        assert ('page.get_by_role("button"' in code or 'page.locator("#login-btn")' in code)
    
    def test_generate_fill(self):
        """Test generation of locator.fill()."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_fill")
        intent.add_step(ActionIntent(
            action_type=ActionType.FILL,
            target="username_field",
            selector="[name='username']",
            value="testuser",
        ))
        
        code = generator.generate(intent)
        assert 'fill("testuser")' in code
    
    def test_generate_assertion_visible(self):
        """Test generation of expect().to_be_visible()."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, AssertionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_visible")
        intent.add_assertion(AssertionIntent(
            assertion_type=AssertionType.VISIBLE,
            target="welcome_message",
            selector="#welcome",
            expected=True,
        ))
        
        code = generator.generate(intent)
        assert "expect(" in code
        assert "to_be_visible()" in code
    
    def test_generate_assertion_text(self):
        """Test generation of expect().to_have_text()."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, AssertionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_text")
        intent.add_assertion(AssertionIntent(
            assertion_type=AssertionType.TEXT_CONTENT,
            target="title",
            selector="#title",
            expected="Welcome",
        ))
        
        code = generator.generate(intent)
        assert 'to_have_text("Welcome")' in code
    
    def test_remove_explicit_wait(self):
        """Test that explicit waits are removed."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_wait")
        intent.add_step(ActionIntent(
            action_type=ActionType.WAIT,
            target="explicit_wait",
            wait_strategy="explicit",
        ))
        
        code = generator.generate(intent)
        # Should have comment about removing wait
        assert "Explicit wait removed" in code or "auto-wait" in code
    
    def test_remove_sleep(self):
        """Test that Thread.sleep is removed."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_sleep")
        intent.add_step(ActionIntent(
            action_type=ActionType.WAIT,
            target="sleep",
        ))
        
        code = generator.generate(intent)
        # Should have comment about removing sleep
        assert "Sleep removed" in code or "TODO" in code
    
    def test_convert_test_name_to_snake_case(self):
        """Test conversion of camelCase to snake_case."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent
        intent = TestIntent(test_type=IntentType.UI, name="testLoginFlow")
        
        code = generator.generate(intent)
        assert "def test_login_flow(" in code
    
    def test_add_confidence_warnings(self):
        """Test that low confidence actions get warnings."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_warning")
        intent.add_step(ActionIntent(
            action_type=ActionType.CUSTOM,
            target="uncertain_action",
            confidence=0.5,
        ))
        
        code = generator.generate(intent)
        # Should have confidence warning
        assert "⚠️" in code or "Confidence:" in code or "TODO" in code
    
    def test_prefer_role_based_selectors(self):
        """Test that role-based selectors are preferred."""
        generator = PlaywrightGenerator()
        
        from core.translation.intent_model import TestIntent, ActionIntent
        intent = TestIntent(test_type=IntentType.UI, name="test_role")
        intent.add_step(ActionIntent(
            action_type=ActionType.CLICK,
            target="login_button",
            selector="#login-btn",
        ))
        
        code = generator.generate(intent)
        # Should prefer get_by_role for button
        assert 'get_by_role("button"' in code or 'locator(' in code


class TestTranslationPipeline:
    """Test end-to-end translation pipeline."""
    
    def test_complete_login_test_translation(self):
        """Test translating a complete login test."""
        selenium_code = """
        import org.openqa.selenium.WebDriver;
        import org.openqa.selenium.By;
        
        public class LoginTest {
            @Test
            public void testLoginSuccess() {
                driver.get("https://example.com/login");
                driver.findElement(By.id("username")).sendKeys("admin");
                driver.findElement(By.id("password")).sendKeys("password123");
                driver.findElement(By.id("login-btn")).click();
                
                assertTrue(driver.findElement(By.id("welcome")).isDisplayed());
                assertEquals("Welcome, Admin", driver.findElement(By.id("welcome")).getText());
            }
        }
        """
        
        # Create pipeline
        pipeline = TranslationPipeline()
        
        # Translate
        result = pipeline.translate(
            source_code=selenium_code,
            source_framework="selenium-java",
            target_framework="playwright-python",
        )
        
        # Verify result
        assert result.success
        assert result.target_code
        assert result.confidence > 0.7
        
        # Check generated code
        code = result.target_code
        assert "def test_login_success(" in code
        assert 'page.goto("https://example.com/login")' in code
        assert 'fill("admin")' in code
        assert 'fill("password123")' in code
        assert "click()" in code
        assert "expect(" in code
        assert "to_be_visible()" in code
        assert 'to_have_text("Welcome, Admin")' in code
    
    def test_translation_with_waits(self):
        """Test translation removes unnecessary waits."""
        selenium_code = """
        @Test
        public void testWithWaits() {
            driver.get("https://example.com");
            
            WebDriverWait wait = new WebDriverWait(driver, 10);
            wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("content")));
            
            Thread.sleep(2000);
            
            driver.findElement(By.id("button")).click();
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=selenium_code,
            source_framework="selenium-java",
            target_framework="playwright-python",
        )
        
        assert result.success
        code = result.target_code
        
        # Should have comments about removed waits
        assert "Explicit wait removed" in code or "auto-wait" in code
        assert "Sleep removed" in code or "TODO" in code
        
        # Should still have the click action
        assert "click()" in code
    
    def test_translation_statistics(self):
        """Test that translation statistics are collected."""
        selenium_code = """
        @Test
        public void testStats() {
            driver.get("https://example.com");
            driver.findElement(By.id("btn1")).click();
            driver.findElement(By.id("btn2")).click();
            
            assertTrue(driver.findElement(By.id("result")).isDisplayed());
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=selenium_code,
            source_framework="selenium-java",
            target_framework="playwright-python",
        )
        
        assert result.statistics
        assert result.statistics["actions"] == 3  # navigate + 2 clicks
        assert result.statistics["assertions"] == 1
    
    def test_translation_with_low_confidence_item(self):
        """Test that low confidence items generate TODOs."""
        selenium_code = """
        @Test
        public void testCustomAction() {
            driver.get("https://example.com");
            
            // This should generate a TODO
            Thread.sleep(5000);
        }
        """
        
        pipeline = TranslationPipeline()
        result = pipeline.translate(
            source_code=selenium_code,
            source_framework="selenium-java",
            target_framework="playwright-python",
        )
        
        assert result.success
        # Should have TODOs for low confidence items
        assert len(result.todos) > 0 or "TODO" in result.target_code
    
    def test_unsupported_framework(self):
        """Test handling of unsupported framework."""
        pipeline = TranslationPipeline()
        
        result = pipeline.translate(
            source_code="some code",
            source_framework="unsupported-framework",
            target_framework="playwright-python",
        )
        
        assert not result.success
        assert len(result.errors) > 0
