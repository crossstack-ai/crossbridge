"""
Unit Tests for Phase 2: Page Object & Locator Awareness

Tests cover:
- Page Object detection (AST-based, multi-heuristic)
- Locator extraction (@FindBy, By fields)
- Playwright/Robot code generation
- Usage mapping (Test → PageObject → Locator)
- Locator inventory and reporting
- Preservation guarantees
"""

import pytest
from core.locator_awareness.models import (
    Locator, 
    PageObject, 
    LocatorUsage, 
    LocatorInventory,
    LocatorStrategy
)
from core.locator_awareness.detectors import PageObjectDetector, LocatorExtractor
from core.locator_awareness.generators import (
    PlaywrightPageObjectGenerator,
    RobotFrameworkPageObjectGenerator
)
from core.locator_awareness.mappers import UsageMapper


class TestLocatorModel:
    """Test the core Locator model"""
    
    @pytest.fixture
    def sample_locator(self):
        return Locator(
            name="loginButton",
            strategy=LocatorStrategy.XPATH,
            value="//div[@class='btn']",
            source_file="pages/LoginPage.java",
            page_object="LoginPage"
        )
    
    def test_locator_creation(self, sample_locator):
        """Test Locator model creation"""
        assert sample_locator.name == "loginButton"
        assert sample_locator.strategy == LocatorStrategy.XPATH
        assert sample_locator.value == "//div[@class='btn']"
        assert sample_locator.page_object == "LoginPage"
        assert sample_locator.preserved is True  # Always preserved in Phase 2
    
    def test_to_playwright_locator_xpath(self, sample_locator):
        """Test XPath conversion to Playwright"""
        result = sample_locator.to_playwright_locator()
        assert result == 'page.locator("//div[@class=\'btn\']")'
        # CRITICAL: Value preserved exactly
        assert "//div[@class='btn']" in result
    
    def test_to_playwright_locator_id(self):
        """Test ID locator conversion to Playwright"""
        locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="username-input",
            source_file="test.java",
            page_object="LoginPage"
        )
        result = locator.to_playwright_locator()
        assert result == 'page.locator("#username-input")'
        # Value preserved, only wrapped in Playwright API
        assert "username-input" in result
    
    def test_to_playwright_locator_css(self):
        """Test CSS selector conversion to Playwright"""
        locator = Locator(
            name="submitBtn",
            strategy=LocatorStrategy.CSS_SELECTOR,
            value=".btn-primary",
            source_file="test.java",
            page_object="LoginPage"
        )
        result = locator.to_playwright_locator()
        assert result == 'page.locator(".btn-primary")'
        assert ".btn-primary" in result
    
    def test_to_playwright_locator_name(self):
        """Test NAME locator conversion to Playwright"""
        locator = Locator(
            name="emailField",
            strategy=LocatorStrategy.NAME,
            value="email",
            source_file="test.java",
            page_object="LoginPage"
        )
        result = locator.to_playwright_locator()
        assert 'page.locator("[name=\\"email\\"]")' in result
    
    def test_to_robot_locator_xpath(self, sample_locator):
        """Test XPath conversion to Robot Framework"""
        result = sample_locator.to_robot_locator()
        assert result == "xpath=//div[@class='btn']"
        # Value preserved exactly
        assert "//div[@class='btn']" in result
    
    def test_to_robot_locator_id(self):
        """Test ID conversion to Robot Framework"""
        locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="username-input",
            source_file="test.java",
            page_object="LoginPage"
        )
        result = locator.to_robot_locator()
        assert result == "id=username-input"
    
    def test_to_robot_locator_css(self):
        """Test CSS conversion to Robot Framework"""
        locator = Locator(
            name="btn",
            strategy=LocatorStrategy.CSS_SELECTOR,
            value=".btn-primary",
            source_file="test.java",
            page_object="LoginPage"
        )
        result = locator.to_robot_locator()
        assert result == "css=.btn-primary"
    
    def test_locator_usage_tracking(self, sample_locator):
        """Test that locator tracks usage"""
        sample_locator.used_in_tests.append("LoginTest.testValidLogin")
        sample_locator.used_by_methods.append("clickLogin")
        sample_locator.usage_count = 5
        
        assert len(sample_locator.used_in_tests) == 1
        assert "LoginTest.testValidLogin" in sample_locator.used_in_tests
        assert "clickLogin" in sample_locator.used_by_methods
        assert sample_locator.usage_count == 5


