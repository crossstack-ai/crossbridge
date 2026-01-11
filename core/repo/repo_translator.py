"""
Repository-native translation integration.

Connects repo connectors with the translation pipeline to enable seamless
framework migrations without local clones.
"""

from typing import Optional, List, Dict
from pathlib import Path
import re

from .base import RepoConnector, PullRequest
from .virtual_workspace import VirtualRepo
from .github import GitHubConnector
from .gitlab import GitLabConnector
from .bitbucket import BitbucketConnector
from ..translation.pipeline import TranslationPipeline
from ..translation.intent_model import TestIntent


def translate_repo_to_connector(
    repo_url: str,
    token: str,
    base_branch: Optional[str] = None,
    username: Optional[str] = None
) -> RepoConnector:
    """
    Translate repository URL to appropriate connector.
    
    Args:
        repo_url: Repository URL
        token: Authentication token
        base_branch: Optional base branch
        username: Optional username (for Bitbucket)
    
    Returns:
        Appropriate RepoConnector instance
    
    Raises:
        ValueError: If repository platform is not supported
    """
    url_lower = repo_url.lower()
    
    if "github.com" in url_lower:
        # Parse GitHub URL: https://github.com/org/repo
        parts = repo_url.rstrip("/").split("/")
        org, repo = parts[-2], parts[-1]
        return GitHubConnector(
            org=org,
            repo=repo,
            token=token,
            base_branch=base_branch
        )
    
    elif "bitbucket.org" in url_lower or "bitbucket.com" in url_lower:
        # Parse Bitbucket URL: https://bitbucket.org/workspace/repo[/src/branch/...]
        # Extract only workspace and repo, ignoring any /src/branch paths
        parts = repo_url.rstrip("/").split("/")
        # Find bitbucket.org/workspace/repo (indices 2, 3, 4 after split)
        domain_idx = next(i for i, p in enumerate(parts) if "bitbucket" in p.lower())
        owner = parts[domain_idx + 1]
        repo = parts[domain_idx + 2]
        return BitbucketConnector(
            owner=owner,
            repo=repo,
            username=username,
            token=token,
            base_branch=base_branch,
            is_cloud=True
        )
    
    elif "gitlab.com" in url_lower:
        # Parse GitLab URL
        parts = repo_url.rstrip("/").split("/")
        project_id = f"{parts[-2]}/{parts[-1]}"
        return GitLabConnector(
            project_id=project_id,
            token=token,
            base_branch=base_branch
        )
    
    else:
        raise ValueError(f"Unsupported repository platform: {repo_url}")


