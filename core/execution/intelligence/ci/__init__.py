"""
CI Annotation System

Surfaces execution intelligence in CI/CD pipelines via PR annotations.
"""

from .annotator import (
    CIAnnotator,
    GitHubAnnotator,
    BitbucketAnnotator,
    generate_ci_output,
    should_fail_ci,
    create_pr_comment
)
from .models import CIOutput, PRAnnotation

__all__ = [
    'CIAnnotator',
    'GitHubAnnotator',
    'BitbucketAnnotator',
    'generate_ci_output',
    'should_fail_ci',
    'create_pr_comment',
    'CIOutput',
    'PRAnnotation'
]