class TestPageObjectModel:
    """Test PageObject model"""
    
    @pytest.fixture
    def sample_page_object(self):
        return PageObject(
            name="LoginPage",
            file_path="src/main/java/pages/LoginPage.java",
            package="com.example.pages",
            detection_reasons=["class_name_page_suffix", "findby_annotation"]
        )
    
    def test_page_object_creation(self, sample_page_object):
        """Test PageObject creation"""
        assert sample_page_object.name == "LoginPage"
        assert sample_page_object.file_path == "src/main/java/pages/LoginPage.java"
        assert "findby_annotation" in sample_page_object.detection_reasons
    
    def test_add_locator(self, sample_page_object):
        """Test adding locator to Page Object"""
        locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="user",
            source_file=sample_page_object.file_path,
            page_object=""
        )
        
        sample_page_object.add_locator(locator)
        
        assert len(sample_page_object.locators) == 1
        assert locator.page_object == "LoginPage"  # Updated by add_locator
    
    def test_get_locator(self, sample_page_object):
        """Test retrieving locator by name"""
        locator1 = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="user",
            source_file="test.java",
            page_object="LoginPage"
        )
        locator2 = Locator(
            name="password",
            strategy=LocatorStrategy.ID,
            value="pass",
            source_file="test.java",
            page_object="LoginPage"
        )
        
        sample_page_object.add_locator(locator1)
        sample_page_object.add_locator(locator2)
        
        found = sample_page_object.get_locator("username")
        assert found is not None
        assert found.name == "username"
        assert found.value == "user"
    
    def test_add_method(self, sample_page_object):
        """Test adding method to Page Object"""
        sample_page_object.add_method("clickLogin", {
            "line_number": 25,
            "signature": "public void clickLogin()"
        })
        
        assert len(sample_page_object.methods) == 1
        assert sample_page_object.methods[0]["name"] == "clickLogin"


class TestPageObjectDetector:
    """Test Page Object detection logic"""
    
    @pytest.fixture
    def detector(self):
        return PageObjectDetector()
    
    def test_detect_by_filename_pattern(self, detector):
        """Test detection by filename (LoginPage.java)"""
        file_path = "src/pages/LoginPage.java"
        content = "public class LoginPage {}"
        
        is_po, reasons = detector.is_page_object(file_path, content)
        
        assert is_po is True
        assert "filename_pattern" in reasons
    
    def test_detect_by_package_pattern(self, detector):
        """Test detection by package path (/pages/)"""
        file_path = "src/main/java/pages/Login.java"
        content = "public class Login {}"
        
        is_po, reasons = detector.is_page_object(file_path, content)
        
        assert is_po is True
        assert "package_pattern" in reasons
    
    def test_detect_by_findby_annotation(self, detector):
        """Test detection by @FindBy annotation"""
        file_path = "src/Login.java"
        content = """
        public class Login {
            @FindBy(id = "username")
            WebElement usernameField;
        }
        """
        
        is_po, reasons = detector.is_page_object(file_path, content)
        
        assert is_po is True
        assert "findby_annotation" in reasons
    
    def test_detect_by_webelement_fields(self, detector):
        """Test detection by WebElement fields"""
        file_path = "src/Login.java"
        content = """
        public class Login {
            private WebElement loginButton;
        }
        """
        
        is_po, reasons = detector.is_page_object(file_path, content)
        
        assert is_po is True
        assert "webelement_fields" in reasons
    
    def test_detect_by_by_fields(self, detector):
        """Test detection by By fields"""
        file_path = "src/Login.java"
        content = """
        public class Login {
            By loginBtn = By.xpath("//button");
        }
        """
        
        is_po, reasons = detector.is_page_object(file_path, content)
        
        assert is_po is True
        assert "by_fields" in reasons
    
    def test_detect_by_extends_basepage(self, detector):
        """Test detection by inheritance"""
        file_path = "src/Login.java"
        content = """
        public class Login extends BasePage {
        }
        """
        
        is_po, reasons = detector.is_page_object(file_path, content)
        
        assert is_po is True
        assert "extends_base_page" in reasons
    
    def test_not_a_page_object(self, detector):
        """Test that non-Page Object files are not detected"""
        file_path = "src/utils/Helper.java"
        content = "public class Helper {}"
        
        is_po, reasons = detector.is_page_object(file_path, content)
        
        assert is_po is False
        assert len(reasons) == 0
    
    def test_multiple_detection_reasons(self, detector):
        """Test Page Object with multiple indicators"""
        file_path = "src/pages/LoginPage.java"
        content = """
        public class LoginPage extends BasePage {
            @FindBy(id = "username")
            WebElement usernameField;
        }
        """
        
        is_po, reasons = detector.is_page_object(file_path, content)
        
        assert is_po is True
        # Should have multiple reasons
        assert len(reasons) >= 3
        assert "filename_pattern" in reasons
        assert "package_pattern" in reasons
        assert "findby_annotation" in reasons
    
    def test_extract_class_name(self, detector):
        """Test class name extraction"""
        content = "public class LoginPage extends BasePage {}"
        class_name = detector.extract_class_name(content, "LoginPage.java")
        
        assert class_name == "LoginPage"
    
    def test_extract_package(self, detector):
        """Test package extraction"""
        content = "package com.example.pages;\npublic class LoginPage {}"
        package = detector.extract_package(content)
        
        assert package == "com.example.pages"
    
    def test_detect_page_object_full(self, detector):
        """Test complete Page Object detection"""
        file_path = "src/pages/LoginPage.java"
        content = """
        package com.example.pages;
        
        public class LoginPage extends BasePage {
            @FindBy(id = "username")
            WebElement usernameField;
        }
        """
        
        page_object = detector.detect_page_object(file_path, content)
        
        assert page_object is not None
        assert page_object.name == "LoginPage"
        assert page_object.package == "com.example.pages"
        assert page_object.extends == "BasePage"
        assert page_object.detection_confidence > 0.5


