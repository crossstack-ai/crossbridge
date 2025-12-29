"""
Unit tests for Java/Selenium Page Object impact mapper.

Tests detection and mapping of Page Objects in Java projects.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from adapters.java.impact_mapper import (
    JavaPageObjectDetector,
    JavaTestToPageObjectMapper,
    create_impact_map
)
from adapters.common.impact_models import MappingSource


class TestJavaPageObjectDetector:
    """Test Page Object detection in Java code."""
    
    def test_detect_page_object_by_name(self, tmp_path):
        """Test detection of Page Object by class name ending with 'Page'."""
        pages_dir = tmp_path / "src" / "main" / "java" / "com" / "example" / "pages"
        pages_dir.mkdir(parents=True)
        
        # Create a Page Object
        page_file = pages_dir / "LoginPage.java"
        page_file.write_text("""
package com.example.pages;

public class LoginPage {
    public void enterUsername(String username) {
        // implementation
    }
    
    public void enterPassword(String password) {
        // implementation
    }
    
    public void clickLogin() {
        // implementation
    }
}
""")
        
        detector = JavaPageObjectDetector(str(tmp_path / "src" / "main" / "java"))
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 1
        assert page_objects[0].class_name == "com.example.pages.LoginPage"
        assert page_objects[0].language == "java"
        assert page_objects[0].is_page_object()
    
    def test_detect_page_object_by_base_class(self, tmp_path):
        """Test detection of Page Object by inheritance."""
        pages_dir = tmp_path / "src" / "main" / "java" / "com" / "example" / "pages"
        pages_dir.mkdir(parents=True)
        
        # Create base class
        base_file = pages_dir / "BasePage.java"
        base_file.write_text("""
package com.example.pages;

public class BasePage {
    protected WebDriver driver;
    
    public BasePage(WebDriver driver) {
        this.driver = driver;
    }
}
""")
        
        # Create derived class
        dashboard_file = pages_dir / "DashboardPage.java"
        dashboard_file.write_text("""
package com.example.pages;

public class DashboardPage extends BasePage {
    public DashboardPage(WebDriver driver) {
        super(driver);
    }
    
    public String getWelcomeMessage() {
        return "Welcome";
    }
}
""")
        
        detector = JavaPageObjectDetector(str(tmp_path / "src" / "main" / "java"))
        page_objects = detector.detect_page_objects()
        
        # Should detect both (BasePage by name, DashboardPage by inheritance)
        assert len(page_objects) == 2
        
        dashboard = [po for po in page_objects if "Dashboard" in po.class_name][0]
        assert dashboard.base_class == "BasePage"
    
    def test_detect_multiple_page_objects(self, tmp_path):
        """Test detection of multiple Page Objects in same package."""
        pages_dir = tmp_path / "src" / "main" / "java" / "com" / "example" / "pages"
        pages_dir.mkdir(parents=True)
        
        # Create multiple Page Objects
        for page_name in ["LoginPage", "HomePage", "SettingsPage"]:
            page_file = pages_dir / f"{page_name}.java"
            page_file.write_text(f"""
package com.example.pages;

public class {page_name} {{
    public void doSomething() {{}}
}}
""")
        
        # Create non-Page Object
        util_file = pages_dir / "Utility.java"
        util_file.write_text("""
package com.example.pages;

public class Utility {
    public static void helper() {}
}
""")
        
        detector = JavaPageObjectDetector(str(tmp_path / "src" / "main" / "java"))
        page_objects = detector.detect_page_objects()
        
        # Should detect 4 classes: 3 Page Objects (LoginPage, HomePage, SettingsPage) 
        # + Utility (detected because it's in the "pages" package)
        assert len(page_objects) == 4
        page_names = [po.get_simple_name() for po in page_objects]
        assert "LoginPage" in page_names
        assert "HomePage" in page_names
        assert "SettingsPage" in page_names
        assert "Utility" in page_names
    
    def test_no_page_objects_directory(self, tmp_path):
        """Test handling of missing source directory."""
        detector = JavaPageObjectDetector(str(tmp_path / "nonexistent"))
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 0
    
    def test_package_detection(self, tmp_path):
        """Test package name extraction."""
        pages_dir = tmp_path / "src" / "main" / "java" / "org" / "test" / "pages"
        pages_dir.mkdir(parents=True)
        
        page_file = pages_dir / "LoginPage.java"
        page_file.write_text("""
