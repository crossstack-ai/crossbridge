"""
Unit tests for AI credential priority in memory commands.

Tests the credential priority logic in cli/commands/memory.py:
1. Cached credentials from 'crossbridge auth login' take priority
2. Config file settings are used as fallback
3. All AI providers work correctly (openai, anthropic, selfhosted)

Features tested:
- get_ai_provider_config() function
- Credential priority: cached > config file
- Support for all AI providers (openai, anthropic, selfhosted/ollama)
- Proper logging of credential source
- Framework-agnostic credential handling
"""

import pytest
from unittest.mock import patch, MagicMock
from cli.commands.memory import get_ai_provider_config


class TestAICredentialPriority:
    """Test credential priority logic for AI providers."""
    
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    def test_cached_selfhosted_takes_priority(
        self, 
        mock_get_ai_creds, 
        mock_get_selfhosted
    ):
        """Test that cached self-hosted credentials take priority over config."""
        # Setup: cached self-hosted credentials exist
        mock_get_selfhosted.return_value = {
            'endpoint_url': 'http://10.60.75.145:11434',
            'model_name': 'deepseek-coder:6.7b',
            'api_key': None
        }
        
        # Config has different provider
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': 'openai',
                            'model': 'text-embedding-3-small',
                            'api_key': 'sk-test123'
                        }
                    }
                }
            }
        }
        
        # Execute
        provider_type, provider_args = get_ai_provider_config(config)
        
        # Verify: cached credentials used, not config
        assert provider_type == 'local'
        assert provider_args['base_url'] == 'http://10.60.75.145:11434'
        assert provider_args['model'] == 'deepseek-coder:6.7b'
        assert 'api_key' not in provider_args or provider_args.get('api_key') is None
        
        # Verify selfhosted check was called first
        mock_get_selfhosted.assert_called_once()
        # OpenAI credentials should not be checked since selfhosted found
        mock_get_ai_creds.assert_not_called()
    
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    def test_cached_openai_takes_priority(
        self, 
        mock_get_ai_creds, 
        mock_get_selfhosted
    ):
        """Test that cached OpenAI credentials take priority over config."""
        # Setup: no selfhosted, but OpenAI cached
        mock_get_selfhosted.return_value = None
        mock_get_ai_creds.side_effect = lambda provider, auto_cache=False: (
            'sk-cached-key-xyz' if provider == 'openai' else None
        )
        
        # Config has different provider
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': 'local',
                            'model': 'sentence-transformers/all-MiniLM-L6-v2'
                        }
                    }
                }
            }
        }
        
        # Execute
        provider_type, provider_args = get_ai_provider_config(config)
        
        # Verify: cached OpenAI used
        assert provider_type == 'openai'
        assert provider_args['api_key'] == 'sk-cached-key-xyz'
        
        # Verify credential checks in correct order
        mock_get_selfhosted.assert_called_once()
        assert mock_get_ai_creds.call_count >= 1
        mock_get_ai_creds.assert_any_call('openai', auto_cache=False)
    
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    def test_cached_anthropic_takes_priority(
        self, 
        mock_get_ai_creds, 
        mock_get_selfhosted
    ):
        """Test that cached Anthropic credentials take priority over config."""
        # Setup: no selfhosted, no openai, but Anthropic cached
        mock_get_selfhosted.return_value = None
        mock_get_ai_creds.side_effect = lambda provider, auto_cache=False: (
            'sk-ant-cached-xyz' if provider == 'anthropic' else None
        )
        
        # Config has different provider
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': 'openai',
                            'model': 'text-embedding-3-small',
                            'api_key': 'sk-config-key'
                        }
                    }
                }
            }
        }
        
        # Execute
        provider_type, provider_args = get_ai_provider_config(config)
        
        # Verify: cached Anthropic used
        assert provider_type == 'anthropic'
        assert provider_args['api_key'] == 'sk-ant-cached-xyz'
        
        # Verify credential checks in correct order
        mock_get_selfhosted.assert_called_once()
        assert mock_get_ai_creds.call_count >= 2
        mock_get_ai_creds.assert_any_call('openai', auto_cache=False)
        mock_get_ai_creds.assert_any_call('anthropic', auto_cache=False)
    
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    def test_fallback_to_config_when_no_cached_credentials(
        self, 
        mock_get_ai_creds, 
        mock_get_selfhosted
    ):
        """Test fallback to config file when no cached credentials exist."""
        # Setup: no cached credentials at all
        mock_get_selfhosted.return_value = None
        mock_get_ai_creds.return_value = None
        
        # Config specifies OpenAI
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': 'openai',
                            'model': 'text-embedding-3-small',
                            'api_key': 'sk-config-key-123',
                            'batch_size': 100
                        }
                    }
                }
            }
        }
        
        # Execute
        provider_type, provider_args = get_ai_provider_config(config)
        
        # Verify: config file used as fallback
        assert provider_type == 'openai'
        assert provider_args['model'] == 'text-embedding-3-small'
        assert provider_args['api_key'] == 'sk-config-key-123'
        assert provider_args['batch_size'] == 100
        
        # Verify all credential sources checked
        mock_get_selfhosted.assert_called_once()
        assert mock_get_ai_creds.call_count >= 2
    
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    def test_config_local_provider_with_ollama_settings(
        self, 
        mock_get_ai_creds, 
        mock_get_selfhosted
    ):
        """Test config-based local/ollama provider with proper base_url."""
        # Setup: no cached credentials
        mock_get_selfhosted.return_value = None
        mock_get_ai_creds.return_value = None
        
        # Config specifies local/ollama
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': 'local',
                            'model': 'sentence-transformers/all-MiniLM-L6-v2'
                        }
                    },
                    'ollama': {
                        'base_url': 'http://localhost:11434',
                        'model': 'deepseek-coder:6.7b'
                    }
                }
            }
        }
        
        # Execute
        provider_type, provider_args = get_ai_provider_config(config)
        
        # Verify: local provider with ollama settings
        assert provider_type == 'local'
        assert provider_args['base_url'] == 'http://localhost:11434'
        assert provider_args['model'] == 'deepseek-coder:6.7b'
    
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    def test_selfhosted_with_api_key(
        self, 
        mock_get_ai_creds, 
        mock_get_selfhosted
    ):
        """Test self-hosted credentials with API key (some ollama servers require auth)."""
        # Setup: cached self-hosted with API key
        mock_get_selfhosted.return_value = {
            'endpoint_url': 'http://secure-ollama:11434',
            'model_name': 'deepseek-coder:33b',
            'api_key': 'ollama-secret-key'
        }
        
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': 'openai'
                        }
                    }
                }
            }
        }
        
        # Execute
        provider_type, provider_args = get_ai_provider_config(config)
        
        # Verify: API key included
        assert provider_type == 'local'
        assert provider_args['base_url'] == 'http://secure-ollama:11434'
        assert provider_args['model'] == 'deepseek-coder:33b'
        assert provider_args['api_key'] == 'ollama-secret-key'
    
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    @patch('cli.commands.memory.logger')
    def test_logging_for_cached_credentials(
        self, 
        mock_logger,
        mock_get_ai_creds, 
        mock_get_selfhosted
    ):
        """Test that credential source is properly logged."""
        # Setup: cached selfhosted
        mock_get_selfhosted.return_value = {
            'endpoint_url': 'http://10.60.75.145:11434',
            'model_name': 'deepseek-coder:6.7b',
            'api_key': None
        }
        
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': 'openai'
                        }
                    }
                }
            }
        }
        
        # Execute
        get_ai_provider_config(config)
        
        # Verify logging
        assert mock_logger.debug.call_count >= 1
        assert mock_logger.info.call_count >= 1
        
        # Check that we logged checking for cached credentials
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any('cached' in str(call).lower() for call in debug_calls)
        
        # Check that we logged using cached selfhosted
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any('cached' in str(call).lower() and 'self-hosted' in str(call).lower() 
                   for call in info_calls)
    
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    @patch('cli.commands.memory.logger')
    def test_logging_for_config_fallback(
        self, 
        mock_logger,
        mock_get_ai_creds, 
        mock_get_selfhosted
    ):
        """Test that config fallback is properly logged."""
        # Setup: no cached credentials
        mock_get_selfhosted.return_value = None
        mock_get_ai_creds.return_value = None
        
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': 'openai',
                            'model': 'text-embedding-3-small'
                        }
                    }
                }
            }
        }
        
        # Execute
        get_ai_provider_config(config)
        
        # Verify logging
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any('config-based provider' in str(call).lower() for call in info_calls)


