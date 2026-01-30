"""
CI Models

Data models for CI/CD integration and PR annotations.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class CIDecision(Enum):
    """CI pipeline decision"""
    FAIL = "FAIL"               # Fail the pipeline
    WARN = "WARN"               # Annotate but don't fail
    PASS = "PASS"               # Continue without action


@dataclass
class CodeReference:
    """Reference to code location"""
    file: str
    line: Optional[int] = None
    column: Optional[int] = None
    
    def to_github_format(self) -> str:
        """Format for GitHub annotations"""
        if self.line:
            return f"{self.file}:{self.line}"
        return self.file
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'file': self.file,
            'line': self.line,
            'column': self.column
        }


@dataclass
class CIOutput:
    """
    Structured output for CI/CD consumption.
    
    This is the primary output format for execution intelligence in CI.
    """
    
    test_name: str                      # Test name (also aliased as 'test')
    failure_type: str                   # PRODUCT_DEFECT, AUTOMATION_DEFECT, etc.
    confidence: float                   # Confidence score (0.0-1.0)
    nature: str                         # FLAKY or DETERMINISTIC
    summary: str                        # One-line summary
    
    # Optional fields
    code_reference: Optional[CodeReference] = None
    error_message: Optional[str] = None
    stacktrace: Optional[str] = None
    recommendation: Optional[str] = None
    
    # CI decision
    ci_decision: CIDecision = CIDecision.WARN
    
    # Metadata
    metadata: Dict = field(default_factory=dict)
    
    @property
    def test(self) -> str:
        """Alias for test_name for backward compatibility"""
        return self.test_name
    
    @property
    def confidence_percent(self) -> str:
        """Get confidence as percentage string"""
        return f"{self.confidence * 100:.0f}%"
    
    def to_json(self) -> str:
        """Convert to JSON string for CI consumption"""
        import json
        data = {
            'test': self.test_name,
            'failure_type': self.failure_type,
            'confidence': self.confidence,
            'confidence_percent': self.confidence_percent,
            'nature': self.nature,
            'summary': self.summary,
            'code_reference': self.code_reference.to_dict() if self.code_reference else None,
            'error_message': self.error_message,
            'stacktrace': self.stacktrace,
            'recommendation': self.recommendation,
            'ci_decision': self.ci_decision.value,
            'metadata': self.metadata
        }
    
    def to_markdown(self) -> str:
        """Convert to Markdown for PR comments"""
        lines = [
            f"## ❌ Test Failure: `{self.test}`",
            "",
            f"**Type:** {self.failure_type}  ",
            f"**Confidence:** {self.confidence * 100:.0f}%  ",
            f"**Nature:** {self.nature}",
            "",
            f"**Summary:** {self.summary}",
        ]
        
        if self.code_reference:
            lines.append("")
            lines.append(f"**Location:** {self.code_reference.to_github_format()}")
        
        if self.error_message:
            lines.append("")
            lines.append("**Error:**")
            lines.append(f"```\n{self.error_message[:500]}\n```")
        
        if self.recommendation:
            lines.append("")
            lines.append(f"**Recommendation:** {self.recommendation}")
        
        return "\n".join(lines)
    
    def get_emoji(self) -> str:
        """Get emoji for failure type"""
        emoji_map = {
            'PRODUCT_DEFECT': '🐛',
            'AUTOMATION_DEFECT': '🔧',
            'ENVIRONMENT_ISSUE': '⚙️',
            'CONFIGURATION_ISSUE': '⚠️'
        }
        return emoji_map.get(self.failure_type, '❌')


@dataclass
class PRAnnotation:
    """
    Pull Request annotation.
    
    Platform-agnostic representation of a PR comment.
    """
    
    title: str
    body: str
    level: str = "warning"          # "warning", "error", "notice"
    file: Optional[str] = None
    line: Optional[int] = None
    
    def to_github_format(self) -> str:
        """Format for GitHub PR comment"""
        return self.body
    
    def to_bitbucket_format(self) -> Dict:
        """Format for Bitbucket PR comment"""
        return {
            'content': {
                'raw': self.body
            }
        }
    
    def to_gitlab_format(self) -> Dict:
        """Format for GitLab MR comment"""
        comment = {
            'body': self.body
        }
        if self.file and self.line:
            comment['position'] = {
                'new_path': self.file,
                'new_line': self.line
            }
        return comment


@dataclass
class CIConfig:
    """
    Configuration for CI behavior.
    
    Controls how execution intelligence integrates with CI/CD.
    """
    
    fail_on_product_defect: bool = True          # Fail CI on high-confidence product defects
    fail_on_automation_defect: bool = False      # Don't fail CI on automation defects
    fail_on_flaky: bool = False                  # Don't fail CI on flaky tests
    
    annotate_automation_defects: bool = True     # Annotate automation defects in PR
    annotate_flaky_tests: bool = True            # Annotate flaky tests
    
    min_confidence_to_fail: float = 0.85         # Minimum confidence to fail CI
    min_confidence_to_annotate: float = 0.65     # Minimum confidence to annotate
    
    def should_fail_ci(self, failure_type: str, confidence: float, nature: str) -> bool:
        """
        Determine if CI should fail.
        
        Args:
            failure_type: Type of failure
            confidence: Confidence score
            nature: FLAKY or DETERMINISTIC
            
        Returns:
            True if CI should fail
        """
        # Never fail on flaky tests
        if nature == "FLAKY" and not self.fail_on_flaky:
            return False
        
        # Check confidence threshold
        if confidence < self.min_confidence_to_fail:
            return False
        
        # Check failure type rules
        if failure_type == "PRODUCT_DEFECT" and self.fail_on_product_defect:
            return True
        
        if failure_type == "AUTOMATION_DEFECT" and self.fail_on_automation_defect:
            return True
        
        return False
    
    def should_annotate(self, failure_type: str, confidence: float) -> bool:
        """
        Determine if PR should be annotated.
        
        Args:
            failure_type: Type of failure
            confidence: Confidence score
            
        Returns:
            True if PR should be annotated
        """
        if confidence < self.min_confidence_to_annotate:
            return False
        
        if failure_type == "AUTOMATION_DEFECT" and not self.annotate_automation_defects:
            return False
        
        return True
