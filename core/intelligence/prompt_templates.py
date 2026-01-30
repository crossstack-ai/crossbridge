"""
Prompt Templates for AI-Powered Test Intelligence.

This module provides structured prompt templates for different
test classification and analysis scenarios.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Structured prompt template."""
    name: str
    template: str
    required_vars: List[str]
    description: str


class PromptTemplates:
    """Collection of prompt templates for test intelligence."""
    
    # Base system prompt for all classifications
    SYSTEM_PROMPT = """You are a test intelligence expert analyzing automated test failures and behavior patterns. Your role is to provide actionable insights about test classification results.

Guidelines:
- Be concise and specific (2-3 sentences max per section)
- Focus on actionable recommendations
- Consider both technical and process factors
- Avoid speculation without data
- Prioritize high-impact suggestions"""

    # Template for flaky test analysis
    FLAKY_ANALYSIS = PromptTemplate(
        name="flaky_analysis",
        template="""Analyzing a FLAKY test classification:

Test: {test_name}
Classification: FLAKY (Confidence: {confidence}%)
Deterministic Reasons:
{reasons}

Test Signals:
- Retry count: {retry_count}
- Failure rate: {failure_rate}%
- Total runs: {total_runs}
- Recent pattern: {recent_pattern}
{additional_context}

Provide:
1. Root Cause Analysis (2-3 most likely causes):
   - Consider: timing issues, race conditions, external dependencies, resource contention
   
2. Risk Assessment:
   - Impact: [LOW/MEDIUM/HIGH]
   - Urgency: [Can wait / Should fix soon / Fix immediately]
   
3. Recommended Actions (prioritized):
   - Immediate steps to stabilize
   - Long-term fixes
   - Prevention measures

Be specific and actionable.""",
        required_vars=["test_name", "confidence", "reasons", "retry_count", "failure_rate", "total_runs", "recent_pattern"],
        description="Analyze flaky test behavior and provide root cause insights"
    )

    # Template for unstable test analysis
    UNSTABLE_ANALYSIS = PromptTemplate(
        name="unstable_analysis",
        template="""Analyzing an UNSTABLE test classification:

Test: {test_name}
Classification: UNSTABLE (Confidence: {confidence}%)
Deterministic Reasons:
{reasons}

Test Signals:
- Failure rate: {failure_rate}%
- Total runs: {total_runs}
- Consecutive failures: {consecutive_failures}
- Test environment: {environment}
{additional_context}

Provide:
1. Severity Assessment:
   - Why is this test consistently failing?
   - Is this blocking critical functionality?
   
2. Investigation Priority:
   - Priority: [P0/P1/P2/P3]
   - Rationale: One sentence explanation
   
3. Recommended Actions:
   - Should this test be disabled temporarily? (Yes/No + reasoning)
   - Investigation steps (ordered by priority)
   - Stakeholders to notify

Be direct and focus on unblocking the team.""",
        required_vars=["test_name", "confidence", "reasons", "failure_rate", "total_runs", "consecutive_failures", "environment"],
        description="Analyze unstable test and provide severity assessment"
    )

    # Template for regression analysis
    REGRESSION_ANALYSIS = PromptTemplate(
        name="regression_analysis",
        template="""Analyzing a REGRESSION classification:

Test: {test_name}
Classification: REGRESSION (Confidence: {confidence}%)
Deterministic Reasons:
{reasons}

Context:
- Code changed: {code_changed}
- Changed files: {changed_files}
- Commit: {commit_sha}
- Previously passed: {consecutive_passes} times
- Error message: {error_message}
{additional_context}

Provide:
1. Likely Cause:
   - Which code change most likely caused this?
   - Is this a test issue or production code issue?
   
2. Impact Scope:
   - Does this affect other tests?
   - User-facing impact: [None / Low / High]
   
3. Recommended Actions:
   - Should this commit be reverted? (Yes/No + reasoning)
   - Alternative fixes
   - Testing steps to verify fix

Focus on helping the developer quickly resolve the regression.""",
        required_vars=["test_name", "confidence", "reasons", "code_changed", "changed_files", "commit_sha", "consecutive_passes", "error_message"],
        description="Analyze regression and identify likely causes"
    )

    # Template for stable test insights
    STABLE_ANALYSIS = PromptTemplate(
        name="stable_analysis",
        template="""Analyzing a STABLE test:

Test: {test_name}
Classification: STABLE (Confidence: {confidence}%)
Deterministic Reasons:
{reasons}

Test Signals:
- Pass rate: {pass_rate}%
- Total runs: {total_runs}
- Last failure: {last_failure_date}
- Coverage: {coverage_info}
{additional_context}

Provide:
1. Quality Assessment:
   - Is this test providing good value?
   - Any red flags despite stability?
   
2. Optimization Opportunities:
   - Can execution time be improved?
   - Can coverage be expanded?
   
3. Maintenance Suggestions:
   - Updates needed (if any)
   - Documentation improvements

Keep it brief - this is a healthy test.""",
        required_vars=["test_name", "confidence", "reasons", "pass_rate", "total_runs", "last_failure_date", "coverage_info"],
        description="Provide insights on stable test quality and optimization"
    )

    # Template for pattern recognition across multiple tests
    PATTERN_ANALYSIS = PromptTemplate(
        name="pattern_analysis",
        template="""Analyzing failure patterns across multiple tests:

Test Suite: {test_suite}
Time Period: {time_period}

Failing Tests ({count}):
{failing_tests}

Common Characteristics:
{common_characteristics}

Environment: {environment}
Recent Changes: {recent_changes}

Provide:
1. Pattern Recognition:
   - What common thread connects these failures?
   - Is this a systemic issue?
   
2. Root Cause Hypothesis:
   - Most likely root cause
   - Confidence in hypothesis: [LOW/MEDIUM/HIGH]
   
3. Recommended Investigation:
   - Where to look first
   - What to check
   - Who should investigate

Focus on identifying systemic issues that affect multiple tests.""",
        required_vars=["test_suite", "time_period", "count", "failing_tests", "common_characteristics", "environment", "recent_changes"],
        description="Identify patterns across multiple test failures"
    )

    # Template for similar test comparison
    SIMILARITY_ANALYSIS = PromptTemplate(
        name="similarity_analysis",
        template="""Comparing similar test failures:

Current Test: {current_test}
Current Status: {current_status}

Similar Historical Failures:
{similar_failures}

Shared Characteristics:
{shared_characteristics}

Provide:
1. Similarity Assessment:
   - How similar are these failures?
   - Is the root cause likely the same?
   
2. Historical Insights:
   - What fixed these similar issues before?
   - How long did resolution take?
   
3. Recommended Actions:
   - Apply previous solutions? (Yes/No + which ones)
   - New investigation needed?

Leverage historical knowledge to speed up resolution.""",
        required_vars=["current_test", "current_status", "similar_failures", "shared_characteristics"],
        description="Compare current failure with similar historical failures"
    )


