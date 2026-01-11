"""
GitHub repository connector implementation.

Uses the PyGithub library to interact with GitHub's REST API for repo-native
transformations without requiring local clones.
"""

from typing import Optional, List
from datetime import datetime
import base64

try:
    from github import Github, GithubException, UnknownObjectException
    from github.Repository import Repository
    from github.ContentFile import ContentFile
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

from .base import (
    RepoConnector,
    RepoFile,
    RepoBranch,
    PullRequest,
    RepoNotFoundError,
    FileNotFoundError,
    BranchNotFoundError,
    AuthenticationError,
    RateLimitError,
)


class GitHubConnector(RepoConnector):
    """
    GitHub repository connector using PyGithub.
    
    Supports:
    - Public and private repositories
    - Personal Access Tokens (PAT)
    - Fine-grained tokens
    - Branch management
    - Pull request creation
    """
    
    def __init__(self, owner: str, repo: str, token: str, base_branch: str = "main"):
        """
        Initialize GitHub connector.
        
        Args:
            owner: GitHub username or organization
            repo: Repository name
            token: GitHub Personal Access Token
            base_branch: Default branch name
            
        Raises:
            ImportError: If PyGithub is not installed
            AuthenticationError: If token is invalid
            RepoNotFoundError: If repository doesn't exist or is inaccessible
        """
        if not GITHUB_AVAILABLE:
            raise ImportError(
                "PyGithub is required for GitHub connector. "
                "Install with: pip install PyGithub"
            )
        
        self._client = Github(token)
        super().__init__(owner, repo, token, base_branch)
    
    def _validate_connection(self):
        """Validate GitHub connection and repository access."""
        try:
            self._repo: Repository = self._client.get_repo(f"{self.owner}/{self.repo}")
            # Test access by getting repo info
            _ = self._repo.full_name
        except UnknownObjectException:
            raise RepoNotFoundError(
                f"Repository {self.owner}/{self.repo} not found or access denied"
            )
        except GithubException as e:
            if e.status == 401:
                raise AuthenticationError("Invalid GitHub token")
            elif e.status == 403:
                raise RateLimitError("GitHub API rate limit exceeded")
            else:
                raise RepoNotFoundError(f"Failed to access repository: {e.data.get('message', str(e))}")
    
    def list_files(self, path: str = "", ref: Optional[str] = None) -> List[RepoFile]:
        """List files in a directory."""
        ref = ref or self.base_branch
        
        try:
            contents = self._repo.get_contents(path, ref=ref)
            
            # Handle single file vs directory
            if not isinstance(contents, list):
                contents = [contents]
            
            files = []
            for content in contents:
                files.append(RepoFile(
                    path=content.path,
                    sha=content.sha,
                    size=content.size,
                    is_binary=content.encoding != 'base64' if hasattr(content, 'encoding') else False
                ))
            
            return files
            
        except UnknownObjectException:
            return []  # Path doesn't exist
        except GithubException as e:
            if e.status == 404:
                return []
            raise
    
    def read_file(self, path: str, ref: Optional[str] = None) -> str:
        """Read file content."""
        ref = ref or self.base_branch
        
        try:
            content = self._repo.get_contents(path, ref=ref)
            
            if isinstance(content, list):
                raise FileNotFoundError(f"{path} is a directory, not a file")
            
            # Decode base64 content
            if content.encoding == 'base64':
                return content.decoded_content.decode('utf-8')
            else:
                raise FileNotFoundError(f"{path} is not a text file")
                
        except UnknownObjectException:
            raise FileNotFoundError(f"File not found: {path}")
        except UnicodeDecodeError:
            raise FileNotFoundError(f"{path} is a binary file")
        except GithubException as e:
            if e.status == 404:
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def file_exists(self, path: str, ref: Optional[str] = None) -> bool:
        """Check if a file exists."""
        try:
            self.read_file(path, ref)
            return True
        except FileNotFoundError:
            return False
    
    def list_branches(self) -> List[RepoBranch]:
        """List all branches."""
        branches = []
        default_branch = self._repo.default_branch
        
        for branch in self._repo.get_branches():
            branches.append(RepoBranch(
                name=branch.name,
                sha=branch.commit.sha,
                is_default=(branch.name == default_branch)
            ))
        
        return branches
    
    def get_branch(self, name: str) -> RepoBranch:
        """Get information about a specific branch."""
        try:
            branch = self._repo.get_branch(name)
            return RepoBranch(
                name=branch.name,
                sha=branch.commit.sha,
                is_default=(branch.name == self._repo.default_branch)
            )
        except UnknownObjectException:
            raise BranchNotFoundError(f"Branch not found: {name}")
        except GithubException as e:
            if e.status == 404:
                raise BranchNotFoundError(f"Branch not found: {name}")
            raise
    
    def create_branch(self, name: str, from_branch: Optional[str] = None) -> RepoBranch:
        """Create a new branch."""
        from_branch = from_branch or self.base_branch
        
        try:
            # Get source branch
            source = self._repo.get_branch(from_branch)
            
            # Create new branch reference
            ref = self._repo.create_git_ref(
                ref=f"refs/heads/{name}",
                sha=source.commit.sha
            )
            
            return RepoBranch(
                name=name,
                sha=source.commit.sha,
                is_default=False
            )
            
        except GithubException as e:
            if e.status == 422:
                raise ValueError(f"Branch {name} already exists")
            raise
    
    def delete_branch(self, name: str):
        """Delete a branch."""
        try:
            ref = self._repo.get_git_ref(f"heads/{name}")
            ref.delete()
        except UnknownObjectException:
            raise BranchNotFoundError(f"Branch not found: {name}")
        except GithubException as e:
            if e.status == 404:
                raise BranchNotFoundError(f"Branch not found: {name}")
            raise
    
    def write_file(self, path: str, content: str, message: str,
                   branch: Optional[str] = None) -> RepoFile:
        """Create or update a file."""
        branch = branch or self.base_branch
        
        try:
            # Check if file exists
            try:
                existing = self._repo.get_contents(path, ref=branch)
                # Update existing file
                result = self._repo.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=existing.sha,
                    branch=branch
                )
                return RepoFile(
                    path=path,
                    content=content,
                    sha=result['commit'].sha,
                    size=len(content.encode('utf-8'))
                )
            except UnknownObjectException:
                # Create new file
                result = self._repo.create_file(
                    path=path,
                    message=message,
                    content=content,
                    branch=branch
                )
                return RepoFile(
                    path=path,
                    content=content,
                    sha=result['commit'].sha,
                    size=len(content.encode('utf-8'))
                )
                
        except GithubException as e:
            if e.status == 404:
                raise BranchNotFoundError(f"Branch not found: {branch}")
            raise
    
    def delete_file(self, path: str, message: str, branch: Optional[str] = None):
        """Delete a file."""
        branch = branch or self.base_branch
        
        try:
            content = self._repo.get_contents(path, ref=branch)
            self._repo.delete_file(
                path=path,
                message=message,
                sha=content.sha,
                branch=branch
            )
        except UnknownObjectException:
            raise FileNotFoundError(f"File not found: {path}")
        except GithubException as e:
            if e.status == 404:
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: Optional[str] = None,
        draft: bool = False
    ) -> PullRequest:
        """Create a pull request.
        
        Args:
            title: PR title
            body: PR description
            source_branch: Source branch name
            target_branch: Target branch (defaults to base_branch)
            draft: Create as draft PR (GitHub native support)
        
        Returns:
            PullRequest object
        """
        target_branch = target_branch or self.base_branch
        
        try:
            pr = self._repo.create_pull(
                title=title,
                body=body,
                head=source_branch,
                base=target_branch,
                draft=draft
            )
            
            return PullRequest(
                number=pr.number,
                title=pr.title,
                body=pr.body,
                source_branch=source_branch,
                target_branch=target_branch,
                url=pr.html_url,
                state=pr.state,
                created_at=pr.created_at
            )
            
        except GithubException as e:
            if e.status == 422:
                raise ValueError(f"Pull request validation failed: {e.data.get('message', str(e))}")
            raise
    
    def get_pull_request(self, number: int) -> PullRequest:
        """Get information about a pull request."""
        try:
            pr = self._repo.get_pull(number)
            
            return PullRequest(
                number=pr.number,
                title=pr.title,
                body=pr.body or "",
                source_branch=pr.head.ref,
                target_branch=pr.base.ref,
                url=pr.html_url,
                state=pr.state,
                created_at=pr.created_at
            )
            
        except UnknownObjectException:
            raise ValueError(f"Pull request #{number} not found")
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"Pull request #{number} not found")
            raise
    
    def list_pull_requests(self, state: str = "open") -> List[PullRequest]:
        """List pull requests."""
        prs = []
        
        for pr in self._repo.get_pulls(state=state):
            prs.append(PullRequest(
                number=pr.number,
                title=pr.title,
                body=pr.body or "",
                source_branch=pr.head.ref,
                target_branch=pr.base.ref,
                url=pr.html_url,
                state=pr.state,
                created_at=pr.created_at
            ))
        
        return prs
    
    def get_repo_url(self) -> str:
        """Get the GitHub repository URL."""
        return f"https://github.com/{self.owner}/{self.repo}"
