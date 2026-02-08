"""
Unit tests for AI credential caching functionality.

Tests cover:
- cache_ai_credentials() - Caching AI provider credentials
- get_ai_credentials() - Retrieving cached AI credentials
- clear_ai_credentials() - Clearing cached AI credentials
- list_cached_test_creds() - Listing AI credentials
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
import os
import tempfile
from pathlib import Path

# Import AI credential functions
from core.repo.test_credentials import (
    cache_ai_credentials,
    get_ai_credentials,
    get_selfhosted_ai_config,
    clear_ai_credentials,
    list_cached_test_creds,
    _get_test_creds_manager,
)

# Import credential manager only if cryptography is available
try:
    from core.repo.credentials import CredentialManager, RepoCredential
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    CredentialManager = None
    RepoCredential = None


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_credential_manager(temp_config_dir):
    """Create mock credential manager."""
    if not CRYPTO_AVAILABLE:
        pytest.skip("cryptography not available")
    
    with patch('core.repo.test_credentials._get_test_creds_manager') as mock_get_mgr:
        manager = CredentialManager(config_dir=temp_config_dir)
        mock_get_mgr.return_value = manager
        yield manager


class TestCacheAICredentials:
    """Tests for cache_ai_credentials function."""
    
    def test_cache_openai_credentials_with_params(self, mock_credential_manager):
        """Test caching OpenAI credentials with parameters provided."""
        provider, api_key = cache_ai_credentials(
            provider="openai",
            api_key="sk-test-openai-key-12345",
            force_prompt=False
        )
        
        assert provider == "openai"
        assert api_key == "sk-test-openai-key-12345"
        assert os.environ.get("OPENAI_API_KEY") == "sk-test-openai-key-12345"
        
        # Verify it was stored in the manager
        mock_credential_manager._load_credentials()
        found = False
        for cred in mock_credential_manager._credentials.values():
            if cred.provider == "openai" and cred.repo == "_ai_cache_":
                found = True
                assert cred.token == "sk-test-openai-key-12345"
                break
        assert found, "OpenAI credentials not found in manager"
    
    def test_cache_anthropic_credentials_with_params(self, mock_credential_manager):
        """Test caching Anthropic credentials with parameters provided."""
        provider, api_key = cache_ai_credentials(
            provider="anthropic",
            api_key="sk-ant-test-key-67890",
            force_prompt=False
        )
        
        assert provider == "anthropic"
        assert api_key == "sk-ant-test-key-67890"
        assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test-key-67890"
        
        # Verify it was stored
        mock_credential_manager._load_credentials()
        found = False
        for cred in mock_credential_manager._credentials.values():
            if cred.provider == "anthropic" and cred.repo == "_ai_cache_":
                found = True
                assert cred.token == "sk-ant-test-key-67890"
                break
        assert found, "Anthropic credentials not found in manager"
    
    def test_cache_credentials_returns_cached_when_exists(self, mock_credential_manager):
        """Test that cached credentials are returned if they exist and force_prompt is False."""
        # First cache
        cache_ai_credentials(
            provider="openai",
            api_key="sk-original-key",
            force_prompt=False
        )
        
        # Try to cache again without force_prompt - should return cached
        provider, api_key = cache_ai_credentials(
            provider="openai",
            force_prompt=False
        )
        
        assert provider == "openai"
        assert api_key == "sk-original-key"
    
    def test_cache_credentials_updates_when_new_key_provided(self, mock_credential_manager):
        """Test that credentials are updated when a new API key is provided."""
        # First cache
        cache_ai_credentials(
            provider="openai",
            api_key="sk-old-key",
            force_prompt=False
        )
        
        # Cache with new key
        provider, api_key = cache_ai_credentials(
            provider="openai",
            api_key="sk-new-key",
            force_prompt=False
        )
        
        assert provider == "openai"
        assert api_key == "sk-new-key"
        assert os.environ.get("OPENAI_API_KEY") == "sk-new-key"
    
    @patch('builtins.input', side_effect=["1", "sk-prompted-key"])
    @patch('getpass.getpass', return_value="sk-prompted-key")
    def test_cache_credentials_prompts_when_no_params(self, mock_getpass, mock_input, mock_credential_manager):
        """Test that user is prompted when no parameters provided."""
        provider, api_key = cache_ai_credentials(force_prompt=True)
        
        assert provider == "openai"  # Choice "1" maps to openai
        assert api_key == "sk-prompted-key"
        assert mock_input.called or mock_getpass.called
    
    def test_cache_without_crypto_uses_env_vars(self):
        """Test that without cryptography, credentials are stored in environment only."""
        with patch('core.repo.test_credentials._get_test_creds_manager', return_value=None):
            provider, api_key = cache_ai_credentials(
                provider="openai",
                api_key="sk-env-only-key",
                force_prompt=False
            )
            
            assert provider == "openai"
            assert api_key == "sk-env-only-key"
            # Should only be in env vars
            assert os.environ.get("OPENAI_API_KEY") == "sk-env-only-key"


class TestGetAICredentials:
    """Tests for get_ai_credentials function."""
    
    def test_get_credentials_from_environment(self):
        """Test retrieving credentials from environment variables."""
        os.environ["OPENAI_API_KEY"] = "sk-from-env"
        
        api_key = get_ai_credentials("openai", auto_cache=False)
        
        assert api_key == "sk-from-env"
    
    def test_get_credentials_from_cache(self, mock_credential_manager):
        """Test retrieving credentials from cache."""
        # First cache some credentials
        cache_ai_credentials(
            provider="anthropic",
            api_key="sk-cached-anthropic",
            force_prompt=False
        )
        
        # Clear env var to ensure we're getting from cache
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        # Get from cache
        api_key = get_ai_credentials("anthropic", auto_cache=False)
        
        assert api_key == "sk-cached-anthropic"
        # Should also set env var
        assert os.environ.get("ANTHROPIC_API_KEY") == "sk-cached-anthropic"
    
    def test_get_credentials_returns_none_when_not_found(self):
        """Test that None is returned when credentials are not found."""
        # Clear environment
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        with patch('core.repo.test_credentials._get_test_creds_manager') as mock_get_mgr:
            manager = Mock()
            manager._load_credentials = Mock()
            manager._credentials = {}
            mock_get_mgr.return_value = manager
            
            api_key = get_ai_credentials("openai", auto_cache=False)
            
            assert api_key is None
    
    @patch('builtins.input', return_value='y')
    def test_get_credentials_prompts_to_cache_when_auto_cache(self, mock_input, mock_credential_manager):
        """Test that user is prompted to cache when auto_cache=True and credentials not found."""
        # Clear environment
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        with patch('core.repo.test_credentials.cache_ai_credentials') as mock_cache:
            mock_cache.return_value = ("openai", "sk-new-cached-key")
            
            api_key = get_ai_credentials("openai", auto_cache=True)
            
            assert mock_input.called
            assert mock_cache.called
            assert api_key == "sk-new-cached-key"
    
    @patch('builtins.input', return_value='n')
    def test_get_credentials_respects_user_decline_to_cache(self, mock_input, mock_credential_manager):
        """Test that None is returned when user declines to cache."""
        # Clear environment
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        api_key = get_ai_credentials("openai", auto_cache=True)
        
        assert mock_input.called
        assert api_key is None
    
    def test_get_credentials_without_manager_returns_none(self):
        """Test behavior when credential manager is not available."""
        # Clear environment
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        with patch('core.repo.test_credentials._get_test_creds_manager', return_value=None):
            api_key = get_ai_credentials("openai", auto_cache=False)
            
            assert api_key is None


class TestClearAICredentials:
    """Tests for clear_ai_credentials function."""
    
    def test_clear_specific_provider_credentials(self, mock_credential_manager):
        """Test clearing credentials for a specific provider."""
        # Cache both OpenAI and Anthropic
        cache_ai_credentials(provider="openai", api_key="sk-openai", force_prompt=False)
        cache_ai_credentials(provider="anthropic", api_key="sk-anthropic", force_prompt=False)
        
        # Clear only OpenAI
        result = clear_ai_credentials("openai")
        
        assert result is True
        
        # Verify OpenAI is cleared but Anthropic remains
        mock_credential_manager._load_credentials()
        openai_found = False
        anthropic_found = False
        
        for cred in mock_credential_manager._credentials.values():
            if cred.repo == "_ai_cache_":
                if cred.provider == "openai":
                    openai_found = True
                if cred.provider == "anthropic":
                    anthropic_found = True
        
        assert not openai_found, "OpenAI credentials should be cleared"
        assert anthropic_found, "Anthropic credentials should remain"
    
    def test_clear_all_ai_credentials(self, mock_credential_manager):
        """Test clearing all AI credentials."""
        # Cache both providers
        cache_ai_credentials(provider="openai", api_key="sk-openai", force_prompt=False)
        cache_ai_credentials(provider="anthropic", api_key="sk-anthropic", force_prompt=False)
        
        # Clear all AI credentials
        result = clear_ai_credentials(provider=None)
        
        assert result is True
        
        # Verify all AI credentials are cleared
        mock_credential_manager._load_credentials()
        ai_creds_found = False
        
        for cred in mock_credential_manager._credentials.values():
            if cred.repo == "_ai_cache_":
                ai_creds_found = True
                break
        
        assert not ai_creds_found, "All AI credentials should be cleared"
    
    def test_clear_returns_false_when_no_credentials(self, mock_credential_manager):
        """Test that False is returned when no credentials exist to clear."""
        result = clear_ai_credentials("openai")
        
        assert result is False
    
    def test_clear_without_manager_returns_false(self):
        """Test behavior when credential manager is not available."""
        with patch('core.repo.test_credentials._get_test_creds_manager', return_value=None):
            result = clear_ai_credentials("openai")
            
            assert result is False


class TestListCachedCredentials:
    """Tests for list_cached_test_creds function with AI credentials."""
    
    def test_list_shows_ai_credentials(self, mock_credential_manager, capsys):
        """Test that listing shows AI credentials."""
        # Cache AI credentials
        cache_ai_credentials(provider="openai", api_key="sk-test-openai-key", force_prompt=False)
        cache_ai_credentials(provider="anthropic", api_key="sk-test-anthropic-key", force_prompt=False)
        
        # List credentials
        list_cached_test_creds()
        
        captured = capsys.readouterr()
        assert "Cached AI Provider Credentials" in captured.out
        assert "OPENAI" in captured.out.upper()
        assert "ANTHROPIC" in captured.out.upper()
        # Keys should be masked
        assert "sk-test-openai-key" not in captured.out
        assert "..." in captured.out  # Masked format
    
    def test_list_shows_no_credentials_message(self, mock_credential_manager, capsys):
        """Test that appropriate message is shown when no credentials exist."""
        list_cached_test_creds()
        
        captured = capsys.readouterr()
        assert "No cached credentials" in captured.out
    
    def test_list_handles_missing_manager(self, capsys):
        """Test behavior when credential manager is not available."""
        with patch('core.repo.test_credentials._get_test_creds_manager', return_value=None):
            list_cached_test_creds()
            
            captured = capsys.readouterr()
            assert "Credential manager not available" in captured.out


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_cache_with_empty_api_key(self, mock_credential_manager):
        """Test behavior with empty API key."""
        provider, api_key = cache_ai_credentials(
            provider="openai",
            api_key="",
            force_prompt=False
        )
        
        assert provider == "openai"
        assert api_key == ""
    
    def test_cache_with_invalid_provider(self, mock_credential_manager):
        """Test caching with custom provider name."""
        # Should still work - we don't validate provider names
        provider, api_key = cache_ai_credentials(
            provider="custom-llm",
            api_key="sk-custom-key",
            force_prompt=False
        )
        
        assert provider == "custom-llm"
        assert api_key == "sk-custom-key"
    
    def test_get_credentials_case_sensitivity(self):
        """Test that provider name matching is case-sensitive."""
        # Create a completely fresh temp directory and manager for this test
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        
        # Clear ALL potentially interfering env vars
        env_backup = {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY')
        }
        
        try:
            # Clear environment
            for key in env_backup.keys():
                if key in os.environ:
                    del os.environ[key]
            
            with patch('core.repo.test_credentials._get_test_creds_manager') as mock_get_mgr:
                manager = CredentialManager(config_dir=temp_dir)
                mock_get_mgr.return_value = manager
                
                # Cache with lowercase provider
                cache_ai_credentials(provider="openai", api_key="sk-lowercase", force_prompt=False)
                
                # Clear env again
                if "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]
                
                # Should not find with uppercase (case-sensitive)
                api_key = get_ai_credentials("OPENAI", auto_cache=False)
                # Note: get_ai_credentials first checks env vars, which are cleared
                # Then checks cache which should not have "OPENAI" (uppercase)
                assert api_key is None, f"Expected None for uppercase 'OPENAI' but got {api_key}"
                
                # Clear env again before testing lowercase
                if "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]
                    
                # Should find with lowercase
                api_key = get_ai_credentials("openai", auto_cache=False)
                assert api_key == "sk-lowercase", f"Expected 'sk-lowercase' for lowercase 'openai' but got {api_key}"
        finally:
            # Restore environment
            for key, value in env_backup.items():
                if value is not None:
                    os.environ[key] = value
                elif key in os.environ:
                    del os.environ[key]
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_multiple_cache_calls_same_provider(self, mock_credential_manager):
        """Test multiple caching calls for same provider."""
        # Cache multiple times
        cache_ai_credentials(provider="openai", api_key="key1", force_prompt=False)
        cache_ai_credentials(provider="openai", api_key="key2", force_prompt=False)
        cache_ai_credentials(provider="openai", api_key="key3", force_prompt=False)
        
        # Should have the latest key
        api_key = get_ai_credentials("openai", auto_cache=False)
        assert api_key == "key3"


class TestIntegrationScenarios:
    """Integration tests for complete workflows."""
    
    def test_full_workflow_cache_get_clear(self, mock_credential_manager):
        """Test complete workflow: cache -> get -> clear."""
        # Step 1: Cache credentials
        provider, api_key = cache_ai_credentials(
            provider="openai",
            api_key="sk-workflow-test",
            force_prompt=False
        )
        assert provider == "openai"
        assert api_key == "sk-workflow-test"
        
        # Step 2: Retrieve credentials
        retrieved_key = get_ai_credentials("openai", auto_cache=False)
        assert retrieved_key == "sk-workflow-test"
        
        # Step 3: Clear credentials
        cleared = clear_ai_credentials("openai")
        assert cleared is True
        
        # Step 4: Verify cleared
        # Clear env first
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        final_key = get_ai_credentials("openai", auto_cache=False)
        assert final_key is None
    
    def test_multiple_providers_workflow(self, mock_credential_manager):
        """Test working with multiple AI providers simultaneously."""
        # Cache multiple providers
        cache_ai_credentials(provider="openai", api_key="sk-openai-key", force_prompt=False)
        cache_ai_credentials(provider="anthropic", api_key="sk-anthropic-key", force_prompt=False)
        
        # Clear environment
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            if key in os.environ:
                del os.environ[key]
        
        # Retrieve each
        openai_key = get_ai_credentials("openai", auto_cache=False)
        anthropic_key = get_ai_credentials("anthropic", auto_cache=False)
        
        assert openai_key == "sk-openai-key"
        assert anthropic_key == "sk-anthropic-key"
        
        # Clear one provider
        clear_ai_credentials("openai")
        
        # Verify selective clearing
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        openai_after = get_ai_credentials("openai", auto_cache=False)
        anthropic_after = get_ai_credentials("anthropic", auto_cache=False)
        
        assert openai_after is None
        assert anthropic_after == "sk-anthropic-key"


class TestSelfHostedAI:
    """Tests for self-hosted AI credential functionality."""
    
    def test_cache_selfhosted_with_all_params(self, mock_credential_manager):
        """Test caching self-hosted AI with all parameters."""
        provider, api_key = cache_ai_credentials(
            provider="selfhosted",
            api_key="custom-api-key",
            endpoint_url="http://10.60.75.145:11434",
            model_name="deepseek-coder:6.7b",
            force_prompt=False
        )
        
        assert provider == "selfhosted"
        assert api_key == "custom-api-key"
        
        # Verify it was stored with correct fields
        mock_credential_manager._load_credentials()
        found = False
        for cred in mock_credential_manager._credentials.values():
            if cred.provider == "selfhosted" and cred.repo == "_ai_cache_":
                found = True
                assert cred.token == "custom-api-key"
                assert cred.url == "http://10.60.75.145:11434"
                assert cred.source_branch == "deepseek-coder:6.7b"
                break
        assert found, "Self-hosted credentials not found in manager"
    
    def test_cache_selfhosted_without_api_key(self, mock_credential_manager):
        """Test caching self-hosted AI without API key (optional)."""
        provider, api_key = cache_ai_credentials(
            provider="selfhosted",
            api_key="",
            endpoint_url="http://localhost:11434",
            model_name="llama2",
            force_prompt=False
        )
        
        assert provider == "selfhosted"
        assert api_key == ""
        
        # Verify it was stored
        mock_credential_manager._load_credentials()
        found = False
        for cred in mock_credential_manager._credentials.values():
            if cred.provider == "selfhosted":
                found = True
                assert cred.token == ""
                assert cred.url == "http://localhost:11434"
                assert cred.source_branch == "llama2"
                break
        assert found
    
    def test_get_selfhosted_ai_config(self, mock_credential_manager):
        """Test retrieving self-hosted AI configuration."""
        from core.repo.test_credentials import get_selfhosted_ai_config
        
        # Cache self-hosted credentials
        cache_ai_credentials(
            provider="selfhosted",
            api_key="test-key",
            endpoint_url="http://192.168.1.100:8000",
            model_name="custom-model-v1",
            force_prompt=False
        )
        
        # Retrieve config
        config = get_selfhosted_ai_config()
        
        assert config is not None
        assert config['endpoint_url'] == "http://192.168.1.100:8000"
        assert config['model_name'] == "custom-model-v1"
        assert config['api_key'] == "test-key"
    
    def test_get_selfhosted_ai_config_not_found(self, mock_credential_manager):
        """Test get_selfhosted_ai_config when no credentials cached."""
        from core.repo.test_credentials import get_selfhosted_ai_config
        
        config = get_selfhosted_ai_config()
        assert config is None
    
    def test_clear_selfhosted_credentials(self, mock_credential_manager):
        """Test clearing self-hosted AI credentials."""
        # Cache self-hosted credentials
        cache_ai_credentials(
            provider="selfhosted",
            api_key="key-to-clear",
            endpoint_url="http://example.com:1234",
            model_name="test-model",
            force_prompt=False
        )
        
        # Clear them
        result = clear_ai_credentials("selfhosted")
        assert result is True
        
        # Verify they're gone
        from core.repo.test_credentials import get_selfhosted_ai_config
        config = get_selfhosted_ai_config()
        assert config is None
    
    def test_list_shows_selfhosted_details(self, mock_credential_manager, capsys):
        """Test that list_cached_test_creds shows self-hosted AI details."""
        # Cache self-hosted credentials
        cache_ai_credentials(
            provider="selfhosted",
            api_key="display-key",
            endpoint_url="http://ai.local:5000",
            model_name="gpt-local",
            force_prompt=False
        )
        
        # List credentials
        list_cached_test_creds()
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Verify self-hosted details are shown
        assert "SELFHOSTED" in output
        assert "http://ai.local:5000" in output
        assert "gpt-local" in output
    
    def test_get_ai_credentials_with_selfhosted(self, mock_credential_manager):
        """Test get_ai_credentials works with selfhosted provider."""
        # Cache self-hosted credentials
        cache_ai_credentials(
            provider="selfhosted",
            api_key="selfhosted-key",
            endpoint_url="http://localhost:8080",
            model_name="model-x",
            force_prompt=False
        )
        
        # Retrieve using get_ai_credentials
        api_key = get_ai_credentials("selfhosted", auto_cache=False)
        
        assert api_key == "selfhosted-key"
    
    def test_selfhosted_with_empty_api_key_retrieval(self, mock_credential_manager):
        """Test retrieving self-hosted credentials with empty API key."""
        # Cache with no API key
        cache_ai_credentials(
            provider="selfhosted",
            api_key="",
            endpoint_url="http://ollama:11434",
            model_name="mistral",
            force_prompt=False
        )
        
        # Should return empty string, not None
        api_key = get_ai_credentials("selfhosted", auto_cache=False)
        assert api_key == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
