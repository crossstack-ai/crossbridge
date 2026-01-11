"""
Azure DevOps / TFS (Team Foundation Server) repository connector implementation.

Supports both Azure DevOps Services (cloud) and Azure DevOps Server / TFS (on-premises).
"""

from typing import List, Optional
import base64
from .base import (
    RepoConnector, RepoFile, RepoBranch, PullRequest,
    RepoNotFoundError, FileNotFoundError, BranchNotFoundError,
    AuthenticationError, RateLimitError
)

try:
    from azure.devops.connection import Connection
    from msrest.authentication import BasicAuthentication
    from azure.devops.v7_0.git.models import (
        GitPullRequest,
        GitPullRequestSearchCriteria,
        GitRefUpdate,
        GitCommitRef,
        ItemContent
    )
    AZUREDEVOPS_AVAILABLE = True
except ImportError:
    AZUREDEVOPS_AVAILABLE = False


class AzureDevOpsConnector(RepoConnector):
    """
    Azure DevOps / TFS repository connector using azure-devops library.
    
    Supports both:
    - Azure DevOps Services (dev.azure.com)
    - Azure DevOps Server / TFS (on-premises)
    
    Features:
    - Personal Access Tokens (PAT)
    - Branch management
    - Pull request creation and management
    - File CRUD operations
    
    Example:
        # Azure DevOps Services (Cloud)
        connector = AzureDevOpsConnector(
            "organization",
            "project",
            "repo",
            token="pat_token"
        )
        
        # Azure DevOps Server / TFS (On-Prem)
        connector = AzureDevOpsConnector(
            "collection",
            "project",
            "repo",
            token="pat_token",
            url="https://tfs.company.com"
        )
    """
    
    def __init__(
        self,
        organization: str,
        project: str,
        repo: str,
        token: Optional[str] = None,
        base_branch: str = "main",
        url: Optional[str] = None,
        username: Optional[str] = None
    ):
        """
        Initialize Azure DevOps / TFS connector.
        
        Args:
            organization: Organization name (Services) or Collection name (Server/TFS)
            project: Project name
            repo: Repository name
            token: Personal Access Token or password
            base_branch: Default branch name
            url: Server URL for on-prem (e.g., https://tfs.company.com)
                 If None, uses Azure DevOps Services (dev.azure.com)
            username: Username for TFS (optional, for username/password auth)
        
        Raises:
            ImportError: If azure-devops is not installed
            AuthenticationError: If credentials are invalid
        """
        if not AZUREDEVOPS_AVAILABLE:
            raise ImportError(
                "azure-devops is required for Azure DevOps / TFS support. "
                "Install with: pip install azure-devops"
            )
        
        self.organization = organization
        self.project = project
        self.repo = repo
        self.token = token
        self.username = username
        self.base_branch = base_branch
        self.url = url or f"https://dev.azure.com/{organization}"
        
        try:
            # Create connection
            # For TFS with username/password, use username
            # For PAT authentication, use empty username
            auth_username = username if username else ''
            credentials = BasicAuthentication(auth_username, token)
            self.connection = Connection(base_url=self.url, creds=credentials)
            
            # Get Git client
            self.git_client = self.connection.clients.get_git_client()
            
        except Exception as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                raise AuthenticationError(f"Authentication failed: {e}")
            raise
    
    def _validate_connection(self):
        """Validate connection to Azure DevOps repository."""
        try:
            # Try to get repository info
            self.git_client.get_repository(
                repository_id=self.repo,
                project=self.project
            )
        except Exception as e:
            if "404" in str(e):
                raise RepoNotFoundError(
                    f"Repository not found: {self.project}/{self.repo}"
                )
            elif "401" in str(e) or "403" in str(e):
                raise AuthenticationError(f"Authentication failed: {e}")
            # Don't fail on other errors during initialization
            pass
    
    def list_files(self, path: str = "", branch: Optional[str] = None) -> List[RepoFile]:
        """
        List files in a directory.
        
        Args:
            path: Directory path (empty for root)
            branch: Branch name (defaults to base_branch)
        
        Returns:
            List of RepoFile objects
        """
        ref = branch or self.base_branch
        files = []
        
        try:
            # Get items in path
            items = self.git_client.get_items(
                repository_id=self.repo,
                project=self.project,
                scope_path=path or "/",
                version_descriptor={'version': ref, 'version_type': 'branch'},
                recursion_level='OneLevel'
            )
            
            for item in items:
                if not item.is_folder:
                    files.append(RepoFile(
                        path=item.path.lstrip('/'),
                        size=item.size or 0,
                        sha=item.object_id or ""
                    ))
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"Path not found: {path}")
            raise
        
        return files
    
    def read_file(self, path: str, branch: Optional[str] = None) -> str:
        """
        Read file content.
        
        Args:
            path: File path
            branch: Branch name (defaults to base_branch)
        
        Returns:
            File content as string
        """
        ref = branch or self.base_branch
        
        try:
            # Get file content
            item = self.git_client.get_item(
                repository_id=self.repo,
                project=self.project,
                path=path if path.startswith('/') else f'/{path}',
                version_descriptor={'version': ref, 'version_type': 'branch'},
                include_content=True
            )
            
            return item.content
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def write_file(
        self,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None
    ) -> None:
        """
        Create or update a file.
        
        Args:
            path: File path
            content: File content
            message: Commit message
            branch: Branch name (defaults to base_branch)
        """
        ref = branch or self.base_branch
        
        try:
            # Get current branch ref
            refs = self.git_client.get_refs(
                repository_id=self.repo,
                project=self.project,
                filter=f'heads/{ref}'
            )
            
            if not refs:
                raise BranchNotFoundError(f"Branch not found: {ref}")
            
            old_object_id = refs[0].object_id
            
            # Create push with file change
            push = {
                'refUpdates': [{
                    'name': f'refs/heads/{ref}',
                    'oldObjectId': old_object_id
                }],
                'commits': [{
                    'comment': message,
                    'changes': [{
                        'changeType': 'add',  # or 'edit' if file exists
                        'item': {'path': path if path.startswith('/') else f'/{path}'},
                        'newContent': {
                            'content': content,
                            'contentType': 'rawtext'
                        }
                    }]
                }]
            }
            
            self.git_client.create_push(
                push=push,
                repository_id=self.repo,
                project=self.project
            )
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"Cannot write to: {path}")
            raise
    
    def delete_file(
        self,
        path: str,
        message: str,
        branch: Optional[str] = None
    ) -> None:
        """
        Delete a file.
        
        Args:
            path: File path
            message: Commit message
            branch: Branch name (defaults to base_branch)
        """
        ref = branch or self.base_branch
        
        try:
            # Get current branch ref
            refs = self.git_client.get_refs(
                repository_id=self.repo,
                project=self.project,
                filter=f'heads/{ref}'
            )
            
            if not refs:
                raise BranchNotFoundError(f"Branch not found: {ref}")
            
            old_object_id = refs[0].object_id
            
            # Create push with file deletion
            push = {
                'refUpdates': [{
                    'name': f'refs/heads/{ref}',
                    'oldObjectId': old_object_id
                }],
                'commits': [{
                    'comment': message,
                    'changes': [{
                        'changeType': 'delete',
                        'item': {'path': path if path.startswith('/') else f'/{path}'}
                    }]
                }]
            }
            
            self.git_client.create_push(
                push=push,
                repository_id=self.repo,
                project=self.project
            )
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def file_exists(self, path: str, branch: Optional[str] = None) -> bool:
        """
        Check if a file exists.
        
        Args:
            path: File path
            branch: Branch name (defaults to base_branch)
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.read_file(path, branch)
            return True
        except FileNotFoundError:
            return False
    
    def create_branch(self, branch_name: str, from_branch: Optional[str] = None) -> RepoBranch:
        """
        Create a new branch.
        
        Args:
            branch_name: Name for the new branch
            from_branch: Source branch (defaults to base_branch)
        
        Returns:
            RepoBranch object
        """
        source = from_branch or self.base_branch
        
        try:
            # Get source branch ref
            refs = self.git_client.get_refs(
                repository_id=self.repo,
                project=self.project,
                filter=f'heads/{source}'
            )
            
            if not refs:
                raise BranchNotFoundError(f"Source branch not found: {source}")
            
            source_object_id = refs[0].object_id
            
            # Create new branch
            ref_update = {
                'name': f'refs/heads/{branch_name}',
                'oldObjectId': '0000000000000000000000000000000000000000',
                'newObjectId': source_object_id
            }
            
            result = self.git_client.update_refs(
                ref_updates=[ref_update],
                repository_id=self.repo,
                project=self.project
            )
            
            return RepoBranch(
                name=branch_name,
                sha=source_object_id
            )
        except Exception as e:
            if "409" in str(e) or "already exists" in str(e).lower():
                raise ValueError(f"Branch already exists: {branch_name}")
            raise
    
    def delete_branch(self, branch_name: str) -> None:
        """
        Delete a branch.
        
        Args:
            branch_name: Branch name to delete
        """
        try:
            # Get branch ref
            refs = self.git_client.get_refs(
                repository_id=self.repo,
                project=self.project,
                filter=f'heads/{branch_name}'
            )
            
            if not refs:
                raise BranchNotFoundError(f"Branch not found: {branch_name}")
            
            # Delete branch
            ref_update = {
                'name': f'refs/heads/{branch_name}',
                'oldObjectId': refs[0].object_id,
                'newObjectId': '0000000000000000000000000000000000000000'
            }
            
            self.git_client.update_refs(
                ref_updates=[ref_update],
                repository_id=self.repo,
                project=self.project
            )
        except Exception as e:
            if "404" in str(e):
                raise BranchNotFoundError(f"Branch not found: {branch_name}")
            raise
    
    def list_branches(self) -> List[RepoBranch]:
        """
        List all branches.
        
        Returns:
            List of RepoBranch objects
        """
        branches = []
        
        try:
            refs = self.git_client.get_refs(
                repository_id=self.repo,
                project=self.project,
                filter='heads/'
            )
            
            for ref in refs:
                branch_name = ref.name.replace('refs/heads/', '')
                branches.append(RepoBranch(
                    name=branch_name,
                    sha=ref.object_id
                ))
        except Exception as e:
            raise Exception(f"Failed to list branches: {e}")
        
        return branches
    
    def get_branch(self, branch_name: str) -> RepoBranch:
        """
        Get branch information.
        
        Args:
            branch_name: Branch name
        
        Returns:
            RepoBranch object
        """
        try:
            refs = self.git_client.get_refs(
                repository_id=self.repo,
                project=self.project,
                filter=f'heads/{branch_name}'
            )
            
            if not refs:
                raise BranchNotFoundError(f"Branch not found: {branch_name}")
            
            return RepoBranch(
                name=branch_name,
                sha=refs[0].object_id
            )
        except BranchNotFoundError:
            raise
        except Exception as e:
            if "404" in str(e):
                raise BranchNotFoundError(f"Branch not found: {branch_name}")
            raise
    
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
            source_branch: Source branch name
            target_branch: Target branch (defaults to base_branch)
            draft: Create as draft PR
        
        Returns:
            PullRequest object
        """
        target = target_branch or self.base_branch
        
        try:
            # Create pull request
            pr = {
                'sourceRefName': f'refs/heads/{source_branch}',
                'targetRefName': f'refs/heads/{target}',
                'title': title,
                'description': body,
                'isDraft': draft
            }
            
            result = self.git_client.create_pull_request(
                git_pull_request_to_create=pr,
                repository_id=self.repo,
                project=self.project
            )
            
            # Get web URL
            web_url = f"{self.url}/{self.project}/_git/{self.repo}/pullrequest/{result.pull_request_id}"
            
            return PullRequest(
                number=result.pull_request_id,
                title=title,
                body=body,
                source_branch=source_branch,
                target_branch=target,
                state=result.status.lower() if result.status else "active",
                url=web_url
            )
        except Exception as e:
            raise Exception(f"Failed to create pull request: {e}")
    
    def get_pull_request(self, pr_number: int) -> PullRequest:
        """
        Get pull request information.
        
        Args:
            pr_number: Pull request number/ID
        
        Returns:
            PullRequest object
        """
        try:
            pr = self.git_client.get_pull_request_by_id(
                pull_request_id=pr_number,
                project=self.project
            )
            
            source_branch = pr.source_ref_name.replace('refs/heads/', '') if pr.source_ref_name else ""
            target_branch = pr.target_ref_name.replace('refs/heads/', '') if pr.target_ref_name else ""
            
            web_url = f"{self.url}/{self.project}/_git/{self.repo}/pullrequest/{pr.pull_request_id}"
            
            # Map Azure DevOps status to standard states
            state_map = {
                'active': 'open',
                'completed': 'merged',
                'abandoned': 'closed'
            }
            state = state_map.get(pr.status.lower() if pr.status else 'active', 'open')
            
            return PullRequest(
                number=pr.pull_request_id,
                title=pr.title or "",
                body=pr.description or "",
                source_branch=source_branch,
                target_branch=target_branch,
                state=state,
                url=web_url
            )
        except Exception as e:
            if "404" in str(e):
                raise ValueError(f"Pull request not found: {pr_number}")
            raise
    
    def list_pull_requests(self, state: str = "open") -> List[PullRequest]:
        """
        List pull requests.
        
        Args:
            state: PR state filter ('open', 'closed', 'all')
        
        Returns:
            List of PullRequest objects
        """
        prs = []
        
        try:
            # Map state to Azure DevOps status
            status_map = {
                'open': 'active',
                'closed': 'completed',
                'all': 'all'
            }
            azure_status = status_map.get(state, 'active')
            
            # Get pull requests
            search_criteria = GitPullRequestSearchCriteria(
                repository_id=self.repo,
                status=azure_status if azure_status != 'all' else None
            )
            
            results = self.git_client.get_pull_requests(
                repository_id=self.repo,
                project=self.project,
                search_criteria=search_criteria
            )
            
            for pr in results:
                source_branch = pr.source_ref_name.replace('refs/heads/', '') if pr.source_ref_name else ""
                target_branch = pr.target_ref_name.replace('refs/heads/', '') if pr.target_ref_name else ""
                
                web_url = f"{self.url}/{self.project}/_git/{self.repo}/pullrequest/{pr.pull_request_id}"
                
                # Map status
                state_map = {
                    'active': 'open',
                    'completed': 'merged',
                    'abandoned': 'closed'
                }
                pr_state = state_map.get(pr.status.lower() if pr.status else 'active', 'open')
                
                prs.append(PullRequest(
                    number=pr.pull_request_id,
                    title=pr.title or "",
                    body=pr.description or "",
                    source_branch=source_branch,
                    target_branch=target_branch,
                    state=pr_state,
                    url=web_url
                ))
        except Exception as e:
            raise Exception(f"Failed to list pull requests: {e}")
        
        return prs
