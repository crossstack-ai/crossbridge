"""
AI Transformation Validation Framework

Provides robust validation, quality checks, and feedback loops for AI-generated
transformations. Ensures production-grade quality and reliability for
AI transformation maturity.

Key Features:
- Confidence scoring with detailed metrics
- Automated quality checks (syntax, imports, locators)
- Human-in-the-loop review integration
- Rollback and diff reporting
- Audit trails for all transformations
- Performance and cost tracking
"""

import ast
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from core.ai.confidence_scoring import (
    ConfidenceMetrics,
    ConfidenceLevel,
    TransformationStatus,
    ConfidenceScorer,
)
from core.logging import get_logger, LogCategory
from core.runtime.retry import retry_with_backoff, RetryPolicy, RetryableError

logger = get_logger(__name__, category=LogCategory.AI)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"  # Blocks deployment
    ERROR = "error"  # Requires fix
    WARNING = "warning"  # Should review
    INFO = "info"  # Informational


@dataclass
class ValidationIssue:
    """Represents a validation issue found in transformed code."""
    severity: ValidationSeverity
    category: str  # e.g., "syntax", "import", "locator", "semantic"
    message: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    """Complete validation results for a transformation."""
    transformation_id: str
    source_file: str
    target_file: str
    confidence: ConfidenceMetrics
    issues: List[ValidationIssue] = field(default_factory=list)
    syntax_valid: bool = True
    imports_resolved: bool = True
    locators_quality_score: float = 0.0
    passed: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def critical_issues(self) -> List[ValidationIssue]:
        """Get critical issues that block deployment."""
        return [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]

    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are any blocking issues."""
        return len(self.critical_issues) > 0 or not self.syntax_valid

    @property
    def quality_score(self) -> float:
        """
        Calculate overall quality score (0.0 to 1.0).
        
        Combines confidence, syntax validity, import resolution, and issue count.
        """
        base_score = self.confidence.overall_score * 0.5
        
        # Penalty for syntax/import issues
        if not self.syntax_valid:
            base_score *= 0.3
        if not self.imports_resolved:
            base_score *= 0.7
        
        # Penalty for issues
        issue_penalty = len(self.critical_issues) * 0.1 + len(self.issues) * 0.02
        base_score = max(0.0, base_score - issue_penalty)
        
        # Bonus for high locator quality
        base_score += self.locators_quality_score * 0.2
        
        return min(1.0, base_score)


class TransformationValidator:
    """
    Comprehensive validator for AI-generated transformations.
    
    Performs multiple validation passes:
    1. Syntax validation
    2. Import resolution
    3. Locator quality checks
    4. Semantic preservation checks
    5. Framework idiom validation
    """

    def __init__(
        self,
        target_framework: str = "robot",
        strict_mode: bool = False,
        auto_fix_enabled: bool = True,
    ):
        """
        Initialize validator.
        
        Args:
            target_framework: Target framework for transformation
            strict_mode: Enable strict validation (fail on warnings)
            auto_fix_enabled: Attempt automatic fixes for simple issues
        """
        self.target_framework = target_framework
        self.strict_mode = strict_mode
        self.auto_fix_enabled = auto_fix_enabled
        self.scorer = ConfidenceScorer()
        
        logger.info(
            f"Initialized TransformationValidator for {target_framework}, "
            f"strict={strict_mode}, auto_fix={auto_fix_enabled}"
        )

    def validate(
        self,
        source_content: str,
        transformed_content: str,
        source_file: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Perform comprehensive validation of a transformation.
        
        Args:
            source_content: Original source code
            transformed_content: AI-generated transformed code
            source_file: Path to source file
            metadata: Additional metadata (cost, tokens, model, etc.)
        
        Returns:
            ValidationResult with all checks and confidence scoring
            
        Raises:
            ValueError: If input validation fails
        """
        transformation_id = str(uuid.uuid4())
        
        # Input validation
        if not source_content or not transformed_content:
            logger.error("Validation failed: empty content provided", extra={
                "source_file": source_file,
                "has_source": bool(source_content),
                "has_transformed": bool(transformed_content)
            })
            raise ValueError("Both source_content and transformed_content must be non-empty")
        
        if not source_file:
            logger.error("Validation failed: no source file specified")
            raise ValueError("source_file must be specified")
        
        logger.info(f"Validating transformation {transformation_id} for {source_file}", extra={
            "transformation_id": transformation_id,
            "source_file": source_file,
            "source_length": len(source_content),
            "target_length": len(transformed_content),
            "target_framework": self.target_framework,
            "metadata": metadata
        })
        
        issues: List[ValidationIssue] = []
        
        # 1. Syntax validation
        syntax_valid, syntax_issues = self._validate_syntax(transformed_content)
        issues.extend(syntax_issues)
        
        # 2. Import resolution
        imports_valid, import_issues = self._validate_imports(transformed_content)
        issues.extend(import_issues)
        
        # 3. Locator quality (for UI test transformations)
        locator_score, locator_issues = self._validate_locators(transformed_content)
        issues.extend(locator_issues)
        
        # 4. Semantic preservation check
        semantic_issues = self._validate_semantics(source_content, transformed_content)
        issues.extend(semantic_issues)
        
        # 5. Framework idiom validation
        idiom_issues = self._validate_framework_idioms(transformed_content)
        issues.extend(idiom_issues)
        
        # Calculate confidence using scorer's actual method
        confidence = self.scorer.score_transformation(
            source_code=source_content,
            target_code=transformed_content,
            source_framework=metadata.get('source_framework', 'unknown') if metadata else 'unknown',
            target_framework=self.target_framework,
            ai_raw_confidence=metadata.get('ai_confidence') if metadata else None,
        )
        
        # Create result
        result = ValidationResult(
            transformation_id=transformation_id,
            source_file=source_file,
            target_file=source_file.replace(".java", ".robot").replace(".py", ".robot"),
            confidence=confidence,
            issues=issues,
            syntax_valid=syntax_valid,
            imports_resolved=imports_valid,
            locators_quality_score=locator_score,
            metadata=metadata or {},
        )
        
        # Determine pass/fail
        result.passed = self._determine_pass_status(result)
        
        logger.info(
            f"Validation complete: {transformation_id}, "
            f"passed={result.passed}, quality={result.quality_score:.2f}, "
            f"issues={len(issues)}"
        )
        
        return result

    def _validate_syntax(
        self, content: str
    ) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate syntax of transformed code.
        
        For Python/Robot: AST parsing
        For other formats: Basic structure checks
        """
        issues = []
        
        if self.target_framework in ["pytest", "python", "playwright"]:
            try:
                ast.parse(content)
                return True, []
            except SyntaxError as e:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="syntax",
                        message=f"Python syntax error: {e.msg}",
                        line_number=e.lineno,
                        column=e.offset,
                    )
                )
                return False, issues
        
        elif self.target_framework == "robot":
            # Robot Framework basic validation
            if not content.strip():
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="syntax",
                        message="Empty Robot Framework file",
                    )
                )
                return False, issues
            
            # Check for required sections
            required_sections = ["*** Test Cases ***", "*** Keywords ***"]
            has_test_content = any(section in content for section in required_sections)
            
            if not has_test_content:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="syntax",
                        message="No test cases or keywords sections found",
                    )
                )
                return False, issues
        
        return True, issues

    def _validate_imports(
        self, content: str
    ) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate that all imports are resolvable and correct.
        """
        issues = []
        
        if self.target_framework in ["pytest", "python", "playwright"]:
            # Extract import statements
            try:
                tree = ast.parse(content)
                imports = [
                    node for node in ast.walk(tree)
                    if isinstance(node, (ast.Import, ast.ImportFrom))
                ]
                
                # Check for undefined imports
                for imp in imports:
                    if isinstance(imp, ast.ImportFrom):
                        if imp.module and "PLACEHOLDER" in imp.module:
                            issues.append(
                                ValidationIssue(
                                    severity=ValidationSeverity.ERROR,
                                    category="import",
                                    message=f"Placeholder import found: {imp.module}",
                                    line_number=imp.lineno,
                                    auto_fixable=True,
                                )
                            )
            except:
                pass  # Already handled in syntax validation
        
        elif self.target_framework == "robot":
            # Check Robot Framework library imports
            library_pattern = r"Library\s+(\S+)"
            libraries = re.findall(library_pattern, content)
            
            for lib in libraries:
                if "PLACEHOLDER" in lib or "TODO" in lib:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="import",
                            message=f"Placeholder library import: {lib}",
                            auto_fixable=True,
                        )
                    )
        
        return len(issues) == 0, issues

    def _validate_locators(
        self, content: str
    ) -> Tuple[float, List[ValidationIssue]]:
        """
        Validate locator quality and best practices.
        
        Returns quality score (0.0 to 1.0) and issues.
        """
        issues = []
        score = 1.0
        
        # Extract locators (simplified)
        xpath_locators = re.findall(r"xpath[=:](.+?)[\s\)]", content, re.IGNORECASE)
        css_locators = re.findall(r"css[=:](.+?)[\s\)]", content, re.IGNORECASE)
        id_locators = re.findall(r"id[=:](.+?)[\s\)]", content, re.IGNORECASE)
        
        # Also check for find_element_by_xpath patterns
        xpath_method_patterns = re.findall(r"find_element(?:_by_xpath|\(.*?By\.xpath).*?[\"'](.*?)[\"']", content, re.IGNORECASE)
        xpath_locators.extend(xpath_method_patterns)
        
        total_locators = len(xpath_locators) + len(css_locators) + len(id_locators)
        
        if total_locators == 0:
            return 1.0, []  # No locators to validate
        
        # Check for brittle XPath - enhanced patterns
        brittle_xpath_count = 0
        for xpath in xpath_locators:
            # Detect brittle patterns: absolute paths, positional selectors, contains with complex expressions
            if re.search(r"/html/body|//*\[contains|//*\[\d+\]|\[\d+\]/|/div\[\d+\]|/body/div", xpath):
                brittle_xpath_count += 1
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="locator",
                        message=f"Brittle XPath detected: {xpath[:50]}...",
                        suggestion="Use data-testid or id attributes instead",
                    )
                )
        
        # Penalty for brittle locators
        if brittle_xpath_count > 0:
            score -= (brittle_xpath_count / total_locators) * 0.5
        
        # Bonus for data-testid usage
        data_testid_count = len(re.findall(r"data-testid", content))
        if data_testid_count > 0:
            score += min(0.2, data_testid_count * 0.05)
        
        return max(0.0, min(1.0, score)), issues

    def _validate_semantics(
        self, source: str, transformed: str
    ) -> List[ValidationIssue]:
        """
        Check semantic preservation between source and transformed code.
        
        This is a simplified version - production would use more sophisticated
        analysis including:
        - Control flow comparison
        - Data flow analysis
        - Intent preservation checks
        """
        issues = []
        
        # Extract action keywords/verbs
        source_actions = set(re.findall(r"\b(click|type|get|set|find|wait|assert)\w*\b", source.lower()))
        target_actions = set(re.findall(r"\b(click|type|get|set|find|wait|should)\w*\b", transformed.lower()))
        
        # Check for missing critical actions
        missing_actions = source_actions - target_actions
        if missing_actions:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="semantic",
                    message=f"Potentially missing actions: {', '.join(missing_actions)}",
                    suggestion="Verify all source actions are represented in target",
                )
            )
        
        return issues

    def _validate_framework_idioms(self, content: str) -> List[ValidationIssue]:
        """
        Validate proper framework idiom usage.
        
        Checks for framework best practices and anti-patterns.
        """
        issues = []
        
        if self.target_framework == "robot":
            # Check for anti-patterns
            if "time.sleep" in content:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="idiom",
                        message="Using time.sleep instead of Robot Framework waits",
                        suggestion="Use 'Wait Until' keywords from SeleniumLibrary",
                        auto_fixable=True,
                    )
                )
            
            # Check for proper keyword casing
            if re.search(r"^\s*[a-z_]+\s+[a-z_]+", content, re.MULTILINE):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="idiom",
                        message="Keywords should use Title Case in Robot Framework",
                        suggestion="Convert keywords to Title Case (e.g., 'Click Button')",
                    )
                )
        
        return issues

    def _determine_pass_status(self, result: ValidationResult) -> bool:
        """
        Determine if validation passes based on configured thresholds.
        """
        # Critical failures always fail
        if result.has_blocking_issues:
            return False
        
        # In strict mode, warnings also fail
        if self.strict_mode:
            return len(result.issues) == 0
        
        # Pass if quality score meets threshold (lenient for non-strict mode)
        min_quality_threshold = 0.4
        return result.quality_score >= min_quality_threshold

    def generate_diff_report(
        self, source: str, transformed: str, result: ValidationResult
    ) -> str:
        """
        Generate a human-readable diff report for review.
        
        Returns:
            Formatted diff report with validation details
        """
        report = []
        report.append("=" * 80)
        report.append("TRANSFORMATION VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Transformation ID: {result.transformation_id}")
        report.append(f"Source File: {result.source_file}")
        report.append(f"Target File: {result.target_file}")
        report.append(f"Timestamp: {result.timestamp.isoformat()}")
        report.append(f"Status: {'PASSED' if result.passed else 'FAILED'}")
        report.append("")
        
        report.append("CONFIDENCE METRICS:")
        report.append(f"  Overall Score: {result.confidence.overall_score:.2f}")
        report.append(f"  Quality Score: {result.quality_score:.2f}")
        report.append(f"  Confidence Level: {result.confidence.confidence_level.value}")
        report.append(f"  Structural Accuracy: {result.confidence.structural_accuracy:.2f}")
        report.append(f"  Semantic Preservation: {result.confidence.semantic_preservation:.2f}")
        report.append(f"  Locator Quality: {result.locators_quality_score:.2f}")
        report.append("")
        
        if result.issues:
            report.append("VALIDATION ISSUES:")
            for i, issue in enumerate(result.issues, 1):
                report.append(f"  {i}. [{issue.severity.value.upper()}] {issue.category}")
                report.append(f"     {issue.message}")
                if issue.line_number:
                    report.append(f"     Line: {issue.line_number}")
                if issue.suggestion:
                    report.append(f"     Suggestion: {issue.suggestion}")
                if issue.auto_fixable:
                    report.append(f"     ✓ Auto-fixable")
                report.append("")
        else:
            report.append("✓ No validation issues found")
            report.append("")
        
        report.append("METADATA:")
        for key, value in result.metadata.items():
            report.append(f"  {key}: {value}")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)


