"""
Migration Validation Module

Validates generated code for correctness, completeness, and quality.
Performs syntax validation, semantic checks, and best practices verification.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"      # Blocks migration
    WARNING = "warning"  # Should be fixed
    INFO = "info"        # Nice to have


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    level: ValidationLevel
    category: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report"""
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    
    def add_issue(self, issue: ValidationIssue):
        """Add an issue to the report"""
        self.issues.append(issue)
        
    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues"""
        return [i for i in self.issues if i.level == ValidationLevel.ERROR]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues"""
        return [i for i in self.issues if i.level == ValidationLevel.WARNING]
    
    def compute_summary(self):
        """Compute issue summary statistics"""
        self.summary = {
            "total": len(self.issues),
            "errors": len(self.get_errors()),
            "warnings": len(self.get_warnings()),
            "info": len([i for i in self.issues if i.level == ValidationLevel.INFO])
        }
        self.passed = self.summary["errors"] == 0


class PythonCodeValidator:
    """
    Validates Python code for syntax and quality.
    
    Used for pytest-bdd generated code validation.
    """
    
    def __init__(self):
        self.report = ValidationReport(passed=True)
    
    def validate_file(self, file_path: Path) -> ValidationReport:
        """Validate a Python file"""
        self.report = ValidationReport(passed=True)
        
        if not file_path.exists():
            self.report.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="file_not_found",
                message=f"File not found: {file_path}",
                file_path=str(file_path)
            ))
            self.report.compute_summary()
            return self.report
        
        content = file_path.read_text(encoding="utf-8")
        
        # Syntax validation
        self._validate_syntax(content, file_path)
        
        # Import validation
        self._validate_imports(content, file_path)
        
        # Best practices
        self._validate_best_practices(content, file_path)
        
        self.report.compute_summary()
        return self.report
    
    def _validate_syntax(self, content: str, file_path: Path):
        """Validate Python syntax"""
        try:
            ast.parse(content)
        except SyntaxError as e:
            self.report.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="syntax_error",
                message=f"Syntax error: {e.msg}",
                file_path=str(file_path),
                line_number=e.lineno,
                suggestion="Fix syntax error before proceeding"
            ))
    
    def _validate_imports(self, content: str, file_path: Path):
        """Validate required imports are present"""
        required_imports = {
            "page_objects": ["playwright.sync_api"],
            "step_definitions": ["pytest_bdd"],
            "conftest": ["pytest", "playwright.sync_api"]
        }
        
        # Determine file type
        file_type = None
        if "page_objects" in str(file_path):
            file_type = "page_objects"
        elif "step_definitions" in str(file_path):
            file_type = "step_definitions"
        elif file_path.name == "conftest.py":
            file_type = "conftest"
        
        if file_type and file_type in required_imports:
            for required_import in required_imports[file_type]:
                if required_import not in content:
                    self.report.add_issue(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category="missing_import",
                        message=f"Missing recommended import: {required_import}",
                        file_path=str(file_path),
                        suggestion=f"Add: from {required_import} import ..."
                    ))
    
    def _validate_best_practices(self, content: str, file_path: Path):
        """Validate Python best practices"""
        lines = content.split('\n')
        
        # Check for TODO comments
        for i, line in enumerate(lines, 1):
            if "TODO" in line:
                self.report.add_issue(ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="todo_found",
                    message="TODO comment requires manual implementation",
                    file_path=str(file_path),
                    line_number=i,
                    suggestion="Implement the TODO or remove if complete"
                ))
        
        # Check for docstrings in classes
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if not ast.get_docstring(node):
                        self.report.add_issue(ValidationIssue(
                            level=ValidationLevel.INFO,
                            category="missing_docstring",
                            message=f"Class {node.name} missing docstring",
                            file_path=str(file_path),
                            line_number=node.lineno,
                            suggestion="Add docstring for better documentation"
                        ))
        except SyntaxError:
            pass  # Already caught in syntax validation


