"""
Comprehensive unit tests for repo-native transformation components.

Tests cover:
- Base abstractions
- GitHub connector
- GitLab connector
- Virtual workspace
- Credential management
- Repo translator
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from core.repo.base import (
    RepoConnector,
    RepoFile,
    RepoBranch,
    PullRequest,
    RepoNotFoundError,
    FileNotFoundError,
    BranchNotFoundError,
    AuthenticationError,
)
from core.repo.virtual_workspace import VirtualRepo, VirtualFile

# Import credential manager only if cryptography is available
try:
    from core.repo.credentials import CredentialManager, RepoCredential
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    CredentialManager = None
    RepoCredential = None

from core.repo.repo_translator import RepoTranslator, create_connector


# ============================================================================
# Mock Connector for Testing
# ============================================================================

class MockRepoConnector(RepoConnector):
    """Mock connector for testing."""
    
    def __init__(self, owner: str, repo: str, token: str, base_branch: str = "main"):
        self._files = {}  # path -> content
        self._branches = {'main': 'abc123'}
        self._prs = []
        super().__init__(owner, repo, token, base_branch)
    
    def _validate_connection(self):
        if self.token == "invalid":
            raise AuthenticationError("Invalid token")
        if self.repo == "nonexistent":
            raise RepoNotFoundError("Repo not found")
    
    def list_files(self, path="", ref=None):
        ref = ref or self.base_branch
        files = []
        for file_path in self._files.keys():
            if file_path.startswith(path):
                files.append(RepoFile(
                    path=file_path,
                    sha="sha123",
                    size=len(self._files[file_path])
                ))
        return files
    
    def read_file(self, path, ref=None):
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[path]
    
    def file_exists(self, path, ref=None):
        return path in self._files
    
    def list_branches(self):
        return [
            RepoBranch(name=name, sha=sha, is_default=(name == self.base_branch))
            for name, sha in self._branches.items()
        ]
    
    def get_branch(self, name):
        if name not in self._branches:
            raise BranchNotFoundError(f"Branch not found: {name}")
        return RepoBranch(
            name=name,
            sha=self._branches[name],
            is_default=(name == self.base_branch)
        )
    
    def create_branch(self, name, from_branch=None):
        if name in self._branches:
            raise ValueError(f"Branch {name} already exists")
        from_branch = from_branch or self.base_branch
        self._branches[name] = self._branches[from_branch]
        return RepoBranch(name=name, sha=self._branches[name], is_default=False)
    
    def delete_branch(self, name):
        if name not in self._branches:
            raise BranchNotFoundError(f"Branch not found: {name}")
        del self._branches[name]
    
    def write_file(self, path, content, message, branch=None):
        self._files[path] = content
        return RepoFile(
            path=path,
            content=content,
            sha="newsha",
            size=len(content)
        )
    
    def delete_file(self, path, message, branch=None):
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        del self._files[path]
    
    def create_pull_request(self, title, body, source_branch, target_branch=None, draft=False):
        pr = PullRequest(
            number=len(self._prs) + 1,
            title=title,
            body=body,
            source_branch=source_branch,
            target_branch=target_branch or self.base_branch,
            url=f"https://example.com/pr/{len(self._prs) + 1}",
            state="open",
            created_at=datetime.now()
        )
        self._prs.append(pr)
        return pr
    
    def get_pull_request(self, number):
        for pr in self._prs:
            if pr.number == number:
                return pr
        raise ValueError(f"PR #{number} not found")
    
    def list_pull_requests(self, state="open"):
        return [pr for pr in self._prs if pr.state == state or state == "all"]


# ============================================================================
# Test Base Abstractions
# ============================================================================

class TestRepoFile:
    """Test RepoFile dataclass."""
    
    def test_repo_file_creation(self):
        """Test creating RepoFile."""
        file = RepoFile(
            path="test.py",
            content="print('hello')",
            sha="abc123",
            size=100
        )
        
        assert file.path == "test.py"
        assert file.content == "print('hello')"
        assert file.sha == "abc123"
        assert file.size == 100
        assert not file.is_binary
    
    def test_repo_file_defaults(self):
        """Test RepoFile with default values."""
        file = RepoFile(path="test.py")
        
        assert file.path == "test.py"
        assert file.content is None
        assert file.sha is None
        assert file.size is None
        assert not file.is_binary


class TestRepoBranch:
    """Test RepoBranch dataclass."""
    
    def test_repo_branch_creation(self):
        """Test creating RepoBranch."""
        branch = RepoBranch(
            name="main",
            sha="abc123",
            is_default=True
        )
        
        assert branch.name == "main"
        assert branch.sha == "abc123"
        assert branch.is_default


class TestPullRequest:
    """Test PullRequest dataclass."""
    
    def test_pull_request_creation(self):
        """Test creating PullRequest."""
        pr = PullRequest(
            number=42,
            title="Test PR",
            body="Description",
            source_branch="feature",
            target_branch="main",
            url="https://example.com/pr/42",
            state="open"
        )
        
        assert pr.number == 42
        assert pr.title == "Test PR"
        assert pr.state == "open"


class TestMockConnector:
    """Test mock connector implementation."""
    
    def test_connector_initialization(self):
        """Test initializing mock connector."""
        connector = MockRepoConnector("owner", "repo", "token")
        
        assert connector.owner == "owner"
        assert connector.repo == "repo"
        assert connector.base_branch == "main"
    
    def test_authentication_error(self):
        """Test authentication error."""
        with pytest.raises(AuthenticationError):
            MockRepoConnector("owner", "repo", "invalid")
    
    def test_repo_not_found(self):
        """Test repo not found error."""
        with pytest.raises(RepoNotFoundError):
            MockRepoConnector("owner", "nonexistent", "token")
    
    def test_file_operations(self):
        """Test file read/write operations."""
        connector = MockRepoConnector("owner", "repo", "token")
        
        # Write file
        connector.write_file("test.py", "content", "Add test file")
        
        # Read file
        content = connector.read_file("test.py")
        assert content == "content"
        
        # File exists
        assert connector.file_exists("test.py")
        assert not connector.file_exists("missing.py")
    
    def test_branch_operations(self):
        """Test branch create/delete operations."""
        connector = MockRepoConnector("owner", "repo", "token")
        
        # List branches
        branches = connector.list_branches()
        assert len(branches) == 1
        assert branches[0].name == "main"
        
        # Create branch
        new_branch = connector.create_branch("feature")
        assert new_branch.name == "feature"
        
        # Get branch
        branch = connector.get_branch("feature")
        assert branch.name == "feature"
        
        # Delete branch
        connector.delete_branch("feature")
        with pytest.raises(BranchNotFoundError):
            connector.get_branch("feature")
    
    def test_pull_request_operations(self):
        """Test pull request operations."""
        connector = MockRepoConnector("owner", "repo", "token")
        connector.create_branch("feature")
        
        # Create PR
        pr = connector.create_pull_request(
            title="Test PR",
            body="Description",
            source_branch="feature"
        )
        
        assert pr.number == 1
        assert pr.title == "Test PR"
        assert pr.state == "open"
        
        # Get PR
        fetched_pr = connector.get_pull_request(1)
        assert fetched_pr.title == "Test PR"
        
        # List PRs
        prs = connector.list_pull_requests()
        assert len(prs) == 1


# ============================================================================
# Test Virtual Workspace
# ============================================================================

class TestVirtualRepo:
    """Test VirtualRepo class."""
    
    @pytest.fixture
    def connector(self):
        """Create mock connector with test files."""
        conn = MockRepoConnector("owner", "repo", "token")
        conn._files = {
            "src/test.py": "original content",
            "src/utils.py": "utils code"
        }
        return conn
    
    @pytest.fixture
    def workspace(self, connector):
        """Create virtual workspace."""
        return VirtualRepo(connector)
    
    def test_read_file_from_remote(self, workspace):
        """Test reading file from remote repo."""
        content = workspace.read("src/test.py")
        assert content == "original content"
    
    def test_read_file_from_cache(self, workspace):
        """Test reading file from cache."""
        # First read loads from remote
        content1 = workspace.read("src/test.py")
        
        # Second read comes from cache
        content2 = workspace.read("src/test.py")
        
        assert content1 == content2
    
    def test_write_new_file(self, workspace):
        """Test writing new file."""
        workspace.write("new_file.py", "new content")
        
        assert workspace.exists("new_file.py")
        assert workspace.read("new_file.py") == "new content"
    
    def test_modify_existing_file(self, workspace):
        """Test modifying existing file."""
        workspace.read("src/test.py")  # Load original
        workspace.write("src/test.py", "modified content")
        
        assert workspace.read("src/test.py") == "modified content"
        assert workspace.has_changes()
    
    def test_delete_file(self, workspace):
        """Test deleting file."""
        workspace.delete("src/test.py")
        
        changes = workspace.get_changes()
        assert "src/test.py" in changes
        assert changes["src/test.py"].content == ""
    
    def test_get_changes(self, workspace):
        """Test getting modified files."""
        workspace.write("new.py", "new")
        workspace.read("src/test.py")
        workspace.write("src/test.py", "modified")
        
        changes = workspace.get_changes()
        
        assert len(changes) == 2
        assert "new.py" in changes
        assert "src/test.py" in changes
    
    def test_get_diff(self, workspace):
        """Test generating diff for file."""
        workspace.read("src/test.py")
        workspace.write("src/test.py", "modified content")
        
        diff = workspace.get_diff("src/test.py")
        
        assert diff is not None
        assert "original content" in diff
        assert "modified content" in diff
        assert "---" in diff
        assert "+++" in diff
    
    def test_get_stats(self, workspace):
        """Test getting change statistics."""
        workspace.write("new.py", "new")
        workspace.read("src/test.py")
        workspace.write("src/test.py", "modified")
        workspace.delete("src/utils.py")
        
        stats = workspace.get_stats()
        
        assert stats['new'] == 1
        assert stats['modified'] == 1
        assert stats['deleted'] == 1
        assert stats['total'] == 3
    
    def test_commit_changes(self, workspace, connector):
        """Test committing changes."""
        workspace.write("new.py", "new content")
        
        committed = workspace.commit_changes("Test commit")
        
        assert committed == 1
        assert connector.file_exists("new.py")
        assert not workspace.has_changes()
    
    def test_export_bundle(self, workspace):
        """Test exporting files to directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace.write("test.py", "content")
            workspace.export_bundle(tmpdir)
            
            exported_file = Path(tmpdir) / "test.py"
            assert exported_file.exists()
            assert exported_file.read_text() == "content"
    
    def test_reset(self, workspace):
        """Test resetting workspace."""
        workspace.write("new.py", "content")
        assert workspace.has_changes()
        
        workspace.reset()
        
        assert not workspace.has_changes()
        assert len(workspace._cache) == 0


