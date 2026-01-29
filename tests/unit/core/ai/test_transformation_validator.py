"""
Unit tests for AI Transformation Validator

Tests the comprehensive validation framework for AI-generated transformations.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from core.ai.transformation_validator import (
    TransformationValidator,
    ValidationSeverity,
    ValidationIssue,
    ValidationResult,
    FeedbackCollector,
)
from core.ai.confidence_scoring import ConfidenceMetrics, ConfidenceLevel


class TestTransformationValidator:
    """Test suite for TransformationValidator"""

    @pytest.fixture
    def validator(self):
        """Create a validator instance for testing"""
        return TransformationValidator(
            target_framework="robot",
            strict_mode=False,
            auto_fix_enabled=True
        )

    @pytest.fixture
    def strict_validator(self):
        """Create a strict validator instance"""
        return TransformationValidator(
            target_framework="robot",
            strict_mode=True,
            auto_fix_enabled=False
        )

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_validator_initialization(self, validator):
        """Test validator initializes correctly"""
        assert validator is not None
        assert validator.target_framework == "robot"
        assert validator.strict_mode is False
        assert validator.auto_fix_enabled is True
        assert validator.scorer is not None

    def test_strict_validator_initialization(self, strict_validator):
        """Test strict validator initialization"""
        assert strict_validator.strict_mode is True
        assert strict_validator.auto_fix_enabled is False

    # ========================================================================
    # Syntax Validation Tests
    # ========================================================================

    def test_validate_syntax_valid_python(self, validator):
        """Test syntax validation with valid Python code"""
        validator.target_framework = "pytest"
        
        valid_python = """
def test_example():
    assert True
"""
        valid, issues = validator._validate_syntax(valid_python)
        
        assert valid is True
        assert len(issues) == 0

    def test_validate_syntax_invalid_python(self, validator):
        """Test syntax validation with invalid Python code"""
        validator.target_framework = "pytest"
        
        invalid_python = """
def test_example()
    assert True  # Missing colon
"""
        valid, issues = validator._validate_syntax(invalid_python)
        
        assert valid is False
        assert len(issues) > 0
        assert issues[0].severity == ValidationSeverity.CRITICAL
        assert "syntax" in issues[0].category.lower()

    def test_validate_syntax_valid_robot(self, validator):
        """Test syntax validation with valid Robot Framework code"""
        valid_robot = """
*** Test Cases ***
Valid Test
    Log    Hello World
"""
        valid, issues = validator._validate_syntax(valid_robot)
        
        assert valid is True
        assert len(issues) == 0

    def test_validate_syntax_empty_robot(self, validator):
        """Test syntax validation with empty Robot Framework file"""
        empty_robot = ""
        
        valid, issues = validator._validate_syntax(empty_robot)
        
        assert valid is False
        assert len(issues) > 0
        assert issues[0].severity == ValidationSeverity.CRITICAL

    def test_validate_syntax_robot_missing_sections(self, validator):
        """Test syntax validation with Robot file missing required sections"""
        invalid_robot = """
*** Settings ***
Library    SeleniumLibrary
"""
        valid, issues = validator._validate_syntax(invalid_robot)
        
        assert valid is False
        assert len(issues) > 0

    # ========================================================================
    # Import Validation Tests
    # ========================================================================

    def test_validate_imports_valid_python(self, validator):
        """Test import validation with valid Python imports"""
        validator.target_framework = "pytest"
        
        valid_code = """
import pytest
from selenium import webdriver
from typing import List, Dict
"""
        valid, issues = validator._validate_imports(valid_code)
        
        assert valid is True
        assert len(issues) == 0

    def test_validate_imports_placeholder_python(self, validator):
        """Test import validation detects placeholder imports"""
        validator.target_framework = "pytest"
        
        code_with_placeholder = """
import pytest
from PLACEHOLDER import something
from typing import List
"""
        valid, issues = validator._validate_imports(code_with_placeholder)
        
        assert valid is False
        assert len(issues) > 0
        assert any("placeholder" in i.message.lower() for i in issues)

    def test_validate_imports_robot(self, validator):
        """Test import validation for Robot Framework"""
        valid_robot = """
