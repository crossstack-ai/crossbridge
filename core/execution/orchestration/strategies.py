"""
Execution Strategies

Implements different strategies for intelligent test selection:
- Smoke: Fast signal tests only
- Impacted: Tests affected by code changes
- Risk-Based: Tests ranked by historical risk
- Full: All available tests

Each strategy decides WHAT to run, not HOW to run it.
Framework adapters handle the HOW.

PLUGIN ARCHITECTURE:
-------------------
Strategies are DECISION PLUGINS in CrossBridge's plugin architecture.
They determine WHAT tests to run, not HOW to run them.

Each strategy can be:
- Extended by inheriting from ExecutionStrategy
- Registered dynamically via PluginRegistry
- Used with any framework adapter
- Combined with sidecar or orchestration modes
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

from .api import ExecutionContext, ExecutionPlan, StrategyType

logger = logging.getLogger(__name__)


class ExecutionStrategy(ABC):
    """
    Base class for execution strategies (Decision Plugins).
    
    Strategies determine which tests to run based on various signals:
    - Code changes (impacted)
    - Historical failures (risk)
    - Tags/annotations (smoke)
    - Everything (full)
    
    PLUGIN PATTERN:
    - Each strategy is a pluggable decision component
    - Strategies are framework-agnostic
    - Strategies can be registered dynamically
    - Third-party strategies can be added
    """
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def select_tests(self, context: ExecutionContext) -> ExecutionPlan:
        """
        Select tests to execute based on strategy logic.
        
        This is the plugin's decision method - it returns WHAT to run,
        not HOW to run it (that's the adapter's job).
        
        Args:
            context: Execution context with all available data
            
        Returns:
            ExecutionPlan with selected tests and metadata
        """
        pass
    
    def get_name(self) -> str:
        """Get strategy name (for plugin registry)."""
        return self.name
    
    def _create_plan(
        self,
        context: ExecutionContext,
        selected: List[str],
        reasons: Dict[str, str],
        priority: Optional[Dict[str, int]] = None,
    ) -> ExecutionPlan:
        """Helper to create execution plan"""
        all_tests = set(context.available_tests)
        selected_set = set(selected)
        skipped = list(all_tests - selected_set)
        
        # Add skip reasons
        for test in skipped:
            if test not in reasons:
                reasons[test] = f"Not selected by {self.name} strategy"
        
        # Default priorities
        if priority is None:
            priority = {test: 3 for test in selected}
        
        # Create simple grouping (can be enhanced later)
        grouping = {"default": selected}
        
        # Estimate duration (placeholder - can be enhanced with historical data)
        estimated_duration = len(selected) * 2  # Assume 2 min per test
        if context.request.parallel:
            estimated_duration = estimated_duration // 4  # Rough parallel speedup
        
        return ExecutionPlan(
            selected_tests=selected,
            skipped_tests=skipped,
            grouping=grouping,
            priority=priority,
            reasons=reasons,
            framework=context.request.framework,
            strategy=context.request.strategy,
            environment=context.request.environment,
            parallel=context.request.parallel,
            max_duration_minutes=context.request.max_duration_minutes,
            estimated_duration_minutes=estimated_duration,
            confidence_score=1.0,
        )


class SmokeStrategy(ExecutionStrategy):
    """
    Smoke Strategy - Fast signal tests only.
    
    Selects tests tagged as 'smoke', 'sanity', or marked as critical.
    Ideal for:
    - PR validation
    - Quick feedback
    - Pre-deployment checks
    
    Typically reduces suite by 80-95%.
    """
    
    def __init__(self):
        super().__init__("smoke")
        self.smoke_tags = {"smoke", "sanity", "critical", "p0"}
    
    def select_tests(self, context: ExecutionContext) -> ExecutionPlan:
        """Select tests with smoke tags"""
        selected = []
        reasons = {}
        priority = {}
        
        for test_id in context.available_tests:
            test_tags = set(context.get_test_tags(test_id))
            
            # Check if test has smoke tags
            if test_tags & self.smoke_tags:
                selected.append(test_id)
                matched_tags = test_tags & self.smoke_tags
                reasons[test_id] = f"Smoke test with tags: {', '.join(matched_tags)}"
                priority[test_id] = 5  # High priority
            else:
                reasons[test_id] = "Not tagged as smoke/critical"
        
        logger.info(
            f"Smoke strategy selected {len(selected)}/{len(context.available_tests)} tests "
            f"({len(selected)/max(len(context.available_tests), 1)*100:.1f}%)"
        )
        
        return self._create_plan(context, selected, reasons, priority)


class ImpactedStrategy(ExecutionStrategy):
    """
    Impacted Strategy - Tests affected by code changes.
    
    Selects tests that cover changed code or are semantically related.
    Uses:
    - Git diff
    - Code coverage mapping
    - Crossbridge memory graph
    - Semantic similarity (if available)
    
    Ideal for:
    - PR validation
    - Feature development
    - Targeted regression
    
    Typically reduces suite by 60-80%.
    """
    
    def __init__(self):
        super().__init__("impacted")
    
    def select_tests(self, context: ExecutionContext) -> ExecutionPlan:
        """Select tests impacted by code changes"""
        selected = []
        reasons = {}
        priority = {}
        
        if not context.changed_files:
            logger.warning("No changed files detected, falling back to smoke tests")
            return SmokeStrategy().select_tests(context)
        
        logger.info(f"Analyzing impact of {len(context.changed_files)} changed files")
        
        for test_id in context.available_tests:
            # Direct coverage impact
            if context.is_impacted(test_id):
                selected.append(test_id)
                covered_files = context.test_to_code_mapping.get(test_id, [])
                impacted_files = [f for f in covered_files if f in context.changed_files]
                reasons[test_id] = f"Covers changed files: {', '.join(impacted_files[:3])}"
                priority[test_id] = 4  # High priority for direct impact
                continue
            
            # Semantic impact (if memory graph available)
            if context.memory_graph:
                # Check if test is semantically related to changed code
                # This would use the semantic engine we just implemented
                semantic_score = self._calculate_semantic_impact(test_id, context)
                if semantic_score > 0.7:
                    selected.append(test_id)
                    reasons[test_id] = f"Semantically related (score: {semantic_score:.2f})"
                    priority[test_id] = 3
                    continue
            
            # Critical tests always included
            if "critical" in context.get_test_tags(test_id):
                selected.append(test_id)
                reasons[test_id] = "Critical test (always included in impacted runs)"
                priority[test_id] = 5
        
        # If we selected too few tests, add smoke tests as backup
        if len(selected) < 5:
            logger.warning(f"Only {len(selected)} tests selected, adding smoke tests")
            smoke_plan = SmokeStrategy().select_tests(context)
            for test in smoke_plan.selected_tests:
                if test not in selected:
                    selected.append(test)
                    reasons[test] = "Smoke test (backup for low coverage)"
                    priority[test] = 4
        
        logger.info(
            f"Impacted strategy selected {len(selected)}/{len(context.available_tests)} tests "
            f"({len(selected)/max(len(context.available_tests), 1)*100:.1f}%)"
        )
        
        return self._create_plan(context, selected, reasons, priority)
    
    def _calculate_semantic_impact(self, test_id: str, context: ExecutionContext) -> float:
        """Calculate semantic similarity between test and changed code"""
        # Placeholder for semantic similarity calculation
        # This would integrate with the semantic engine we just built
        # For now, return 0 (no semantic impact)
        return 0.0


class RiskBasedStrategy(ExecutionStrategy):
    """
    Risk-Based Strategy - Tests ranked by historical risk.
    
    Selects tests based on:
    - Historical failure rate
    - Recent failures
    - Code churn in covered areas
    - Flakiness (penalized)
    - Criticality tags
    
    Ideal for:
    - Release pipelines
    - Nightly regression
    - High-value testing
    
    Reduction varies (typically 40-60%).
    """
    
    def __init__(self):
        super().__init__("risk_based")
    
    def select_tests(self, context: ExecutionContext) -> ExecutionPlan:
        """Select tests based on risk score"""
        # Calculate risk scores for all tests
        risk_scores = {}
        reasons = {}
        
        for test_id in context.available_tests:
            score, reason = self._calculate_risk_score(test_id, context)
            risk_scores[test_id] = score
            reasons[test_id] = reason
        
        # Sort by risk score (descending)
        ranked_tests = sorted(
            context.available_tests,
            key=lambda t: risk_scores[t],
            reverse=True
        )
        
        # Apply budget if specified
        if context.request.max_tests:
            selected = ranked_tests[:context.request.max_tests]
            logger.info(f"Budget limit: selecting top {context.request.max_tests} risky tests")
        else:
            # Select tests with risk score > threshold
            threshold = 0.3
            selected = [t for t in ranked_tests if risk_scores[t] > threshold]
            logger.info(f"Selecting tests with risk score > {threshold}")
        
        # Ensure minimum coverage (smoke tests)
        if len(selected) < 10:
            logger.warning("Too few tests selected, adding smoke tests")
            smoke_plan = SmokeStrategy().select_tests(context)
            for test in smoke_plan.selected_tests:
                if test not in selected:
                    selected.append(test)
                    reasons[test] = "Smoke test (minimum coverage)"
        
        # Convert risk scores to priorities (1-5)
        max_score = max(risk_scores.values()) if risk_scores else 1.0
        priority = {
            test: min(5, max(1, int(risk_scores[test] / max_score * 5) + 1))
            for test in selected
        }
        
        logger.info(
            f"Risk-based strategy selected {len(selected)}/{len(context.available_tests)} tests "
            f"({len(selected)/max(len(context.available_tests), 1)*100:.1f}%)"
        )
        
        return self._create_plan(context, selected, reasons, priority)
    
    def _calculate_risk_score(self, test_id: str, context: ExecutionContext) -> tuple[float, str]:
        """
        Calculate risk score for a test (0-1).
        
        Higher score = higher risk = should run sooner.
        """
        score = 0.0
        factors = []
        
        # Factor 1: Historical failure rate (0-0.4)
        failure_rate = context.get_failure_rate(test_id)
        if failure_rate > 0:
            score += failure_rate * 0.4
            factors.append(f"failure_rate={failure_rate:.2f}")
        
        # Factor 2: Critical tag (0-0.3)
        tags = context.get_test_tags(test_id)
        if "critical" in tags or "p0" in tags:
            score += 0.3
            factors.append("critical")
        elif "high" in tags or "p1" in tags:
            score += 0.2
            factors.append("high_priority")
        
        # Factor 3: Code impact (0-0.2)
        if context.is_impacted(test_id):
            score += 0.2
            factors.append("code_impacted")
        
        # Factor 4: Flakiness penalty (subtract 0-0.3)
        if not context.request.include_flaky and context.is_flaky(test_id):
            score -= 0.3
            factors.append("flaky_penalty")
        
        # Factor 5: Recent execution (0-0.1)
        test_history = context.test_history.get(test_id, [])
        if test_history:
            recent_failures = sum(1 for run in test_history[:10] if run.get("status") == "failed")
            if recent_failures > 0:
                score += 0.1
                factors.append(f"recent_failures={recent_failures}")
        
        # Clamp score
        score = max(0.0, min(1.0, score))
        
        reason = f"Risk score: {score:.2f} ({', '.join(factors) if factors else 'baseline'})"
        return score, reason


class FullStrategy(ExecutionStrategy):
    """
    Full Strategy - Run all available tests.
    
    No intelligence, just run everything.
    Useful for:
    - Baseline runs
    - Nightly full regression
    - Release validation
    - When confidence matters more than speed
    """
    
    def __init__(self):
        super().__init__("full")
    
    def select_tests(self, context: ExecutionContext) -> ExecutionPlan:
        """Select all tests"""
        selected = context.available_tests.copy()
        reasons = {test: "Full regression - all tests selected" for test in selected}
        priority = {test: context.get_test_priority(test) for test in selected}
        
        logger.info(f"Full strategy selected all {len(selected)} tests")
        
        return self._create_plan(context, selected, reasons, priority)


# Strategy factory
def create_strategy(strategy_type: StrategyType) -> ExecutionStrategy:
    """Create strategy instance based on type"""
    strategies = {
        StrategyType.SMOKE: SmokeStrategy,
        StrategyType.IMPACTED: ImpactedStrategy,
        StrategyType.RISK_BASED: RiskBasedStrategy,
        StrategyType.FULL: FullStrategy,
    }
    
    strategy_class = strategies.get(strategy_type)
    if not strategy_class:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    return strategy_class()