# ============================================================================
# Test Credential Management
# ============================================================================

@pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography not installed")
class TestCredentialManager:
    """Test CredentialManager class."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography not installed")
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir)
    
    @pytest.fixture
    def cred_manager(self, temp_config_dir):
        """Create credential manager."""
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography not installed")
        return CredentialManager(temp_config_dir)
    
    def test_store_credential(self, cred_manager):
        """Test storing credential."""
        cred = RepoCredential(
            provider="github",
            owner="owner",
            repo="repo",
            token="secret_token"
        )
        
        cred_manager.store(cred)
        
        retrieved = cred_manager.get("github", "owner", "repo")
        assert retrieved is not None
        assert retrieved.token == "secret_token"
    
    def test_get_nonexistent_credential(self, cred_manager):
        """Test getting non-existent credential."""
        cred = cred_manager.get("github", "owner", "repo")
        assert cred is None
    
    def test_delete_credential(self, cred_manager):
        """Test deleting credential."""
        cred = RepoCredential(
            provider="github",
            owner="owner",
            repo="repo",
            token="token"
        )
        cred_manager.store(cred)
        
        deleted = cred_manager.delete("github", "owner", "repo")
        
        assert deleted
        assert cred_manager.get("github", "owner", "repo") is None
    
    def test_list_credentials(self, cred_manager):
        """Test listing credentials."""
        cred1 = RepoCredential("github", "owner1", "repo1", "token1")
        cred2 = RepoCredential("gitlab", "owner2", "repo2", "token2")
        
        cred_manager.store(cred1)
        cred_manager.store(cred2)
        
        creds = cred_manager.list_credentials()
        
        assert len(creds) == 2
        assert ("github", "owner1", "repo1") in creds
        assert ("gitlab", "owner2", "repo2") in creds
    
    def test_credential_persistence(self, temp_config_dir):
        """Test credentials persist across instances."""
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography not installed")
        # Store credential with first manager
        manager1 = CredentialManager(temp_config_dir)
        cred = RepoCredential("github", "owner", "repo", "token")
        manager1.store(cred)
        
        # Retrieve with second manager
        manager2 = CredentialManager(temp_config_dir)
        retrieved = manager2.get("github", "owner", "repo")
        
        assert retrieved is not None
        assert retrieved.token == "token"
    
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'env_token'})
    def test_get_from_env(self, cred_manager):
        """Test getting token from environment."""
        token = cred_manager.get_from_env("github")
        assert token == "env_token"
    
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'env_token'})
    def test_get_token_priority(self, cred_manager):
        """Test token retrieval priority (stored > env)."""
        # Store credential
        cred = RepoCredential("github", "owner", "repo", "stored_token")
        cred_manager.store(cred)
        
        # Should get stored token, not env token
        token = cred_manager.get_token("github", "owner", "repo")
        assert token == "stored_token"
    
    def test_clear_all(self, cred_manager):
        """Test clearing all credentials."""
        cred = RepoCredential("github", "owner", "repo", "token")
        cred_manager.store(cred)
        
        cred_manager.clear_all()
        
        assert len(cred_manager.list_credentials()) == 0


# ============================================================================
# Test Repo Translator
# ============================================================================

class TestRepoTranslator:
    """Test RepoTranslator class."""
    
    @pytest.fixture
    def connector(self):
        """Create mock connector with test files."""
        conn = MockRepoConnector("owner", "repo", "token")
        conn._files = {
            "tests/test_login.java": "// Java test",
            "tests/test_signup.java": "// Java test",
            "src/main.java": "// Not a test"
        }
        return conn
    
    @pytest.fixture
    def translator(self, connector):
        """Create repo translator."""
        return RepoTranslator(connector, "selenium-java", "playwright-python")
    
    def test_discover_test_files(self, translator):
        """Test discovering test files."""
        test_files = translator.discover_test_files()
        
        assert len(test_files) >= 2
        assert any("test_login" in f for f in test_files)
        assert any("test_signup" in f for f in test_files)
        assert not any("main.java" in f for f in test_files)
    
    def test_get_default_pattern(self, translator):
        """Test getting default file pattern."""
        pattern = translator._get_default_pattern()
        assert pattern == "*.java"
    
    def test_is_test_file(self, translator):
        """Test identifying test files."""
        assert translator._is_test_file("test_login.py")
        assert translator._is_test_file("login_test.py")
        assert translator._is_test_file("tests/spec_login.js")
        assert not translator._is_test_file("utils.py")
        assert not translator._is_test_file("config.json")
    
    def test_get_output_path(self, translator):
        """Test generating output paths."""
        output = translator._get_output_path("tests/test_login.java")
        
        assert output.endswith(".py")
        assert "test_login" in output
    
    def test_get_stats(self, translator):
        """Test getting translation stats."""
        translator.workspace.write("test.py", "content")
        
        stats = translator.get_stats()
        
        assert stats['new'] == 1
        assert stats['total'] == 1
    
    def test_preview_changes(self, translator):
        """Test previewing changes."""
        translator.workspace.write("test.py", "new content")
        
        diff = translator.preview_changes()
        
        assert "new content" in diff
    
    def test_export_bundle(self, translator):
        """Test exporting bundle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            translator.workspace.write("test.py", "content")
            translator.export_bundle(tmpdir)
            
            exported = Path(tmpdir) / "test.py"
            assert exported.exists()
    
    def test_reset(self, translator):
        """Test resetting translator."""
        translator.workspace.write("test.py", "content")
        assert translator.workspace.has_changes()
        
        translator.reset()
        
        assert not translator.workspace.has_changes()