*** Settings ***
Library    SeleniumLibrary
Library    RequestsLibrary
"""
        valid, issues = validator._validate_imports(valid_robot)
        
        assert valid is True
        assert len(issues) == 0

    def test_validate_imports_placeholder_robot(self, validator):
        """Test Robot import validation detects placeholders"""
        robot_with_placeholder = """
*** Settings ***
Library    SeleniumLibrary
Library    PLACEHOLDER_Library
"""
        valid, issues = validator._validate_imports(robot_with_placeholder)
        
        assert valid is False
        assert len(issues) > 0

    # ========================================================================
    # Locator Quality Tests
    # ========================================================================

    def test_validate_locators_no_locators(self, validator):
        """Test locator validation with no locators"""
        code_without_locators = """
def test_example():
    print("Hello")
"""
        score, issues = validator._validate_locators(code_without_locators)
        
        assert score == 1.0  # Perfect score for no locators
        assert len(issues) == 0

    def test_validate_locators_good_quality(self, validator):
        """Test locator validation with high-quality locators"""
        code_with_good_locators = """
def test_login():
    page.get_by_test_id("username").fill("user")
    page.locator("id=password").fill("pass")
    page.locator("data-testid=login-button").click()
"""
        score, issues = validator._validate_locators(code_with_good_locators)
        
        assert score > 0.8  # High quality score
        assert len([i for i in issues if i.severity == ValidationSeverity.CRITICAL]) == 0

    def test_validate_locators_brittle_xpath(self, validator):
        """Test locator validation detects brittle XPath"""
        code_with_brittle_xpath = """
def test_login():
    element = driver.find_element_by_xpath("/html/body/div[1]/form/input[1]")
    element.click()
"""
        score, issues = validator._validate_locators(code_with_brittle_xpath)
        
        assert score < 1.0  # Penalized for brittle XPath
        assert len(issues) > 0
        assert any("brittle" in i.message.lower() for i in issues)

    # ========================================================================
    # Semantic Validation Tests
    # ========================================================================

    def test_validate_semantics_preserved(self, validator):
        """Test semantic validation when actions are preserved"""
        source = """
driver.find_element(By.ID, "username").send_keys("user")
driver.find_element(By.ID, "password").send_keys("pass")
driver.find_element(By.ID, "login").click()
"""
        
        transformed = """
Input Text    id=username    user
Input Text    id=password    pass
Click Button  id=login
"""
        
        issues = validator._validate_semantics(source, transformed)
        
        # Should have minimal issues
        assert len([i for i in issues if i.severity == ValidationSeverity.CRITICAL]) == 0

    def test_validate_semantics_missing_actions(self, validator):
        """Test semantic validation detects missing actions"""
        source = """
driver.find_element(By.ID, "username").send_keys("user")
driver.find_element(By.ID, "password").send_keys("pass")
driver.find_element(By.ID, "login").click()
driver.find_element(By.ID, "logout").click()
"""
        
        transformed = """
Input Text    id=username    user
Input Text    id=password    pass
"""
        
        issues = validator._validate_semantics(source, transformed)
        
        assert len(issues) > 0
        assert any("missing" in i.message.lower() for i in issues)

    # ========================================================================
    # Framework Idiom Tests
    # ========================================================================

    def test_validate_idioms_robot_sleep_antipattern(self, validator):
        """Test idiom validation detects time.sleep in Robot"""
        robot_code = """
*** Test Cases ***
Test Example
    Click Button    login
    time.sleep(5)
    Page Should Contain    Welcome
"""
        
        issues = validator._validate_framework_idioms(robot_code)
        
        assert len(issues) > 0
        assert any("sleep" in i.message.lower() for i in issues)
        assert any(i.auto_fixable for i in issues)

    def test_validate_idioms_robot_casing(self, validator):
        """Test idiom validation for Robot keyword casing"""
        robot_code = """
*** Test Cases ***
Test Example
    click_button    login
    input_text      username    user
