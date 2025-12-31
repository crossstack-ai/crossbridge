"""
Policy definition framework.

Defines the structure and types of policies that can be enforced.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime


class PolicySeverity(Enum):
    """Severity levels for policy violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PolicyCategory(Enum):
    """Categories of policies."""
    TESTING = "testing"
    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    COMPLIANCE = "compliance"


@dataclass
class PolicyRule:
    """
    A single rule within a policy.
    
    Attributes:
        id: Unique identifier for the rule
        name: Human-readable name
        description: Detailed description of what the rule checks
        severity: Severity level if violated
        check_function: Function that performs the check
        enabled: Whether the rule is active
        metadata: Additional rule metadata
    """
    id: str
    name: str
    description: str
    severity: PolicySeverity
    check_function: Callable[[Any], bool]
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def check(self, context: Any) -> bool:
        """
        Execute the rule check.
        
        Args:
            context: Context data to check against
            
        Returns:
            True if compliant, False if violated
        """
        if not self.enabled:
            return True
        
        try:
            return self.check_function(context)
        except Exception as e:
            # Rule execution failure is treated as violation
            return False


@dataclass
class Policy:
    """
    A policy consisting of multiple rules.
    
    Attributes:
        id: Unique identifier for the policy
        name: Human-readable name
        description: Detailed description
        category: Policy category
        rules: List of rules in this policy
        enabled: Whether the policy is active
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Additional policy metadata
    """
    id: str
    name: str
    description: str
    category: PolicyCategory
    rules: List[PolicyRule] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_rule(self, rule: PolicyRule) -> None:
        """Add a rule to this policy."""
        self.rules.append(rule)
        self.updated_at = datetime.now()
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule from this policy.
        
        Args:
            rule_id: ID of rule to remove
            
        Returns:
            True if removed, False if not found
        """
        initial_len = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        if len(self.rules) < initial_len:
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Get a specific rule by ID."""
        return next((r for r in self.rules if r.id == rule_id), None)
    
    def get_enabled_rules(self) -> List[PolicyRule]:
        """Get all enabled rules."""
        return [r for r in self.rules if r.enabled]


# Predefined policy templates
def create_test_coverage_policy() -> Policy:
    """Create a policy for test coverage requirements."""
    policy = Policy(
        id="test-coverage",
        name="Test Coverage Policy",
        description="Ensures adequate test coverage across the codebase",
        category=PolicyCategory.TESTING,
    )
    
    policy.add_rule(PolicyRule(
        id="min-coverage",
        name="Minimum Coverage Threshold",
        description="Test coverage must be at least 80%",
        severity=PolicySeverity.ERROR,
        check_function=lambda ctx: ctx.get('coverage', 0) >= 80,
        metadata={'threshold': 80}
    ))
    
    policy.add_rule(PolicyRule(
        id="no-untested-critical",
        name="Critical Paths Must Be Tested",
        description="All critical code paths must have tests",
        severity=PolicySeverity.CRITICAL,
        check_function=lambda ctx: not ctx.get('untested_critical_paths', []),
    ))
    
    return policy


def create_test_quality_policy() -> Policy:
    """Create a policy for test quality standards."""
    policy = Policy(
        id="test-quality",
        name="Test Quality Policy",
        description="Ensures tests meet quality standards",
        category=PolicyCategory.QUALITY,
    )
    
    policy.add_rule(PolicyRule(
        id="no-flaky-tests",
        name="No Flaky Tests",
        description="Tests must not be flaky (pass rate < 95%)",
        severity=PolicySeverity.WARNING,
        check_function=lambda ctx: ctx.get('flaky_tests', []) == [],
    ))
    
    policy.add_rule(PolicyRule(
        id="test-execution-time",
        name="Test Execution Time Limit",
        description="Tests should complete within reasonable time",
        severity=PolicySeverity.WARNING,
        check_function=lambda ctx: ctx.get('avg_execution_time', 0) <= 300,
        metadata={'max_time_seconds': 300}
    ))
    
    policy.add_rule(PolicyRule(
        id="test-assertions",
        name="Tests Must Have Assertions",
        description="All tests must contain at least one assertion",
        severity=PolicySeverity.ERROR,
        check_function=lambda ctx: not ctx.get('tests_without_assertions', []),
    ))
    
    return policy


def create_security_policy() -> Policy:
    """Create a policy for security requirements."""
    policy = Policy(
        id="security",
        name="Security Policy",
        description="Ensures security best practices are followed",
        category=PolicyCategory.SECURITY,
    )
    
    policy.add_rule(PolicyRule(
        id="no-hardcoded-secrets",
        name="No Hardcoded Secrets",
        description="Test code must not contain hardcoded credentials or secrets",
        severity=PolicySeverity.CRITICAL,
        check_function=lambda ctx: not ctx.get('hardcoded_secrets', []),
    ))
    
    policy.add_rule(PolicyRule(
        id="secure-data-handling",
        name="Secure Test Data Handling",
        description="Sensitive test data must be encrypted or masked",
        severity=PolicySeverity.ERROR,
        check_function=lambda ctx: ctx.get('unprotected_sensitive_data', []) == [],
    ))
    
    return policy


def create_documentation_policy() -> Policy:
    """Create a policy for documentation requirements."""
    policy = Policy(
        id="documentation",
        name="Documentation Policy",
        description="Ensures adequate documentation",
        category=PolicyCategory.DOCUMENTATION,
    )
    
    policy.add_rule(PolicyRule(
        id="test-descriptions",
        name="Tests Must Have Descriptions",
        description="All tests must have meaningful descriptions or docstrings",
        severity=PolicySeverity.WARNING,
        check_function=lambda ctx: not ctx.get('tests_without_descriptions', []),
    ))
    
    policy.add_rule(PolicyRule(
        id="readme-exists",
        name="README Must Exist",
        description="Test suites must have README documentation",
        severity=PolicySeverity.INFO,
        check_function=lambda ctx: ctx.get('has_readme', False),
    ))
    
    return policy