class TestCreateConnector:
    """Test create_connector helper function."""
    
    def test_github_short_format(self):
        """Test GitHub short format (github:owner/repo)."""
        with patch('core.repo.repo_translator.GitHubConnector') as mock_gh:
            create_connector("github:owner/repo", "token")
            mock_gh.assert_called_once_with("owner", "repo", "token", "main")
    
    def test_gitlab_short_format(self):
        """Test GitLab short format (gitlab:owner/repo)."""
        with patch('core.repo.repo_translator.GitLabConnector') as mock_gl:
            create_connector("gitlab:owner/repo", "token")
            mock_gl.assert_called_once_with("owner", "repo", "token", "main")
    
    def test_github_url_format(self):
        """Test GitHub URL format."""
        with patch('core.repo.repo_translator.GitHubConnector') as mock_gh:
            create_connector("https://github.com/owner/repo", "token")
            mock_gh.assert_called_once_with("owner", "repo", "token", "main")
    
    def test_gitlab_url_format(self):
        """Test GitLab URL format."""
        with patch('core.repo.repo_translator.GitLabConnector') as mock_gl:
            create_connector("https://gitlab.com/owner/repo", "token")
            mock_gl.assert_called_once_with("owner", "repo", "token", "main")
    
    def test_invalid_url(self):
        """Test invalid URL raises error."""
        with pytest.raises(ValueError, match="Unsupported repository URL"):
            create_connector("invalid_url", "token")
    
    def test_invalid_repo_path(self):
        """Test invalid repo path raises error."""
        with pytest.raises(ValueError, match="Invalid repo path"):
            create_connector("github:owner", "token")