class RepoTranslator:
    """
    Orchestrates repo-native test framework translation.
    
    Features:
    - Discovers test files remotely
    - Translates in virtual workspace
    - Generates diffs
    - Creates pull requests
    - Exports bundles
    """
    
    def __init__(self, connector: RepoConnector, source_framework: str, 
                 target_framework: str):
        """
        Initialize repo translator.
        
        Args:
            connector: Repository connector
            source_framework: Source test framework
            target_framework: Target test framework
        """
        self.connector = connector
        self.source_framework = source_framework
        self.target_framework = target_framework
        self.workspace = VirtualRepo(connector)
        self.pipeline = TranslationPipeline()
    
    def discover_test_files(self, path: str = "", pattern: Optional[str] = None) -> List[str]:
        """
        Discover test files in repository.
        
        Args:
            path: Starting path for discovery
            pattern: Glob pattern to match files
            
        Returns:
            List of test file paths
        """
        # Default patterns based on source framework
        if pattern is None:
            pattern = self._get_default_pattern()
        
        files = self.connector.get_file_tree(path=path, pattern=pattern)
        
        # Filter for test files
        test_files = []
        for file_path in files:
            if self._is_test_file(file_path):
                test_files.append(file_path)
        
        return test_files
    
    def _get_default_pattern(self) -> str:
        """Get default file pattern based on source framework."""
        patterns = {
            'selenium-java': '*.java',
            'selenium-bdd-java': '*.java',
            'cypress': '*.js',
            'pytest': '*.py',
            'junit': '*.java',
            'testng': '*.java',
            'robot': '*.robot',
            'behave': '*.py',
            'pytest-bdd': '*.py',
            'python-bdd': '*.py',
            'specflow': '*.cs',
        }
        
        return patterns.get(self.source_framework.lower(), '*.*')
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file based on naming conventions."""
        path_lower = file_path.lower()
        
        # Common test patterns
        test_indicators = [
            'test', 'spec', 'tests', 'specs',
            '_test', '_spec', 'test_', 'spec_',
            '.test.', '.spec.'
        ]
        
        return any(indicator in path_lower for indicator in test_indicators)
    
    def translate_file(self, file_path: str) -> Optional[str]:
        """
        Translate a single test file.
        
        Args:
            file_path: Path to test file
            
        Returns:
            Translated file path or None if translation failed
        """
        try:
            # Read source file
            source_code = self.workspace.read(file_path)
            
            # Translate using pipeline
            result = self.pipeline.translate(
                source_code=source_code,
                source_framework=self.source_framework,
                target_framework=self.target_framework
            )
            
            if not result or not result.code:
                return None
            
            # Determine output file path
            output_path = self._get_output_path(file_path)
            
            # Write translated code to virtual workspace
            self.workspace.write(output_path, result.code)
            
            return output_path
            
        except Exception as e:
            print(f"Error translating {file_path}: {str(e)}")
            return None
    
    def _get_output_path(self, source_path: str) -> str:
        """
        Generate output file path based on target framework.
        
        Args:
            source_path: Original file path
            
        Returns:
            New file path for translated code
        """
        path = Path(source_path)
        
        # Extension mapping
        extensions = {
            'playwright-python': '.py',
            'playwright-typescript': '.ts',
            'pytest': '.py',
            'robot': '.robot',
            'cypress': '.js',
        }
        
        new_ext = extensions.get(self.target_framework.lower(), path.suffix)
        
        # Directory mapping
        if 'tests' in str(path.parent).lower():
            output_dir = path.parent
        else:
            output_dir = Path('tests_translated')
        
        # Generate new filename
        stem = path.stem
        new_name = f"{stem}{new_ext}"
        
        return str(output_dir / new_name)
    
    def translate_all(self, path: str = "", pattern: Optional[str] = None) -> Dict[str, str]:
        """
        Translate all test files in repository.
        
        Args:
            path: Starting path
            pattern: File pattern to match
            
        Returns:
            Dictionary mapping source paths to output paths
        """
        test_files = self.discover_test_files(path, pattern)
        results = {}
        
        for file_path in test_files:
            output_path = self.translate_file(file_path)
            if output_path:
                results[file_path] = output_path
        
        return results
    
    def preview_changes(self) -> str:
        """
        Generate unified diff preview of all changes.
        
        Returns:
            Unified diff string
        """
        return self.workspace.get_all_diffs()
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get translation statistics.
        
        Returns:
            Dictionary with file counts
        """
        return self.workspace.get_stats()
    
    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: Optional[str] = None,
        commit_message: Optional[str] = None,
        draft: bool = False
    ) -> PullRequest:
        """
        Create pull request with translated code.
        
        Args:
            branch_name: Name for new branch
            title: PR title
            body: PR description
            commit_message: Commit message (defaults to title)
            draft: Create as draft PR
            
        Returns:
            Created PullRequest object
        """
        commit_message = commit_message or title
        
        # Create branch
        self.connector.create_branch(branch_name)
        
        # Commit changes to new branch
        self.workspace.commit_changes(commit_message, branch=branch_name)
        
        # Generate PR body if not provided
        if body is None:
            stats = self.get_stats()
            body = self._generate_pr_body(stats)
        
        # Create pull request
        return self.connector.create_pull_request(
            title=title,
            body=body,
            source_branch=branch_name,
            draft=draft
        )
    
    def _generate_pr_body(self, stats: Dict[str, int]) -> str:
        """Generate PR description from translation stats."""
        return f"""## Automated Framework Migration

**Source Framework:** {self.source_framework}
**Target Framework:** {self.target_framework}

### Translation Summary

- **New Files:** {stats.get('new', 0)}
- **Modified Files:** {stats.get('modified', 0)}
- **Total Changes:** {stats.get('total', 0)}

This pull request was automatically generated by CrossBridge.
Please review the translated code before merging.

### Review Checklist

- [ ] Verify test assertions are correctly translated
- [ ] Check locator strategies are appropriate
- [ ] Ensure setup/teardown logic is preserved
- [ ] Validate any custom helpers or utilities
- [ ] Run tests to confirm functionality
"""
    
    def export_bundle(self, output_dir: str):
        """
        Export translated files to local directory.
        
        Args:
            output_dir: Directory to export to
        """
        self.workspace.export_bundle(output_dir)
    
    def reset(self):
        """Reset workspace and discard changes."""
        self.workspace.reset()


