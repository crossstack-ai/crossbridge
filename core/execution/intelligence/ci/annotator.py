"""
CI Annotator

Creates PR annotations and determines CI behavior based on execution intelligence.
"""

from typing import List, Optional, Dict
import json
import logging
import os

from core.execution.intelligence.ci.models import (
    CIOutput,
    PRAnnotation,
    CIConfig,
    CIDecision,
    CodeReference
)

logger = logging.getLogger(__name__)


class CIAnnotator:
    """
    Base class for CI/CD platform annotators.
    
    Generates PR annotations based on execution intelligence results.
    """
    
    def __init__(self, config: Optional[CIConfig] = None):
        """
        Initialize CI annotator.
        
        Args:
            config: CI configuration (uses defaults if None)
        """
        self.config = config or CIConfig()
    
    def generate_output(self, analysis_result) -> CIOutput:
        """
        Generate CI output from analysis result.
        
        Args:
            analysis_result: FailureAnalysisResult object
            
        Returns:
            CIOutput object
        """
        # Determine CI decision
        ci_decision = CIDecision.PASS
        
        if hasattr(analysis_result, 'nature'):
            nature = analysis_result.nature
        else:
            nature = "DETERMINISTIC"  # Default assumption
        
        if self.config.should_fail_ci(
            analysis_result.classification,
            analysis_result.confidence,
            nature
        ):
            ci_decision = CIDecision.FAIL
        elif self.config.should_annotate(
            analysis_result.classification,
            analysis_result.confidence
        ):
            ci_decision = CIDecision.WARN
        
        # Create code reference if available
        code_ref = None
        if hasattr(analysis_result, 'code_reference') and analysis_result.code_reference:
            ref = analysis_result.code_reference
            code_ref = CodeReference(
                file=ref.get('file', ''),
                line=ref.get('line'),
                column=ref.get('column')
            )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            analysis_result.classification,
            nature,
            analysis_result.confidence
        )
        
        return CIOutput(
            test=analysis_result.test_name,
            failure_type=analysis_result.classification,
            confidence=analysis_result.confidence,
            nature=nature,
            summary=analysis_result.summary,
            code_reference=code_ref,
            error_message=getattr(analysis_result, 'error_message', None),
            stacktrace=getattr(analysis_result, 'stacktrace', None),
            recommendation=recommendation,
            ci_decision=ci_decision
        )
    
    def _generate_recommendation(self, failure_type: str, nature: str, confidence: float) -> str:
        """Generate actionable recommendation"""
        if nature == "FLAKY":
            return "⚠️ This appears to be a flaky test. Consider adding retry logic or investigating intermittent conditions."
        
        if failure_type == "PRODUCT_DEFECT":
            if confidence >= 0.85:
                return "🐛 High-confidence product defect detected. Review application code and fix the underlying issue."
            else:
                return "🐛 Possible product defect. Investigate application behavior."
        
        if failure_type == "AUTOMATION_DEFECT":
            return "🔧 Test automation issue detected. Update test code, locators, or wait strategies."
        
        if failure_type == "ENVIRONMENT_ISSUE":
            return "⚙️ Environment issue detected. Check test infrastructure, services, and connectivity."
        
        if failure_type == "CONFIGURATION_ISSUE":
            return "⚠️ Configuration issue detected. Verify test data, settings, and environment variables."
        
        return "ℹ️ Review the failure details and take appropriate action."
    
    def create_annotation(self, ci_output: CIOutput) -> PRAnnotation:
        """
        Create PR annotation from CI output.
        
        Args:
            ci_output: CIOutput object
            
        Returns:
            PRAnnotation object
        """
        emoji = ci_output.get_emoji()
        
        title = f"{emoji} {ci_output.failure_type}: {ci_output.test}"
        
        level = "error" if ci_output.ci_decision == CIDecision.FAIL else "warning"
        
        return PRAnnotation(
            title=title,
            body=ci_output.to_markdown(),
            level=level,
            file=ci_output.code_reference.file if ci_output.code_reference else None,
            line=ci_output.code_reference.line if ci_output.code_reference else None
        )


class GitHubAnnotator(CIAnnotator):
    """
    GitHub-specific annotator.
    
    Creates annotations compatible with GitHub Actions.
    """
    
    def create_github_comment(self, ci_output: CIOutput) -> str:
        """
        Create GitHub PR comment.
        
        Returns:
            Markdown string for PR comment
        """
        return ci_output.to_markdown()
    
    def create_github_action_output(self, ci_outputs: List[CIOutput]) -> str:
        """
        Create output for GitHub Actions.
        
        Args:
            ci_outputs: List of CIOutput objects
            
        Returns:
            JSON string for GitHub Actions output
        """
        return json.dumps({
            'failures': [output.to_json() for output in ci_outputs],
            'should_fail': any(o.ci_decision == CIDecision.FAIL for o in ci_outputs)
        })
    
    def post_comment_script(self, pr_number: str, comment_body: str) -> str:
        """
        Generate shell script to post GitHub PR comment.
        
        Args:
            pr_number: PR number
            comment_body: Comment body (Markdown)
            
        Returns:
            Shell command string
        """
        return f'gh pr comment {pr_number} --body "{comment_body}"'