package org.test.pages;

public class LoginPage {
    public void login() {}
}
""")
        
        detector = JavaPageObjectDetector(str(tmp_path / "src" / "main" / "java"))
        page_objects = detector.detect_page_objects()
        
        assert len(page_objects) == 1
        assert page_objects[0].package == "org.test.pages"


class TestJavaTestToPageObjectMapper:
    """Test mapping of Java tests to Page Objects."""
    
    def test_detect_page_object_import(self, tmp_path):
        """Test detection of Page Object via import statement."""
        test_dir = tmp_path / "src" / "test" / "java" / "com" / "example" / "tests"
        test_dir.mkdir(parents=True)
        
        test_file = test_dir / "LoginTest.java"
        test_file.write_text("""
package com.example.tests;

import com.example.pages.LoginPage;
import org.junit.Test;

public class LoginTest {
    @Test
    public void testValidLogin() {
        LoginPage page = new LoginPage();
        page.login("user", "pass");
    }
}
""")
        
        mapper = JavaTestToPageObjectMapper(
            str(tmp_path / "src" / "test" / "java"),
            known_page_objects={"LoginPage"}
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) >= 1
        
        # Find the testValidLogin mapping
        login_test = [m for m in impact_map.mappings if "testValidLogin" in m.test_id]
        assert len(login_test) > 0
        assert "LoginPage" in login_test[0].page_objects
    
    def test_detect_page_object_instantiation(self, tmp_path):
        """Test detection of Page Object via instantiation."""
        test_dir = tmp_path / "src" / "test" / "java" / "com" / "example" / "tests"
        test_dir.mkdir(parents=True)
        
        test_file = test_dir / "HomeTest.java"
        test_file.write_text("""
package com.example.tests;

import org.junit.Test;

public class HomeTest {
    @Test
    public void testHomepage() {
        HomePage page = new HomePage();
        page.verifyLoaded();
    }
}
""")
        
        mapper = JavaTestToPageObjectMapper(
            str(tmp_path / "src" / "test" / "java"),
            known_page_objects={"HomePage"}
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) >= 1
        
        homepage_test = [m for m in impact_map.mappings if "testHomepage" in m.test_id]
        assert len(homepage_test) > 0
        assert "HomePage" in homepage_test[0].page_objects
    
    def test_detect_multiple_page_objects_in_test(self, tmp_path):
        """Test detection of multiple Page Objects in single test."""
        test_dir = tmp_path / "src" / "test" / "java" / "com" / "example" / "tests"
        test_dir.mkdir(parents=True)
        
        test_file = test_dir / "FlowTest.java"
        test_file.write_text("""
package com.example.tests;

import com.example.pages.LoginPage;
import com.example.pages.DashboardPage;
import com.example.pages.SettingsPage;
import org.junit.Test;

public class FlowTest {
    @Test
    public void testCompleteFlow() {
        LoginPage login = new LoginPage();
        login.login("user", "pass");
        
        DashboardPage dashboard = new DashboardPage();
        dashboard.navigateToSettings();
        
        SettingsPage settings = new SettingsPage();
        settings.updateProfile();
    }
}
""")
        
        mapper = JavaTestToPageObjectMapper(
            str(tmp_path / "src" / "test" / "java"),
            known_page_objects={"LoginPage", "DashboardPage", "SettingsPage"}
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) >= 1
        
        flow_test = [m for m in impact_map.mappings if "testCompleteFlow" in m.test_id]
        assert len(flow_test) > 0
        
        # Should detect all 3 Page Objects
        assert len(flow_test[0].page_objects) >= 3
        assert "LoginPage" in flow_test[0].page_objects
        assert "DashboardPage" in flow_test[0].page_objects
        assert "SettingsPage" in flow_test[0].page_objects
    
    def test_multiple_tests_in_class(self, tmp_path):
        """Test mapping multiple tests in same class."""
        test_dir = tmp_path / "src" / "test" / "java" / "com" / "example" / "tests"
        test_dir.mkdir(parents=True)
        
        test_file = test_dir / "AuthTest.java"
        test_file.write_text("""