"""
        
        issues = validator._validate_framework_idioms(robot_code)
        
        # Should suggest Title Case
        assert any("title case" in i.message.lower() for i in issues)

    # ========================================================================
    # Complete Validation Tests
    # ========================================================================

    def test_validate_complete_valid_transformation(self, validator):
        """Test complete validation with valid transformation"""
        source = """
public class LoginTest {
    public void testLogin() {
        driver.findElement(By.id("username")).sendKeys("user");
        driver.findElement(By.id("password")).sendKeys("pass");
        driver.findElement(By.id("login")).click();
    }
}
"""
        
        transformed = """
*** Test Cases ***
Test Login
    Input Text    id=username    user
    Input Text    id=password    pass
    Click Button  id=login
"""
        
        result = validator.validate(source, transformed, "LoginTest.java")
        
        assert result is not None
        assert result.transformation_id is not None
        assert result.syntax_valid is True
        assert result.imports_resolved is True
        assert result.quality_score > 0.5

    def test_validate_complete_invalid_transformation(self, validator):
        """Test complete validation with invalid transformation"""
        source = """
public void testLogin() {
    driver.findElement(By.id("username")).sendKeys("user");
}
"""
        
        transformed = """
*** Test Cases
Test Login
    Invalid Python Syntax Here
"""
        
        result = validator.validate(source, transformed, "LoginTest.java")
        
        assert result is not None
        assert result.syntax_valid is False
        assert result.passed is False
        assert result.has_blocking_issues

    def test_validate_with_metadata(self, validator):
        """Test validation includes metadata in result"""
        source = "def test(): pass"
        transformed = "*** Test Cases ***\nTest\n    Log    Hello"
        
        metadata = {
            "tokens_used": 1000,
            "cost_usd": 0.002,
            "model": "gpt-3.5-turbo"
        }
        
        result = validator.validate(source, transformed, "test.py", metadata)
        
        assert result.metadata == metadata
        assert "tokens_used" in result.metadata
        assert "cost_usd" in result.metadata

    # ========================================================================
    # Quality Score Tests
    # ========================================================================

    def test_quality_score_calculation(self, validator):
        """Test quality score calculation"""
        source = "def test(): pass"
        transformed = """
*** Test Cases ***
Test Example
    Log    Hello World
"""
        
        result = validator.validate(source, transformed, "test.py")
        
        assert 0.0 <= result.quality_score <= 1.0
        assert result.quality_score > 0.4  # Should be reasonable quality

    def test_quality_score_penalties(self, validator):
        """Test that issues reduce quality score"""
        source = "def test(): pass"
        
        # Transformation with issues
        transformed_with_issues = """
*** Test Cases
Missing stars for section
    time.sleep(5)
    click_button    id=login
"""
        
        result = validator.validate(source, transformed_with_issues, "test.py")
        
        assert result.quality_score < 0.5  # Penalties applied

    # ========================================================================
    # Strict Mode Tests
    # ========================================================================

    def test_strict_mode_fails_on_warnings(self, strict_validator):
        """Test strict mode fails validation on warnings"""
        source = "def test(): pass"
        transformed = """
*** Test Cases ***
Test Example
    time.sleep(5)
    Log    Done
"""
        
        result = strict_validator.validate(source, transformed, "test.py")
        
        # Strict mode should fail due to sleep warning
        assert result.passed is False

    def test_non_strict_mode_passes_warnings(self, validator):
        """Test non-strict mode passes with warnings"""
        source = "def test(): pass"
        transformed = """
*** Test Cases ***
Test Example
    Log    Hello
