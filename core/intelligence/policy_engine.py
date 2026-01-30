"""
Policy-Based Overrides for Test Intelligence.

This module provides a policy system that allows organization-level rules
to override or augment deterministic classifications based on business rules,
team conventions, and organizational requirements.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import re

from .deterministic_classifier import ClassificationLabel, DeterministicResult, SignalData

logger = logging.getLogger(__name__)


class PolicyAction(Enum):
    """Actions a policy can take."""
    OVERRIDE = "override"  # Replace classification entirely
    AUGMENT = "augment"  # Add metadata/reasons without changing label
    SKIP = "skip"  # Skip this policy (no action)
    BLOCK = "block"  # Block classification (mark as quarantined)


@dataclass
class PolicyResult:
    """Result of applying a policy."""
    action: PolicyAction
    new_label: Optional[ClassificationLabel] = None
    added_reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    policy_name: str = ""


class Policy:
    """
    Base class for classification policies.
    
    Policies can override or augment classification results based on
    organizational rules, conventions, or requirements.
    """
    
    def __init__(self, name: str, priority: int = 50):
        """
        Initialize policy.
        
        Args:
            name: Policy name
            priority: Priority (lower = higher priority, evaluated first)
        """
        self.name = name
        self.priority = priority
        self.enabled = True
    
    def evaluate(
        self,
        signal: SignalData,
        deterministic_result: DeterministicResult
    ) -> PolicyResult:
        """
        Evaluate policy against a classification.
        
        Args:
            signal: Test signal data
            deterministic_result: Deterministic classification result
            
        Returns:
            PolicyResult indicating action to take
        """
        raise NotImplementedError("Subclasses must implement evaluate()")
    
    def __repr__(self) -> str:
        return f"<Policy: {self.name} (priority={self.priority}, enabled={self.enabled})>"


class TestNamePatternPolicy(Policy):
    """Policy that overrides based on test name patterns."""
    
    def __init__(
        self,
        name: str,
        pattern: str,
        target_label: ClassificationLabel,
        reason: str,
        priority: int = 50
    ):
        """
        Initialize pattern-based policy.
        
        Args:
            name: Policy name
            pattern: Regex pattern to match test names
            target_label: Label to apply on match
            reason: Reason for override
            priority: Policy priority
        """
        super().__init__(name, priority)
        self.pattern = re.compile(pattern)
        self.target_label = target_label
        self.reason = reason
    
    def evaluate(
        self,
        signal: SignalData,
        deterministic_result: DeterministicResult
    ) -> PolicyResult:
        """Evaluate pattern policy."""
        if self.pattern.search(signal.test_name):
            logger.info(
                "Policy '%s' matched test '%s', overriding to %s",
                self.name, signal.test_name, self.target_label.value
            )
            return PolicyResult(
                action=PolicyAction.OVERRIDE,
                new_label=self.target_label,
                added_reasons=[self.reason],
                policy_name=self.name
            )
        
        return PolicyResult(action=PolicyAction.SKIP, policy_name=self.name)


class ThresholdOverridePolicy(Policy):
    """Policy that overrides based on failure rate thresholds."""
    
    def __init__(
        self,
        name: str,
        min_failure_rate: float,
        max_failure_rate: float,
        target_label: ClassificationLabel,
        reason_template: str,
        priority: int = 50
    ):
        """
        Initialize threshold override policy.
        
        Args:
            name: Policy name
            min_failure_rate: Minimum failure rate to trigger (0.0 - 1.0)
            max_failure_rate: Maximum failure rate to trigger (0.0 - 1.0)
            target_label: Label to apply
            reason_template: Reason template (can include {failure_rate})
            priority: Policy priority
        """
        super().__init__(name, priority)
        self.min_failure_rate = min_failure_rate
        self.max_failure_rate = max_failure_rate
        self.target_label = target_label
        self.reason_template = reason_template
    
    def evaluate(
        self,
        signal: SignalData,
        deterministic_result: DeterministicResult
    ) -> PolicyResult:
        """Evaluate threshold policy."""
        if self.min_failure_rate <= signal.historical_failure_rate <= self.max_failure_rate:
            reason = self.reason_template.format(
                failure_rate=f"{signal.historical_failure_rate:.1%}"
            )
            
            logger.info(
                "Policy '%s' triggered for test '%s' (failure_rate=%.1f%%), overriding to %s",
                self.name, signal.test_name, signal.historical_failure_rate * 100,
                self.target_label.value
            )
            
            return PolicyResult(
                action=PolicyAction.OVERRIDE,
                new_label=self.target_label,
                added_reasons=[reason],
                policy_name=self.name
            )
        
        return PolicyResult(action=PolicyAction.SKIP, policy_name=self.name)


class QuarantinePolicy(Policy):
    """Policy that quarantines tests based on criteria."""
    
    def __init__(
        self,
        name: str,
        consecutive_failures_threshold: int,
        reason: str = "Test quarantined due to excessive failures",
        priority: int = 10  # High priority
    ):
        """
        Initialize quarantine policy.
        
        Args:
            name: Policy name
            consecutive_failures_threshold: Threshold for quarantine
            reason: Reason for quarantine
            priority: Policy priority
        """
        super().__init__(name, priority)
        self.threshold = consecutive_failures_threshold
        self.reason = reason
    
    def evaluate(
        self,
        signal: SignalData,
        deterministic_result: DeterministicResult
    ) -> PolicyResult:
        """Evaluate quarantine policy."""
        if signal.consecutive_failures >= self.threshold:
            logger.warning(
                "Policy '%s' quarantining test '%s' (%d consecutive failures)",
                self.name, signal.test_name, signal.consecutive_failures
            )
            
            return PolicyResult(
                action=PolicyAction.BLOCK,
                added_reasons=[
                    self.reason,
                    f"Consecutive failures: {signal.consecutive_failures}"
                ],
                metadata={"quarantined": True},
                policy_name=self.name
            )
        
        return PolicyResult(action=PolicyAction.SKIP, policy_name=self.name)


class MetadataAugmentPolicy(Policy):
    """Policy that adds metadata without changing classification."""
    
    def __init__(
        self,
        name: str,
        condition: Callable[[SignalData, DeterministicResult], bool],
        metadata_fn: Callable[[SignalData, DeterministicResult], Dict[str, Any]],
        priority: int = 100  # Low priority (runs last)
    ):
        """
        Initialize metadata augment policy.
        
        Args:
            name: Policy name
            condition: Function to check if policy should apply
            metadata_fn: Function to generate metadata
            priority: Policy priority
        """
        super().__init__(name, priority)
        self.condition = condition
        self.metadata_fn = metadata_fn
    
    def evaluate(
        self,
        signal: SignalData,
        deterministic_result: DeterministicResult
    ) -> PolicyResult:
        """Evaluate metadata augment policy."""
        if self.condition(signal, deterministic_result):
            metadata = self.metadata_fn(signal, deterministic_result)
            
            logger.debug(
                "Policy '%s' augmenting test '%s' with metadata",
                self.name, signal.test_name
            )
            
            return PolicyResult(
                action=PolicyAction.AUGMENT,
                metadata=metadata,
                policy_name=self.name
            )
        
        return PolicyResult(action=PolicyAction.SKIP, policy_name=self.name)


class PolicyEngine:
    """
    Policy engine that applies policies to classification results.
    
    Policies are evaluated in priority order (lower priority number = higher priority).
    The first policy that returns OVERRIDE or BLOCK stops evaluation.
    AUGMENT policies always run (even after OVERRIDE).
    """
    
    def __init__(self):
        """Initialize policy engine."""
        self.policies: List[Policy] = []
        self.metrics = {
            "evaluations": 0,
            "overrides": 0,
            "augments": 0,
            "blocks": 0,
            "skips": 0
        }
    
    def add_policy(self, policy: Policy):
        """
        Add a policy to the engine.
        
        Args:
            policy: Policy to add
        """
        self.policies.append(policy)
        # Sort by priority (lower = higher priority)
        self.policies.sort(key=lambda p: p.priority)
        
        logger.info("Added policy: %s (priority=%d)", policy.name, policy.priority)
    
    def remove_policy(self, policy_name: str):
        """Remove a policy by name."""
        self.policies = [p for p in self.policies if p.name != policy_name]
        logger.info("Removed policy: %s", policy_name)
    
    def apply_policies(
        self,
        signal: SignalData,
        deterministic_result: DeterministicResult
    ) -> DeterministicResult:
        """
        Apply all policies to a classification result.
        
        Args:
            signal: Test signal data
            deterministic_result: Original deterministic result
            
        Returns:
            Modified deterministic result (or original if no policies applied)
        """
        self.metrics["evaluations"] += 1
        
        # Start with original result
        result = deterministic_result
        applied_policies = []
        augmentations = []
        
        # Evaluate policies in priority order
        for policy in self.policies:
            if not policy.enabled:
                continue
            
            try:
                policy_result = policy.evaluate(signal, result)
                
                if policy_result.action == PolicyAction.OVERRIDE:
                    # Override classification
                    result = DeterministicResult(
                        label=policy_result.new_label,
                        confidence=result.confidence,  # Keep original confidence
                        reasons=result.reasons + policy_result.added_reasons,
                        applied_rules=result.applied_rules + [f"policy:{policy.name}"],
                        metadata={**result.metadata, **policy_result.metadata}
                    )
                    applied_policies.append(policy.name)
                    self.metrics["overrides"] += 1
                    
                    # Stop evaluation for override/block (but still run augments)
                    logger.info(
                        "Policy '%s' overrode classification for '%s': %s -> %s",
                        policy.name, signal.test_name,
                        deterministic_result.label.value, result.label.value
                    )
                    break
                
                elif policy_result.action == PolicyAction.BLOCK:
                    # Block/quarantine test
                    result = DeterministicResult(
                        label=ClassificationLabel.UNKNOWN,
                        confidence=0.0,
                        reasons=result.reasons + policy_result.added_reasons,
                        applied_rules=result.applied_rules + [f"policy:{policy.name}"],
                        metadata={**result.metadata, **policy_result.metadata, "blocked": True}
                    )
                    applied_policies.append(policy.name)
                    self.metrics["blocks"] += 1
                    
                    logger.warning(
                        "Policy '%s' blocked classification for '%s'",
                        policy.name, signal.test_name
                    )
                    break
                
                elif policy_result.action == PolicyAction.AUGMENT:
                    # Augment with metadata (runs even after override)
                    augmentations.append(policy_result)
                    self.metrics["augments"] += 1
                
                else:
                    # SKIP
                    self.metrics["skips"] += 1
            
            except Exception as e:
                logger.error(
                    "Policy '%s' failed during evaluation: %s",
                    policy.name, str(e), exc_info=True
                )
        
        # Apply augmentations
        for augment in augmentations:
            result.metadata.update(augment.metadata)
            result.reasons.extend(augment.added_reasons)
            applied_policies.append(augment.policy_name)
        
        # Add policy tracking to metadata
        if applied_policies:
            result.metadata["applied_policies"] = applied_policies
        
        return result
    
    def get_metrics(self) -> Dict[str, int]:
        """Get policy engine metrics."""
        return self.metrics.copy()
    
    def get_policies(self) -> List[Dict[str, Any]]:
        """Get list of registered policies."""
        return [
            {
                "name": p.name,
                "type": p.__class__.__name__,
                "priority": p.priority,
                "enabled": p.enabled
            }
            for p in self.policies
        ]


# Pre-built policy factories

def create_integration_test_policy() -> Policy:
    """Create policy for integration tests (typically more unstable)."""
    return TestNamePatternPolicy(
        name="integration_test_tolerance",
        pattern=r"integration|e2e|end.?to.?end",
        target_label=ClassificationLabel.FLAKY,
        reason="Integration tests have higher tolerance for instability",
        priority=30
    )


def create_smoke_test_policy() -> Policy:
    """Create policy for smoke tests (should be highly stable)."""
    return ThresholdOverridePolicy(
        name="smoke_test_strictness",
        min_failure_rate=0.01,
        max_failure_rate=1.0,
        target_label=ClassificationLabel.UNSTABLE,
        reason="Smoke tests must be highly stable (failure rate: {failure_rate})",
        priority=20
    )


def create_quarantine_policy(threshold: int = 10) -> Policy:
    """
    Create policy to quarantine tests with excessive failures.
    
    Args:
        threshold: Consecutive failures threshold
        
    Returns:
        QuarantinePolicy instance
    """
    return QuarantinePolicy(
        name="auto_quarantine",
        consecutive_failures_threshold=threshold,
        reason=f"Test automatically quarantined after {threshold} consecutive failures",
        priority=10
    )


def create_team_ownership_policy() -> Policy:
    """Create policy to add team ownership metadata."""
    def has_team_annotation(signal: SignalData, _: DeterministicResult) -> bool:
        # Check if test name contains team annotation
        return "@team:" in signal.test_name.lower() or "team=" in signal.test_name.lower()
    
    def extract_team(signal: SignalData, _: DeterministicResult) -> Dict[str, Any]:
        # Extract team name from annotation
        import re
        match = re.search(r'@team:(\w+)|team=(\w+)', signal.test_name, re.IGNORECASE)
        if match:
            team = match.group(1) or match.group(2)
            return {"owner_team": team}
        return {}
    
    return MetadataAugmentPolicy(
        name="team_ownership",
        condition=has_team_annotation,
        metadata_fn=extract_team,
        priority=90
    )


# Global policy engine instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get global policy engine instance."""
    global _policy_engine
    
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    
    return _policy_engine


def reset_policy_engine():
    """Reset global policy engine."""
    global _policy_engine
    _policy_engine = None
