"""
Unit tests for TRANSFORMATION operation fixes.

Tests:
1. Graceful exit when no migrated files found
2. Branch handling for TRANSFORMATION operations
3. User-specified target branch usage
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import (
    MigrationRequest, 
    OperationType, 
    TransformationMode, 
    MigrationType, 
    MigrationStatus,
    MigrationMode,
    RepositoryAuth,
    AuthType
)


class TestTransformationOperationFix:
    """Test suite for TRANSFORMATION operation fixes."""
    
    @staticmethod
    def _create_test_auth():
        """Create a test authentication object."""
        return RepositoryAuth(
            auth_type=AuthType.BITBUCKET_TOKEN,
            username="test_user",
            token="test_token"
        )
    
    def test_transformation_exits_gracefully_with_no_files(self):
        """Test that TRANSFORMATION exits gracefully when no migrated files found."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.ENHANCED,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=self._create_test_auth(),
            target_branch="feature/existing-branch",
            dry_run=False
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_migrated_files') as mock_discover:
                mock_connector = Mock()
                mock_validate.return_value = mock_connector
                mock_discover.return_value = []  # No migrated files
                
                progress_updates = []
                def progress_callback(message, status, completed_percent=None):
                    progress_updates.append((message, status))
                
                response = orchestrator.run(request, progress_callback)
                
                # Assertions
                assert response.status == MigrationStatus.COMPLETED
                assert "No files to transform" in response.error_message
                assert mock_discover.called
                
                # Verify early exit - should not proceed to transformation
                status_sequence = [status for _, status in progress_updates]
                assert MigrationStatus.TRANSFORMING not in status_sequence
                
                # Verify user-friendly message
                final_messages = [msg for msg, status in progress_updates if status == MigrationStatus.COMPLETED]
                assert any("No migrated files found" in msg for msg in final_messages)
    
    def test_transformation_uses_user_specified_branch(self):
        """Test that TRANSFORMATION uses the user-specified target branch."""
        orchestrator = MigrationOrchestrator()
        
        user_branch = "feature/my-migration-branch"
        request = MigrationRequest(
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.ENHANCED,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=self._create_test_auth(),
            target_branch=user_branch,
            dry_run=False
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_migrated_files') as mock_discover:
                with patch.object(orchestrator, '_transform_existing_files') as mock_transform:
                    mock_connector = Mock()
                    mock_validate.return_value = mock_connector
                    
                    # Return some files to avoid early exit
                    mock_files = [Mock(path="test1.robot"), Mock(path="test2.robot")]
                    mock_discover.return_value = mock_files
                    mock_transform.return_value = mock_files
                    
                    orchestrator.run(request)
                    
                    # Verify the request still has the user-specified branch
                    assert request.target_branch == user_branch
                    
                    # Verify _discover_migrated_files was called with correct request
                    mock_discover.assert_called_once()
                    call_request = mock_discover.call_args[0][0]
                    assert call_request.target_branch == user_branch
    
    def test_transformation_does_not_create_new_branch(self):
        """Test that TRANSFORMATION does not create a new branch."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.ENHANCED,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=self._create_test_auth(),
            target_branch="feature/existing-branch",
            dry_run=False
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_migrated_files') as mock_discover:
                with patch.object(orchestrator, '_create_migration_branch') as mock_create_branch:
                    with patch.object(orchestrator, '_transform_existing_files') as mock_transform:
                        mock_connector = Mock()
                        mock_validate.return_value = mock_connector
                        
                        mock_files = [Mock(path="test.robot")]
                        mock_discover.return_value = mock_files
                        mock_transform.return_value = mock_files
                        
                        orchestrator.run(request)
                        
                        # Verify branch creation was NOT called
                        mock_create_branch.assert_not_called()
    
    def test_transformation_processes_discovered_files(self):
        """Test that TRANSFORMATION processes all discovered migrated files."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.HYBRID,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=self._create_test_auth(),
            target_branch="feature/migration",
            dry_run=False
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_migrated_files') as mock_discover:
                with patch.object(orchestrator, '_transform_existing_files') as mock_transform:
                    mock_connector = Mock()
                    mock_validate.return_value = mock_connector
                    
                    # Create mock files
                    mock_files = [
                        Mock(path="tests/test1.robot"),
                        Mock(path="tests/test2.robot"),
                        Mock(path="tests/test3.robot")
                    ]
                    mock_discover.return_value = mock_files
                    mock_transform.return_value = mock_files
                    
                    response = orchestrator.run(request)
                    
                    # Verify all files were passed to transform
                    mock_transform.assert_called_once()
                    call_files = mock_transform.call_args[0][2]
                    assert len(call_files) == 3
                    assert call_files == mock_files
    
    def test_migration_operation_still_creates_branch(self):
        """Test that MIGRATION operation still creates a new branch."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            operation_type=OperationType.MIGRATION,
            transformation_mode=TransformationMode.MANUAL,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=self._create_test_auth(),
            dry_run=False
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_test_files') as mock_discover:
                with patch.object(orchestrator, '_create_migration_branch') as mock_create_branch:
                    with patch.object(orchestrator, '_migrate_files_only') as mock_migrate:
                        mock_connector = Mock()
                        mock_validate.return_value = mock_connector
                        
                        mock_java_files = [Mock(path="test.java")]
                        mock_feature_files = [Mock(path="test.feature")]
                        mock_discover.return_value = (mock_java_files, mock_feature_files)
                        mock_migrate.return_value = []
                        
                        orchestrator.run(request)
                        
                        # Verify branch creation WAS called for MIGRATION
                        mock_create_branch.assert_called_once()
    
    def test_migration_and_transformation_still_creates_branch(self):
        """Test that MIGRATION_AND_TRANSFORMATION operation creates a new branch."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,
            transformation_mode=TransformationMode.ENHANCED,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=self._create_test_auth(),
            dry_run=False
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_test_files') as mock_discover:
                with patch.object(orchestrator, '_create_migration_branch') as mock_create_branch:
                    with patch.object(orchestrator, '_transform_files') as mock_transform:
                        mock_connector = Mock()
                        mock_validate.return_value = mock_connector
                        
                        mock_java_files = [Mock(path="test.java")]
                        mock_feature_files = [Mock(path="test.feature")]
                        mock_discover.return_value = (mock_java_files, mock_feature_files)
                        mock_transform.return_value = []
                        
                        orchestrator.run(request)
                        
                        # Verify branch creation WAS called
                        mock_create_branch.assert_called_once()
    
    def test_transformation_progress_messages(self):
        """Test that TRANSFORMATION provides appropriate progress messages."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.ENHANCED,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",            auth=self._create_test_auth(),            target_branch="feature/migration",
            dry_run=False
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_migrated_files') as mock_discover:
                with patch.object(orchestrator, '_transform_existing_files') as mock_transform:
                    mock_connector = Mock()
                    mock_validate.return_value = mock_connector
                    
                    mock_files = [Mock(path="test.robot")]
                    mock_discover.return_value = mock_files
                    mock_transform.return_value = mock_files
                    
                    progress_messages = []
                    def progress_callback(message, status, completed_percent=None):
                        progress_messages.append(message)
                    
                    orchestrator.run(request, progress_callback)
                    
                    # Verify key messages appear
                    assert any("Discovering already migrated files" in msg for msg in progress_messages)
                    assert any("Using existing branch" in msg for msg in progress_messages)
                    assert any("Transforming" in msg and "existing files" in msg for msg in progress_messages)
    
    def test_transformation_with_dry_run(self):
        """Test that TRANSFORMATION respects dry_run flag."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.ENHANCED,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=self._create_test_auth(),
            target_branch="feature/migration",
            dry_run=True  # Dry run enabled
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_migrated_files') as mock_discover:
                with patch.object(orchestrator, '_transform_existing_files') as mock_transform:
                    mock_connector = Mock()
                    mock_validate.return_value = mock_connector
                    
                    mock_files = [Mock(path="test.robot")]
                    mock_discover.return_value = mock_files
                    
                    orchestrator.run(request)
                    
                    # Verify transformation was NOT called in dry run
                    mock_transform.assert_not_called()
    
    def test_transformation_return_value_structure(self):
        """Test that TRANSFORMATION returns properly structured response."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.ENHANCED,
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",            auth=self._create_test_auth(),            target_branch="feature/migration",
            dry_run=False
        )
        
        with patch.object(orchestrator, '_validate_repository_access') as mock_validate:
            with patch.object(orchestrator, '_discover_migrated_files') as mock_discover:
                mock_connector = Mock()
                mock_validate.return_value = mock_connector
                mock_discover.return_value = []
                
                response = orchestrator.run(request)
                
                # Verify response structure
                assert hasattr(response, 'status')
                assert hasattr(response, 'error_message')
                assert response.status == MigrationStatus.COMPLETED
                assert isinstance(response.error_message, str)
                assert len(response.error_message) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