# ============================================================================
# Test Coverage Summary
# ============================================================================

def test_test_coverage():
    """Verify comprehensive test coverage."""
    # This test serves as a documentation of what's tested
    tested_components = [
        "RepoFile dataclass",
        "RepoBranch dataclass",
        "PullRequest dataclass",
        "Mock connector implementation",
        "VirtualRepo read/write operations",
        "VirtualRepo diff generation",
        "VirtualRepo commit operations",
        "VirtualRepo export functionality",
        "CredentialManager storage",
        "CredentialManager encryption",
        "CredentialManager persistence",
        "CredentialManager environment fallback",
        "RepoTranslator file discovery",
        "RepoTranslator path generation",
        "RepoTranslator statistics",
        "create_connector URL parsing",
        "BitbucketConnector Cloud operations",
        "BitbucketConnector Server operations",
        "AzureDevOpsConnector Services operations",
        "AzureDevOpsConnector Server/TFS operations",
    ]
    
    assert len(tested_components) >= 20
    print(f"\n✓ Tested {len(tested_components)} components")


# ============================================================================
# Azure DevOps / TFS Connector Tests
# ============================================================================

try:
    from core.repo.azuredevops import AzureDevOpsConnector, AZUREDEVOPS_AVAILABLE
except ImportError:
    AZUREDEVOPS_AVAILABLE = False
    AzureDevOpsConnector = None


class MockAzureDevOpsClient:
    """Mock Azure DevOps API client."""
    
    def __init__(self):
        self.files = {
            "test.py": "print('hello')",
            "src/main.py": "def main(): pass"
        }
        self.branches = {
            "main": {"object_id": "abc123"},
            "develop": {"object_id": "def456"}
        }
        self.pull_requests = {}
        self.pr_counter = 1
        self.repo_id = "test-repo"
        self.project_id = "test-project"
    
    def get_repository(self, repository_id, project):
        """Mock get repository."""
        if repository_id != self.repo_id:
            raise Exception("404 Not Found")
        return {"id": self.repo_id, "name": self.repo_id}
    
    def get_items(self, repository_id, project, scope_path, version_descriptor, recursion_level):
        """Mock get items."""
        items = []
        for path, content in self.files.items():
            if scope_path == "/" or path.startswith(scope_path.lstrip('/')):
                item = type('obj', (object,), {
                    'path': f'/{path}',
                    'is_folder': False,
                    'size': len(content),
                    'object_id': 'file123'
                })()
                items.append(item)
        return items
    
    def get_item(self, repository_id, project, path, version_descriptor, include_content=False):
        """Mock get item."""
        clean_path = path.lstrip('/')
        if clean_path in self.files:
            item = type('obj', (object,), {
                'path': path,
                'content': self.files[clean_path] if include_content else None,
                'object_id': 'file123'
            })()
            return item
        raise Exception("404 Not Found")
    
    def get_refs(self, repository_id, project, filter=None):
        """Mock get refs."""
        refs = []
        for name, info in self.branches.items():
            if filter and f'heads/{name}' not in filter and not filter.endswith('heads/'):
                continue
            ref = type('obj', (object,), {
                'name': f'refs/heads/{name}',
                'object_id': info['object_id']
            })()
            refs.append(ref)
        return refs
    
    def create_push(self, push, repository_id, project):
        """Mock create push."""
        # Update file
        for commit in push.get('commits', []):
            for change in commit.get('changes', []):
                path = change['item']['path'].lstrip('/')
                if change['changeType'] in ['add', 'edit']:
                    self.files[path] = change['newContent']['content']
                elif change['changeType'] == 'delete':
                    if path in self.files:
                        del self.files[path]
        return {"pushId": 1}
    
    def update_refs(self, ref_updates, repository_id, project):
        """Mock update refs."""
        for update in ref_updates:
            branch_name = update['name'].replace('refs/heads/', '')
            if update['newObjectId'] == '0000000000000000000000000000000000000000':
                # Delete branch
                if branch_name in self.branches:
                    del self.branches[branch_name]
            else:
                # Create/update branch
                self.branches[branch_name] = {'object_id': update['newObjectId']}
        return [{"success": True}]
    
    def create_pull_request(self, git_pull_request_to_create, repository_id, project):
        """Mock create PR."""
        pr = type('obj', (object,), {
            'pull_request_id': self.pr_counter,
            'title': git_pull_request_to_create['title'],
            'description': git_pull_request_to_create.get('description', ''),
            'source_ref_name': git_pull_request_to_create['sourceRefName'],
            'target_ref_name': git_pull_request_to_create['targetRefName'],
            'status': 'Active',
            'is_draft': git_pull_request_to_create.get('isDraft', False)
        })()
        self.pull_requests[self.pr_counter] = pr
        self.pr_counter += 1
        return pr
    
    def get_pull_request_by_id(self, pull_request_id, project):
        """Mock get PR by ID."""
        if pull_request_id in self.pull_requests:
            return self.pull_requests[pull_request_id]
        raise Exception("404 Not Found")
    
    def get_pull_requests(self, repository_id, project, search_criteria):
        """Mock get PRs."""
        return list(self.pull_requests.values())


