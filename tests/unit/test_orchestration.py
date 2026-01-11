"""
Unit tests for MigrationOrchestrator.

Tests the core orchestration engine independently of CLI.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from core.orchestration import (
    MigrationOrchestrator,
    MigrationRequest,
    MigrationResponse,
    MigrationType,
    AuthType,
    AIMode,
    MigrationStatus,
    RepositoryAuth,
    AIConfig
)


class TestMigrationRequest:
    """Test MigrationRequest Pydantic model."""
    
    def test_create_basic_request(self):
        """Test creating a basic migration request."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            branch="main",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="ghp_test_token"
            )
        )
        
        assert request.migration_type == MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT
        assert request.repo_url == "https://github.com/org/repo"
        assert request.branch == "main"
        assert request.use_ai is False
        assert request.dry_run is False
        assert request.create_pr is True
        assert len(request.request_id) == 15  # Format: YYYYMMDD_HHMMSS
    
    def test_token_excluded_from_dict(self):
        """Test that token is excluded from model_dump()."""
        auth = RepositoryAuth(
            auth_type=AuthType.GITHUB_TOKEN,
            token="ghp_secret_token"
        )
        
        auth_dict = auth.model_dump()
        assert "token" not in auth_dict
        assert auth_dict["auth_type"] == "github_token"
    
    def test_repo_url_validation_success(self):
        """Test repo URL validation accepts valid platforms."""
        valid_urls = [
            "https://github.com/org/repo",
            "https://bitbucket.org/workspace/repo",
            "https://dev.azure.com/org/project/_git/repo",
            "https://gitlab.com/group/repo"
        ]
        
        for url in valid_urls:
            request = MigrationRequest(
                migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
                repo_url=url,
                branch="main",
                auth=RepositoryAuth(
                    auth_type=AuthType.GITHUB_TOKEN,
                    token="token"
                )
            )
            assert request.repo_url == url
    
    def test_repo_url_validation_failure(self):
        """Test repo URL validation rejects unsupported platforms."""
        with pytest.raises(ValueError, match="Unsupported repository platform"):
            MigrationRequest(
                migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
                repo_url="https://unsupported.com/repo",
                branch="main",
                auth=RepositoryAuth(
                    auth_type=AuthType.GITHUB_TOKEN,
                    token="token"
                )
            )
    
    def test_ai_config_with_api_key_excluded(self):
        """Test that AI config API key is excluded from serialization."""
        ai_config = AIConfig(
            mode=AIMode.PUBLIC_CLOUD,
            api_key="sk-secret-key",
            model="gpt-4"
        )
        
        config_dict = ai_config.model_dump()
        assert "api_key" not in config_dict
        assert config_dict["mode"] == "public_cloud"
        assert config_dict["model"] == "gpt-4"


class TestMigrationResponse:
    """Test MigrationResponse model."""
    
    def test_create_response(self):
        """Test creating a migration response."""
        response = MigrationResponse(
            request_id="migration-123",
            status=MigrationStatus.NOT_STARTED
        )
        
        assert response.request_id == "migration-123"
        assert response.status == MigrationStatus.NOT_STARTED
        assert response.files_discovered == {}
        assert response.files_transformed == []
        assert response.started_at is not None
    
    def test_mark_completed(self):
        """Test marking response as completed."""
        response = MigrationResponse(
            request_id="migration-123",
            status=MigrationStatus.TRANSFORMING
        )
        
        import time
        time.sleep(0.1)  # Simulate work
        
        response.mark_completed()
        
        assert response.status == MigrationStatus.COMPLETED
        assert response.completed_at is not None
        assert response.duration_seconds is not None
        assert response.duration_seconds > 0
    
    def test_mark_failed(self):
        """Test marking response as failed."""
        response = MigrationResponse(
            request_id="migration-123",
            status=MigrationStatus.ANALYZING
        )
        
        response.mark_failed(
            error="Repository not found",
            code="CS-REPO-001"
        )
        
        assert response.status == MigrationStatus.FAILED
        assert response.error_message == "Repository not found"
        assert response.error_code == "CS-REPO-001"
        assert response.completed_at is not None


