"""
Tests for advanced page object detection.
"""

import pytest
from pathlib import Path
from adapters.java.advanced_page_object_detector import (
    AdvancedPageObjectDetector,
    PageObjectClass
)


@pytest.fixture
def detector():
    return AdvancedPageObjectDetector()


@pytest.fixture
def sample_page_object(tmp_path):
    """Create a sample Page Object Java file."""
    java_file = tmp_path / "LoginPage.java"
    java_file.write_text("""
package com.example.pages;

import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

public class LoginPage extends BasePage {
    
    @FindBy(id = "username")
    private WebElement usernameField;
    
    @FindBy(name = "password")
    private WebElement passwordField;
    
    @FindBy(xpath = "//button[@type='submit']")
    private WebElement loginButton;
    
    public LoginPage() {
        PageFactory.initElements(driver, this);
    }
    
    public void enterUsername(String username) {
        usernameField.sendKeys(username);
    }
    
    public void enterPassword(String password) {
        passwordField.sendKeys(password);
    }
    
    public HomePage clickLogin() {
        loginButton.click();
        return new HomePage();
    }
}
    """)
    return java_file


def test_extract_page_object(detector, sample_page_object):
    """Test extracting page object details."""
    po = detector.extract_page_object(sample_page_object)
    
    assert po is not None
    assert po.class_name == "LoginPage"
    assert po.parent_class == "BasePage"
    assert po.package == "com.example.pages"
    assert po.uses_page_factory is True
    assert len(po.elements) == 3
    assert len(po.methods) >= 2  # enterUsername, enterPassword, clickLogin


def test_detect_elements(detector, sample_page_object):
    """Test element detection."""
    po = detector.extract_page_object(sample_page_object)
    
    # Check username field
    username_elem = next((e for e in po.elements if e['name'] == 'usernameField'), None)
    assert username_elem is not None
    assert username_elem['locator_strategy'] == 'id'
    assert username_elem['locator_value'] == 'username'
    
    # Check password field
    password_elem = next((e for e in po.elements if e['name'] == 'passwordField'), None)
    assert password_elem is not None
    assert password_elem['locator_strategy'] == 'name'


def test_inheritance_level_calculation(detector, tmp_path):
    """Test inheritance level calculation."""
    # Create BasePage
    base_page = tmp_path / "BasePage.java"
    base_page.write_text("""
package com.example.pages;
public class BasePage {}
    """)
    
    # Create LoginPage extends BasePage
    login_page = tmp_path / "LoginPage.java"
    login_page.write_text("""
package com.example.pages;
public class LoginPage extends BasePage {}
    """)
    
    # Create SecureLoginPage extends LoginPage
    secure_page = tmp_path / "SecureLoginPage.java"
    secure_page.write_text("""
package com.example.pages;
public class SecureLoginPage extends LoginPage {}
    """)
    
    page_objects = [
        detector.extract_page_object(f)
        for f in [base_page, login_page, secure_page]
    ]
    page_objects = [po for po in page_objects if po]
    
    page_objects = detector._calculate_inheritance_levels(page_objects)
    
    # Find each page object
    base_po = next(po for po in page_objects if po.class_name == "BasePage")
    login_po = next(po for po in page_objects if po.class_name == "LoginPage")
    secure_po = next(po for po in page_objects if po.class_name == "SecureLoginPage")
    
    assert base_po.inheritance_level == 0
    assert login_po.inheritance_level == 1
    assert secure_po.inheritance_level == 2


def test_convert_to_robot_resource(detector, sample_page_object):
    """Test conversion to Robot Framework resource."""
    po = detector.extract_page_object(sample_page_object)
    resource = detector.convert_to_robot_resource(po)
    
    assert "*** Settings ***" in resource
    assert "*** Variables ***" in resource
    assert "*** Keywords ***" in resource
    assert "LOC_USERNAMEFIELD" in resource
    assert "id=username" in resource


def test_loadable_component_detection(detector, tmp_path):
    """Test detection of LoadableComponent pattern."""
    page_file = tmp_path / "DashboardPage.java"
    page_file.write_text("""
package com.example.pages;
import org.openqa.selenium.support.ui.LoadableComponent;

public class DashboardPage extends LoadableComponent<DashboardPage> {
    @Override
    protected void load() {
        driver.get("https://example.com/dashboard");
    }
    
    @Override
    protected void isLoaded() throws Error {
        // Verify page loaded
    }
}
    """)
    
    po = detector.extract_page_object(page_file)
    assert po.is_loadable_component is True


def test_build_inheritance_tree(detector, tmp_path):
    """Test building inheritance tree."""
    # Create several related page objects
    base = tmp_path / "BasePage.java"
    base.write_text("package com.example; public class BasePage {}")
    
    login = tmp_path / "LoginPage.java"
    login.write_text("package com.example; public class LoginPage extends BasePage {}")
    
    home = tmp_path / "HomePage.java"
    home.write_text("package com.example; public class HomePage extends BasePage {}")
    
    page_objects = [
        detector.extract_page_object(f)
        for f in [base, login, home]
    ]
    page_objects = [po for po in page_objects if po]
    
    tree = detector.build_inheritance_tree(page_objects)
    
    assert "BasePage" in tree
    assert "LoginPage" in tree["BasePage"]
    assert "HomePage" in tree["BasePage"]