package com.example.tests;

import com.example.pages.LoginPage;
import com.example.pages.RegistrationPage;
import org.junit.Test;

public class AuthTest {
    @Test
    public void testLogin() {
        LoginPage page = new LoginPage();
        page.login("user", "pass");
    }
    
    @Test
    public void testLogout() {
        LoginPage page = new LoginPage();
        page.logout();
    }
    
    @Test
    public void testRegister() {
        RegistrationPage page = new RegistrationPage();
        page.register();
    }
}
""")
        
        mapper = JavaTestToPageObjectMapper(
            str(tmp_path / "src" / "test" / "java"),
            known_page_objects={"LoginPage", "RegistrationPage"}
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        assert len(impact_map.mappings) >= 3
        
        test_ids = [m.test_id for m in impact_map.mappings]
        assert any("testLogin" in tid for tid in test_ids)
        assert any("testLogout" in tid for tid in test_ids)
        assert any("testRegister" in tid for tid in test_ids)
    
    def test_no_page_objects_used(self, tmp_path):
        """Test handling of tests that don't use Page Objects."""
        test_dir = tmp_path / "src" / "test" / "java" / "com" / "example" / "tests"
        test_dir.mkdir(parents=True)
        
        test_file = test_dir / "UnitTest.java"
        test_file.write_text("""
package com.example.tests;

import org.junit.Test;
import static org.junit.Assert.*;

public class UnitTest {
    @Test
    public void testCalculator() {
        assertEquals(2, 1 + 1);
    }
    
    @Test
    public void testStringUtils() {
        assertEquals("HELLO", "hello".toUpperCase());
    }
}
""")
        
        mapper = JavaTestToPageObjectMapper(
            str(tmp_path / "src" / "test" / "java"),
            known_page_objects=set()
        )
        impact_map = mapper.map_tests_to_page_objects()
        
        # Should not create mappings for tests without Page Objects
        assert len(impact_map.mappings) == 0


class TestCreateJavaImpactMap:
    """Test complete impact map creation."""
    
    def test_create_complete_impact_map(self, tmp_path):
        """Test end-to-end impact map creation."""
        # Setup project structure
        pages_dir = tmp_path / "src" / "main" / "java" / "com" / "example" / "pages"
        pages_dir.mkdir(parents=True)
        test_dir = tmp_path / "src" / "test" / "java" / "com" / "example" / "tests"
        test_dir.mkdir(parents=True)
        
        # Create Page Objects
        (pages_dir / "LoginPage.java").write_text("""
package com.example.pages;

public class LoginPage {
    public void login(String user, String pass) {}
}
""")
        
        (pages_dir / "HomePage.java").write_text("""
package com.example.pages;

public class HomePage {
    public void navigate() {}
}
""")
        
        # Create tests
        (test_dir / "AuthTest.java").write_text("""
package com.example.tests;

import com.example.pages.LoginPage;
import com.example.pages.HomePage;
import org.junit.Test;

public class AuthTest {
    @Test
    public void testLogin() {
        LoginPage page = new LoginPage();
        page.login("user", "pass");
    }
    
    @Test
    public void testLogout() {
        HomePage page = new HomePage();
        page.navigate();
    }
}
""")
        
        # Create impact map
        impact_map = create_impact_map(str(tmp_path))
        
        assert len(impact_map.mappings) >= 2
        
        # Verify impact queries
        login_tests = impact_map.get_impacted_tests("LoginPage")
        assert len(login_tests) >= 1
        assert any("testLogin" in test for test in login_tests)
        
        home_tests = impact_map.get_impacted_tests("HomePage")
        assert len(home_tests) >= 1
        assert any("testLogout" in test for test in home_tests)
    
    def test_impact_map_serialization(self, tmp_path):
        """Test serialization and deserialization of impact map."""
        pages_dir = tmp_path / "src" / "main" / "java" / "pages"
        pages_dir.mkdir(parents=True)
        test_dir = tmp_path / "src" / "test" / "java" / "tests"
        test_dir.mkdir(parents=True)
        
        (pages_dir / "TestPage.java").write_text("""
package pages;
public class TestPage {}
""")
        
        (test_dir / "TestClass.java").write_text("""
package tests;
import pages.TestPage;
import org.junit.Test;

public class TestClass {
    @Test
    public void testFeature() {
        TestPage page = new TestPage();
    }
}
""")
        
        impact_map = create_impact_map(str(tmp_path))
        
        # Serialize
        data = impact_map.to_dict()
        assert "mappings" in data
        assert "project_root" in data
        
        # Verify mapping format
        if data["mappings"]:
            mapping = data["mappings"][0]
            assert "test_id" in mapping
            assert "page_objects" in mapping
            assert "mapping_source" in mapping
            assert mapping["mapping_source"] == MappingSource.STATIC_AST.value
    
    def test_unified_model_format(self, tmp_path):
        """Test conversion to unified data model format."""
        pages_dir = tmp_path / "src" / "main" / "java" / "pages"
        pages_dir.mkdir(parents=True)
        test_dir = tmp_path / "src" / "test" / "java" / "tests"
        test_dir.mkdir(parents=True)
        
        (pages_dir / "LoginPage.java").write_text("""
package pages;
public class LoginPage {}
""")
        
        (test_dir / "LoginTest.java").write_text("""
package tests;
import pages.LoginPage;
import org.junit.Test;

public class LoginTest {
    @Test
    public void testValidLogin() {
        LoginPage page = new LoginPage();
    }
}
""")
        
        impact_map = create_impact_map(str(tmp_path))
        
        # Get unified format
        if impact_map.mappings:
            mapping = impact_map.mappings[0]
            if mapping.page_objects:
                po = list(mapping.page_objects)[0]
                unified = mapping.to_unified_model(po)
                
                # Verify format: {test_id, page_object, source, confidence}
                assert "test_id" in unified
                assert "page_object" in unified
                assert unified["source"] == "static_ast"
                assert "confidence" in unified
                assert 0.0 <= unified["confidence"] <= 1.0