class TestLocatorExtractor:
    """Test locator extraction"""
    
    @pytest.fixture
    def extractor(self):
        return LocatorExtractor()
    
    def test_extract_findby_id(self, extractor):
        """Test @FindBy with ID strategy"""
        content = """
        @FindBy(id = "username")
        WebElement usernameField;
        """
        
        locators = extractor.extract_locators(content, "LoginPage.java", "LoginPage")
        
        assert len(locators) == 1
        assert locators[0].name == "usernameField"
        assert locators[0].strategy == LocatorStrategy.ID
        assert locators[0].value == "username"
        assert locators[0].field_type == "WebElement"
    
    def test_extract_findby_xpath(self, extractor):
        """Test @FindBy with XPath strategy"""
        content = """
        @FindBy(xpath = "//button[@class='login']")
        WebElement loginButton;
        """
        
        locators = extractor.extract_locators(content, "LoginPage.java", "LoginPage")
        
        assert len(locators) == 1
        assert locators[0].name == "loginButton"
        assert locators[0].strategy == LocatorStrategy.XPATH
        assert locators[0].value == "//button[@class='login']"
    
    def test_extract_findby_css(self, extractor):
        """Test @FindBy with CSS selector"""
        content = """
        @FindBy(cssSelector = ".btn-primary")
        WebElement submitButton;
        """
        
        locators = extractor.extract_locators(content, "LoginPage.java", "LoginPage")
        
        assert len(locators) == 1
        assert locators[0].strategy == LocatorStrategy.CSS_SELECTOR
        assert locators[0].value == ".btn-primary"
    
    def test_extract_by_xpath(self, extractor):
        """Test By field with XPath"""
        content = """
        By loginButton = By.xpath("//div[@id='login']");
        """
        
        locators = extractor.extract_locators(content, "LoginPage.java", "LoginPage")
        
        assert len(locators) == 1
        assert locators[0].name == "loginButton"
        assert locators[0].strategy == LocatorStrategy.XPATH
        assert locators[0].value == "//div[@id='login']"
        assert locators[0].field_type == "By"
    
    def test_extract_by_id(self, extractor):
        """Test By field with ID"""
        content = """
        private By usernameField = By.id("username");
        """
        
        locators = extractor.extract_locators(content, "LoginPage.java", "LoginPage")
        
        assert len(locators) == 1
        assert locators[0].strategy == LocatorStrategy.ID
        assert locators[0].value == "username"
    
    def test_extract_multiple_locators(self, extractor):
        """Test extracting multiple locators from same file"""
        content = """
        public class LoginPage {
            @FindBy(id = "username")
            WebElement usernameField;
            
            @FindBy(id = "password")
            WebElement passwordField;
            
            By loginButton = By.xpath("//button");
        }
        """
        
        locators = extractor.extract_locators(content, "LoginPage.java", "LoginPage")
        
        assert len(locators) == 3
        assert locators[0].name == "usernameField"
        assert locators[1].name == "passwordField"
        assert locators[2].name == "loginButton"
    
    def test_extract_methods(self, extractor):
        """Test method extraction"""
        content = """
        public void clickLogin() {
            loginButton.click();
        }
        
        public void enterUsername(String username) {
            usernameField.sendKeys(username);
        }
        """
        
        methods = extractor.extract_methods(content)
        
        assert len(methods) >= 2
        method_names = [m['name'] for m in methods]
        assert "clickLogin" in method_names
        assert "enterUsername" in method_names