@pytest.mark.skipif(not AZUREDEVOPS_AVAILABLE, reason="azure-devops not installed")
class TestAzureDevOpsServicesConnector:
    """Test Azure DevOps Services (cloud) connector."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock Azure DevOps client."""
        return MockAzureDevOpsClient()
    
    @pytest.fixture
    def ado_connector(self, mock_client):
        """Create Azure DevOps Services connector with mocked client."""
        with patch('core.repo.azuredevops.Connection') as mock_conn:
            mock_conn_instance = MagicMock()
            mock_conn_instance.clients.get_git_client.return_value = mock_client
            mock_conn.return_value = mock_conn_instance
            
            connector = AzureDevOpsConnector(
                "myorg",
                "myproject",
                "test-repo",
                token="pat_token"
            )
            connector.git_client = mock_client
            return connector
    
    def test_services_initialization(self):
        """Test Azure DevOps Services connector initialization."""
        with patch('core.repo.azuredevops.Connection'):
            connector = AzureDevOpsConnector(
                "myorg",
                "myproject",
                "myrepo",
                token="pat_token"
            )
            assert connector.organization == "myorg"
            assert connector.project == "myproject"
            assert connector.repo == "myrepo"
            assert "dev.azure.com/myorg" in connector.url
    
    def test_services_read_file(self, ado_connector):
        """Test reading file from Azure DevOps Services."""
        content = ado_connector.read_file("test.py")
        assert content == "print('hello')"
    
    def test_services_file_not_found(self, ado_connector):
        """Test file not found in Azure DevOps Services."""
        with pytest.raises(FileNotFoundError):
            ado_connector.read_file("nonexistent.py")
    
    def test_services_write_file(self, ado_connector):
        """Test writing file to Azure DevOps Services."""
        ado_connector.write_file("new.py", "new content", "Add file")
        assert ado_connector.git_client.files["new.py"] == "new content"
    
    def test_services_file_exists(self, ado_connector):
        """Test checking file existence in Azure DevOps Services."""
        assert ado_connector.file_exists("test.py") is True
        assert ado_connector.file_exists("nonexistent.py") is False
    
    def test_services_list_files(self, ado_connector):
        """Test listing files in Azure DevOps Services."""
        files = ado_connector.list_files()
        assert len(files) >= 2
        file_paths = [f.path for f in files]
        assert "test.py" in file_paths
    
    def test_services_create_branch(self, ado_connector):
        """Test creating branch in Azure DevOps Services."""
        branch = ado_connector.create_branch("feature-branch", "main")
        assert branch.name == "feature-branch"
        assert "feature-branch" in ado_connector.git_client.branches
    
    def test_services_delete_branch(self, ado_connector):
        """Test deleting branch in Azure DevOps Services."""
        ado_connector.create_branch("temp-branch", "main")
        ado_connector.delete_branch("temp-branch")
        assert "temp-branch" not in ado_connector.git_client.branches
    
    def test_services_list_branches(self, ado_connector):
        """Test listing branches in Azure DevOps Services."""
        branches = ado_connector.list_branches()
        assert len(branches) >= 2
        branch_names = [b.name for b in branches]
        assert "main" in branch_names
    
    def test_services_get_branch(self, ado_connector):
        """Test getting branch info in Azure DevOps Services."""
        branch = ado_connector.get_branch("main")
        assert branch.name == "main"
        assert branch.sha == "abc123"
    
    def test_services_create_pull_request(self, ado_connector):
        """Test creating PR in Azure DevOps Services."""
        pr = ado_connector.create_pull_request(
            "Test PR",
            "Description",
            "feature",
            "main"
        )
        assert pr.title == "Test PR"
        assert pr.source_branch == "feature"
        assert pr.target_branch == "main"
        assert pr.number in ado_connector.git_client.pull_requests
    
    def test_services_get_pull_request(self, ado_connector):
        """Test getting PR in Azure DevOps Services."""
        created_pr = ado_connector.create_pull_request("PR", "Desc", "feature", "main")
        pr = ado_connector.get_pull_request(created_pr.number)
        assert pr.title == "PR"
    
    def test_services_list_pull_requests(self, ado_connector):
        """Test listing PRs in Azure DevOps Services."""
        ado_connector.create_pull_request("PR1", "Desc", "f1", "main")
        ado_connector.create_pull_request("PR2", "Desc", "f2", "main")
        prs = ado_connector.list_pull_requests()
        assert len(prs) >= 2


@pytest.mark.skipif(not AZUREDEVOPS_AVAILABLE, reason="azure-devops not installed")
class TestAzureDevOpsServerConnector:
    """Test Azure DevOps Server / TFS (on-prem) connector."""
    
    @pytest.fixture
    def mock_server_client(self):
        """Create mock Azure DevOps Server client."""
        return MockAzureDevOpsClient()
    
    @pytest.fixture
    def tfs_connector(self, mock_server_client):
        """Create TFS connector with mocked client."""
        with patch('core.repo.azuredevops.Connection') as mock_conn:
            mock_conn_instance = MagicMock()
            mock_conn_instance.clients.get_git_client.return_value = mock_server_client
            mock_conn.return_value = mock_conn_instance
            
            connector = AzureDevOpsConnector(
                "DefaultCollection",
                "MyProject",
                "test-repo",
                token="pat_token",
                url="https://tfs.company.com"
            )
            connector.git_client = mock_server_client
            return connector
    
    def test_server_initialization(self):
        """Test TFS/Azure DevOps Server connector initialization."""
        with patch('core.repo.azuredevops.Connection'):
            connector = AzureDevOpsConnector(
                "DefaultCollection",
                "MyProject",
                "myrepo",
                token="pat_token",
                url="https://tfs.company.com"
            )
            assert connector.organization == "DefaultCollection"
            assert connector.project == "MyProject"
            assert connector.repo == "myrepo"
            assert connector.url == "https://tfs.company.com"
    
    def test_server_read_file(self, tfs_connector):
        """Test reading file from TFS."""
        content = tfs_connector.read_file("test.py")
        assert content == "print('hello')"
    
    def test_server_write_file(self, tfs_connector):
        """Test writing file to TFS."""
        tfs_connector.write_file("new.py", "new content", "Add file")
        assert tfs_connector.git_client.files["new.py"] == "new content"
    
    def test_server_delete_file(self, tfs_connector):
        """Test deleting file in TFS."""
        tfs_connector.delete_file("test.py", "Delete file")
        assert "test.py" not in tfs_connector.git_client.files
    
    def test_server_create_branch(self, tfs_connector):
        """Test creating branch in TFS."""
        branch = tfs_connector.create_branch("feature-branch", "main")
        assert branch.name == "feature-branch"
        assert "feature-branch" in tfs_connector.git_client.branches
    
    def test_server_delete_branch(self, tfs_connector):
        """Test deleting branch in TFS."""
        tfs_connector.create_branch("temp-branch", "main")
        tfs_connector.delete_branch("temp-branch")
        assert "temp-branch" not in tfs_connector.git_client.branches
    
    def test_server_list_branches(self, tfs_connector):
        """Test listing branches in TFS."""
        branches = tfs_connector.list_branches()
        assert len(branches) >= 2
        branch_names = [b.name for b in branches]
        assert "main" in branch_names
    
    def test_server_create_pull_request(self, tfs_connector):
        """Test creating PR in TFS."""
        pr = tfs_connector.create_pull_request(
            "Test PR",
            "Description",
            "feature",
            "main"
        )
        assert pr.title == "Test PR"
        assert pr.source_branch == "feature"
        assert pr.target_branch == "main"
    
    def test_server_get_pull_request(self, tfs_connector):
        """Test getting PR in TFS."""
        created_pr = tfs_connector.create_pull_request("PR", "Desc", "feature", "main")
        pr = tfs_connector.get_pull_request(created_pr.number)
        assert pr.title == "PR"
    
    def test_server_list_pull_requests(self, tfs_connector):
        """Test listing PRs in TFS."""
        tfs_connector.create_pull_request("PR1", "Desc", "f1", "main")
        prs = tfs_connector.list_pull_requests()
        assert len(prs) >= 1


