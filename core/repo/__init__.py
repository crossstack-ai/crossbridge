"""
Repo-native transformation support for CrossBridge.

This module provides abstractions and implementations for connecting to remote
repositories (GitHub, GitLab, Bitbucket) without requiring local clones.
"""

from .base import RepoConnector, RepoFile, RepoBranch, PullRequest
from .virtual_workspace import VirtualRepo
from .credentials import CredentialManager, RepoCredential
from .repo_translator import RepoTranslator, create_connector

# Optional imports (may not be available without dependencies)
try:
    from .github import GitHubConnector
except ImportError:
    GitHubConnector = None

try:
    from .gitlab import GitLabConnector
except ImportError:
    GitLabConnector = None

try:
    from .bitbucket import BitbucketConnector
except ImportError:
    BitbucketConnector = None

try:
    from .azuredevops import AzureDevOpsConnector
except ImportError:
    AzureDevOpsConnector = None

__all__ = [
    'RepoConnector',
    'RepoFile',
    'RepoBranch',
    'PullRequest',
    'VirtualRepo',
    'CredentialManager',
    'RepoCredential',
    'RepoTranslator',
    'create_connector',
    'GitHubConnector',
    'GitLabConnector',
    'BitbucketConnector',
    'AzureDevOpsConnector',
]
