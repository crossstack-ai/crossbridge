"""
Base abstractions for repository connectors.

Provides platform-agnostic interfaces for interacting with remote repositories
without requiring local clones.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class RepoFile:
    """Represents a file in a repository."""
    path: str
    content: Optional[str] = None
    sha: Optional[str] = None
    size: Optional[int] = None
    is_binary: bool = False


@dataclass
class RepoBranch:
    """Represents a branch in a repository."""
    name: str
    sha: str
    is_default: bool = False


@dataclass
class PullRequest:
    """Represents a pull request."""
    number: int
    title: str
    body: str
    source_branch: str
    target_branch: str
    url: str
    state: str  # 'open', 'closed', 'merged'
    created_at: Optional[datetime] = None


class RepoConnector(ABC):
    """
    Abstract base class for repository connectors.
    
    All provider implementations (GitHub, GitLab, Bitbucket) must implement
    this interface to ensure consistent behavior across platforms.
    """
    
    def __init__(self, owner: str, repo: str, token: str, base_branch: str = "main"):
        """
        Initialize repository connector.
        
        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            token: Authentication token
            base_branch: Default branch name
        """
        self.owner = owner
        self.repo = repo
        self.token = token
        self.base_branch = base_branch
        self._validate_connection()
    
    @abstractmethod
    def _validate_connection(self):
        """Validate that the connection to the repository is working."""
        pass
    
    @abstractmethod
    def list_files(self, path: str = "", ref: Optional[str] = None) -> List[RepoFile]:
        """
        List files in a directory.
        
        Args:
            path: Directory path (empty for root)
            ref: Branch/commit reference (defaults to base_branch)
            
        Returns:
            List of RepoFile objects
        """
        pass
    
    @abstractmethod
    def read_file(self, path: str, ref: Optional[str] = None) -> str:
        """
        Read file content.
        
        Args:
            path: File path
            ref: Branch/commit reference (defaults to base_branch)
            
        Returns:
            File content as string
        """
        pass
    
    @abstractmethod
    def file_exists(self, path: str, ref: Optional[str] = None) -> bool:
        """
        Check if a file exists.
        
        Args:
            path: File path
            ref: Branch/commit reference
            
        Returns:
            True if file exists
        """
        pass
    
    @abstractmethod
    def list_branches(self) -> List[RepoBranch]:
        """
        List all branches in the repository.
        
        Returns:
            List of RepoBranch objects
        """
        pass
    
    @abstractmethod
    def get_branch(self, name: str) -> RepoBranch:
        """
        Get information about a specific branch.
        
        Args:
            name: Branch name
            
        Returns:
            RepoBranch object
        """
        pass
    
    @abstractmethod
    def create_branch(self, name: str, from_branch: Optional[str] = None) -> RepoBranch:
        """
        Create a new branch.
        
        Args:
            name: New branch name
            from_branch: Source branch (defaults to base_branch)
            
        Returns:
            Created RepoBranch object
        """
        pass
    
    @abstractmethod
    def delete_branch(self, name: str):
        """
        Delete a branch.
        
        Args:
            name: Branch name to delete
        """
        pass
    
    @abstractmethod
    def write_file(self, path: str, content: str, message: str, 
                   branch: Optional[str] = None) -> RepoFile:
        """
        Create or update a file.
        
        Args:
            path: File path
            content: File content
            message: Commit message
            branch: Target branch (defaults to base_branch)
            
        Returns:
            Updated RepoFile object
        """
        pass
    
    @abstractmethod
    def delete_file(self, path: str, message: str, branch: Optional[str] = None):
        """
        Delete a file.
        
        Args:
            path: File path
            message: Commit message
            branch: Target branch
        """
        pass
    
    @abstractmethod
    def create_pull_request(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: Optional[str] = None,
        draft: bool = False
    ) -> PullRequest:
        """
        Create a pull request.
        
        Args:
            title: PR title
            body: PR description
            source_branch: Source branch with changes
            target_branch: Target branch (defaults to base_branch)
            draft: Create as draft PR
            
        Returns:
            Created PullRequest object
        """
        pass
    
    @abstractmethod
    def get_pull_request(self, number: int) -> PullRequest:
        """
        Get information about a pull request.
        
        Args:
            number: PR number
            
        Returns:
            PullRequest object
        """
        pass
    
    @abstractmethod
    def list_pull_requests(self, state: str = "open") -> List[PullRequest]:
        """
        List pull requests.
        
        Args:
            state: Filter by state ('open', 'closed', 'all')
            
        Returns:
            List of PullRequest objects
        """
        pass
    
    def get_file_tree(self, path: str = "", ref: Optional[str] = None, 
                      pattern: Optional[str] = None) -> List[str]:
        """
        Get a flat list of all file paths recursively.
        
        Args:
            path: Starting directory path
            ref: Branch/commit reference
            pattern: Optional glob pattern to filter files
            
        Returns:
            List of file paths
        """
        import fnmatch
        
        files = []
        items = self.list_files(path, ref)
        
        for item in items:
            if item.path.endswith('/'):  # Directory
                # Recursively get files in subdirectory
                files.extend(self.get_file_tree(item.path.rstrip('/'), ref, pattern))
            else:
                if pattern is None or fnmatch.fnmatch(item.path, pattern):
                    files.append(item.path)
        
        return files
    
    def get_repo_url(self) -> str:
        """Get the repository URL."""
        return f"{self.owner}/{self.repo}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.get_repo_url()})"


class RepoConnectorError(Exception):
    """Base exception for repository connector errors."""
    pass


class RepoNotFoundError(RepoConnectorError):
    """Repository not found or access denied."""
    pass


class FileNotFoundError(RepoConnectorError):
    """File not found in repository."""
    pass


class BranchNotFoundError(RepoConnectorError):
    """Branch not found in repository."""
    pass


class AuthenticationError(RepoConnectorError):
    """Authentication failed."""
    pass


class RateLimitError(RepoConnectorError):
    """API rate limit exceeded."""
    pass