class TestMigrationOrchestrator:
    """Test MigrationOrchestrator workflow."""
    
    @pytest.fixture
    def mock_connector(self):
        """Create a mock repository connector."""
        connector = Mock()
        connector.list_branches.return_value = [
            Mock(name="main"),
            Mock(name="develop")
        ]
        connector.list_all_files.return_value = [
            Mock(path="Test1.java"),
            Mock(path="Test2.java")
        ]
        # Create branch mock with name as string attribute
        branch_mock = Mock()
        branch_mock.name = "feature/migration"
        connector.create_branch.return_value = branch_mock
        
        connector.create_pull_request.return_value = Mock(
            number=123,
            url="https://github.com/org/repo/pull/123"
        )
        return connector
    
    @pytest.fixture
    def sample_request(self):
        """Create a sample migration request."""
        return MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            branch="main",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="ghp_test"
            ),
            java_source_path="src/test/java",
            feature_files_path="src/test/resources/features",
            dry_run=True,
            create_pr=False
        )
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = MigrationOrchestrator()
        assert orchestrator.response is None
    
    @patch('core.orchestration.orchestrator.translate_repo_to_connector')
    def test_run_dry_run_success(self, mock_translate, mock_connector, sample_request):
        """Test dry-run migration workflow."""
        mock_translate.return_value = mock_connector
        
        orchestrator = MigrationOrchestrator()
        progress_calls = []
        
        def progress_callback(msg, status):
            progress_calls.append((msg, status))
        
        response = orchestrator.run(sample_request, progress_callback)
        
        # Verify response
        assert response.request_id == sample_request.request_id
        assert response.status == MigrationStatus.COMPLETED
        assert response.files_discovered.get("java") == 2
        assert response.duration_seconds is not None
        
        # Verify progress callbacks were called
        assert len(progress_calls) > 0
        statuses = [status for _, status in progress_calls]
        assert MigrationStatus.VALIDATING in statuses
        assert MigrationStatus.ANALYZING in statuses
        assert MigrationStatus.COMPLETED in statuses
        
        # Verify connector calls
        mock_connector.list_branches.assert_called_once()
        assert mock_connector.list_all_files.call_count == 2  # Java + features
    
    @patch('core.orchestration.orchestrator.translate_repo_to_connector')
    def test_run_with_pr_creation(self, mock_translate, mock_connector, sample_request):
        """Test migration with PR creation."""
        mock_translate.return_value = mock_connector
        sample_request.dry_run = False
        sample_request.create_pr = True
        
        orchestrator = MigrationOrchestrator()
        response = orchestrator.run(sample_request)
        
        # Verify PR was created
        assert response.pr_number == 123
        assert response.pr_url == "https://github.com/org/repo/pull/123"
        assert response.branch_created == "feature/migration"  # String, not Mock object
        
        mock_connector.create_branch.assert_called_once()
        mock_connector.create_pull_request.assert_called_once()
    
    @patch('core.orchestration.orchestrator.translate_repo_to_connector')
    def test_run_validation_failure(self, mock_translate, sample_request):
        """Test orchestrator handles validation failures."""
        mock_translate.side_effect = ValueError("Invalid credentials")
        
        orchestrator = MigrationOrchestrator()
        response = orchestrator.run(sample_request)
        
        assert response.status == MigrationStatus.FAILED
        assert "Invalid credentials" in response.error_message
        assert response.error_code is not None
    
    @patch('core.orchestration.orchestrator.translate_repo_to_connector')
    def test_run_no_branches_found(self, mock_translate, mock_connector, sample_request):
        """Test orchestrator handles empty repository."""
        mock_translate.return_value = mock_connector
        mock_connector.list_branches.return_value = []
        
        orchestrator = MigrationOrchestrator()
        response = orchestrator.run(sample_request)
        
        assert response.status == MigrationStatus.FAILED
        assert "No branches found" in response.error_message
    
    @patch('core.orchestration.orchestrator.translate_repo_to_connector')
    def test_error_code_generation(self, mock_translate, sample_request):
        """Test error code inference from exceptions."""
        orchestrator = MigrationOrchestrator()
        
        # Auth error
        assert orchestrator._get_error_code(ValueError("auth failed")) == "CS-AUTH-001"
        
        # Repo error
        assert orchestrator._get_error_code(ValueError("repository not found")) == "CS-REPO-001"
        
        # Transform error
        assert orchestrator._get_error_code(ValueError("transform failed")) == "CS-TRANSFORM-001"
        
        # Unknown error
        assert orchestrator._get_error_code(ValueError("something else")) == "CS-UNKNOWN-001"
    
    def test_generate_pr_description(self, sample_request):
        """Test PR description generation."""
        orchestrator = MigrationOrchestrator()
        orchestrator.response = MigrationResponse(
            request_id=sample_request.request_id,
            status=MigrationStatus.GENERATING
        )
        orchestrator.response.files_discovered = {
            "java": 150,
            "feature": 260
        }
        
        description = orchestrator._generate_pr_description(sample_request)
        
        assert "CrossBridge" in description
        assert "selenium_java_bdd_to_robot_playwright" in description  # Check enum value
        assert "150" in description
        assert "260" in description
        assert sample_request.request_id in description
    
    @patch('core.orchestration.orchestrator.translate_repo_to_connector')
    def test_progress_callback_invocation(self, mock_translate, mock_connector, sample_request):
        """Test that progress callback is invoked at each stage."""
        mock_translate.return_value = mock_connector
        
        orchestrator = MigrationOrchestrator()
        callback_mock = Mock()
        
        response = orchestrator.run(sample_request, progress_callback=callback_mock)
        
        # Verify callback was called multiple times
        assert callback_mock.call_count >= 4
        
        # Verify different statuses were reported
        call_args = [call[0] for call in callback_mock.call_args_list]
        statuses = [args[1] for args in call_args]
        
        assert MigrationStatus.VALIDATING in statuses
        assert MigrationStatus.ANALYZING in statuses
        assert MigrationStatus.COMPLETED in statuses