def create_connector(
    repo_url: str,
    token: str,
    base_branch: str = "main",
    username: Optional[str] = None,
    project: Optional[str] = None,
    use_repo_token: bool = False
) -> RepoConnector:
    """
    Create appropriate connector based on repository URL.
    
    Args:
        repo_url: Repository URL (github:owner/repo, gitlab:owner/repo, 
                 bitbucket:workspace/repo, azuredevops:org/project/repo, or full URL)
        token: Authentication token
        base_branch: Default branch name
        username: Username for Bitbucket Cloud (app password authentication, optional with repo token)
        project: Project name for Azure DevOps (required for azuredevops: format)
        use_repo_token: True if using Bitbucket repository access token (no username needed)
        
    Returns:
        RepoConnector instance
        
    Raises:
        ValueError: If repo URL format is invalid
    """
    # Parse repo URL
    if repo_url.startswith('github:'):
        provider = 'github'
        repo_path = repo_url[7:]  # Remove 'github:' prefix
    elif repo_url.startswith('gitlab:'):
        provider = 'gitlab'
        repo_path = repo_url[7:]  # Remove 'gitlab:' prefix
    elif repo_url.startswith('bitbucket:'):
        provider = 'bitbucket'
        repo_path = repo_url[10:]  # Remove 'bitbucket:' prefix
    elif repo_url.startswith('azuredevops:') or repo_url.startswith('ado:'):
        provider = 'azuredevops'
        prefix_len = 12 if repo_url.startswith('azuredevops:') else 4
        repo_path = repo_url[prefix_len:]  # Remove prefix
    elif 'github.com' in repo_url:
        provider = 'github'
        # Extract owner/repo from URL
        match = re.search(r'github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        repo_path = f"{match.group(1)}/{match.group(2)}"
    elif 'gitlab.com' in repo_url or 'gitlab' in repo_url:
        provider = 'gitlab'
        # Extract owner/repo from URL
        match = re.search(r'gitlab\.[^/]+[/:]([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
        if not match:
            raise ValueError(f"Invalid GitLab URL: {repo_url}")
        repo_path = f"{match.group(1)}/{match.group(2)}"
    elif 'bitbucket.org' in repo_url or 'bitbucket' in repo_url:
        provider = 'bitbucket'
        # Extract workspace/repo from URL
        match = re.search(r'bitbucket\.[^/]+[/:]([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
        if not match:
            raise ValueError(f"Invalid Bitbucket URL: {repo_url}")
        repo_path = f"{match.group(1)}/{match.group(2)}"
    elif 'dev.azure.com' in repo_url or 'visualstudio.com' in repo_url:
        provider = 'azuredevops'
        # Extract org/project/repo from Azure DevOps URL
        # Format: https://dev.azure.com/{org}/{project}/_git/{repo}
        # Or: https://{org}.visualstudio.com/{project}/_git/{repo}
        if 'dev.azure.com' in repo_url:
            match = re.search(r'dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+?)(?:\.git)?$', repo_url)
        else:
            match = re.search(r'([^.]+)\.visualstudio\.com/([^/]+)/_git/([^/]+?)(?:\.git)?$', repo_url)
        
        if not match:
            raise ValueError(f"Invalid Azure DevOps URL: {repo_url}")
        repo_path = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
    elif '_git' in repo_url or 'tfs' in repo_url.lower():
        # TFS / Azure DevOps Server on-prem
        provider = 'azuredevops'
        # Try to extract from TFS/Azure DevOps Server URL
        # Format 1: http://server:port/tfs/collection/project/_git/repo
        # Format 2: http://server:port/tfs/project/_git/repo (DefaultCollection implied)
        match = re.search(r'/tfs/([^/]+)/([^/]+)/_git/([^/]+?)(?:\.git)?$', repo_url, re.IGNORECASE)
        if match:
            # Could be collection/project/repo or project-path/sub-project/repo
            # For TFS, organization = collection or first part of project path
            repo_path = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
        else:
            # Try without tfs prefix
            match = re.search(r'/([^/]+)/([^/]+)/_git/([^/]+?)(?:\.git)?$', repo_url)
            if not match:
                raise ValueError(f"Invalid TFS/Azure DevOps Server URL: {repo_url}")
            repo_path = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
    else:
        raise ValueError(
            f"Unsupported repository URL: {repo_url}\n"
            f"Expected format: github:owner/repo, gitlab:owner/repo, "
            f"bitbucket:workspace/repo, azuredevops:org/project/repo, or full URL"
        )
    
    # Parse path based on provider
    if provider == 'azuredevops':
        # Azure DevOps needs org/project/repo
        parts = repo_path.split('/')
        if len(parts) == 3:
            org, proj, repo = parts
        elif len(parts) == 1 and project:
            # Format: azuredevops:repo with project parameter
            org = repo_path  # Actually the org
            proj = project
            repo = None  # Will need to be specified differently
            raise ValueError(
                f"Invalid Azure DevOps format. Use: azuredevops:org/project/repo"
            )
        else:
            raise ValueError(
                f"Invalid Azure DevOps path: {repo_path}. "
                f"Expected: org/project/repo"
            )
        
        from .azuredevops import AzureDevOpsConnector
        # Extract server URL if present
        server_url = None
        if 'dev.azure.com' not in repo_url and 'visualstudio.com' not in repo_url and provider == 'azuredevops':
            # Extract base URL for on-prem TFS
            if '://' in repo_url:
                # For TFS: http://server:port/tfs -> this is the base URL
                if '/tfs' in repo_url.lower():
                    server_url = repo_url.split('/_git')[0]
                    # Ensure we include the full path up to but not including the repo
                    # http://msptfsapp01:8080/tfs/UDP/UDPAuto -> base URL
                else:
                    server_url = repo_url.split('/_git')[0].rsplit('/', 2)[0]
        
        return AzureDevOpsConnector(org, proj, repo, token, base_branch, url=server_url, username=username)
    else:
        # GitHub, GitLab, Bitbucket need owner/repo
        parts = repo_path.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid repo path: {repo_path}. Expected: owner/repo")
        
        owner, repo = parts
        
        # Create connector
        if provider == 'github':
            return GitHubConnector(owner, repo, token, base_branch)
        elif provider == 'gitlab':
            return GitLabConnector(owner, repo, token, base_branch)
        elif provider == 'bitbucket':
            from .bitbucket import BitbucketConnector
            return BitbucketConnector(
                owner, 
                repo, 
                token, 
                base_branch, 
                is_cloud=True, 
                username=username,
                use_repo_token=use_repo_token
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