class TestPlaywrightPageObjectGenerator:
    """Test Playwright Page Object code generation"""
    
    @pytest.fixture
    def generator(self):
        return PlaywrightPageObjectGenerator(target_language="python")
    
    @pytest.fixture
    def sample_page_object(self):
        po = PageObject(
            name="LoginPage",
            file_path="pages/LoginPage.java",
            package="com.example.pages",
            detection_reasons=["findby_annotation"]
        )
        
        locator1 = Locator(
            name="usernameField",
            strategy=LocatorStrategy.ID,
            value="username",
            source_file="pages/LoginPage.java",
            page_object="LoginPage"
        )
        
        locator2 = Locator(
            name="loginButton",
            strategy=LocatorStrategy.XPATH,
            value="//button[@type='submit']",
            source_file="pages/LoginPage.java",
            page_object="LoginPage"
        )
        
        po.add_locator(locator1)
        po.add_locator(locator2)
        
        po.add_method("clickLogin", {
            "line_number": 20,
            "signature": "public void clickLogin()"
        })
        
        return po
    
    def test_generate_python_code(self, generator, sample_page_object):
        """Test Playwright Python code generation"""
        code = generator.generate(sample_page_object)
        
        # Verify structure
        assert "class LoginPage:" in code
        assert "def __init__(self, page: Page):" in code
        assert "from playwright.sync_api import Page, Locator" in code
        
        # Verify locators preserved
        assert "username" in code
        assert "//button[@type='submit']" in code
        
        # Verify Playwright API used
        assert "page.locator" in code
    
    def test_preserves_locator_values(self, generator, sample_page_object):
        """Test that locator values are preserved exactly"""
        code = generator.generate(sample_page_object)
        
        # CRITICAL: Original values must be in generated code
        assert "username" in code
        assert "//button[@type='submit']" in code
        
        # Should NOT have modified values
        assert "getByRole" not in code or "# id:" in code  # No auto-improvement
    
    def test_includes_documentation(self, generator, sample_page_object):
        """Test that generated code includes documentation"""
        code = generator.generate(sample_page_object)
        
        assert "Migrated by CrossStack Phase 2" in code
        assert "Semantic Preservation" in code
        assert "All locators preserved exactly as-is" in code
        assert sample_page_object.file_path in code
    
    def test_pythonize_names(self, generator):
        """Test camelCase to snake_case conversion"""
        assert generator._pythonize_name("loginButton") == "login_button"
        assert generator._pythonize_name("usernameField") == "username_field"
        assert generator._pythonize_name("clickSubmit") == "click_submit"


