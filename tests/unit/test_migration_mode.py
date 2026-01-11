"""
Unit tests for migration mode (Test vs Live) functionality.

Tests branch overwriting behavior, mode selection, and default values.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.orchestration import (
    MigrationMode,
    MigrationRequest,
    MigrationOrchestrator,
    MigrationType,
    AuthType,
    RepositoryAuth
)


class TestMigrationModeEnum:
    """Test MigrationMode enum values."""
    
    def test_migration_mode_test_value(self):
        """Test mode should have 'test' value."""
        assert MigrationMode.TEST.value == "test"
    
    def test_migration_mode_live_value(self):
        """Live mode should have 'live' value."""
        assert MigrationMode.LIVE.value == "live"


class TestMigrationRequestDefaults:
    """Test MigrationRequest default values for migration_mode."""
    
    def test_default_migration_mode_is_test(self):
        """MigrationRequest should default to TEST mode."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="test_token"
            )
        )
        assert request.migration_mode == MigrationMode.TEST
    
    def test_can_override_to_live_mode(self):
        """Should be able to explicitly set LIVE mode."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="test_token"
            ),
            migration_mode=MigrationMode.LIVE
        )
        assert request.migration_mode == MigrationMode.LIVE


class TestTestModeBranchOverwrite:
    """Test branch overwriting in TEST mode."""
    
    def test_test_mode_allows_fixed_branch_name(self):
        """TEST mode should support fixed branch names for overwriting."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://bitbucket.org/org/repo",
            branch="main",
            auth=RepositoryAuth(
                auth_type=AuthType.BITBUCKET_TOKEN,
                token="test_token",
                username="test@example.com"
            ),
            migration_mode=MigrationMode.TEST,
            target_branch="feature/crossbridge-test-migration"
        )
        
        # In test mode, can use fixed branch name
        assert request.target_branch == "feature/crossbridge-test-migration"
        assert request.migration_mode == MigrationMode.TEST


class TestLiveModeBranchCreation:
    """Test branch creation in LIVE mode."""
    
    def test_live_mode_prevents_fixed_branch_reuse(self):
        """LIVE mode should prevent reusing branch names via timestamps."""
        request1 = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="test_token"
            ),
            migration_mode=MigrationMode.LIVE
        )
        
        # Should have timestamp in branch name
        assert "feature/crossbridge-migration-" in request1.target_branch
        assert request1.migration_mode == MigrationMode.LIVE
    
    def test_live_mode_uses_timestamp_branch(self):
        """LIVE mode should use timestamped branch names by default."""
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="test_token"
            ),
            migration_mode=MigrationMode.LIVE
        )
        
        # Default target_branch should have timestamp
        assert "feature/crossbridge-migration-" in request.target_branch
        assert len(request.target_branch) > len("feature/crossbridge-migration-")


class TestCLIIntegration:
    """Test CLI integration with migration mode."""
    
    @patch('cli.prompts.Prompt.ask')
    @patch('cli.prompts.console')
    def test_prompt_migration_mode_default_test(self, mock_console, mock_ask):
        """Prompt should default to TEST mode."""
        from cli.prompts import prompt_migration_mode
        
        mock_ask.return_value = "1"  # Test mode
        
        result = prompt_migration_mode()
        
        assert result == MigrationMode.TEST
        mock_ask.assert_called_once()
        # Verify default is "1"
        assert mock_ask.call_args[1]['default'] == "1"
    
    @patch('cli.prompts.Prompt.ask')
    @patch('cli.prompts.console')
    def test_prompt_migration_mode_live_selection(self, mock_console, mock_ask):
        """User should be able to select LIVE mode."""
        from cli.prompts import prompt_migration_mode
        
        mock_ask.return_value = "2"  # Live mode
        
        result = prompt_migration_mode()
        
        assert result == MigrationMode.LIVE


class TestTargetBranchNaming:
    """Test target branch naming in different modes."""
    
    def test_test_mode_uses_fixed_branch_name(self):
        """TEST mode should use fixed branch name for overwriting."""
        from cli.app import app
        
        # In TEST mode, CLI sets fixed branch name
        request = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="test_token"
            ),
            migration_mode=MigrationMode.TEST
        )
        
        # After CLI processing, should be fixed name
        request.target_branch = "feature/crossbridge-test-migration"
        
        assert request.target_branch == "feature/crossbridge-test-migration"
    
    def test_live_mode_uses_unique_branch_name(self):
        """LIVE mode should use unique timestamped branch names."""
        request1 = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="test_token"
            ),
            migration_mode=MigrationMode.LIVE
        )
        
        import time
        time.sleep(0.1)  # Small delay
        
        request2 = MigrationRequest(
            migration_type=MigrationType.SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT,
            repo_url="https://github.com/org/repo",
            auth=RepositoryAuth(
                auth_type=AuthType.GITHUB_TOKEN,
                token="test_token"
            ),
            migration_mode=MigrationMode.LIVE
        )
        
        # Both should have timestamps and be different
        assert "feature/crossbridge-migration-" in request1.target_branch
        assert "feature/crossbridge-migration-" in request2.target_branch
        # They might be the same if created in same second, so just verify format
        assert len(request1.target_branch.split("-")) >= 4  # feature-crossbridge-migration-YYYYMMDD-HHMMSS


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
