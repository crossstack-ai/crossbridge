"""
GitLab repository connector implementation.

Uses the python-gitlab library to interact with GitLab's REST API for repo-native
transformations without requiring local clones.
"""

from typing import Optional, List
from datetime import datetime

try:
    import gitlab
    from gitlab.exceptions import GitlabError, GitlabGetError, GitlabAuthenticationError
    GITLAB_AVAILABLE = True
except ImportError:
    GITLAB_AVAILABLE = False

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


class GitLabConnector(RepoConnector):
    """
    GitLab repository connector using python-gitlab.
    
    Supports:
    - gitlab.com and self-hosted GitLab instances
    - Personal Access Tokens (PAT)
    - Project access tokens
    - Branch management
    - Merge request creation
    """
    
    def __init__(self, owner: str, repo: str, token: str, base_branch: str = "main",
                 url: str = "https://gitlab.com"):
        """
        Initialize GitLab connector.
        
        Args:
            owner: GitLab username or group
            repo: Repository (project) name
            token: GitLab Personal Access Token
            base_branch: Default branch name
            url: GitLab instance URL (defaults to gitlab.com)
            
        Raises:
            ImportError: If python-gitlab is not installed
            AuthenticationError: If token is invalid
            RepoNotFoundError: If project doesn't exist or is inaccessible
        """
        if not GITLAB_AVAILABLE:
            raise ImportError(
                "python-gitlab is required for GitLab connector. "
                "Install with: pip install python-gitlab"
            )
        
        self.gitlab_url = url
        self._client = gitlab.Gitlab(url, private_token=token)
        super().__init__(owner, repo, token, base_branch)
    
    def _validate_connection(self):
        """Validate GitLab connection and project access."""
        try:
            self._client.auth()
            project_path = f"{self.owner}/{self.repo}"
            self._project = self._client.projects.get(project_path)
        except GitlabAuthenticationError:
            raise AuthenticationError("Invalid GitLab token")
        except GitlabGetError as e:
            if e.response_code == 404:
                raise RepoNotFoundError(
                    f"Project {self.owner}/{self.repo} not found or access denied"
                )
            elif e.response_code == 403:
                raise AuthenticationError("Access denied to project")
            raise RepoNotFoundError(f"Failed to access project: {str(e)}")
        except GitlabError as e:
            raise RepoNotFoundError(f"GitLab error: {str(e)}")
    
    def list_files(self, path: str = "", ref: Optional[str] = None) -> List[RepoFile]:
        """List files in a directory."""
        ref = ref or self.base_branch
        
        try:
            items = self._project.repository_tree(path=path, ref=ref, all=True)
            
            files = []
            for item in items:
                files.append(RepoFile(
                    path=item['path'],
                    sha=item.get('id'),
                    is_binary=(item['type'] != 'blob')
                ))
            
            return files
            
        except GitlabGetError as e:
            if e.response_code == 404:
                return []  # Path doesn't exist
            raise
        except GitlabError:
            return []
    
    def read_file(self, path: str, ref: Optional[str] = None) -> str:
        """Read file content."""
        ref = ref or self.base_branch
        
        try:
            file_info = self._project.files.get(file_path=path, ref=ref)
            content = file_info.decode()
            
            if isinstance(content, bytes):
                return content.decode('utf-8')
            return content
            
        except GitlabGetError as e:
            if e.response_code == 404:
                raise FileNotFoundError(f"File not found: {path}")
            raise
        except UnicodeDecodeError:
            raise FileNotFoundError(f"{path} is a binary file")
        except GitlabError as e:
            raise FileNotFoundError(f"Failed to read file: {str(e)}")
    
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
        default_branch = self._project.default_branch
        
        for branch in self._project.branches.list(all=True):
            branches.append(RepoBranch(
                name=branch.name,
                sha=branch.commit['id'],
                is_default=(branch.name == default_branch)
            ))
        
        return branches
    
    def get_branch(self, name: str) -> RepoBranch:
        """Get information about a specific branch."""
        try:
            branch = self._project.branches.get(name)
            return RepoBranch(
                name=branch.name,
                sha=branch.commit['id'],
                is_default=(branch.name == self._project.default_branch)
            )
        except GitlabGetError as e:
            if e.response_code == 404:
                raise BranchNotFoundError(f"Branch not found: {name}")
            raise
    
    def create_branch(self, name: str, from_branch: Optional[str] = None) -> RepoBranch:
        """Create a new branch."""
        from_branch = from_branch or self.base_branch
        
        try:
            branch = self._project.branches.create({
                'branch': name,
                'ref': from_branch
            })
            
            return RepoBranch(
                name=branch.name,
                sha=branch.commit['id'],
                is_default=False
            )
            
        except GitlabError as e:
            if "already exists" in str(e).lower():
                raise ValueError(f"Branch {name} already exists")
            raise
    
    def delete_branch(self, name: str):
        """Delete a branch."""
        try:
            self._project.branches.delete(name)
        except GitlabGetError as e:
            if e.response_code == 404:
                raise BranchNotFoundError(f"Branch not found: {name}")
            raise
    
    def write_file(self, path: str, content: str, message: str,
                   branch: Optional[str] = None) -> RepoFile:
        """Create or update a file."""
        branch = branch or self.base_branch
        
        try:
            # Check if file exists
            try:
                file_info = self._project.files.get(file_path=path, ref=branch)
                # Update existing file
                file_info.content = content
                file_info.save(branch=branch, commit_message=message)
                
                return RepoFile(
                    path=path,
                    content=content,
                    sha=file_info.last_commit_id,
                    size=len(content.encode('utf-8'))
                )
            except GitlabGetError as e:
                if e.response_code == 404:
                    # Create new file
                    file_info = self._project.files.create({
                        'file_path': path,
                        'branch': branch,
                        'content': content,
                        'commit_message': message
                    })
                    
                    return RepoFile(
                        path=path,
                        content=content,
                        sha=file_info.last_commit_id,
                        size=len(content.encode('utf-8'))
                    )
                raise
                
        except GitlabError as e:
            if "branch" in str(e).lower() and "not found" in str(e).lower():
                raise BranchNotFoundError(f"Branch not found: {branch}")
            raise
    
    def delete_file(self, path: str, message: str, branch: Optional[str] = None):
        """Delete a file."""
        branch = branch or self.base_branch
        
        try:
            file_info = self._project.files.get(file_path=path, ref=branch)
            file_info.delete(branch=branch, commit_message=message)
        except GitlabGetError as e:
            if e.response_code == 404:
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
        """Create a merge request (GitLab's equivalent of pull request)."""
        target_branch = target_branch or self.base_branch
        
        try:
            mr_data = {
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
                'description': body,
            }
            
            # GitLab native draft support (modern API)
            # Note: GitLab 13.2+ uses 'draft' parameter, older versions use 'WIP:' prefix
            if draft:
                # Try modern draft parameter first
                try:
                    mr_data['draft'] = True
                except Exception:
                    # Fallback to WIP prefix for older GitLab versions
                    mr_data['title'] = f"Draft: {title}"
            
            mr = self._project.mergerequests.create(mr_data)
            
            return PullRequest(
                number=mr.iid,
                title=mr.title,
                body=mr.description or "",
                source_branch=source_branch,
                target_branch=target_branch,
                url=mr.web_url,
                state=mr.state,
                created_at=datetime.fromisoformat(mr.created_at.replace('Z', '+00:00'))
            )
            
        except GitlabError as e:
            raise ValueError(f"Merge request creation failed: {str(e)}")
    
    def get_pull_request(self, number: int) -> PullRequest:
        """Get information about a merge request."""
        try:
            mr = self._project.mergerequests.get(number)
            
            return PullRequest(
                number=mr.iid,
                title=mr.title,
                body=mr.description or "",
                source_branch=mr.source_branch,
                target_branch=mr.target_branch,
                url=mr.web_url,
                state=mr.state,
                created_at=datetime.fromisoformat(mr.created_at.replace('Z', '+00:00'))
            )
            
        except GitlabGetError as e:
            if e.response_code == 404:
                raise ValueError(f"Merge request #{number} not found")
            raise
    
    def list_pull_requests(self, state: str = "open") -> List[PullRequest]:
        """List merge requests."""
        # Convert state format (GitHub uses 'open', 'closed', 'all')
        # GitLab uses 'opened', 'closed', 'merged', 'all'
        gitlab_state = {
            'open': 'opened',
            'closed': 'closed',
            'all': 'all'
        }.get(state, state)
        
        prs = []
        
        for mr in self._project.mergerequests.list(state=gitlab_state, all=True):
            prs.append(PullRequest(
                number=mr.iid,
                title=mr.title,
                body=mr.description or "",
                source_branch=mr.source_branch,
                target_branch=mr.target_branch,
                url=mr.web_url,
                state=mr.state,
                created_at=datetime.fromisoformat(mr.created_at.replace('Z', '+00:00'))
            ))
        
        return prs
    
    def get_repo_url(self) -> str:
        """Get the GitLab project URL."""
        return f"{self.gitlab_url}/{self.owner}/{self.repo}"