class TestMemoryCommandsFrameworkSupport:
    """Test that credential priority works across all frameworks."""
    
    @pytest.mark.parametrize("provider_type,provider_config", [
        ("openai", {"api_key": "sk-test"}),
        ("anthropic", {"api_key": "sk-ant-test"}),
        ("local", {"base_url": "http://localhost:11434", "model": "deepseek"}),
    ])
    @patch('cli.commands.memory.get_selfhosted_ai_config')
    @patch('cli.commands.memory.get_ai_credentials')
    def test_all_providers_with_config_fallback(
        self, 
        mock_get_ai_creds,
        mock_get_selfhosted,
        provider_type,
        provider_config
    ):
        """Test that all AI providers work with config fallback."""
        # Setup: no cached credentials
        mock_get_selfhosted.return_value = None
        mock_get_ai_creds.return_value = None
        
        # Build config with specific provider
        config = {
            'crossbridge': {
                'ai': {
                    'semantic_engine': {
                        'embedding': {
                            'provider': provider_type,
                            **provider_config
                        }
                    }
                }
            }
        }
        
        if provider_type == 'local':
            config['crossbridge']['ai']['ollama'] = provider_config
        
        # Execute
        result_type, result_args = get_ai_provider_config(config)
        
        # Verify correct provider returned
        assert result_type == provider_type
        assert all(key in result_args for key in provider_config.keys())