class PromptBuilder:
    """
    Builder for constructing AI prompts from templates.
    
    This provides a convenient interface for filling templates
    with test data and context.
    """
    
    def __init__(self):
        """Initialize prompt builder."""
        self.templates = PromptTemplates()
    
    def build_flaky_prompt(
        self,
        test_name: str,
        confidence: float,
        reasons: List[str],
        retry_count: int,
        failure_rate: float,
        total_runs: int,
        recent_pattern: str = "Unknown",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build prompt for flaky test analysis.
        
        Args:
            test_name: Name of the test
            confidence: Confidence level (0.0 - 1.0)
            reasons: List of reasons for classification
            retry_count: Number of retries
            failure_rate: Failure rate (0.0 - 1.0)
            total_runs: Total number of runs
            recent_pattern: Recent failure pattern description
            additional_context: Optional additional context
            
        Returns:
            Formatted prompt string
        """
        return self._fill_template(
            self.templates.FLAKY_ANALYSIS,
            {
                "test_name": test_name,
                "confidence": int(confidence * 100),
                "reasons": "\n".join(f"  - {r}" for r in reasons),
                "retry_count": retry_count,
                "failure_rate": f"{failure_rate * 100:.1f}",
                "total_runs": total_runs,
                "recent_pattern": recent_pattern,
                "additional_context": self._format_additional_context(additional_context)
            }
        )
    
    def build_unstable_prompt(
        self,
        test_name: str,
        confidence: float,
        reasons: List[str],
        failure_rate: float,
        total_runs: int,
        consecutive_failures: int,
        environment: str = "Unknown",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for unstable test analysis."""
        return self._fill_template(
            self.templates.UNSTABLE_ANALYSIS,
            {
                "test_name": test_name,
                "confidence": int(confidence * 100),
                "reasons": "\n".join(f"  - {r}" for r in reasons),
                "failure_rate": f"{failure_rate * 100:.1f}",
                "total_runs": total_runs,
                "consecutive_failures": consecutive_failures,
                "environment": environment,
                "additional_context": self._format_additional_context(additional_context)
            }
        )
    
    def build_regression_prompt(
        self,
        test_name: str,
        confidence: float,
        reasons: List[str],
        code_changed: bool,
        changed_files: List[str],
        commit_sha: str,
        consecutive_passes: int,
        error_message: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for regression analysis."""
        return self._fill_template(
            self.templates.REGRESSION_ANALYSIS,
            {
                "test_name": test_name,
                "confidence": int(confidence * 100),
                "reasons": "\n".join(f"  - {r}" for r in reasons),
                "code_changed": "Yes" if code_changed else "No",
                "changed_files": ", ".join(changed_files[:5]) + ("..." if len(changed_files) > 5 else ""),
                "commit_sha": commit_sha[:8],
                "consecutive_passes": consecutive_passes,
                "error_message": error_message[:200] + ("..." if len(error_message) > 200 else ""),
                "additional_context": self._format_additional_context(additional_context)
            }
        )
    
    def build_stable_prompt(
        self,
        test_name: str,
        confidence: float,
        reasons: List[str],
        pass_rate: float,
        total_runs: int,
        last_failure_date: str,
        coverage_info: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for stable test insights."""
        return self._fill_template(
            self.templates.STABLE_ANALYSIS,
            {
                "test_name": test_name,
                "confidence": int(confidence * 100),
                "reasons": "\n".join(f"  - {r}" for r in reasons),
                "pass_rate": f"{pass_rate * 100:.1f}",
                "total_runs": total_runs,
                "last_failure_date": last_failure_date,
                "coverage_info": coverage_info,
                "additional_context": self._format_additional_context(additional_context)
            }
        )
    
    def build_pattern_prompt(
        self,
        test_suite: str,
        time_period: str,
        failing_tests: List[str],
        common_characteristics: List[str],
        environment: str,
        recent_changes: List[str]
    ) -> str:
        """Build prompt for pattern analysis."""
        return self._fill_template(
            self.templates.PATTERN_ANALYSIS,
            {
                "test_suite": test_suite,
                "time_period": time_period,
                "count": len(failing_tests),
                "failing_tests": "\n".join(f"  - {t}" for t in failing_tests[:10]),
                "common_characteristics": "\n".join(f"  - {c}" for c in common_characteristics),
                "environment": environment,
                "recent_changes": "\n".join(f"  - {c}" for c in recent_changes[:5])
            }
        )
    
    def build_similarity_prompt(
        self,
        current_test: str,
        current_status: str,
        similar_failures: List[Dict[str, Any]],
        shared_characteristics: List[str]
    ) -> str:
        """Build prompt for similarity analysis."""
        similar_str = "\n".join(
            f"  - {f['test_name']}: {f['status']} (resolved in {f.get('resolution_time', 'N/A')})"
            for f in similar_failures[:5]
        )
        
        return self._fill_template(
            self.templates.SIMILARITY_ANALYSIS,
            {
                "current_test": current_test,
                "current_status": current_status,
                "similar_failures": similar_str,
                "shared_characteristics": "\n".join(f"  - {c}" for c in shared_characteristics)
            }
        )
    
    def _fill_template(self, template: PromptTemplate, vars: Dict[str, Any]) -> str:
        """
        Fill a template with variables.
        
        Args:
            template: Template to fill
            vars: Variables to substitute
            
        Returns:
            Filled template string
        """
        # Check for missing required variables
        missing = set(template.required_vars) - set(vars.keys())
        if missing:
            raise ValueError(f"Missing required variables for template '{template.name}': {missing}")
        
        # Fill template
        filled = template.template.format(**vars)
        
        # Add system prompt
        return f"{self.templates.SYSTEM_PROMPT}\n\n{filled}"
    
    def _format_additional_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Format additional context for inclusion in prompt."""
        if not context:
            return ""
        
        lines = ["\nAdditional Context:"]
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)


# Convenience function
def build_prompt(
    classification_label: str,
    test_name: str,
    confidence: float,
    reasons: List[str],
    **kwargs
) -> str:
    """
    Convenience function to build prompt based on classification.
    
    Args:
        classification_label: Classification label (flaky, unstable, etc.)
        test_name: Test name
        confidence: Confidence level
        reasons: Reasons for classification
        **kwargs: Additional template-specific parameters
        
    Returns:
        Formatted prompt string
    """
    builder = PromptBuilder()
    
    if classification_label == "flaky":
        return builder.build_flaky_prompt(test_name, confidence, reasons, **kwargs)
    elif classification_label == "unstable":
        return builder.build_unstable_prompt(test_name, confidence, reasons, **kwargs)
    elif classification_label == "regression":
        return builder.build_regression_prompt(test_name, confidence, reasons, **kwargs)
    elif classification_label == "stable":
        return builder.build_stable_prompt(test_name, confidence, reasons, **kwargs)
    else:
        raise ValueError(f"Unknown classification label: {classification_label}")