@pytest.fixture
def sample_java_project(tmp_path):
    """Create a sample Java project with Page Objects and tests."""
    # Pages
    pages_dir = tmp_path / "src" / "main" / "java" / "com" / "example" / "pages"
    pages_dir.mkdir(parents=True)
    
    (pages_dir / "LoginPage.java").write_text("""
package com.example.pages;

public class LoginPage {
    public void login(String username, String password) {
        // implementation
    }
}
""")
    
    (pages_dir / "HomePage.java").write_text("""
package com.example.pages;

public class HomePage {
    public void navigateToSettings() {
        // implementation
    }
}
""")
    
    # Tests
    test_dir = tmp_path / "src" / "test" / "java" / "com" / "example" / "tests"
    test_dir.mkdir(parents=True)
    
    (test_dir / "AuthTest.java").write_text("""
package com.example.tests;

import com.example.pages.LoginPage;
import org.junit.Test;

public class AuthTest {
    @Test
    public void testValidLogin() {
        LoginPage page = new LoginPage();
        page.login("user", "pass");
    }
    
    @Test
    public void testInvalidLogin() {
        LoginPage page = new LoginPage();
        page.login("bad", "bad");
    }
}
""")
    
    (test_dir / "NavigationTest.java").write_text("""
package com.example.tests;

import com.example.pages.HomePage;
import org.junit.Test;

public class NavigationTest {
    @Test
    public void testNavigate() {
        HomePage page = new HomePage();
        page.navigateToSettings();
    }
}
""")
    
    return tmp_path


def test_end_to_end_java_impact(sample_java_project):
    """End-to-end test with realistic Java project structure."""
    impact_map = create_impact_map(str(sample_java_project))
    
    # Should have 3 test mappings
    assert len(impact_map.mappings) >= 3
    
    # Test impact queries
    login_tests = impact_map.get_impacted_tests("LoginPage")
    assert len(login_tests) >= 2
    assert any("testValidLogin" in t for t in login_tests)
    assert any("testInvalidLogin" in t for t in login_tests)
    
    home_tests = impact_map.get_impacted_tests("HomePage")
    assert len(home_tests) >= 1
    assert any("testNavigate" in t for t in home_tests)
    
    # Test statistics
    stats = impact_map.get_statistics()
    assert stats["total_tests"] >= 3
    assert stats["total_page_objects"] >= 2
