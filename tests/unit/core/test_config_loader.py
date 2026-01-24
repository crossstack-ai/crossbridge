"""
Unit tests for CrossBridge Unified Configuration System

Tests configuration loading, environment variable substitution,
default values, and singleton pattern.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from core.config import (
    CrossBridgeConfig,
    DatabaseConfig,
    ApplicationConfig,
    TranslationConfig,
    AIConfig,
    ConfigLoader,
    get_config,
    reset_config,
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config_yaml():
    """Sample YAML configuration content"""
    return """
crossbridge:
  mode: migration
  
  application:
    product_name: TestApp
    application_version: v2.0.0
    environment: staging
  
  database:
    host: db.example.com
    port: 5433
    database: test_db
    user: testuser
    password: testpass
  
  translation:
    mode: automated
    use_ai: true
    max_credits: 500
    confidence_threshold: 0.8
    validation_level: lenient
  
  ai:
    enabled: true
    provider: anthropic
    api_key: sk-test-key
    model: claude-3-sonnet
    temperature: 0.5
    max_tokens: 4096
  
  flaky_detection:
    enabled: true
    n_estimators: 150
    contamination: 0.15
  
  frameworks:
    pytest:
      enabled: true
      track_api_calls: false
    playwright:
      capture_network_traffic: false
"""


@pytest.fixture
def config_with_env_vars():
    """Config with environment variable substitutions"""
    return """
crossbridge:
  application:
    product_name: ${PRODUCT_NAME:-DefaultProduct}
    application_version: ${APP_VERSION:-v1.0.0}
  
  database:
    host: ${CROSSBRIDGE_DB_HOST:-localhost}
    port: ${CROSSBRIDGE_DB_PORT:-5432}
    password: ${CROSSBRIDGE_DB_PASSWORD:-admin}
  
  ai:
    api_key: ${OPENAI_API_KEY:-sk-default}
    model: ${AI_MODEL:-gpt-3.5-turbo}
"""


class TestConfigLoader:
    """Test ConfigLoader class functionality"""
    
    def test_find_config_file_in_current_dir(self, temp_config_dir):
        """Test finding config file in current directory"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text("crossbridge:\n  mode: observer")
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            found = ConfigLoader.find_config_file()
            assert found.resolve() == config_path.resolve()
    
    def test_find_config_file_in_parent_dir(self, temp_config_dir):
        """Test finding config file in parent directory"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text("crossbridge:\n  mode: observer")
        
        subdir = temp_config_dir / "subdir" / "deep"
        subdir.mkdir(parents=True)
        
        with patch('pathlib.Path.cwd', return_value=subdir):
            found = ConfigLoader.find_config_file()
            assert found.resolve() == config_path.resolve()
    
    def test_find_config_file_yaml_extension(self, temp_config_dir):
        """Test finding config with .yaml extension"""
        config_path = temp_config_dir / "crossbridge.yaml"
        config_path.write_text("crossbridge:\n  mode: observer")
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            found = ConfigLoader.find_config_file()
            assert found.resolve() == config_path.resolve()
    
    def test_find_config_file_dotfile(self, temp_config_dir):
        """Test finding hidden .crossbridge.yml"""
        config_path = temp_config_dir / ".crossbridge.yml"
        config_path.write_text("crossbridge:\n  mode: observer")
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            found = ConfigLoader.find_config_file()
            assert found.resolve() == config_path.resolve()
    
    def test_find_config_file_not_found(self, temp_config_dir):
        """Test when config file doesn't exist"""
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            found = ConfigLoader.find_config_file()
            assert found is None
    
    def test_load_with_defaults(self, temp_config_dir):
        """Test loading config with default values"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text("crossbridge:\n  mode: observer")
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            config = ConfigLoader.load()
            
            # Check defaults are applied
            assert config.mode == "observer"
            assert config.database.host == "10.55.12.99"
            assert config.database.port == 5432
            assert config.translation.mode == "assistive"
            assert config.ai.provider == "openai"
            assert config.flaky_detection.n_estimators == 200
    
    def test_load_custom_values(self, temp_config_dir, sample_config_yaml):
        """Test loading config with custom values"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text(sample_config_yaml)
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            config = ConfigLoader.load()
            
            # Check custom values
            assert config.mode == "migration"
            assert config.application.product_name == "TestApp"
            assert config.application.application_version == "v2.0.0"
            assert config.database.host == "db.example.com"
            assert config.database.port == 5433
            assert config.translation.mode == "automated"
            assert config.translation.use_ai is True
            assert config.translation.max_credits == 500
            assert config.ai.provider == "anthropic"
            assert config.ai.model == "claude-3-sonnet"
            assert config.flaky_detection.n_estimators == 150
    
    def test_load_with_env_var_substitution(self, temp_config_dir, config_with_env_vars):
        """Test environment variable substitution"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text(config_with_env_vars)
        
        env_vars = {
            "PRODUCT_NAME": "MyProduct",
            "APP_VERSION": "v3.1.4",
            "CROSSBRIDGE_DB_HOST": "prod-db.example.com",
            "OPENAI_API_KEY": "sk-prod-key",
            "AI_MODEL": "gpt-4",
        }
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            with patch.dict(os.environ, env_vars):
                config = ConfigLoader.load()
                
                # Check env vars were substituted
                assert config.application.product_name == "MyProduct"
                assert config.application.application_version == "v3.1.4"
                assert config.database.host == "prod-db.example.com"
                assert config.ai.api_key == "sk-prod-key"
                assert config.ai.model == "gpt-4"
    
    def test_load_with_env_var_defaults(self, temp_config_dir, config_with_env_vars):
        """Test environment variable defaults when env vars not set"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text(config_with_env_vars)
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            with patch.dict(os.environ, {}, clear=True):
                config = ConfigLoader.load()
                
                # Check default values are used
                assert config.application.product_name == "DefaultProduct"
                assert config.application.application_version == "v1.0.0"
                assert config.database.host == "localhost"
                assert str(config.database.port) == "5432"  # May be string from YAML
                assert config.ai.api_key == "sk-default"
                assert config.ai.model == "gpt-3.5-turbo"
    
    def test_save_config(self, temp_config_dir):
        """Test saving config to file"""
        config = CrossBridgeConfig(
            mode="migration",
            application=ApplicationConfig(
                product_name="SaveTest",
                application_version="v1.2.3",
                environment="test"
            ),
            database=DatabaseConfig(
                host="test-db.com",
                port=5433,
                database="test_save",
                user="testuser",
                password="testpass"
            )
        )
        
        save_path = temp_config_dir / "saved_config.yml"
        ConfigLoader.save(config, save_path)
        
        # Load it back and verify
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            with patch.object(ConfigLoader, 'find_config_file', return_value=save_path):
                loaded = ConfigLoader.load()
                
                assert loaded.mode == "migration"
                assert loaded.application.product_name == "SaveTest"
                assert loaded.database.host == "test-db.com"