class TestRobotFrameworkPageObjectGenerator:
    """Test Robot Framework resource generation"""
    
    @pytest.fixture
    def generator(self):
        return RobotFrameworkPageObjectGenerator()
    
    @pytest.fixture
    def sample_page_object(self):
        po = PageObject(
            name="LoginPage",
            file_path="pages/LoginPage.java",
            package="com.example.pages"
        )
        
        locator1 = Locator(
            name="usernameField",
            strategy=LocatorStrategy.ID,
            value="username",
            source_file="pages/LoginPage.java",
            page_object="LoginPage"
        )
        
        po.add_locator(locator1)
        
        po.add_method("enterUsername", {
            "line_number": 15,
            "signature": "public void enterUsername(String username)"
        })
        
        return po
    
    def test_generate_robot_code(self, generator, sample_page_object):
        """Test Robot Framework resource generation"""
        code = generator.generate(sample_page_object)
        
        assert "*** Settings ***" in code
        assert "*** Variables ***" in code
        assert "*** Keywords ***" in code
        assert "Library          Browser" in code
    
    def test_preserves_locators_in_variables(self, generator, sample_page_object):
        """Test that locators are in Variables section"""
        code = generator.generate(sample_page_object)
        
        assert "${USERNAMEFIELD}" in code
        assert "id=username" in code
    
    def test_includes_keywords(self, generator, sample_page_object):
        """Test that methods become keywords"""
        code = generator.generate(sample_page_object)
        
        assert "Enter Username" in code  # Converted from enterUsername


class TestUsageMapper:
    """Test usage mapping (Test → PageObject → Locator)"""
    
    @pytest.fixture
    def mapper(self):
        return UsageMapper()
    
    @pytest.fixture
    def sample_page_object(self):
        po = PageObject(
            name="LoginPage",
            file_path="pages/LoginPage.java",
            package="com.example.pages"
        )
        
        locator = Locator(
            name="loginButton",
            strategy=LocatorStrategy.XPATH,
            value="//button",
            source_file="pages/LoginPage.java",
            page_object="LoginPage"
        )
        
        po.add_locator(locator)
        po.add_method("clickLogin", {
            "line_number": 20,
            "signature": "public void clickLogin()"
        })
        
        return po
    
    def test_add_page_object(self, mapper, sample_page_object):
        """Test adding Page Object to mapper"""
        mapper.add_page_object(sample_page_object)
        
        assert "LoginPage" in mapper.page_objects
        assert len(mapper.inventory.page_objects) == 1
        assert len(mapper.inventory.locators) == 1
    
    def test_map_test_usage(self, mapper, sample_page_object):
        """Test mapping test usage"""
        mapper.add_page_object(sample_page_object)
        
        test_content = """
        public class LoginTest {
            public void testValidLogin() {
                LoginPage loginPage = new LoginPage();
                loginPage.clickLogin();
            }
        }
        """
        
        mapper.map_test_usage(
            test_name="LoginTest.testValidLogin",
            test_file="tests/LoginTest.java",
            test_content=test_content
        )
        
        # Verify Page Object is marked as used
        assert "LoginTest.testValidLogin" in sample_page_object.used_by_tests
    
    def test_camel_to_snake_conversion(self, mapper):
        """Test camelCase to snake_case conversion"""
        assert mapper._camel_to_snake("LoginPage") == "login_page"
        assert mapper._camel_to_snake("clickLoginButton") == "click_login_button"


