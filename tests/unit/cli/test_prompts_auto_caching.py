"""
Unit tests for automatic credential caching functionality.

Tests the auto-caching feature added to prompt_repository() and _prompt_authentication()
that automatically caches credentials when entered during migration/transformation in TEST mode.

Features tested:
- Auto-caching Bitbucket credentials in TEST mode
- Auto-caching GitHub credentials in TEST mode
- No caching in LIVE mode (security)
- Error handling when caching fails
- MigrationMode parameter propagation
"""

import pytest
from unittest.mock import patch, MagicMock, call
from cli.prompts import prompt_repository, _prompt_authentication
from core.orchestration.models import MigrationMode, AuthType, RepositoryAuth


class TestAutoCachingBitbucket:
    """Test automatic caching of Bitbucket credentials."""
    
    @patch('core.repo.test_credentials.cache_test_bitbucket_creds')
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_bitbucket_creds')
    def test_bitbucket_auto_cache_in_test_mode(
        self, 
        mock_get_creds, 
        mock_prompt, 
        mock_cache
    ):
        """Test that Bitbucket credentials are auto-cached in TEST mode."""
        # Setup: no cached credentials, user enters new ones
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_prompt.side_effect = [
            'user@example.com',  # username
            'test-token-12345'   # token
        ]
        
        # Execute
        result = _prompt_authentication(
            platform="bitbucket",
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify credentials cached
        mock_cache.assert_called_once_with(
            username='user@example.com',
            token='test-token-12345',
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="feature/test"
        )
        
        # Verify auth returned correctly
        assert result.auth_type == AuthType.BITBUCKET_TOKEN
        assert result.username == 'user@example.com'
        assert result.token == 'test-token-12345'
    
    @patch('core.repo.test_credentials.cache_test_bitbucket_creds')
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_bitbucket_creds')
    def test_bitbucket_no_cache_in_live_mode(
        self, 
        mock_get_creds, 
        mock_prompt, 
        mock_cache
    ):
        """Test that Bitbucket credentials are NOT cached in LIVE mode."""
        # Setup: no cached credentials, user enters new ones
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_prompt.side_effect = [
            'user@example.com',  # username
            'prod-token-12345'   # token
        ]
        
        # Execute
        result = _prompt_authentication(
            platform="bitbucket",
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="production",
            migration_mode=MigrationMode.LIVE
        )
        
        # Verify credentials NOT cached (security)
        mock_cache.assert_not_called()
        
        # Verify auth still returned correctly
        assert result.auth_type == AuthType.BITBUCKET_TOKEN
        assert result.username == 'user@example.com'
        assert result.token == 'prod-token-12345'
    
    @patch('core.repo.test_credentials.cache_test_bitbucket_creds')
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_bitbucket_creds')
    def test_bitbucket_no_cache_when_migration_mode_none(
        self, 
        mock_get_creds, 
        mock_prompt, 
        mock_cache
    ):
        """Test that credentials are NOT cached when migration_mode is None."""
        # Setup: no cached credentials, user enters new ones
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_prompt.side_effect = [
            'user@example.com',  # username
            'test-token-12345'   # token
        ]
        
        # Execute without migration_mode
        result = _prompt_authentication(
            platform="bitbucket",
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=None
        )
        
        # Verify credentials NOT cached
        mock_cache.assert_not_called()
        
        # Verify auth returned correctly
        assert result.auth_type == AuthType.BITBUCKET_TOKEN
    
    @patch('cli.prompts.console')
    @patch('core.repo.test_credentials.cache_test_bitbucket_creds')
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_bitbucket_creds')
    def test_bitbucket_cache_error_non_fatal(
        self, 
        mock_get_creds, 
        mock_prompt, 
        mock_cache,
        mock_console
    ):
        """Test that caching errors are non-fatal and operation continues."""
        # Setup: caching fails with error
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_prompt.side_effect = [
            'user@example.com',  # username
            'test-token-12345'   # token
        ]
        mock_cache.side_effect = Exception("Cache write failed")
        
        # Execute - should not raise exception
        result = _prompt_authentication(
            platform="bitbucket",
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify error logged but operation continues
        assert any(
            "Could not cache credentials" in str(call_args)
            for call_args in mock_console.print.call_args_list
        )
        
        # Verify auth still returned successfully
        assert result.auth_type == AuthType.BITBUCKET_TOKEN
        assert result.username == 'user@example.com'


class TestAutoCachingGitHub:
    """Test automatic caching of GitHub credentials."""
    
    @patch('core.repo.test_credentials.cache_test_github_creds')
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_github_creds')
    def test_github_auto_cache_in_test_mode(
        self, 
        mock_get_creds, 
        mock_prompt, 
        mock_cache
    ):
        """Test that GitHub credentials are auto-cached in TEST mode."""
        # Setup: no cached credentials, user enters new ones
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_prompt.side_effect = [
            'ghp_test1234567890abcdefghijklmnopqrstuvwxyz'  # GitHub PAT
        ]
        
        # Execute
        result = _prompt_authentication(
            platform="github",
            repo_url="https://github.com/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify credentials cached
        mock_cache.assert_called_once_with(
            username=None,
            token='ghp_test1234567890abcdefghijklmnopqrstuvwxyz'
        )
        
        # Verify auth returned correctly
        assert result.auth_type == AuthType.GITHUB_TOKEN
        assert result.token == 'ghp_test1234567890abcdefghijklmnopqrstuvwxyz'
    
    @patch('core.repo.test_credentials.cache_test_github_creds')
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_github_creds')
    def test_github_no_cache_in_live_mode(
        self, 
        mock_get_creds, 
        mock_prompt, 
        mock_cache
    ):
        """Test that GitHub credentials are NOT cached in LIVE mode."""
        # Setup: no cached credentials, user enters new ones
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_prompt.side_effect = [
            'ghp_prod1234567890abcdefghijklmnopqrstuvwxyz'  # GitHub PAT
        ]
        
        # Execute
        result = _prompt_authentication(
            platform="github",
            repo_url="https://github.com/test/repo",
            source_branch="main",
            target_branch="production",
            migration_mode=MigrationMode.LIVE
        )
        
        # Verify credentials NOT cached (security)
        mock_cache.assert_not_called()
        
        # Verify auth still returned correctly
        assert result.auth_type == AuthType.GITHUB_TOKEN
        assert result.token == 'ghp_prod1234567890abcdefghijklmnopqrstuvwxyz'
    
    @patch('cli.prompts.console')
    @patch('core.repo.test_credentials.cache_test_github_creds')
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_github_creds')
    def test_github_cache_error_non_fatal(
        self, 
        mock_get_creds, 
        mock_prompt, 
        mock_cache,
        mock_console
    ):
        """Test that GitHub caching errors are non-fatal."""
        # Setup: caching fails with error
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_prompt.side_effect = [
            'ghp_test1234567890abcdefghijklmnopqrstuvwxyz'  # GitHub PAT
        ]
        mock_cache.side_effect = Exception("Encryption failed")
        
        # Execute - should not raise exception
        result = _prompt_authentication(
            platform="github",
            repo_url="https://github.com/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify error logged but operation continues
        assert any(
            "Could not cache credentials" in str(call_args)
            for call_args in mock_console.print.call_args_list
        )
        
        # Verify auth still returned successfully
        assert result.auth_type == AuthType.GITHUB_TOKEN


class TestMigrationModeParameter:
    """Test that migration_mode parameter is properly propagated."""
    
    @patch('cli.prompts._prompt_authentication')
    @patch('cli.prompts.Confirm.ask', return_value=False)
    @patch('cli.prompts.Prompt.ask')
    def test_migration_mode_passed_to_auth(
        self, 
        mock_prompt, 
        mock_confirm,
        mock_auth
    ):
        """Test that migration_mode is passed from prompt_repository to _prompt_authentication."""
        # Setup return value for auth
        mock_auth.return_value = RepositoryAuth(
            auth_type=AuthType.BITBUCKET_TOKEN,
            username='test@example.com',
            token='test-token'
        )
        
        # Setup prompts
        mock_prompt.side_effect = [
            'https://bitbucket.org/test/repo',  # repo_url
            'main',                              # source_branch
            'feature/test'                       # target_branch
        ]
        
        # Execute with TEST mode
        result = prompt_repository(
            repo_url=None,
            branch=None,
            migration_type=None,
            skip_target_branch=False,
            migration_mode=MigrationMode.TEST
        )
        
        # Verify migration_mode passed to authentication
        call_args = mock_auth.call_args
        assert call_args is not None
        assert call_args[1]['migration_mode'] == MigrationMode.TEST
    
    @patch('cli.prompts._prompt_authentication')
    @patch('cli.prompts.Confirm.ask', return_value=False)
    @patch('cli.prompts.Prompt.ask')
    def test_migration_mode_none_handled(
        self, 
        mock_prompt, 
        mock_confirm,
        mock_auth
    ):
        """Test that migration_mode=None is handled correctly (backward compatibility)."""
        # Setup return value for auth
        mock_auth.return_value = RepositoryAuth(
            auth_type=AuthType.BITBUCKET_TOKEN,
            username='test@example.com',
            token='test-token'
        )
        
        # Setup prompts
        mock_prompt.side_effect = [
            'https://bitbucket.org/test/repo',  # repo_url
            'main',                              # source_branch
            'feature/test'                       # target_branch
        ]
        
        # Execute without migration_mode (backward compatibility)
        result = prompt_repository(
            repo_url=None,
            branch=None,
            migration_type=None,
            skip_target_branch=False,
            migration_mode=None
        )
        
        # Verify None is passed (no caching should happen)
        call_args = mock_auth.call_args
        assert call_args is not None
        assert call_args[1]['migration_mode'] is None


class TestCachedCredentialsLoading:
    """Test loading of previously cached credentials."""
    
    @patch('cli.prompts.Confirm.ask', return_value=True)
    @patch('core.repo.test_credentials.get_test_bitbucket_creds')
    def test_cached_bitbucket_creds_used(
        self, 
        mock_get_creds,
        mock_confirm
    ):
        """Test that cached Bitbucket credentials are loaded and used."""
        # Setup: cached credentials exist
        mock_get_creds.return_value = ('cached@example.com', 'cached-token-xyz', 
                                        'https://bitbucket.org/test/repo', 'main', 'feature/test')
        
        # Execute
        result = _prompt_authentication(
            platform="bitbucket",
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify cached credentials loaded
        mock_get_creds.assert_called_once()
        
        # Verify user accepted cached credentials
        mock_confirm.assert_called_once()
        
        # Verify cached auth used
        assert result.auth_type == AuthType.BITBUCKET_TOKEN
        assert result.username == 'cached@example.com'
        assert result.token == 'cached-token-xyz'
    
    @patch('cli.prompts.Prompt.ask')
    @patch('cli.prompts.Confirm.ask', return_value=False)
    @patch('core.repo.test_credentials.get_test_bitbucket_creds')
    def test_cached_bitbucket_creds_rejected(
        self, 
        mock_get_creds,
        mock_confirm,
        mock_prompt
    ):
        """Test that user can reject cached credentials and enter new ones."""
        # Setup: cached credentials exist but user rejects them
        mock_get_creds.return_value = ('old@example.com', 'old-token',
                                        'https://bitbucket.org/test/repo', 'main', 'feature/test')
        mock_prompt.side_effect = [
            'new@example.com',  # new username
            'new-token-12345'   # new token
        ]
        
        # Execute
        result = _prompt_authentication(
            platform="bitbucket",
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify cached credentials offered
        mock_get_creds.assert_called_once()
        mock_confirm.assert_called_once()
        
        # Verify new credentials used
        assert result.username == 'new@example.com'
        assert result.token == 'new-token-12345'
    
    @patch('cli.prompts.Confirm.ask', return_value=True)
    @patch('core.repo.test_credentials.get_test_github_creds')
    def test_cached_github_creds_used(
        self, 
        mock_get_creds,
        mock_confirm
    ):
        """Test that cached GitHub credentials are loaded and used."""
        # Setup: cached credentials exist
        mock_get_creds.return_value = ('github-user', 'ghp_cached_token_xyz')
        
        # Execute
        result = _prompt_authentication(
            platform="github",
            repo_url="https://github.com/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify cached credentials loaded
        mock_get_creds.assert_called_once()
        
        # Verify user accepted cached credentials
        mock_confirm.assert_called_once()
        
        # Verify cached auth used
        assert result.auth_type == AuthType.GITHUB_TOKEN
        assert result.token == 'ghp_cached_token_xyz'


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_bitbucket_creds')
    def test_empty_token_retry(
        self, 
        mock_get_creds,
        mock_prompt
    ):
        """Test that empty token prompts retry."""
        # Setup: no cached credentials, user enters empty then valid token
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_prompt.side_effect = [
            'user@example.com',  # username
            '',                  # empty token (retry)
            'valid-token-123'    # valid token
        ]
        
        # Execute
        result = _prompt_authentication(
            platform="bitbucket",
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify token prompt called twice (once for empty, once for valid)
        assert mock_prompt.call_count == 3  # username + empty token + valid token
        assert result.token == 'valid-token-123'
    
    @patch('cli.prompts.Confirm.ask', return_value=True)
    @patch('cli.prompts.Prompt.ask')
    @patch('core.repo.test_credentials.get_test_bitbucket_creds')
    def test_invalid_email_retry(
        self, 
        mock_get_creds,
        mock_prompt,
        mock_confirm
    ):
        """Test that invalid email (no @) shows warning and allows retry."""
        # Setup: no cached credentials
        mock_get_creds.side_effect = ValueError("No credentials")
        
        # User enters invalid email, confirms to continue anyway
        mock_prompt.side_effect = [
            'invalid-email',     # username without @ (triggers warning)
            'test-token-123'     # token
        ]
        
        # Execute
        result = _prompt_authentication(
            platform="bitbucket",
            repo_url="https://bitbucket.org/test/repo",
            source_branch="main",
            target_branch="feature/test",
            migration_mode=MigrationMode.TEST
        )
        
        # Verify warning shown (Confirm.ask called)
        mock_confirm.assert_called_once()
        
        # Verify operation completes with the invalid email
        assert result.auth_type == AuthType.BITBUCKET_TOKEN
        assert result.username == 'invalid-email'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