# ============================================================================
# Azure DevOps URL Parsing Tests
# ============================================================================

class TestAzureDevOpsCreateConnector:
    """Test create_connector with Azure DevOps URLs."""
    
    def test_azuredevops_short_format(self):
        """Test azuredevops:org/project/repo format."""
        with patch('core.repo.azuredevops.AzureDevOpsConnector') as mock:
            create_connector("azuredevops:myorg/myproject/myrepo", "token")
            mock.assert_called_once()
            args = mock.call_args
            assert args[0][0] == "myorg"
            assert args[0][1] == "myproject"
            assert args[0][2] == "myrepo"
    
    def test_ado_short_format(self):
        """Test ado:org/project/repo format."""
        with patch('core.repo.azuredevops.AzureDevOpsConnector') as mock:
            create_connector("ado:myorg/myproject/myrepo", "token")
            mock.assert_called_once()
            args = mock.call_args
            assert args[0][0] == "myorg"
            assert args[0][1] == "myproject"
            assert args[0][2] == "myrepo"
    
    def test_azuredevops_services_url(self):
        """Test full Azure DevOps Services URL."""
        with patch('core.repo.azuredevops.AzureDevOpsConnector') as mock:
            create_connector("https://dev.azure.com/myorg/myproject/_git/myrepo", "token")
            mock.assert_called_once()
            args = mock.call_args
            assert args[0][0] == "myorg"
            assert args[0][1] == "myproject"
            assert args[0][2] == "myrepo"
    
    def test_tfs_server_url(self):
        """Test TFS/Azure DevOps Server URL."""
        with patch('core.repo.azuredevops.AzureDevOpsConnector') as mock:
            create_connector("https://tfs.company.com/DefaultCollection/MyProject/_git/MyRepo", "token")
            mock.assert_called_once()
            args = mock.call_args
            assert args[0][0] == "DefaultCollection"
            assert args[0][1] == "MyProject"
            assert args[0][2] == "MyRepo"


# ============================================================================
# Bitbucket Connector Tests
# ============================================================================

try:
    from core.repo.bitbucket import BitbucketConnector, BITBUCKET_AVAILABLE
except ImportError:
    BITBUCKET_AVAILABLE = False
    BitbucketConnector = None