class BitbucketAnnotator(CIAnnotator):
    """
    Bitbucket-specific annotator.
    
    Creates annotations compatible with Bitbucket Pipelines.
    """
    
    def create_bitbucket_comment(self, ci_output: CIOutput) -> Dict:
        """
        Create Bitbucket PR comment payload.
        
        Returns:
            Dictionary for Bitbucket API
        """
        annotation = self.create_annotation(ci_output)
        return annotation.to_bitbucket_format()
    
    def create_api_payload(self, workspace: str, repo: str, pr_id: str, 
                          ci_output: CIOutput) -> tuple[str, Dict]:
        """
        Create Bitbucket API request payload.
        
        Args:
            workspace: Bitbucket workspace
            repo: Repository name
            pr_id: Pull request ID
            ci_output: CIOutput object
            
        Returns:
            Tuple of (url, payload)
        """
        url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments"
        
        payload = self.create_bitbucket_comment(ci_output)
        
        return url, payload


# ============================================================================
# Functional Interface
# ============================================================================

def generate_ci_output(analysis_result, config: Optional[CIConfig] = None) -> CIOutput:
    """
    Generate CI output from analysis result (functional interface).
    
    Args:
        analysis_result: FailureAnalysisResult object
        config: Optional CI configuration
        
    Returns:
        CIOutput object
    """
    annotator = CIAnnotator(config)
    return annotator.generate_output(analysis_result)


def should_fail_ci(failure_type: str, confidence: float, nature: str = "DETERMINISTIC",
                  config: Optional[CIConfig] = None) -> bool:
    """
    Determine if CI should fail (functional interface).
    
    Args:
        failure_type: Type of failure
        confidence: Confidence score
        nature: FLAKY or DETERMINISTIC
        config: Optional CI configuration
        
    Returns:
        True if CI should fail
    """
    cfg = config or CIConfig()
    return cfg.should_fail_ci(failure_type, confidence, nature)


def create_pr_comment(ci_output: CIOutput, platform: str = "github") -> str:
    """
    Create PR comment for specified platform (functional interface).
    
    Args:
        ci_output: CIOutput object
        platform: Platform name ("github", "bitbucket", "gitlab")
        
    Returns:
        Comment string (Markdown or platform-specific format)
    """
    if platform.lower() == "github":
        annotator = GitHubAnnotator()
        return annotator.create_github_comment(ci_output)
    elif platform.lower() == "bitbucket":
        annotator = BitbucketAnnotator()
        comment_dict = annotator.create_bitbucket_comment(ci_output)
        return json.dumps(comment_dict)
    else:
        # Default to markdown
        return ci_output.to_markdown()


def write_ci_output_file(ci_outputs: List[CIOutput], output_file: str = "crossbridge-ci-output.json"):
    """
    Write CI outputs to file for consumption by CI scripts.
    
    Args:
        ci_outputs: List of CIOutput objects
        output_file: Output file path
    """
    data = {
        'version': '1.0',
        'failures': [output.to_json() for output in ci_outputs],
        'should_fail_ci': any(o.ci_decision == CIDecision.FAIL for o in ci_outputs),
        'summary': {
            'total': len(ci_outputs),
            'product_defects': sum(1 for o in ci_outputs if o.failure_type == "PRODUCT_DEFECT"),
            'automation_defects': sum(1 for o in ci_outputs if o.failure_type == "AUTOMATION_DEFECT"),
            'environment_issues': sum(1 for o in ci_outputs if o.failure_type == "ENVIRONMENT_ISSUE"),
            'flaky': sum(1 for o in ci_outputs if o.nature == "FLAKY"),
            'deterministic': sum(1 for o in ci_outputs if o.nature == "DETERMINISTIC")
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Wrote CI output to {output_file}")


def print_ci_summary(ci_outputs: List[CIOutput]):
    """
    Print summary to console for CI logs.
    
    Args:
        ci_outputs: List of CIOutput objects
    """
    print("\n" + "="*80)
    print("CROSSBRIDGE EXECUTION INTELLIGENCE SUMMARY")
    print("="*80)
    
    for output in ci_outputs:
        emoji = output.get_emoji()
        print(f"\n{emoji} {output.test}")
        print(f"   Type: {output.failure_type} ({output.confidence * 100:.0f}% confidence)")
        print(f"   Nature: {output.nature}")
        print(f"   Summary: {output.summary}")
        if output.code_reference:
            print(f"   Location: {output.code_reference.to_github_format()}")
        print(f"   CI Decision: {output.ci_decision.value}")
    
    print("\n" + "-"*80)
    summary = {
        'total': len(ci_outputs),
        'product_defects': sum(1 for o in ci_outputs if o.failure_type == "PRODUCT_DEFECT"),
        'automation_defects': sum(1 for o in ci_outputs if o.failure_type == "AUTOMATION_DEFECT"),
        'flaky': sum(1 for o in ci_outputs if o.nature == "FLAKY"),
        'will_fail_ci': sum(1 for o in ci_outputs if o.ci_decision == CIDecision.FAIL)
    }
    
    print(f"Total Failures: {summary['total']}")
    print(f"Product Defects: {summary['product_defects']}")
    print(f"Automation Defects: {summary['automation_defects']}")
    print(f"Flaky Tests: {summary['flaky']}")
    print(f"Will Fail CI: {summary['will_fail_ci']}")
    print("="*80 + "\n")