"""
        
        result = validator.validate(source, transformed, "test.py")
        
        # Non-strict should pass
        assert result.passed is True

    # ========================================================================
    # Diff Report Tests
    # ========================================================================

    def test_generate_diff_report(self, validator):
        """Test diff report generation"""
        source = "def test(): pass"
        transformed = "*** Test Cases ***\nTest\n    Log    Hello"
        
        result = validator.validate(source, transformed, "test.py")
        report = validator.generate_diff_report(source, transformed, result)
        
        assert report is not None
        assert "TRANSFORMATION VALIDATION REPORT" in report
        assert result.transformation_id in report
        assert "CONFIDENCE METRICS" in report
        assert f"Quality Score: {result.quality_score:.2f}" in report

    def test_diff_report_with_issues(self, validator):
        """Test diff report includes issues"""
        source = "def test(): pass"
        transformed = "*** Invalid"
        
        result = validator.validate(source, transformed, "test.py")
        report = validator.generate_diff_report(source, transformed, result)
        
        assert "VALIDATION ISSUES" in report
        assert len(result.issues) > 0


class TestFeedbackCollector:
    """Test suite for FeedbackCollector"""

    @pytest.fixture
    def collector(self, tmp_path):
        """Create feedback collector with temp storage"""
        return FeedbackCollector(storage_path=tmp_path / "feedback")

    def test_collector_initialization(self, collector):
        """Test feedback collector initializes correctly"""
        assert collector is not None
        assert collector.storage_path.exists()

    def test_record_feedback_approved(self, collector):
        """Test recording approval feedback"""
        feedback = collector.record_feedback(
            transformation_id="test-123",
            approved=True,
            reviewer="test_user",
            comments="Looks good!"
        )
        
        assert feedback is not None
        assert feedback["transformation_id"] == "test-123"
        assert feedback["approved"] is True
        assert feedback["reviewer"] == "test_user"
        assert feedback["comments"] == "Looks good!"
        assert "timestamp" in feedback

    def test_record_feedback_rejected(self, collector):
        """Test recording rejection feedback"""
        feedback = collector.record_feedback(
            transformation_id="test-456",
            approved=False,
            reviewer="test_user",
            comments="Needs improvement",
            corrections="Fixed code here"
        )
        
        assert feedback["approved"] is False
        assert feedback["corrections"] == "Fixed code here"

    def test_feedback_persisted(self, collector):
        """Test feedback is persisted to disk"""
        transformation_id = "test-persist-123"
        
        collector.record_feedback(
            transformation_id=transformation_id,
            approved=True,
            reviewer="test_user"
        )
        
        feedback_file = collector.storage_path / f"{transformation_id}.json"
        assert feedback_file.exists()

    def test_get_approval_rate_empty(self, collector):
        """Test approval rate with no feedback"""
        rate = collector.get_approval_rate()
        assert rate == 0.0

    def test_get_approval_rate_calculation(self, collector):
        """Test approval rate calculation"""
        # Record some feedback
        collector.record_feedback("test-1", True, "user1")
        collector.record_feedback("test-2", True, "user1")
        collector.record_feedback("test-3", False, "user1")
        collector.record_feedback("test-4", True, "user1")
        
        rate = collector.get_approval_rate()
        assert rate == 0.75  # 3 out of 4 approved


class TestValidationResult:
    """Test suite for ValidationResult dataclass"""

    def test_critical_issues_property(self):
        """Test critical_issues property filters correctly"""
        result = ValidationResult(
            transformation_id="test-123",
            source_file="test.py",
            target_file="test.robot",
            confidence=Mock(overall_score=0.8)
        )
        
        result.issues = [
            ValidationIssue(ValidationSeverity.CRITICAL, "syntax", "Critical error"),
            ValidationIssue(ValidationSeverity.ERROR, "import", "Error"),
            ValidationIssue(ValidationSeverity.WARNING, "style", "Warning"),
        ]
        
        critical = result.critical_issues
        assert len(critical) == 1
        assert critical[0].severity == ValidationSeverity.CRITICAL

    def test_has_blocking_issues(self):
        """Test has_blocking_issues detects critical issues"""
        result = ValidationResult(
            transformation_id="test-123",
            source_file="test.py",
            target_file="test.robot",
            confidence=Mock(overall_score=0.8)
        )
        
        result.issues = [
            ValidationIssue(ValidationSeverity.CRITICAL, "syntax", "Critical error"),
        ]
        
        assert result.has_blocking_issues is True

    def test_has_blocking_issues_syntax_invalid(self):
        """Test has_blocking_issues detects invalid syntax"""
        result = ValidationResult(
            transformation_id="test-123",
            source_file="test.py",
            target_file="test.robot",
            confidence=Mock(overall_score=0.8),
            syntax_valid=False
        )
        
        assert result.has_blocking_issues is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
