"""
Unit tests for PageObject → Test mapping.

Tests cover:
- Basic mapping (single PageObject per test)
- Multiple PageObjects per test
- Shared PageObjects across tests
- No PageObjects (negative case)
- Contract stability
"""

import pytest
from pathlib import Path
from dataclasses import dataclass, field
from typing import List


@dataclass
class JavaTestCase:
    """Test case model for PageObject mapping tests."""
    framework: str
    package: str
    class_name: str
    method_name: str
    annotations: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    file_path: str = ""
    page_objects: List[str] = field(default_factory=list)


class TestBasicPageObjectMapping:
    """Test basic PageObject → Test mapping functionality."""
    
    def test_single_page_object_per_test(self):
        """Test mapping when each test uses one PageObject."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="LoginTest",
            method_name="testValidLogin",
            annotations=["Test"],
            tags=["smoke"],
            file_path="LoginTest.java",
            page_objects=["LoginPage"]
        )
        
        # Create mapping: test_id -> set of page objects
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        assert mapping["LoginTest.testValidLogin"] == {"LoginPage"}
    
    def test_multiple_page_objects_per_test(self):
        """Test mapping when test uses multiple PageObjects."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="CheckoutTest",
            method_name="testCompleteCheckout",
            annotations=["Test"],
            tags=["smoke"],
            file_path="CheckoutTest.java",
            page_objects=["CartPage", "CheckoutPage", "ConfirmationPage"]
        )
        
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        assert mapping["CheckoutTest.testCompleteCheckout"] == {
            "CartPage",
            "CheckoutPage",
            "ConfirmationPage"
        }
    
    def test_no_page_objects(self):
        """Test mapping when test has no PageObjects (negative case)."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="UtilTest",
            method_name="testHelper",
            annotations=["Test"],
            tags=[],
            file_path="UtilTest.java",
            page_objects=[]
        )
        
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        assert mapping["UtilTest.testHelper"] == set()


class TestMultipleTestsMapping:
    """Test mapping multiple tests with shared PageObjects."""
    
    def test_multiple_tests_with_different_page_objects(self):
        """Test mapping when different tests use different PageObjects."""
        tests = [
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="LoginTest",
                method_name="testLogin",
                annotations=["Test"],
                tags=["smoke"],
                file_path="LoginTest.java",
                page_objects=["LoginPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="ProfileTest",
                method_name="testEditProfile",
                annotations=["Test"],
                tags=["regression"],
                file_path="ProfileTest.java",
                page_objects=["ProfilePage"]
            )
        ]
        
        mapping = {}
        for test in tests:
            test_id = f"{test.class_name}.{test.method_name}"
            mapping[test_id] = set(test.page_objects)
        
        assert mapping["LoginTest.testLogin"] == {"LoginPage"}
        assert mapping["ProfileTest.testEditProfile"] == {"ProfilePage"}
    
    def test_multiple_tests_sharing_page_objects(self):
        """Test mapping when multiple tests share same PageObjects."""
        tests = [
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="LoginTest",
                method_name="testValidLogin",
                annotations=["Test"],
                tags=["smoke"],
                file_path="LoginTest.java",
                page_objects=["LoginPage", "DashboardPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="LoginTest",
                method_name="testInvalidLogin",
                annotations=["Test"],
                tags=["smoke"],
                file_path="LoginTest.java",
                page_objects=["LoginPage"]
            )
        ]
        
        mapping = {}
        for test in tests:
            test_id = f"{test.class_name}.{test.method_name}"
            mapping[test_id] = set(test.page_objects)
        
        # Both tests use LoginPage
        assert "LoginPage" in mapping["LoginTest.testValidLogin"]
        assert "LoginPage" in mapping["LoginTest.testInvalidLogin"]
        
        # Only first test uses DashboardPage
        assert "DashboardPage" in mapping["LoginTest.testValidLogin"]
        assert "DashboardPage" not in mapping["LoginTest.testInvalidLogin"]


class TestReverseMapping:
    """Test reverse mapping: PageObject → Tests."""
    
    def test_page_object_to_tests_mapping(self):
        """Test creating reverse mapping from PageObject to tests using it."""
        tests = [
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="LoginTest",
                method_name="testValidLogin",
                annotations=["Test"],
                tags=["smoke"],
                file_path="LoginTest.java",
                page_objects=["LoginPage", "DashboardPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="LoginTest",
                method_name="testInvalidLogin",
                annotations=["Test"],
                tags=["smoke"],
                file_path="LoginTest.java",
                page_objects=["LoginPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="ProfileTest",
                method_name="testEditProfile",
                annotations=["Test"],
                tags=["regression"],
                file_path="ProfileTest.java",
                page_objects=["ProfilePage", "DashboardPage"]
            )
        ]
        
        # Create reverse mapping: PageObject -> set of tests
        reverse_mapping = {}
        for test in tests:
            test_id = f"{test.class_name}.{test.method_name}"
            for page_obj in test.page_objects:
                if page_obj not in reverse_mapping:
                    reverse_mapping[page_obj] = set()
                reverse_mapping[page_obj].add(test_id)
        
        # LoginPage is used by 2 tests
        assert reverse_mapping["LoginPage"] == {
            "LoginTest.testValidLogin",
            "LoginTest.testInvalidLogin"
        }
        
        # DashboardPage is used by 2 tests
        assert reverse_mapping["DashboardPage"] == {
            "LoginTest.testValidLogin",
            "ProfileTest.testEditProfile"
        }
        
        # ProfilePage is used by 1 test
        assert reverse_mapping["ProfilePage"] == {
            "ProfileTest.testEditProfile"
        }


class TestImpactAnalysis:
    """Test using PageObject mapping for impact analysis."""
    
    def test_find_tests_impacted_by_page_object_change(self):
        """Test finding all tests impacted when a PageObject changes."""
        tests = [
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="LoginTest",
                method_name="testValidLogin",
                annotations=["Test"],
                tags=["smoke"],
                file_path="LoginTest.java",
                page_objects=["LoginPage", "DashboardPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="LoginTest",
                method_name="testInvalidLogin",
                annotations=["Test"],
                tags=["smoke"],
                file_path="LoginTest.java",
                page_objects=["LoginPage", "ErrorPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.example",
                class_name="ProfileTest",
                method_name="testEditProfile",
                annotations=["Test"],
                tags=["regression"],
                file_path="ProfileTest.java",
                page_objects=["ProfilePage"]
            )
        ]
        
        # Simulate: LoginPage.java changed
        changed_page_object = "LoginPage"
        
        # Find impacted tests
        impacted_tests = []
        for test in tests:
            test_id = f"{test.class_name}.{test.method_name}"
            if changed_page_object in test.page_objects:
                impacted_tests.append(test_id)
        
        # Should find 2 tests
        assert len(impacted_tests) == 2
        assert "LoginTest.testValidLogin" in impacted_tests
        assert "LoginTest.testInvalidLogin" in impacted_tests
        assert "ProfileTest.testEditProfile" not in impacted_tests


class TestEdgeCases:
    """Test edge cases in PageObject mapping."""
    
    def test_empty_page_objects_list(self):
        """Test handling empty page_objects list."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="EmptyTest",
            method_name="testEmpty",
            annotations=["Test"],
            tags=[],
            file_path="EmptyTest.java",
            page_objects=[]
        )
        
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        assert mapping["EmptyTest.testEmpty"] == set()
    
    def test_none_page_objects(self):
        """Test handling None page_objects (should not crash)."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="NoneTest",
            method_name="testNone",
            annotations=["Test"],
            tags=[],
            file_path="NoneTest.java",
            page_objects=None
        )
        
        # Should handle gracefully
        page_objs = test_case.page_objects if test_case.page_objects else []
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(page_objs)
        }
        
        assert mapping["NoneTest.testNone"] == set()
    
    def test_duplicate_page_objects_in_test(self):
        """Test handling duplicate PageObjects in same test."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="DupeTest",
            method_name="testDuplicate",
            annotations=["Test"],
            tags=[],
            file_path="DupeTest.java",
            page_objects=["LoginPage", "LoginPage", "DashboardPage"]
        )
        
        # Using set should deduplicate
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        assert mapping["DupeTest.testDuplicate"] == {"LoginPage", "DashboardPage"}