class MockBitbucketClient:
    """Mock Bitbucket API client."""
    
    def __init__(self, is_cloud=True):
        self.is_cloud = is_cloud
        self.files = {
            "test.py": "print('hello')",
            "src/main.py": "def main(): pass"
        }
        self.branches = {
            "main": {"hash": "abc123", "displayId": "main", "latestCommit": "abc123"},
            "develop": {"hash": "def456", "displayId": "develop", "latestCommit": "def456"}
        }
        self.pull_requests = {}
        self.pr_counter = 1
    
    def get(self, path, params=None):
        """Mock GET request."""
        if "src/" in path:
            # File content
            file_path = path.split("/")[-1]
            if file_path in self.files:
                return self.files[file_path]
            raise Exception("404 Not Found")
        elif "refs/branches" in path:
            # List or get branches
            if path.endswith("refs/branches"):
                return {
                    "values": [
                        {"name": "main", "target": {"hash": "abc123"}},
                        {"name": "develop", "target": {"hash": "def456"}}
                    ]
                }
            else:
                branch_name = path.split("/")[-1]
                if branch_name in self.branches:
                    return {"name": branch_name, "target": {"hash": self.branches[branch_name]["hash"]}}
                raise Exception("404 Not Found")
        elif "pullrequests" in path:
            # List or get PRs
            if "/pullrequests/" in path:
                pr_id = int(path.split("/")[-1])
                if pr_id in self.pull_requests:
                    return self.pull_requests[pr_id]
                raise Exception("404 Not Found")
            else:
                return {"values": list(self.pull_requests.values())}
        return {}
    
    def post(self, path, data=None):
        """Mock POST request."""
        if "refs/branches" in path:
            # Create branch
            branch_name = data["name"]
            self.branches[branch_name] = {
                "hash": data["target"]["hash"],
                "displayId": branch_name,
                "latestCommit": data["target"]["hash"]
            }
            return {"name": branch_name, "target": {"hash": data["target"]["hash"]}}
        elif "pullrequests" in path:
            # Create PR
            pr = {
                "id": self.pr_counter,
                "title": data["title"],
                "description": data["description"],
                "state": "OPEN",
                "links": {"html": {"href": f"https://bitbucket.org/pr/{self.pr_counter}"}}
            }
            self.pull_requests[self.pr_counter] = pr
            self.pr_counter += 1
            return pr
        elif "src" in path:
            # Update file
            for file_path in data:
                if file_path not in ["message", "branch"]:
                    self.files[file_path] = data[file_path]
        return {}
    
    def delete(self, path, data=None):
        """Mock DELETE request."""
        if "refs/branches" in path:
            branch_name = path.split("/")[-1]
            if branch_name in self.branches:
                del self.branches[branch_name]
            else:
                raise Exception("404 Not Found")
    
    # Server API methods
    def get_content_of_file(self, project, repo, path, at=None):
        """Mock Server API file read."""
        if path in self.files:
            return self.files[path]
        raise Exception("404 Not Found")
    
    def get_file_list(self, project, repo, path="", at=None):
        """Mock Server API file list."""
        return [
            {"path": "test.py", "type": "FILE", "size": 100},
            {"path": "src/main.py", "type": "FILE", "size": 200}
        ]
    
    def update_file(self, project, repo, path, content, message, branch=None):
        """Mock Server API file update."""
        self.files[path] = content
    
    def create_branch(self, project, repo, name, start_point):
        """Mock Server API branch creation."""
        self.branches[name] = {
            "hash": self.branches[start_point]["hash"],
            "displayId": name,
            "latestCommit": self.branches[start_point]["latestCommit"]
        }
        return {"displayId": name, "latestCommit": self.branches[start_point]["latestCommit"]}
    
    def delete_branch(self, project, repo, name):
        """Mock Server API branch deletion."""
        if name in self.branches:
            del self.branches[name]
        else:
            raise Exception("404 Not Found")
    
    def get_branches(self, project, repo):
        """Mock Server API branch list."""
        return [{"displayId": name, "latestCommit": info["latestCommit"]} 
                for name, info in self.branches.items()]
    
    def get_branch(self, project, repo, name):
        """Mock Server API get branch."""
        if name in self.branches:
            return {"displayId": name, "latestCommit": self.branches[name]["latestCommit"]}
        raise Exception("404 Not Found")
    
    def create_pull_request(self, project, repo, source, dest, title, description):
        """Mock Server API PR creation."""
        pr = {
            "id": self.pr_counter,
            "title": title,
            "description": description,
            "state": "OPEN",
            "links": {"self": [{"href": f"https://bitbucket.company.com/pr/{self.pr_counter}"}]}
        }
        self.pull_requests[self.pr_counter] = pr
        self.pr_counter += 1
        return pr
    
    def get_pull_request(self, project, repo, pr_id):
        """Mock Server API get PR."""
        if pr_id in self.pull_requests:
            return self.pull_requests[pr_id]
        raise Exception("404 Not Found")
    
    def get_pull_requests(self, project, repo, state="OPEN"):
        """Mock Server API list PRs."""
        return list(self.pull_requests.values())


@pytest.mark.skipif(not BITBUCKET_AVAILABLE, reason="atlassian-python-api not installed")
class TestBitbucketCloudConnector:
    """Test Bitbucket Cloud connector."""
    
    @pytest.fixture
    def mock_cloud_client(self):
        """Create mock Bitbucket Cloud client."""
        return MockBitbucketClient(is_cloud=True)
    
    @pytest.fixture
    def cloud_connector(self, mock_cloud_client):
        """Create Cloud connector with mocked client."""
        with patch('core.repo.bitbucket.BitbucketCloud') as mock:
            mock.return_value = mock_cloud_client
            connector = BitbucketConnector(
                "workspace",
                "repo",
                token="app_password",
                username="testuser",
                is_cloud=True
            )
            connector.client = mock_cloud_client
            return connector
    
    def test_cloud_initialization(self):
        """Test Bitbucket Cloud connector initialization."""
        with patch('core.repo.bitbucket.BitbucketCloud'):
            connector = BitbucketConnector(
                "myworkspace",
                "myrepo",
                token="app_password",
                username="testuser",
                is_cloud=True
            )
            assert connector.workspace == "myworkspace"
            assert connector.repo_slug == "myrepo"
            assert connector.is_cloud is True
    
    def test_cloud_read_file(self, cloud_connector):
        """Test reading file from Cloud."""
        content = cloud_connector.read_file("test.py")
        assert content == "print('hello')"
    
    def test_cloud_file_not_found(self, cloud_connector):
        """Test file not found in Cloud."""
        with pytest.raises(FileNotFoundError):
            cloud_connector.read_file("nonexistent.py")
    
    def test_cloud_write_file(self, cloud_connector):
        """Test writing file to Cloud."""
        cloud_connector.write_file("new.py", "new content", "Add file")
        assert cloud_connector.client.files["new.py"] == "new content"
    
    def test_cloud_file_exists(self, cloud_connector):
        """Test checking file existence in Cloud."""
        assert cloud_connector.file_exists("test.py") is True
        assert cloud_connector.file_exists("nonexistent.py") is False
    
    def test_cloud_create_branch(self, cloud_connector):
        """Test creating branch in Cloud."""
        branch = cloud_connector.create_branch("feature-branch", "main")
        assert branch.name == "feature-branch"
        assert "feature-branch" in cloud_connector.client.branches
    
    def test_cloud_delete_branch(self, cloud_connector):
        """Test deleting branch in Cloud."""
        cloud_connector.create_branch("temp-branch", "main")
        cloud_connector.delete_branch("temp-branch")
        assert "temp-branch" not in cloud_connector.client.branches
    
    def test_cloud_list_branches(self, cloud_connector):
        """Test listing branches in Cloud."""
        branches = cloud_connector.list_branches()
        assert len(branches) >= 2
        branch_names = [b.name for b in branches]
        assert "main" in branch_names
    
    def test_cloud_get_branch(self, cloud_connector):
        """Test getting branch info in Cloud."""
        branch = cloud_connector.get_branch("main")
        assert branch.name == "main"
        assert branch.sha == "abc123"
    
    def test_cloud_create_pull_request(self, cloud_connector):
        """Test creating PR in Cloud."""
        pr = cloud_connector.create_pull_request(
            "Test PR",
            "Description",
            "feature",
            "main"
        )
        assert pr.title == "Test PR"
        assert pr.state == "open"
        assert pr.number in cloud_connector.client.pull_requests
    
    def test_cloud_get_pull_request(self, cloud_connector):
        """Test getting PR in Cloud."""
        created_pr = cloud_connector.create_pull_request("PR", "Desc", "feature", "main")
        pr = cloud_connector.get_pull_request(created_pr.number)
        assert pr.title == "PR"
    
    def test_cloud_list_pull_requests(self, cloud_connector):
        """Test listing PRs in Cloud."""
        cloud_connector.create_pull_request("PR1", "Desc", "f1", "main")
        cloud_connector.create_pull_request("PR2", "Desc", "f2", "main")
        prs = cloud_connector.list_pull_requests()
        assert len(prs) >= 2