class RobotCodeValidator:
    """
    Validates Robot Framework code.
    
    Used for Robot Framework generated code validation.
    """
    
    def __init__(self):
        self.report = ValidationReport(passed=True)
    
    def validate_file(self, file_path: Path) -> ValidationReport:
        """Validate a Robot Framework file"""
        self.report = ValidationReport(passed=True)
        
        if not file_path.exists():
            self.report.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="file_not_found",
                message=f"File not found: {file_path}",
                file_path=str(file_path)
            ))
            self.report.compute_summary()
            return self.report
        
        content = file_path.read_text(encoding="utf-8")
        
        # Structure validation
        self._validate_structure(content, file_path)
        
        # Section validation
        self._validate_sections(content, file_path)
        
        # Keyword validation
        self._validate_keywords(content, file_path)
        
        self.report.compute_summary()
        return self.report
    
    def _validate_structure(self, content: str, file_path: Path):
        """Validate Robot Framework file structure"""
        required_sections = ["*** Settings ***"]
        
        for section in required_sections:
            if section not in content:
                self.report.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category="missing_section",
                    message=f"Missing section: {section}",
                    file_path=str(file_path),
                    suggestion=f"Add {section} section"
                ))
    
    def _validate_sections(self, content: str, file_path: Path):
        """Validate sections are properly formatted"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for section markers
            if line.strip().startswith("***") and line.strip().endswith("***"):
                # Valid section marker
                continue
            
            # Check for malformed sections
            if line.strip().startswith("***") and not line.strip().endswith("***"):
                self.report.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="malformed_section",
                    message="Section marker not properly closed",
                    file_path=str(file_path),
                    line_number=i,
                    suggestion="Ensure section name ends with ***"
                ))
    
    def _validate_keywords(self, content: str, file_path: Path):
        """Validate keyword definitions"""
        lines = content.split('\n')
        in_keywords_section = False
        
        for i, line in enumerate(lines, 1):
            if "*** Keywords ***" in line:
                in_keywords_section = True
                continue
            
            if in_keywords_section and line.strip().startswith("***"):
                in_keywords_section = False
            
            # Check for TODO in keywords
            if in_keywords_section and "TODO" in line:
                self.report.add_issue(ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="todo_found",
                    message="TODO comment in keyword requires implementation",
                    file_path=str(file_path),
                    line_number=i,
                    suggestion="Implement the keyword or remove TODO"
                ))


class MigrationValidator:
    """
    High-level migration validation orchestrator.
    
    Validates complete migration output across all generated files.
    """
    
    def __init__(self):
        self.python_validator = PythonCodeValidator()
        self.robot_validator = RobotCodeValidator()
    
    def validate_pytest_migration(self, output_dir: Path) -> ValidationReport:
        """
        Validate pytest-bdd migration output.
        
        Args:
            output_dir: Directory containing generated pytest-bdd code
            
        Returns:
            ValidationReport with all issues found
        """
        combined_report = ValidationReport(passed=True)
        
        # Validate Page Objects
        po_dir = output_dir / "page_objects"
        if po_dir.exists():
            for py_file in po_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    report = self.python_validator.validate_file(py_file)
                    combined_report.issues.extend(report.issues)
        else:
            combined_report.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="missing_directory",
                message="page_objects directory not found",
                suggestion="Ensure migration completed successfully"
            ))
        
        # Validate Step Definitions
        step_dir = output_dir / "step_definitions"
        if step_dir.exists():
            for py_file in step_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    report = self.python_validator.validate_file(py_file)
                    combined_report.issues.extend(report.issues)
        else:
            combined_report.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="missing_directory",
                message="step_definitions directory not found",
                suggestion="Ensure migration completed successfully"
            ))
        
        # Validate conftest
        conftest = output_dir / "conftest.py"
        if conftest.exists():
            report = self.python_validator.validate_file(conftest)
            combined_report.issues.extend(report.issues)
        else:
            combined_report.add_issue(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="missing_file",
                message="conftest.py not found",
                suggestion="Add conftest.py with fixtures"
            ))
        
        combined_report.compute_summary()
        return combined_report
    
    def validate_robot_migration(self, output_dir: Path) -> ValidationReport:
        """
        Validate Robot Framework migration output.
        
        Args:
            output_dir: Directory containing generated Robot Framework code
            
        Returns:
            ValidationReport with all issues found
        """
        combined_report = ValidationReport(passed=True)
        
        # Validate Resources
        resources_dir = output_dir / "resources"
        if resources_dir.exists():
            for robot_file in resources_dir.glob("*.robot"):
                report = self.robot_validator.validate_file(robot_file)
                combined_report.issues.extend(report.issues)
        else:
            combined_report.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="missing_directory",
                message="resources directory not found",
                suggestion="Ensure migration completed successfully"
            ))
        
        # Validate Tests
        tests_dir = output_dir / "tests"
        if tests_dir.exists():
            for robot_file in tests_dir.glob("*.robot"):
                report = self.robot_validator.validate_file(robot_file)
                combined_report.issues.extend(report.issues)
        else:
            combined_report.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="missing_directory",
                message="tests directory not found",
                suggestion="Ensure migration completed successfully"
            ))
        
        combined_report.compute_summary()
        return combined_report
    
    def print_report(self, report: ValidationReport, verbose: bool = True):
        """Print validation report to console"""
        print("\n" + "=" * 70)
        print("MIGRATION VALIDATION REPORT")
        print("=" * 70)
        
        if report.passed:
            print("✅ Status: PASSED")
        else:
            print("❌ Status: FAILED")
        
        print(f"\nSummary:")
        print(f"  Total Issues: {report.summary.get('total', 0)}")
        print(f"  Errors: {report.summary.get('errors', 0)}")
        print(f"  Warnings: {report.summary.get('warnings', 0)}")
        print(f"  Info: {report.summary.get('info', 0)}")
        
        if verbose and report.issues:
            print("\nIssues:")
            for issue in report.issues:
                icon = "❌" if issue.level == ValidationLevel.ERROR else "⚠️" if issue.level == ValidationLevel.WARNING else "ℹ️"
                print(f"\n{icon} [{issue.level.value.upper()}] {issue.category}")
                print(f"   {issue.message}")
                if issue.file_path:
                    location = issue.file_path
                    if issue.line_number:
                        location += f":{issue.line_number}"
                    print(f"   Location: {location}")
                if issue.suggestion:
                    print(f"   Suggestion: {issue.suggestion}")
        
        print("\n" + "=" * 70)