class FeedbackCollector:
    """
    Collects human feedback on AI transformations for continuous improvement.
    
    This addresses the gap identified regarding AI quality feedback loops.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize feedback collector.
        
        Args:
            storage_path: Path to store feedback data (default: ./feedback)
        """
        self.storage_path = storage_path or Path("./data/feedback")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def record_feedback(
        self,
        transformation_id: str,
        approved: bool,
        reviewer: str,
        comments: Optional[str] = None,
        corrections: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record human review feedback for a transformation with resilient storage.
        
        Args:
            transformation_id: ID of the transformation
            approved: Whether transformation was approved
            reviewer: Name/ID of reviewer
            comments: Optional review comments
            corrections: Optional corrected code
        
        Returns:
            Feedback record
            
        Raises:
            ValueError: If required inputs are invalid
        """
        # Input validation
        if not transformation_id or not reviewer:
            logger.error("Invalid feedback recording request", extra={
                "has_id": bool(transformation_id),
                "has_reviewer": bool(reviewer)
            })
            raise ValueError("transformation_id and reviewer are required")
        
        feedback = {
            "transformation_id": transformation_id,
            "approved": approved,
            "reviewer": reviewer,
            "comments": comments,
            "corrections": corrections,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        logger.info(
            f"Recording feedback for {transformation_id}",
            extra={
                "transformation_id": transformation_id,
                "approved": approved,
                "reviewer": reviewer,
                "has_comments": bool(comments),
                "has_corrections": bool(corrections)
            }
        )
        
        # Store feedback with retry logic for resilience
        feedback_file = self.storage_path / f"{transformation_id}.json"
        
        def _persist_feedback():
            import json
            try:
                with open(feedback_file, "w") as f:
                    json.dump(feedback, f, indent=2)
                logger.debug(f"Feedback persisted to {feedback_file}")
            except IOError as e:
                logger.error(f"Failed to persist feedback to {feedback_file}: {e}")
                raise RetryableError(f"Feedback persistence failed: {e}") from e
        
        try:
            retry_with_backoff(
                _persist_feedback,
                RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=5.0)
            )
        except Exception as e:
            logger.error(f"Failed to persist feedback after retries: {e}", exc_info=True)
            # Don't fail the operation - return feedback even if persistence fails
            pass
        
        logger.info(
            f"Recorded feedback for {transformation_id}: "
            f"approved={approved}, reviewer={reviewer}"
        )
        
        return feedback

    def get_approval_rate(self) -> float:
        """
        Calculate overall approval rate from collected feedback.
        
        Returns:
            Approval rate (0.0 to 1.0)
        """
        import json
        
        feedbacks = []
        for feedback_file in self.storage_path.glob("*.json"):
            with open(feedback_file) as f:
                feedbacks.append(json.load(f))
        
        if not feedbacks:
            return 0.0
        
        approved_count = sum(1 for f in feedbacks if f.get("approved", False))
        return approved_count / len(feedbacks)
