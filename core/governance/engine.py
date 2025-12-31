"""
Policy engine for executing and enforcing policies.

Evaluates policies against context data and reports violations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from .policy import Policy, PolicyRule, PolicySeverity


class ViolationStatus(Enum):
    """Status of a policy violation."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"


@dataclass
class PolicyViolation:
    """
    Represents a violation of a policy rule.
    
    Attributes:
        policy_id: ID of the violated policy
        rule_id: ID of the violated rule
        rule_name: Name of the violated rule
        description: Description of what was violated
        severity: Severity of the violation
        context: Context data when violation occurred
        timestamp: When the violation occurred
        status: Current status of the violation
        remediation: Suggested remediation steps
    """
    policy_id: str
    rule_id: str
    rule_name: str
    description: str
    severity: PolicySeverity
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    status: ViolationStatus = ViolationStatus.OPEN
    remediation: Optional[str] = None
    
    def acknowledge(self) -> None:
        """Mark violation as acknowledged."""
        self.status = ViolationStatus.ACKNOWLEDGED
    
    def resolve(self) -> None:
        """Mark violation as resolved."""
        self.status = ViolationStatus.RESOLVED
    
    def ignore(self) -> None:
        """Mark violation as ignored."""
        self.status = ViolationStatus.IGNORED


@dataclass
class PolicyResult:
    """
    Result of policy evaluation.
    
    Attributes:
        policy: The evaluated policy
        compliant: Whether the policy is fully compliant
        violations: List of violations found
        checked_rules: Number of rules checked
        passed_rules: Number of rules passed
        timestamp: When the evaluation occurred
        context: Context data used for evaluation
    """
    policy: Policy
    compliant: bool
    violations: List[PolicyViolation] = field(default_factory=list)
    checked_rules: int = 0
    passed_rules: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def failed_rules(self) -> int:
        """Number of rules that failed."""
        return self.checked_rules - self.passed_rules
    
    @property
    def compliance_rate(self) -> float:
        """Compliance rate as percentage."""
        if self.checked_rules == 0:
            return 100.0
        return (self.passed_rules / self.checked_rules) * 100
    
    def get_violations_by_severity(self, severity: PolicySeverity) -> List[PolicyViolation]:
        """Get violations filtered by severity."""
        return [v for v in self.violations if v.severity == severity]
    
    def get_critical_violations(self) -> List[PolicyViolation]:
        """Get critical violations."""
        return self.get_violations_by_severity(PolicySeverity.CRITICAL)
    
    def get_error_violations(self) -> List[PolicyViolation]:
        """Get error violations."""
        return self.get_violations_by_severity(PolicySeverity.ERROR)


class PolicyEngine:
    """
    Engine for evaluating and enforcing policies.
    
    Attributes:
        policies: Registered policies
        strict_mode: If True, critical violations block execution
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize policy engine.
        
        Args:
            strict_mode: Whether to enforce strict compliance
        """
        self.policies: Dict[str, Policy] = {}
        self.strict_mode = strict_mode
        self._evaluation_history: List[PolicyResult] = []
    
    def register_policy(self, policy: Policy) -> None:
        """
        Register a policy with the engine.
        
        Args:
            policy: Policy to register
        """
        self.policies[policy.id] = policy
    
    def unregister_policy(self, policy_id: str) -> bool:
        """
        Unregister a policy.
        
        Args:
            policy_id: ID of policy to unregister
            
        Returns:
            True if unregistered, False if not found
        """
        if policy_id in self.policies:
            del self.policies[policy_id]
            return True
        return False
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self.policies.get(policy_id)
    
    def evaluate_policy(self, policy: Policy, context: Dict[str, Any]) -> PolicyResult:
        """
        Evaluate a single policy against context.
        
        Args:
            policy: Policy to evaluate
            context: Context data to check against
            
        Returns:
            PolicyResult with evaluation results
        """
        if not policy.enabled:
            return PolicyResult(
                policy=policy,
                compliant=True,
                context=context
            )
        
        violations = []
        checked_rules = 0
        passed_rules = 0
        
        for rule in policy.get_enabled_rules():
            checked_rules += 1
            
            try:
                is_compliant = rule.check(context)
                
                if is_compliant:
                    passed_rules += 1
                else:
                    violation = PolicyViolation(
                        policy_id=policy.id,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        description=rule.description,
                        severity=rule.severity,
                        context=context.copy(),
                        remediation=rule.metadata.get('remediation')
                    )
                    violations.append(violation)
                    
            except Exception as e:
                # Rule execution failure is treated as violation
                violation = PolicyViolation(
                    policy_id=policy.id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    description=f"Rule check failed: {str(e)}",
                    severity=PolicySeverity.ERROR,
                    context=context.copy()
                )
                violations.append(violation)
        
        result = PolicyResult(
            policy=policy,
            compliant=len(violations) == 0,
            violations=violations,
            checked_rules=checked_rules,
            passed_rules=passed_rules,
            context=context
        )
        
        self._evaluation_history.append(result)
        return result
    
    def evaluate_all(self, context: Dict[str, Any]) -> List[PolicyResult]:
        """
        Evaluate all registered policies.
        
        Args:
            context: Context data to check against
            
        Returns:
            List of policy results
        """
        results = []
        for policy in self.policies.values():
            result = self.evaluate_policy(policy, context)
            results.append(result)
        
        return results
    
    def enforce_policies(self, context: Dict[str, Any]) -> bool:
        """
        Enforce all policies and return whether execution should proceed.
        
        Args:
            context: Context data to check against
            
        Returns:
            True if execution can proceed, False if blocked
        """
        results = self.evaluate_all(context)
        
        if self.strict_mode:
            # Block execution if any critical violations
            for result in results:
                if result.get_critical_violations():
                    return False
        
        return True
    
    def get_all_violations(self) -> List[PolicyViolation]:
        """Get all violations from evaluation history."""
        violations = []
        for result in self._evaluation_history:
            violations.extend(result.violations)
        return violations
    
    def get_open_violations(self) -> List[PolicyViolation]:
        """Get all open violations."""
        return [v for v in self.get_all_violations() if v.status == ViolationStatus.OPEN]
    
    def clear_history(self) -> None:
        """Clear evaluation history."""
        self._evaluation_history.clear()
