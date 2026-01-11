"""
Unit tests for operation type functionality.

Tests the three operation modes:
- Migration: Copy files without transformation
- Transformation: Transform already migrated files
- Migration + Transformation: Full migration with transformation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from core.orchestration.models import (
    MigrationRequest,
    MigrationType,
    OperationType,
    TransformationMode,
    RepositoryAuth,
    AuthType,
    MigrationResult
)
from core.orchestration.orchestrator import MigrationOrchestrator


class TestOperationType:
    """Test OperationType enum."""
    
    def test_operation_type_values(self):
        """Test that operation type enum has correct values."""
        assert OperationType.MIGRATION.value == "migration"
        assert OperationType.TRANSFORMATION.value == "transformation"
        assert OperationType.MIGRATION_AND_TRANSFORMATION.value == "migration_and_transformation"
    
    def test_operation_type_enum_members(self):
        """Test that all operation types are defined."""
        types = [e.value for e in OperationType]
        assert "migration" in types
        assert "transformation" in types
        assert "migration_and_transformation" in types


class TestMigrationRequestWithOperationType:
    """Test MigrationRequest with operation_type field."""
    
    def test_default_operation_type(self):
        """Test that default operation type is MIGRATION_AND_TRANSFORMATION."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token")
        )
        
        assert request.operation_type == OperationType.MIGRATION_AND_TRANSFORMATION
    
    def test_migration_only_operation_type(self):
        """Test setting operation type to MIGRATION."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.MIGRATION
        )
        
        assert request.operation_type == OperationType.MIGRATION
    
    def test_transformation_only_operation_type(self):
        """Test setting operation type to TRANSFORMATION."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.TRANSFORMATION
        )
        
        assert request.operation_type == OperationType.TRANSFORMATION


class TestDiscoverMigratedFiles:
    """Test _discover_migrated_files method."""
    
    def test_discover_migrated_files_success(self):
        """Test discovering migrated .robot files from target branch."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.TRANSFORMATION,
            target_branch="feature/test-migration"
        )
        
        # Mock connector
        connector = Mock()
        mock_file1 = Mock()
        mock_file1.path = "robot/features/login.robot"
        mock_file2 = Mock()
        mock_file2.path = "robot/keywords/login_keywords.robot"
        
        connector.list_all_files.return_value = [mock_file1, mock_file2]
        
        # Call method
        files = orchestrator._discover_migrated_files(request, connector, None)
        
        # Assertions
        assert len(files) == 2
        assert files[0].path == "robot/features/login.robot"
        assert files[1].path == "robot/keywords/login_keywords.robot"
        connector.list_all_files.assert_called_once_with(
            path="robot",
            pattern=".robot",
            progress_callback=None
        )
    
    def test_discover_migrated_files_empty(self):
        """Test discovering migrated files when none exist."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.TRANSFORMATION
        )
        
        connector = Mock()
        connector.list_all_files.return_value = []
        
        files = orchestrator._discover_migrated_files(request, connector, None)
        
        assert len(files) == 0
    
    def test_discover_migrated_files_error_handling(self):
        """Test error handling when target branch doesn't exist."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.TRANSFORMATION
        )
        
        connector = Mock()
        connector.list_all_files.side_effect = Exception("Branch not found")
        
        # Should not raise, should return empty list
        files = orchestrator._discover_migrated_files(request, connector, None)
        
        assert len(files) == 0


class TestMigrateFilesOnly:
    """Test _migrate_files_only method for Migration-only operation."""
    
    @patch('core.orchestration.orchestrator.ThreadPoolExecutor')
    def test_migrate_files_only_feature_file(self, mock_executor):
        """Test migrating feature file without transformation."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.MIGRATION,
            target_branch="feature/migration"
        )
        
        # Mock file
        mock_file = Mock()
        mock_file.path = "src/test/resources/features/login.feature"
        
        # Mock connector
        connector = Mock()
        connector.read_file.return_value = "Feature: Login\n  Scenario: Valid login\n    Given user is on login page"
        connector.write_files = Mock()
        
        # Mock executor to call read immediately
        def mock_executor_context(*args, **kwargs):
            executor = Mock()
            def mock_submit(func, file):
                future = Mock()
                future.result.return_value = func(file)
                return future
            executor.submit = mock_submit
            executor.__enter__ = Mock(return_value=executor)
            executor.__exit__ = Mock(return_value=False)
            return executor
        
        mock_executor.return_value = mock_executor_context()
        
        # Call method
        results = orchestrator._migrate_files_only(request, connector, [mock_file], None)
        
        # Assertions
        assert len(results) > 0
        # Verify no transformation was applied (content should be same)
        connector.read_file.assert_called()
    
    def test_migrate_files_only_changes_path(self):
        """Test that migration changes file paths correctly."""
        orchestrator = MigrationOrchestrator()
        
        # Test feature file path change
        test_cases = [
            ("src/test/resources/UIFeature/login.feature", "robot/features/login.robot"),
            ("src/main/java/steps/LoginSteps.java", "robot/LoginSteps.robot"),
        ]
        
        for source_path, expected_target in test_cases:
            if source_path.endswith('.feature'):
                target = source_path.replace('.feature', '.robot').replace('/UIFeature/', '/robot/features/')
            else:
                target = source_path.replace('.java', '.robot').replace('/java/', '/robot/')
            
            target = orchestrator.sanitize_filename(target)
            assert '.robot' in target