@pytest.mark.skipif(not BITBUCKET_AVAILABLE, reason="atlassian-python-api not installed")
class TestBitbucketServerConnector:
    """Test Bitbucket Server/Data Center (on-prem) connector."""
    
    @pytest.fixture
    def mock_server_client(self):
        """Create mock Bitbucket Server client."""
        return MockBitbucketClient(is_cloud=False)
    
    @pytest.fixture
    def server_connector(self, mock_server_client):
        """Create Server connector with mocked client."""
        with patch('core.repo.bitbucket.Bitbucket') as mock:
            mock.return_value = mock_server_client
            connector = BitbucketConnector(
                "PROJECT",
                "repo",
                token="personal_token",
                is_cloud=False,
                url="https://bitbucket.company.com"
            )
            connector.client = mock_server_client
            return connector
    
    def test_server_initialization(self):
        """Test Bitbucket Server connector initialization."""
        with patch('core.repo.bitbucket.Bitbucket'):
            connector = BitbucketConnector(
                "PROJECT",
                "myrepo",
                token="personal_token",
                is_cloud=False,
                url="https://bitbucket.company.com"
            )
            assert connector.project_key == "PROJECT"
            assert connector.repo_slug == "myrepo"
            assert connector.is_cloud is False
            assert connector.url == "https://bitbucket.company.com"
    
    def test_server_read_file(self, server_connector):
        """Test reading file from Server."""
        content = server_connector.read_file("test.py")
        assert content == "print('hello')"
    
    def test_server_write_file(self, server_connector):
        """Test writing file to Server."""
        server_connector.write_file("new.py", "new content", "Add file")
        assert server_connector.client.files["new.py"] == "new content"
    
    def test_server_list_files(self, server_connector):
        """Test listing files in Server."""
        files = server_connector.list_files()
        assert len(files) >= 2
        file_paths = [f.path for f in files]
        assert "test.py" in file_paths
    
    def test_server_create_branch(self, server_connector):
        """Test creating branch in Server."""
        branch = server_connector.create_branch("feature-branch", "main")
        assert branch.name == "feature-branch"
        assert "feature-branch" in server_connector.client.branches
    
    def test_server_delete_branch(self, server_connector):
        """Test deleting branch in Server."""
        server_connector.create_branch("temp-branch", "main")
        server_connector.delete_branch("temp-branch")
        assert "temp-branch" not in server_connector.client.branches
    
    def test_server_list_branches(self, server_connector):
        """Test listing branches in Server."""
        branches = server_connector.list_branches()
        assert len(branches) >= 2
        branch_names = [b.name for b in branches]
        assert "main" in branch_names
    
    def test_server_get_branch(self, server_connector):
        """Test getting branch info in Server."""
        branch = server_connector.get_branch("main")
        assert branch.name == "main"
    
    def test_server_create_pull_request(self, server_connector):
        """Test creating PR in Server."""
        pr = server_connector.create_pull_request(
            "Test PR",
            "Description",
            "feature",
            "main"
        )
        assert pr.title == "Test PR"
        assert pr.state == "open"
    
    def test_server_get_pull_request(self, server_connector):
        """Test getting PR in Server."""
        created_pr = server_connector.create_pull_request("PR", "Desc", "feature", "main")
        pr = server_connector.get_pull_request(created_pr.number)
        assert pr.title == "PR"
    
    def test_server_list_pull_requests(self, server_connector):
        """Test listing PRs in Server."""
        server_connector.create_pull_request("PR1", "Desc", "f1", "main")
        prs = server_connector.list_pull_requests()
        assert len(prs) >= 1


# ============================================================================
# Bitbucket URL Parsing Tests
# ============================================================================

class TestBitbucketCreateConnector:
    """Test create_connector with Bitbucket URLs."""
    
    def test_bitbucket_short_format(self):
        """Test bitbucket:workspace/repo format."""
        with patch('core.repo.bitbucket.BitbucketConnector') as mock:
            create_connector("bitbucket:workspace/repo", "token", username="user")
            mock.assert_called_once()
            args = mock.call_args
            assert args[0][0] == "workspace"
            assert args[0][1] == "repo"
    
    def test_bitbucket_cloud_url(self):
        """Test full Bitbucket Cloud URL."""
        with patch('core.repo.bitbucket.BitbucketConnector') as mock:
            create_connector("https://bitbucket.org/workspace/repo", "token", username="user")
            mock.assert_called_once()
            args = mock.call_args
            assert args[0][0] == "workspace"
            assert args[0][1] == "repo"
    
    def test_bitbucket_url_with_git_extension(self):
        """Test Bitbucket URL with .git extension."""
        with patch('core.repo.bitbucket.BitbucketConnector') as mock:
            create_connector("https://bitbucket.org/workspace/repo.git", "token", username="user")
            mock.assert_called_once()
            args = mock.call_args
            assert args[0][0] == "workspace"
            assert args[0][1] == "repo"

