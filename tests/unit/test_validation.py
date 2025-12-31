"""
Tests for Migration Validation Module
"""
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from migration.validation import (
    MigrationValidator,
    PythonCodeValidator,
    RobotCodeValidator,
    ValidationLevel,
    ValidationIssue,
)


def test_python_validator_creation():
    """Test Python validator can be created"""
    validator = PythonCodeValidator()
    assert validator is not None


def test_python_validator_valid_syntax():
    """Test validation of valid Python code"""
    validator = PythonCodeValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
    
    def click_button(self):
        self.page.locator("#button").click()
""")
        f.flush()
        temp_file = Path(f.name)
    
    try:
        report = validator.validate_file(temp_file)
        assert report.summary['errors'] == 0
    finally:
        temp_file.unlink()


def test_python_validator_syntax_error():
    """Test detection of syntax errors"""
    validator = PythonCodeValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def invalid_function(
    # Missing closing parenthesis
    pass
""")
        f.flush()
        temp_file = Path(f.name)
    
    try:
        report = validator.validate_file(temp_file)
        assert report.summary['errors'] > 0
        assert any('syntax' in str(issue.message).lower() for issue in report.issues)
    finally:
        temp_file.unlink()


def test_python_validator_todo_detection():
    """Test detection of TODO comments"""
    validator = PythonCodeValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def some_function():
    # TODO: Implement this
    pass
""")
        f.flush()
        temp_file = Path(f.name)
    
    try:
        report = validator.validate_file(temp_file)
        assert any('todo' in str(issue.category).lower() for issue in report.issues)
    finally:
        temp_file.unlink()


def test_robot_validator_creation():
    """Test Robot validator can be created"""
    validator = RobotCodeValidator()
    assert validator is not None


def test_robot_validator_valid_structure():
    """Test validation of valid Robot code"""
    validator = RobotCodeValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False) as f:
        f.write("""*** Settings ***
Library    Browser

*** Variables ***
${LOCATOR}    id=button

*** Keywords ***
Click Button
    Click    ${LOCATOR}
""")
        f.flush()
        temp_file = Path(f.name)
    
    try:
        report = validator.validate_file(temp_file)
        assert report.summary['errors'] == 0
    finally:
        temp_file.unlink()


def test_robot_validator_missing_section():
    """Test detection of missing sections"""
    validator = RobotCodeValidator()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False) as f:
        f.write("""*** Keywords ***
Some Keyword
    Log    Hello
""")
        f.flush()
        temp_file = Path(f.name)
    
    try:
        report = validator.validate_file(temp_file)
        assert report.summary['warnings'] > 0
    finally:
        temp_file.unlink()


def test_migration_validator_creation():
    """Test migration validator can be created"""
    validator = MigrationValidator()
    assert validator is not None
    assert validator.python_validator is not None
    assert validator.robot_validator is not None


def test_validation_issue_creation():
    """Test creating validation issues"""
    issue = ValidationIssue(
        level=ValidationLevel.ERROR,
        category="test_category",
        message="Test message",
        file_path="test.py",
        line_number=10,
        suggestion="Fix it"
    )
    
    assert issue.level == ValidationLevel.ERROR
    assert issue.category == "test_category"
    assert issue.message == "Test message"
    assert issue.file_path == "test.py"
    assert issue.line_number == 10
    assert issue.suggestion == "Fix it"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