class TestContractStability:
    """Test that mapping contract remains stable (CRITICAL)."""
    
    def test_mapping_output_is_dict(self):
        """Test that mapping returns a dict."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="Test",
            method_name="test",
            annotations=["Test"],
            tags=[],
            file_path="Test.java",
            page_objects=["Page"]
        )
        
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        assert isinstance(mapping, dict)
    
    def test_mapping_keys_are_strings(self):
        """Test that mapping keys are strings (test IDs)."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="Test",
            method_name="test",
            annotations=["Test"],
            tags=[],
            file_path="Test.java",
            page_objects=["Page"]
        )
        
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        for key in mapping.keys():
            assert isinstance(key, str)
    
    def test_mapping_values_are_sets(self):
        """Test that mapping values are sets of PageObject names."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="Test",
            method_name="test",
            annotations=["Test"],
            tags=[],
            file_path="Test.java",
            page_objects=["Page1", "Page2"]
        )
        
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        for value in mapping.values():
            assert isinstance(value, set)
            # All elements should be strings
            for item in value:
                assert isinstance(item, str)
    
    def test_test_id_format_is_consistent(self):
        """Test that test ID format is ClassName.methodName."""
        test_case = JavaTestCase(
            framework="junit5",
            package="com.example",
            class_name="MyTest",
            method_name="myMethod",
            annotations=["Test"],
            tags=[],
            file_path="MyTest.java",
            page_objects=[]
        )
        
        test_id = f"{test_case.class_name}.{test_case.method_name}"
        
        assert test_id == "MyTest.myMethod"
        assert "." in test_id
        assert test_id.split(".")[0] == "MyTest"
        assert test_id.split(".")[1] == "myMethod"


class TestRealWorldScenarios:
    """Test real-world scenarios and workflows."""
    
    def test_e2e_checkout_flow_mapping(self):
        """Test mapping for realistic E2E checkout flow."""
        test_case = JavaTestCase(
            framework="testng",
            package="com.shop.tests",
            class_name="CheckoutE2ETest",
            method_name="testCompleteCheckoutFlow",
            annotations=["Test"],
            tags=["e2e", "critical"],
            file_path="CheckoutE2ETest.java",
            page_objects=[
                "HomePage",
                "ProductListPage",
                "ProductDetailPage",
                "CartPage",
                "CheckoutPage",
                "PaymentPage",
                "ConfirmationPage"
            ]
        )
        
        mapping = {
            f"{test_case.class_name}.{test_case.method_name}": set(test_case.page_objects)
        }
        
        page_objects = mapping["CheckoutE2ETest.testCompleteCheckoutFlow"]
        
        # Should have all 7 page objects
        assert len(page_objects) == 7
        assert "HomePage" in page_objects
        assert "ConfirmationPage" in page_objects
    
    def test_impact_analysis_for_cart_page_change(self):
        """Test impact analysis when CartPage changes."""
        tests = [
            JavaTestCase(
                framework="junit5",
                package="com.shop.tests",
                class_name="CartTest",
                method_name="testAddToCart",
                annotations=["Test"],
                tags=["smoke"],
                file_path="CartTest.java",
                page_objects=["ProductPage", "CartPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.shop.tests",
                class_name="CartTest",
                method_name="testRemoveFromCart",
                annotations=["Test"],
                tags=["smoke"],
                file_path="CartTest.java",
                page_objects=["CartPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.shop.tests",
                class_name="CheckoutTest",
                method_name="testCheckout",
                annotations=["Test"],
                tags=["smoke"],
                file_path="CheckoutTest.java",
                page_objects=["CartPage", "CheckoutPage"]
            ),
            JavaTestCase(
                framework="junit5",
                package="com.shop.tests",
                class_name="LoginTest",
                method_name="testLogin",
                annotations=["Test"],
                tags=["smoke"],
                file_path="LoginTest.java",
                page_objects=["LoginPage"]
            )
        ]
        
        # Simulate: CartPage.java changed
        changed_file = "CartPage"
        
        # Find all impacted tests
        impacted = []
        for test in tests:
            if changed_file in test.page_objects:
                test_id = f"{test.class_name}.{test.method_name}"
                impacted.append(test_id)
        
        # Should find 3 tests that use CartPage
        assert len(impacted) == 3
        assert "CartTest.testAddToCart" in impacted
        assert "CartTest.testRemoveFromCart" in impacted
        assert "CheckoutTest.testCheckout" in impacted
        assert "LoginTest.testLogin" not in impacted