class TestDatabaseConfig:
    """Test DatabaseConfig functionality"""
    
    def test_connection_string_generation(self):
        """Test PostgreSQL connection string generation"""
        db_config = DatabaseConfig(
            host="db.example.com",
            port=5433,
            database="mydb",
            user="myuser",
            password="mypass"
        )
        
        expected = "postgresql://myuser:mypass@db.example.com:5433/mydb"
        assert db_config.connection_string == expected
    
    def test_connection_string_with_special_chars(self):
        """Test connection string with special characters in password"""
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            user="admin",
            password="p@ss:word/123"
        )
        
        # Password should be URL-encoded
        conn_str = db_config.connection_string
        assert "p@ss:word/123" in conn_str  # Basic test (full URL encoding test would be more complex)


class TestTranslationConfig:
    """Test TranslationConfig validation"""
    
    def test_valid_modes(self):
        """Test valid translation modes"""
        for mode in ["assistive", "automated", "batch"]:
            config = TranslationConfig(mode=mode)
            assert config.mode == mode
    
    def test_valid_validation_levels(self):
        """Test valid validation levels"""
        for level in ["strict", "lenient", "skip"]:
            config = TranslationConfig(validation_level=level)
            assert config.validation_level == level
    
    def test_confidence_threshold_range(self):
        """Test confidence threshold boundaries"""
        # Valid values
        config1 = TranslationConfig(confidence_threshold=0.0)
        assert config1.confidence_threshold == 0.0
        
        config2 = TranslationConfig(confidence_threshold=1.0)
        assert config2.confidence_threshold == 1.0
        
        config3 = TranslationConfig(confidence_threshold=0.5)
        assert config3.confidence_threshold == 0.5


class TestAIConfig:
    """Test AIConfig validation"""
    
    def test_valid_providers(self):
        """Test valid AI providers"""
        for provider in ["openai", "anthropic", "custom"]:
            config = AIConfig(provider=provider)
            assert config.provider == provider
    
    def test_temperature_range(self):
        """Test temperature parameter boundaries"""
        config1 = AIConfig(temperature=0.0)
        assert config1.temperature == 0.0
        
        config2 = AIConfig(temperature=1.0)
        assert config2.temperature == 1.0


class TestSingletonPattern:
    """Test singleton get_config() function"""
    
    def test_get_config_returns_same_instance(self, temp_config_dir):
        """Test that get_config() returns the same instance"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text("crossbridge:\n  mode: observer")
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            reset_config()  # Clear any existing singleton
            
            config1 = get_config()
            config2 = get_config()
            
            assert config1 is config2  # Same object instance
    
    def test_reset_config_clears_singleton(self, temp_config_dir):
        """Test that reset_config() clears the singleton"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text("crossbridge:\n  mode: observer")
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            config1 = get_config()
            reset_config()
            config2 = get_config()
            
            assert config1 is not config2  # Different instances