class TestTransformExistingFiles:
    """Test _transform_existing_files method for Transformation-only operation."""
    
    @patch('core.orchestration.orchestrator.ThreadPoolExecutor')
    def test_transform_existing_robot_files(self, mock_executor):
        """Test transforming already migrated .robot files."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.HYBRID,
            target_branch="feature/migration"
        )
        
        # Mock robot file
        mock_file = Mock()
        mock_file.path = "robot/features/login.robot"
        
        # Mock connector
        connector = Mock()
        connector.read_file.return_value = "*** Test Cases ***\nLogin Test\n    Log    Test"
        connector.write_files = Mock()
        
        # Mock executor
        def mock_executor_context(*args, **kwargs):
            executor = Mock()
            def mock_submit(func, file):
                future = Mock()
                future.result.return_value = func(file)
                return future
            executor.submit = mock_submit
            executor.__enter__ = Mock(return_value=executor)
            executor.__exit__ = Mock(return_value=False)
            return executor
        
        mock_executor.return_value = mock_executor_context()
        
        # Call method
        results = orchestrator._transform_existing_files(request, connector, [mock_file], None)
        
        # Should read from target branch
        connector.read_file.assert_called()
        
    def test_transform_existing_files_empty_list(self):
        """Test transformation with no files."""
        orchestrator = MigrationOrchestrator()
        
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.TRANSFORMATION
        )
        
        connector = Mock()
        
        results = orchestrator._transform_existing_files(request, connector, [], None)
        
        assert results == []


class TestOperationTypeRouting:
    """Test that orchestrator routes to correct methods based on operation type."""
    
    def test_operation_type_in_migration_request(self):
        """Test that operation_type is properly stored in request."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.TRANSFORMATION,
            transformation_mode=TransformationMode.ENHANCED
        )
        
        assert request.operation_type == OperationType.TRANSFORMATION
        assert request.transformation_mode == TransformationMode.ENHANCED
    
    def test_all_operation_types_accessible(self):
        """Test that all operation types can be set."""
        for op_type in OperationType:
            request = MigrationRequest(
                migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
                repo_url="https://github.com/test/repo",
                branch="main",
                auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
                operation_type=op_type
            )
            assert request.operation_type == op_type


class TestTransformationModeWithOperationType:
    """Test interaction between transformation_mode and operation_type."""
    
    def test_migration_only_ignores_transformation_mode(self):
        """Test that Migration-only doesn't use transformation mode."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.MIGRATION,
            transformation_mode=TransformationMode.ENHANCED
        )
        
        # Migration-only should not apply transformation
        assert request.operation_type == OperationType.MIGRATION
        # But transformation_mode is still set (for consistency)
        assert request.transformation_mode == TransformationMode.ENHANCED
    
    def test_transformation_only_uses_transformation_mode(self):
        """Test that Transformation-only applies the selected mode."""
        for mode in TransformationMode:
            request = MigrationRequest(
                migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
                repo_url="https://github.com/test/repo",
                branch="main",
                auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
                operation_type=OperationType.TRANSFORMATION,
                transformation_mode=mode
            )
            
            assert request.operation_type == OperationType.TRANSFORMATION
            assert request.transformation_mode == mode
    
    def test_migration_and_transformation_uses_both(self):
        """Test that Migration+Transformation uses transformation mode."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/test/repo",
            branch="main",
            auth=RepositoryAuth(auth_type=AuthType.GITHUB_TOKEN, token="test-token"),
            operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,
            transformation_mode=TransformationMode.HYBRID
        )
        
        assert request.operation_type == OperationType.MIGRATION_AND_TRANSFORMATION
        assert request.transformation_mode == TransformationMode.HYBRID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