class TestEndToEndWorkflow:
    """End-to-end integration tests for full workflow."""
    
    @patch('core.orchestration.orchestrator.translate_repo_to_connector')
    def test_full_workflow_bitbucket(self, mock_translate):
        """Test complete workflow with Bitbucket repository."""
        # Setup mock connector
        connector = Mock()
        connector.list_branches.return_value = [Mock(name="main")]
        connector.list_all_files.side_effect = [
            [Mock(path=f"Test{i}.java") for i in range(150)],  # Java files
            [Mock(path=f"feature{i}.feature") for i in range(260)]  # Feature files
        ]
        # Create branch mock with name as string attribute
        branch_mock = Mock()
        branch_mock.name = "feature/crossbridge-migration"
        connector.create_branch.return_value = branch_mock
        
        connector.create_pull_request.return_value = Mock(
            number=850,
            url="https://bitbucket.org/workspace/repo/pull-requests/850"
        )
        mock_translate.return_value = connector
        
        # Create request
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://bitbucket.org/workspace/repo",
            branch="main",
            auth=RepositoryAuth(
                auth_type=AuthType.BITBUCKET_TOKEN,
                username="user@example.com",
                token="ATATT..."
            ),
            java_source_path="src/main/java",
            feature_files_path="src/main/resources/features",
            use_ai=False,
            dry_run=False,
            create_pr=True
        )
        
        # Run orchestrator
        orchestrator = MigrationOrchestrator()
        progress_log = []
        
        def track_progress(msg, status):
            progress_log.append({
                "message": msg,
                "status": status,
                "timestamp": datetime.now()
            })
        
        response = orchestrator.run(request, progress_callback=track_progress)
        
        # Assertions
        assert response.status == MigrationStatus.COMPLETED
        assert response.files_discovered["java"] == 150
        assert response.files_discovered["feature"] == 260
        assert response.pr_number == 850
        assert response.pr_url == "https://bitbucket.org/workspace/repo/pull-requests/850"
        assert response.branch_created == "feature/crossbridge-migration"  # String, not Mock
        assert response.duration_seconds > 0
        assert response.error_message is None
        
        # Verify workflow progression
        assert len(progress_log) >= 5
        status_progression = [entry["status"] for entry in progress_log]
        assert status_progression[0] == MigrationStatus.VALIDATING
        assert MigrationStatus.ANALYZING in status_progression
        assert MigrationStatus.TRANSFORMING in status_progression
        assert status_progression[-1] == MigrationStatus.COMPLETED
    
    @patch('core.orchestration.orchestrator.translate_repo_to_connector')
    def test_full_workflow_github_with_ai(self, mock_translate):
        """Test complete workflow with GitHub and AI enabled."""
        connector = Mock()
        connector.list_branches.return_value = [Mock(name="main"), Mock(name="develop")]
        connector.list_all_files.side_effect = [
            [Mock(path=f"Test{i}.java") for i in range(50)],
            [Mock(path=f"test{i}.feature") for i in range(30)]
        ]
        connector.create_branch.return_value = Mock(name="feature/crossbridge-migration")
        connector.create_pull_request.return_value = Mock(
            number=42,
            url="https://github.com/org/repo/pull/42"
        )
        mock_translate.return_value = connector
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            branch="main",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="ghp_test"
            ),
            use_ai=True,
            ai_config=AIConfig(
                mode=AIMode.PUBLIC_CLOUD,
                provider="openai",
                api_key="sk-test"
            ),
            dry_run=False,
            create_pr=True
        )
        
        orchestrator = MigrationOrchestrator()
        response = orchestrator.run(request)
        
        assert response.status == MigrationStatus.COMPLETED
        assert response.files_discovered["java"] == 50
        assert response.files_discovered["feature"] == 30
        assert response.pr_number == 42
        
        # Verify PR description mentions AI
        pr_call = connector.create_pull_request.call_args
        pr_body = pr_call[1]["body"]
        assert "AI-assisted: Yes" in pr_body or "CrossBridge" in pr_body