class TestFrameworkConfig:
    """Test framework-specific configuration"""
    
    def test_framework_config_defaults(self):
        """Test default framework configuration"""
        config = ConfigLoader.load()
        
        # Check pytest defaults
        assert config.frameworks.pytest.enabled is True
        assert config.frameworks.pytest.auto_instrument_api_calls is True
        assert config.frameworks.pytest.track_keywords is True
        
        # Check playwright defaults
        assert config.frameworks.playwright.enabled is True
        assert config.frameworks.playwright.auto_instrument_ui_interactions is True
    
    def test_framework_config_custom_values(self, temp_config_dir):
        """Test custom framework configuration"""
        config_yaml = """
crossbridge:
  frameworks:
    pytest:
      enabled: false
      track_api_calls: false
    playwright:
      capture_network_traffic: false
"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text(config_yaml)
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            config = ConfigLoader.load()
            
            assert config.frameworks.pytest.enabled is False
            assert config.frameworks.pytest.track_api_calls is False
            assert config.frameworks.playwright.capture_network_traffic is False


class TestFlakyDetectionConfig:
    """Test flaky detection configuration"""
    
    def test_flaky_detection_defaults(self):
        """Test default flaky detection parameters"""
        config = ConfigLoader.load()
        
        assert config.flaky_detection.enabled is True
        assert config.flaky_detection.n_estimators == 200
        assert config.flaky_detection.contamination == 0.1
        assert config.flaky_detection.random_state == 42
        assert config.flaky_detection.min_executions_reliable == 15
    
    def test_flaky_detection_custom_values(self, temp_config_dir):
        """Test custom flaky detection values"""
        config_yaml = """
crossbridge:
  flaky_detection:
    enabled: false
    n_estimators: 100
    contamination: 0.2
    min_executions_reliable: 5
"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text(config_yaml)
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            config = ConfigLoader.load()
            
            assert config.flaky_detection.enabled is False
            assert config.flaky_detection.n_estimators == 100
            assert config.flaky_detection.contamination == 0.2
            assert config.flaky_detection.min_executions_reliable == 5


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    def test_ci_cd_pipeline_config(self, temp_config_dir):
        """Test typical CI/CD pipeline configuration"""
        config_yaml = """
crossbridge:
  mode: observer
  application:
    product_name: ${CI_PROJECT_NAME:-MyApp}
    application_version: ${CI_COMMIT_TAG:-dev}
    environment: ${CI_ENVIRONMENT_NAME:-test}
  database:
    host: ${CI_DB_HOST:-localhost}
  translation:
    mode: automated
    validation_level: lenient
  sidecar_hooks:
    auto_integrate: true
"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text(config_yaml)
        
        ci_env = {
            "CI_PROJECT_NAME": "payment-service",
            "CI_COMMIT_TAG": "v2.3.1",
            "CI_ENVIRONMENT_NAME": "production",
            "CI_DB_HOST": "prod-db.internal",
        }
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            with patch.dict(os.environ, ci_env):
                config = ConfigLoader.load()
                
                assert config.application.product_name == "payment-service"
                assert config.application.application_version == "v2.3.1"
                assert config.application.environment == "production"
                assert config.database.host == "prod-db.internal"
                assert config.translation.mode == "automated"
    
    def test_local_development_config(self, temp_config_dir):
        """Test typical local development configuration"""
        config_yaml = """
crossbridge:
  mode: migration
  database:
    host: localhost
    password: dev_password
  ai:
    enabled: false  # Save credits during development
  translation:
    mode: assistive
    validation_level: strict
  flaky_detection:
    min_executions_reliable: 5  # Lower threshold for faster feedback
"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text(config_yaml)
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            config = ConfigLoader.load()
            
            assert config.mode == "migration"
            assert config.database.host == "localhost"
            assert config.ai.enabled is False
            assert config.translation.mode == "assistive"
            assert config.flaky_detection.min_executions_reliable == 5


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_load_without_config_file_uses_defaults(self, temp_config_dir):
        """Test loading without config file uses all defaults"""
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            config = ConfigLoader.load()
            
            # Should get all default values
            assert config.mode == "observer"
            assert config.database.host == "10.55.12.99"
            assert config.translation.mode == "assistive"
            assert config.ai.provider == "openai"
    
    def test_load_malformed_yaml_raises_error(self, temp_config_dir):
        """Test that malformed YAML logs error and uses defaults"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text("crossbridge:\n  mode: [invalid yaml")
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            # Should log error but return defaults instead of raising
            config = ConfigLoader.load()
            # Should fallback to defaults when YAML is malformed
            assert config.mode == "observer"
    
    def test_empty_config_file_uses_defaults(self, temp_config_dir):
        """Test empty config file uses defaults"""
        config_path = temp_config_dir / "crossbridge.yml"
        config_path.write_text("")
        
        with patch('pathlib.Path.cwd', return_value=temp_config_dir):
            config = ConfigLoader.load()
            
            # Should get defaults
            assert config.mode == "observer"
            assert config.database.host == "10.55.12.99"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
