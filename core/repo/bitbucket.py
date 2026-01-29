"""
Bitbucket repository connector implementation.

Supports both Bitbucket Cloud and Bitbucket Server/Data Center (on-premises).
"""

from typing import List, Optional
import base64
import requests
import time
import urllib3
import warnings
import os
from requests.auth import HTTPBasicAuth

from core.logging import get_logger, LogCategory
from .base import (
    RepoConnector, RepoFile, RepoBranch, PullRequest,
    RepoNotFoundError, FileNotFoundError, BranchNotFoundError,
    AuthenticationError, RateLimitError
)

logger = get_logger(__name__, category=LogCategory.GOVERNANCE)

try:
    from atlassian import Bitbucket
    from atlassian.bitbucket import Cloud as BitbucketCloud
    BITBUCKET_AVAILABLE = True
except ImportError:
    BITBUCKET_AVAILABLE = False


class BitbucketConnector(RepoConnector):
    """
    Bitbucket repository connector using atlassian-python-api.
    
    Supports both:
    - Bitbucket Cloud (bitbucket.org)
    - Bitbucket Server/Data Center (on-premises)
    
    Features:
    - App passwords (Cloud) or personal access tokens (Server)
    - Branch management
    - Pull request creation and management
    - File CRUD operations
    
    Example:
        # Bitbucket Cloud
        connector = BitbucketConnector("owner", "repo", token="app_password", is_cloud=True)
        
        # Bitbucket Server (on-prem)
        connector = BitbucketConnector(
            "project-key", "repo",
            token="personal_token",
            is_cloud=False,
            url="https://bitbucket.company.com"
        )
    """
    
    def __init__(
        self,
        owner: str,
        repo: str,
        token: Optional[str] = None,
        base_branch: str = "main",
        is_cloud: bool = True,
        url: Optional[str] = None,
        username: Optional[str] = None,
        use_repo_token: bool = False
    ):
        """
        Initialize Bitbucket connector.
        
        Args:
            owner: Workspace ID (Cloud) or Project Key (Server)
            repo: Repository slug/name
            token: App password (Cloud), personal access token (Server), or repository access token
            base_branch: Default branch name
            is_cloud: True for Bitbucket Cloud, False for Server/Data Center
            url: Bitbucket Server URL (required for on-prem, ignored for cloud)
            username: Username for Cloud (required with app password, optional with repo token)
            use_repo_token: True if using repository access token (no username needed)
        
        Raises:
            ImportError: If atlassian-python-api is not installed
            AuthenticationError: If credentials are invalid
        """
        if not BITBUCKET_AVAILABLE:
            raise ImportError(
                "atlassian-python-api is required for Bitbucket support. "
                "Install with: pip install atlassian-python-api"
            )
        
        self.owner = owner
        self.repo = repo
        self.token = token
        self.base_branch = base_branch
        self.is_cloud = is_cloud
        self.url = url
        self.username = username
        self.use_repo_token = use_repo_token
        
        # Store password/token for direct API calls (workaround for atlassian-python-api issues)
        self.password = token
        
        # Configure SSL verification for corporate environments
        self._configure_ssl_handling()
        
        try:
            if is_cloud:
                # Bitbucket Cloud
                # Note: App passwords deprecated Sept 2025, replaced with API tokens
                # API tokens (ATATT3xF...) require email address for API authentication
                if use_repo_token:
                    # Repository access token - use token directly without username
                    self.client = BitbucketCloud(
                        url="https://api.bitbucket.org",
                        token=token,
                        cloud=True,
                        verify_ssl=self._ssl_verify
                    )
                else:
                    # API token or app password - both require username/email
                    if not username:
                        raise ValueError(
                            "Username or email address is required for Bitbucket Cloud API tokens. "
                            "Set BITBUCKET_USERNAME environment variable or pass via arguments."
                        )
                    self.client = BitbucketCloud(
                        url="https://api.bitbucket.org",
                        username=username,  # Email address for API tokens, username for app passwords
                        password=token,     # API token or app password
                        cloud=True,
                        verify_ssl=self._ssl_verify
                    )
                self.workspace = owner
                self.repo_slug = repo
            else:
                # Bitbucket Server/Data Center
                if not url:
                    raise ValueError("url is required for Bitbucket Server")
                self.client = Bitbucket(
                    url=url,
                    token=token,
                    cloud=False,
                    verify_ssl=self._ssl_verify
                )
                self.project_key = owner
                self.repo_slug = repo
                
        except Exception as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                raise AuthenticationError(f"Authentication failed: {e}")
            raise
    
    def _configure_ssl_handling(self):
        """
        Configure SSL handling for corporate environments.
        
        Checks environment variables:
        - CROSSBRIDGE_DISABLE_SSL_VERIFY: Set to 'true' to disable SSL verification
        - REQUESTS_CA_BUNDLE: Path to custom CA bundle
        """
        # Check if SSL verification should be disabled (for corporate environments)
        disable_ssl = os.environ.get('CROSSBRIDGE_DISABLE_SSL_VERIFY', 'false').lower() == 'true'
        
        if disable_ssl:
            # Disable SSL warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
            
            # Configure requests to disable SSL verification
            self._ssl_verify = False
            
            # Patch the requests module for this instance
            original_request = requests.Session.request
            
            def patched_request(session_self, method, url, **kwargs):
                kwargs['verify'] = False
                return original_request(session_self, method, url, **kwargs)
            
            requests.Session.request = patched_request
        else:
            self._ssl_verify = True
    
    def _validate_connection(self):
        """Validate connection to Bitbucket repository."""
        try:
            # Try to list branches to validate connection
            if self.is_cloud:
                self.client.get(
                    f"repositories/{self.workspace}/{self.repo_slug}/refs/branches",
                    params={"pagelen": 1}
                )
            else:
                self.client.get_branches(
                    self.project_key,
                    self.repo_slug,
                    limit=1
                )
        except Exception as e:
            if "404" in str(e):
                raise RepoNotFoundError(
                    f"Repository not found: {self.owner}/{self.repo}"
                )
            elif "401" in str(e) or "403" in str(e):
                raise AuthenticationError(f"Authentication failed: {e}")
            # Don't fail on other errors during initialization
            pass
    
    def _get_file_content_cloud(self, path: str, branch: Optional[str] = None) -> str:
        """Get file content from Bitbucket Cloud."""
        ref = branch or self.base_branch
        
        # If ref contains a slash, resolve it to a commit hash first
        if "/" in ref:
            ref = self._get_commit_hash_for_branch(ref)
        
        try:
            # Cloud API endpoint: /2.0/repositories/{workspace}/{repo_slug}/src/{commit}/{path}
            response = self.client.get(
                f"repositories/{self.workspace}/{self.repo_slug}/src/{ref}/{path}"
            )
            return response
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def _get_file_content_server(self, path: str, branch: Optional[str] = None) -> str:
        """Get file content from Bitbucket Server."""
        ref = branch or self.base_branch
        try:
            # Server API: /rest/api/1.0/projects/{projectKey}/repos/{repositorySlug}/browse/{path}
            content = self.client.get_content_of_file(
                self.project_key,
                self.repo_slug,
                path,
                at=ref
            )
            return content
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
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
            if self.is_cloud:
                # Use requests directly to bypass atlassian-python-api URL handling issues
                # Bitbucket Cloud API requires trailing slash for directory listings
                base_url = "https://api.bitbucket.org/2.0"
                
                # Build path with trailing slash
                file_path = path.rstrip('/') + '/' if path else ''
                url = f"{base_url}/repositories/{self.workspace}/{self.repo_slug}/src/{ref}/{file_path}"
                
                # Use HTTPBasicAuth with username (email) and token/password
                auth = HTTPBasicAuth(self.username, self.password)
                response = requests.get(url, auth=auth, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and "values" in data:
                        for item in data["values"]:
                            if item.get("type") == "commit_file":
                                files.append(RepoFile(
                                    path=item["path"],
                                    size=item.get("size", 0),
                                    sha=item.get("commit", {}).get("hash", "")
                                ))
                elif response.status_code == 404:
                    raise FileNotFoundError(f"Path not found: {path}")
                else:
                    raise Exception(f"Failed to list files: {response.status_code} - {response.text}")
            else:
                # Server API
                response = self.client.get_file_list(
                    self.project_key,
                    self.repo_slug,
                    path=path,
                    at=ref
                )
                for item in response:
                    if item.get("type") == "FILE":
                        files.append(RepoFile(
                            path=item["path"],
                            size=item.get("size", 0),
                            sha=""  # Server doesn't provide SHA in list
                        ))
        except FileNotFoundError:
            raise
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"Path not found: {path}")
            raise
        
        return files
    
    def _get_commit_hash_for_branch(self, branch: str) -> str:
        """
        Get commit hash for a branch. Required for branches with slashes.
        
        Args:
            branch: Branch name (may contain slashes like 'feature/branch-name')
            
        Returns:
            Commit hash string
            
        Raises:
            Exception: If branch not found or API call fails
        """
        from urllib.parse import quote
        
        ref_encoded = quote(branch, safe='')
        base_url = "https://api.bitbucket.org/2.0"
        url = f"{base_url}/repositories/{self.workspace}/{self.repo_slug}/refs/branches/{ref_encoded}"
        
        logger.debug(f"Getting commit hash for branch '{branch}': {url}")
        
        auth = HTTPBasicAuth(self.username, self.password)
        response = requests.get(url, auth=auth, timeout=30)
        
        if response.status_code == 200:
            commit_hash = response.json().get('target', {}).get('hash')
            logger.debug(f"Got commit hash for branch '{branch}': {commit_hash}")
            return commit_hash
        else:
            logger.error(f"Failed to get commit hash for branch '{branch}': {response.status_code}")
            raise Exception(f"Could not resolve branch '{branch}' to commit hash: {response.text[:200]}")
    
    def list_all_files(self, path: str = "", branch: Optional[str] = None, pattern: Optional[str] = None, 
                       progress_callback: Optional[callable] = None) -> List[RepoFile]:
        """
        Recursively list all files in a directory tree.
        
        Args:
            path: Directory path (empty for root)
            branch: Branch name (defaults to base_branch)
            pattern: Optional file extension filter (e.g., ".java")
            progress_callback: Optional callback(current_dir, file_count) for progress updates
        
        Returns:
            List of RepoFile objects (directories are traversed, not returned)
        """
        from urllib.parse import quote
        
        ref = branch or self.base_branch
        
        logger.debug(f"list_all_files called with: path='{path}', branch param='{branch}', resolved ref='{ref}', self.base_branch='{self.base_branch}', pattern='{pattern}'")
        
        # For Bitbucket Cloud, resolve branch to commit hash to handle branches with slashes
        if self.is_cloud and '/' in ref:
            logger.debug(f"Branch '{ref}' contains '/', resolving to commit hash first")
            ref_for_api = self._get_commit_hash_for_branch(ref)
        else:
            # No slash in branch name, can use directly (or URL encode for safety)
            ref_for_api = quote(ref, safe='') if self.is_cloud else ref
        
        all_files = []
        
        def _list_recursive(current_path: str):
            try:
                # Show progress if callback provided
                if progress_callback:
                    display_path = current_path or "(root)"
                    progress_callback(display_path, len(all_files))
                
                if self.is_cloud:
                    # Use requests directly with pagination support
                    base_url = "https://api.bitbucket.org/2.0"
                    # Don't add trailing slash - let API handle it naturally
                    file_path = current_path.rstrip('/') if current_path else ''
                    # Use resolved ref (either commit hash or branch name)
                    url = f"{base_url}/repositories/{self.workspace}/{self.repo_slug}/src/{ref_for_api}/{file_path}"
                    
                    logger.debug(f"Bitbucket API URL: {url}")
                    logger.debug(f"Workspace: {self.workspace}, Repo: {self.repo_slug}, Branch: {ref}, Ref: {ref_for_api}, Path: {file_path}")
                    
                    auth = HTTPBasicAuth(self.username, self.password)
                    
                    # Handle pagination - keep fetching while there's a "next" URL
                    while url:
                        response = requests.get(url, auth=auth, timeout=30)
                        
                        logger.debug(f"Response status: {response.status_code}")
                        
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, dict) and "values" in data:
                                logger.debug(f"Found {len(data['values'])} items in directory")
                                for item in data["values"]:
                                    if item.get("type") == "commit_file":
                                        # It's a file
                                        file_path_item = item["path"]
                                        if not pattern or file_path_item.endswith(pattern):
                                            all_files.append(RepoFile(
                                                path=file_path_item,
                                                size=item.get("size", 0),
                                                sha=item.get("commit", {}).get("hash", "")
                                            ))
                                    elif item.get("type") == "commit_directory":
                                        # It's a directory - recurse into it
                                        dir_path = item["path"]
                                        _list_recursive(dir_path)
                                
                                # Check for next page
                                url = data.get("next")
                                if url:
                                    logger.debug(f"Fetching next page: {len(all_files)} files so far")
                                    # Update progress after each page
                                    if progress_callback:
                                        display_path = current_path or "(root)"
                                        progress_callback(display_path, len(all_files))
                                else:
                                    logger.debug(f"No more pages. Total files collected: {len(all_files)}")
                            else:
                                logger.warning(f"Unexpected response format: {data}")
                                break
                        else:
                            logger.warning(f"Failed to list files: HTTP {response.status_code}")
                            if response.status_code == 404:
                                logger.warning(f"Path not found: {current_path}")
                            break
                else:
                    # Server API - recursive approach
                    response = self.client.get_file_list(
                        self.project_key,
                        self.repo_slug,
                        path=current_path,
                        at=ref
                    )
                    for item in response:
                        if item.get("type") == "FILE":
                            file_path = item["path"]
                            if not pattern or file_path.endswith(pattern):
                                all_files.append(RepoFile(
                                    path=file_path,
                                    size=item.get("size", 0),
                                    sha=""
                                ))
                        elif item.get("type") == "DIRECTORY":
                            _list_recursive(item["path"])
            except Exception as e:
                # Silently skip inaccessible directories
                pass
        
        _list_recursive(path)
        return all_files
    
    def read_file(self, path: str, branch: Optional[str] = None) -> str:
        """
        Read file content.
        
        Args:
            path: File path
            branch: Branch name (defaults to base_branch)
        
        Returns:
            File content as string
        """
        if self.is_cloud:
            return self._get_file_content_cloud(path, branch)
        else:
            return self._get_file_content_server(path, branch)
    
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
            if self.is_cloud:
                # Use requests directly for file creation (Bitbucket Cloud API v2.0)
                url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{self.repo_slug}/src"
                auth = HTTPBasicAuth(self.username, self.password)
                
                # Bitbucket expects multipart/form-data for file uploads
                files = {
                    path: content
                }
                data = {
                    "message": message,
                    "branch": ref
                }
                
                response = requests.post(url, auth=auth, data=data, files=files, timeout=30)
                
                if response.status_code not in [200, 201]:
                    raise Exception(f"Failed to write file: {response.status_code} - {response.text}")
            else:
                # Server API - update file
                self.client.update_file(
                    self.project_key,
                    self.repo_slug,
                    path,
                    content,
                    message,
                    branch=ref
                )
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"Cannot write to: {path}")
            raise
    
    def write_files(
        self,
        files: list[dict[str, str]],
        message: str,
        branch: Optional[str] = None
    ) -> Optional[str]:
        """
        Create or update multiple files in a single commit.
        
        Args:
            files: List of dicts with 'path' and 'content' keys
            message: Commit message
            branch: Branch name (defaults to base_branch)
            
        Returns:
            Commit hash/ID if available, None otherwise
        """
        ref = branch or self.base_branch
        
        try:
            if self.is_cloud:
                # Use requests directly for batch file creation (Bitbucket Cloud API v2.0)
                url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{self.repo_slug}/src"
                auth = HTTPBasicAuth(self.username, self.password)
                
                # Bitbucket expects multipart/form-data with multiple files
                files_data = {
                    file_info['path']: file_info['content']
                    for file_info in files
                }
                data = {
                    "message": message,
                    "branch": ref
                }
                
                response = requests.post(url, auth=auth, data=data, files=files_data, timeout=60)
                
                if response.status_code not in [200, 201]:
                    raise Exception(f"Failed to write files: {response.status_code} - {response.text}")
                
                # Extract commit hash from response
                # Bitbucket POST /src doesn't return commit hash directly, need to fetch latest commit
                try:
                    # Get the latest commit on the branch to get the hash
                    commits_url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{self.repo_slug}/commits/{ref}"
                    commits_response = requests.get(commits_url, auth=auth, params={"pagelen": 1}, timeout=30)
                    if commits_response.status_code == 200:
                        commits_data = commits_response.json()
                        values = commits_data.get('values', [])
                        if values:
                            commit_hash = values[0].get('hash', None)
                            return commit_hash[:7] if commit_hash else None  # Return short hash
                except Exception as e:
                    # If we can't get commit hash, just return None (commit was still successful)
                    pass
                return None
            else:
                # Server API - write files individually (no batch API)
                last_commit = None
                for file_info in files:
                    result = self.client.update_file(
                        self.project_key,
                        self.repo_slug,
                        file_info['path'],
                        file_info['content'],
                        message,
                        branch=ref
                    )
                    # Try to extract commit hash from result if available
                    if isinstance(result, dict) and 'id' in result:
                        last_commit = result['id'][:7] if result['id'] else None
                return last_commit
        except Exception as e:
            raise Exception(f"Failed to write batch of {len(files)} files: {e}")
    
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
            if self.is_cloud:
                # Cloud API
                self.client.delete(
                    f"repositories/{self.workspace}/{self.repo_slug}/src",
                    data={
                        "message": message,
                        "branch": ref,
                        "files": path
                    }
                )
            else:
                # Server API doesn't have direct delete, use update with empty content
                # or handle via Git operations
                raise NotImplementedError(
                    "File deletion via API not supported in Bitbucket Server. "
                    "Use Git operations instead."
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
        logger.debug(f"Creating branch '{branch_name}' from source '{source}'")
        
        try:
            if self.is_cloud:
                # Cloud API - need to resolve branch name to commit hash first
                # Get the commit hash of the source branch
                try:
                    logger.debug(f"Fetching commit hash for source branch: {source}")
                    branches_response = self.client.get(
                        f"repositories/{self.workspace}/{self.repo_slug}/refs/branches/{source}"
                    )
                    source_hash = branches_response.get("target", {}).get("hash")
                    if not source_hash:
                        logger.error(f"Branch '{source}' response: {branches_response}")
                        raise ValueError(f"Could not get commit hash from branch '{source}'")
                    logger.debug(f"Source branch '{source}' resolved to hash: {source_hash}")
                except Exception as e:
                    logger.error(f"Failed to resolve source branch '{source}': {e}")
                    raise ValueError(f"Could not resolve source branch '{source}' to commit hash: {e}")
                
                # Now create the branch with the commit hash
                logger.debug(f"Creating new branch '{branch_name}' from hash {source_hash}")
                response = self.client.post(
                    f"repositories/{self.workspace}/{self.repo_slug}/refs/branches",
                    data={
                        "name": branch_name,
                        "target": {"hash": source_hash}
                    }
                )
                return RepoBranch(
                    name=branch_name,
                    sha=response.get("target", {}).get("hash", "")
                )
            else:
                # Server API - create branch
                response = self.client.create_branch(
                    self.project_key,
                    self.repo_slug,
                    branch_name,
                    source
                )
                return RepoBranch(
                    name=branch_name,
                    sha=response.get("latestCommit", "")
                )
        except Exception as e:
            logger.error(f"Failed to create branch '{branch_name}' from '{source}': {e}")
            if "409" in str(e):
                raise ValueError(f"Branch already exists: {branch_name}")
            raise
    
    def delete_branch(self, branch_name: str) -> None:
        """
        Delete a branch.
        
        Args:
            branch_name: Branch name to delete
        """
        try:
            if self.is_cloud:
                # Cloud API
                self.client.delete(
                    f"repositories/{self.workspace}/{self.repo_slug}/refs/branches/{branch_name}"
                )
            else:
                # Server API
                self.client.delete_branch(
                    self.project_key,
                    self.repo_slug,
                    branch_name
                )
        except Exception as e:
            if "404" in str(e):
                raise BranchNotFoundError(f"Branch not found: {branch_name}")
            raise
    
    def list_branches(self) -> List[RepoBranch]:
        """
        List all branches (handles pagination).
        
        Returns:
            List of RepoBranch objects
        """
        branches = []
        
        try:
            if self.is_cloud:
                # Cloud API with pagination support
                url = f"repositories/{self.workspace}/{self.repo_slug}/refs/branches"
                
                while url:
                    response = self.client.get(url)
                    
                    # Add branches from current page
                    for branch in response.get("values", []):
                        branches.append(RepoBranch(
                            name=branch["name"],
                            sha=branch.get("target", {}).get("hash", "")
                        ))
                    
                    # Check for next page
                    url = response.get("next")
                    if url:
                        # Extract relative path from full URL
                        # URL format: https://api.bitbucket.org/2.0/repositories/...
                        if url.startswith("http"):
                            # Remove base URL, keep only the path after /2.0/
                            url = url.split("/2.0/", 1)[1] if "/2.0/" in url else None
            else:
                # Server API
                response = self.client.get_branches(
                    self.project_key,
                    self.repo_slug
                )
                for branch in response:
                    branches.append(RepoBranch(
                        name=branch["displayId"],
                        sha=branch.get("latestCommit", "")
                    ))
        except Exception as e:
            raise Exception(f"Failed to list branches: {e}")
        
        return branches
    
    def has_files(self, branch: str, path: str = "") -> bool:
        """
        Check if a branch has any files at the given path.
        
        Args:
            branch: Branch name to check
            path: Directory path (empty for root)
        
        Returns:
            True if branch has files, False otherwise
        """
        try:
            files = self.list_files(path, branch=branch)
            return len(files) > 0
        except (IOError, KeyError, ValueError) as e:
            logger.debug(f"Failed to check path existence: {e}")
            return False
    
    def find_branch_with_content(self, candidate_branches: List[str] = None, path: str = "") -> str:
        """
        Find first branch that contains files at the given path.
        
        Args:
            candidate_branches: List of branch names to check (if None, checks common names)
            path: Directory path to check (empty for root)
        
        Returns:
            Branch name with content, or base_branch if none found
        """
        if candidate_branches is None:
            # Default candidates: main, master, develop, then first 10 branches
            all_branches = self.list_branches()
            candidate_branches = ['main', 'master', 'develop']
            # Add first 10 branches that aren't in the default list
            for branch in all_branches[:10]:
                if branch.name not in candidate_branches:
                    candidate_branches.append(branch.name)
        
        for branch_name in candidate_branches:
            if self.has_files(branch_name, path):
                return branch_name
        
        return self.base_branch
    
    def get_branch(self, branch_name: str) -> RepoBranch:
        """
        Get branch information.
        
        Args:
            branch_name: Branch name
        
        Returns:
            RepoBranch object
        """
        try:
            if self.is_cloud:
                # Cloud API
                response = self.client.get(
                    f"repositories/{self.workspace}/{self.repo_slug}/refs/branches/{branch_name}"
                )
                return RepoBranch(
                    name=response["name"],
                    sha=response.get("target", {}).get("hash", "")
                )
            else:
                # Server API
                response = self.client.get_branch(
                    self.project_key,
                    self.repo_slug,
                    branch_name
                )
                return RepoBranch(
                    name=response["displayId"],
                    sha=response.get("latestCommit", "")
                )
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
        Create a pull request with retry logic for rate limits.
        
        Args:
            title: PR title
            body: PR description
            source_branch: Source branch name
            target_branch: Target branch (defaults to base_branch)
            draft: Create as draft PR (Bitbucket Cloud only, uses 'DRAFT' state)
        
        Returns:
            PullRequest object
        """
        target = target_branch or self.base_branch
        
        max_retries = 3
        base_delay = 60  # Start with 60 seconds wait for rate limits
        
        for attempt in range(max_retries):
            try:
                if self.is_cloud:
                    # Cloud API with draft support
                    pr_data = {
                        "title": title,
                        "description": body,
                        "source": {"branch": {"name": source_branch}},
                        "destination": {"branch": {"name": target}}
                    }
                    # Add draft state if requested (Bitbucket uses 'state' field)
                    if draft:
                        pr_data["state"] = "DRAFT"
                    
                    response = self.client.post(
                        f"repositories/{self.workspace}/{self.repo_slug}/pullrequests",
                        data=pr_data
                    )
                    return PullRequest(
                        number=response["id"],
                        title=title,
                        body=body,
                        source_branch=source_branch,
                        target_branch=target,
                        state="open",
                        url=response["links"]["html"]["href"]
                    )
                else:
                    # Server API
                    response = self.client.create_pull_request(
                        self.project_key,
                        self.repo_slug,
                        source_branch,
                        target,
                        title,
                        body
                    )
                    return PullRequest(
                        number=response["id"],
                        title=title,
                        body=body,
                        source_branch=source_branch,
                        target_branch=target,
                        state="open",
                        url=response["links"]["self"][0]["href"]
                    )
                    
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a rate limit error (429)
                if "429" in error_msg and attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"\\nRate limit hit. Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                
                # If not rate limit or final attempt, raise the error
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
            if self.is_cloud:
                # Cloud API
                response = self.client.get(
                    f"repositories/{self.workspace}/{self.repo_slug}/pullrequests/{pr_number}"
                )
                return PullRequest(
                    number=response["id"],
                    title=response["title"],
                    body=response.get("description", ""),
                    source_branch=response.get("source", {}).get("branch", {}).get("name", ""),
                    target_branch=response.get("destination", {}).get("branch", {}).get("name", ""),
                    state=response["state"].lower(),
                    url=response["links"]["html"]["href"]
                )
            else:
                # Server API
                response = self.client.get_pull_request(
                    self.project_key,
                    self.repo_slug,
                    pr_number
                )
                return PullRequest(
                    number=response["id"],
                    title=response["title"],
                    body=response.get("description", ""),
                    source_branch=response.get("fromRef", {}).get("displayId", ""),
                    target_branch=response.get("toRef", {}).get("displayId", ""),
                    state=response["state"].lower(),
                    url=response["links"]["self"][0]["href"]
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
            if self.is_cloud:
                # Cloud API
                params = {}
                if state != "all":
                    params["state"] = state.upper()
                
                response = self.client.get(
                    f"repositories/{self.workspace}/{self.repo_slug}/pullrequests",
                    params=params
                )
                for pr in response.get("values", []):
                    prs.append(PullRequest(
                        number=pr["id"],
                        title=pr["title"],
                        body=pr.get("description", ""),
                        source_branch=pr.get("source", {}).get("branch", {}).get("name", ""),
                        target_branch=pr.get("destination", {}).get("branch", {}).get("name", ""),
                        state=pr["state"].lower(),
                        url=pr["links"]["html"]["href"]
                    ))
            else:
                # Server API
                state_map = {"open": "OPEN", "closed": "MERGED", "all": "ALL"}
                response = self.client.get_pull_requests(
                    self.project_key,
                    self.repo_slug,
                    state=state_map.get(state, "OPEN")
                )
                for pr in response:
                    prs.append(PullRequest(
                        number=pr["id"],
                        title=pr["title"],
                        body=pr.get("description", ""),
                        source_branch=pr.get("fromRef", {}).get("displayId", ""),
                        target_branch=pr.get("toRef", {}).get("displayId", ""),
                        state=pr["state"].lower(),
                        url=pr["links"]["self"][0]["href"]
                    ))
        except Exception as e:
            raise Exception(f"Failed to list pull requests: {e}")
        
        return prs