class TestLocatorInventory:
    """Test Locator Inventory reporting"""
    
    @pytest.fixture
    def inventory(self):
        return LocatorInventory()
    
    def test_add_page_object(self, inventory):
        """Test adding Page Object to inventory"""
        po = PageObject(
            name="LoginPage",
            file_path="pages/LoginPage.java",
            package="com.example.pages"
        )
        
        inventory.add_page_object(po)
        
        assert inventory.total_page_objects == 1
        assert len(inventory.page_objects) == 1
    
    def test_add_locator(self, inventory):
        """Test adding locator to inventory"""
        locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="user",
            source_file="test.java",
            page_object="LoginPage"
        )
        
        inventory.add_locator(locator)
        
        assert inventory.total_locators == 1
        assert len(inventory.locators) == 1
    
    def test_find_duplicate_locators(self, inventory):
        """Test duplicate locator detection"""
        locator1 = Locator(
            name="submitBtn",
            strategy=LocatorStrategy.XPATH,
            value="//button[@type='submit']",
            source_file="LoginPage.java",
            page_object="LoginPage"
        )
        
        locator2 = Locator(
            name="loginButton",
            strategy=LocatorStrategy.XPATH,
            value="//button[@type='submit']",  # Same value!
            source_file="HomePage.java",
            page_object="HomePage"
        )
        
        inventory.add_locator(locator1)
        inventory.add_locator(locator2)
        
        inventory.find_duplicate_locators()
        
        assert len(inventory.duplicate_locators) == 1
        assert inventory.duplicate_locators[0]['value'] == "//button[@type='submit']"
    
    def test_find_unused_locators(self, inventory):
        """Test unused locator detection"""
        used_locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="user",
            source_file="test.java",
            page_object="LoginPage",
            usage_count=5
        )
        
        unused_locator = Locator(
            name="oldField",
            strategy=LocatorStrategy.ID,
            value="old",
            source_file="test.java",
            page_object="LoginPage",
            usage_count=0
        )
        
        inventory.add_locator(used_locator)
        inventory.add_locator(unused_locator)
        
        inventory.find_unused_locators()
        
        assert len(inventory.unused_locators) == 1
        assert inventory.unused_locators[0].name == "oldField"
    
    def test_generate_report(self, inventory):
        """Test inventory report generation"""
        po = PageObject(name="LoginPage", file_path="test.java", package="com.example")
        locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="user",
            source_file="test.java",
            page_object="LoginPage"
        )
        
        po.add_locator(locator)
        inventory.add_page_object(po)
        inventory.add_locator(locator)
        
        report = inventory.generate_report()
        
        assert "Phase 2: Locator Inventory Report" in report
        assert "1 Page Objects detected" in report
        assert "1 Locators extracted" in report
        assert "All locators preserved exactly as-is" in report
    
    def test_to_json_export(self, inventory):
        """Test JSON export for external tools"""
        po = PageObject(name="LoginPage", file_path="test.java", package="com.example")
        locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="user",
            source_file="test.java",
            page_object="LoginPage"
        )
        
        po.add_locator(locator)
        inventory.add_page_object(po)
        inventory.add_locator(locator)
        
        json_data = inventory.to_json()
        
        assert json_data['statistics']['total_page_objects'] == 1
        assert json_data['statistics']['total_locators'] == 1
        assert len(json_data['page_objects']) == 1
        assert json_data['page_objects'][0]['name'] == "LoginPage"


class TestEndToEndPhase2:
    """End-to-end Phase 2 workflow tests"""
    
    def test_complete_page_object_detection_and_generation(self):
        """Test complete flow: Detection → Extraction → Generation"""
        # Step 1: Detect Page Object
        detector = PageObjectDetector()
        content = """
        package com.example.pages;
        
        public class LoginPage extends BasePage {
            @FindBy(id = "username")
            WebElement usernameField;
            
            @FindBy(xpath = "//button[@type='submit']")
            WebElement submitButton;
            
            public void clickSubmit() {
                submitButton.click();
            }
        }
        """
        
        page_object = detector.detect_page_object("pages/LoginPage.java", content)
        assert page_object is not None
        
        # Step 2: Extract locators
        extractor = LocatorExtractor()
        locators = extractor.extract_locators(content, "pages/LoginPage.java", "LoginPage")
        
        for locator in locators:
            page_object.add_locator(locator)
        
        # Extract methods
        methods = extractor.extract_methods(content)
        for method in methods:
            page_object.add_method(method['name'], method)
        
        assert len(page_object.locators) == 2
        assert len(page_object.methods) >= 1
        
        # Step 3: Generate Playwright code
        generator = PlaywrightPageObjectGenerator()
        playwright_code = generator.generate(page_object)
        
        # Verify preservation
        assert "username" in playwright_code
        assert "//button[@type='submit']" in playwright_code
        assert "Semantic Preservation" in playwright_code
    
    def test_locator_preservation_guarantee(self):
        """Test that Phase 2 preserves locators exactly"""
        # Create locator with complex XPath
        complex_xpath = "//div[@class='container']//button[contains(@id,'submit')][1]"
        
        locator = Locator(
            name="complexButton",
            strategy=LocatorStrategy.XPATH,
            value=complex_xpath,
            source_file="test.java",
            page_object="TestPage"
        )
        
        # Convert to Playwright
        playwright = locator.to_playwright_locator()
        
        # CRITICAL: Original XPath must be in output
        assert complex_xpath in playwright
        
        # Convert to Robot
        robot = locator.to_robot_locator()
        
        # CRITICAL: Original XPath must be in output
        assert complex_xpath in robot
        
        # Verify preservation flag
        assert locator.preserved is True
        assert locator.confidence == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
