"""
CrossBridge Unified Configuration Loader

Loads configuration from crossbridge.yml file with environment variable overrides.
Provides a single source of truth for all CrossBridge configuration.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field, asdict
import yaml
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    enabled: bool = True
    host: str = "10.55.12.99"
    port: int = 5432
    database: str = "udp-native-webservices-automation"
    user: str = "postgres"
    password: str = "admin"
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class ApplicationConfig:
    """Application/Product tracking configuration"""
    product_name: str = "CrossBridgeApp"
    application_version: str = "v1.0.0"
    environment: str = "test"


@dataclass
class SidecarHooksConfig:
    """Sidecar observer hooks configuration"""
    enabled: bool = True
    auto_integrate: bool = True  # Auto-integrate during migration


@dataclass
class TranslationConfig:
    """Test translation/migration configuration"""
    # Translation mode
    mode: str = "assistive"  # assistive, automated, batch
    
    # AI settings
    use_ai: bool = False
    max_credits: int = 100
    confidence_threshold: float = 0.7
    
    # Validation
    validation_level: str = "strict"  # strict, lenient, skip
    preserve_comments: bool = True
    inject_todos: bool = True
    
    # Performance
    max_workers: int = 10
    commit_batch_size: int = 10


@dataclass
class AIConfig:
    """AI/LLM configuration"""
    enabled: bool = False
    provider: str = "openai"  # openai, anthropic, custom
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    region: str = "US"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60


@dataclass
class FlakyDetectionConfig:
    """Flaky test detection configuration"""
    enabled: bool = True
    n_estimators: int = 200
    contamination: float = 0.1
    random_state: int = 42
    min_executions_reliable: int = 15
    min_executions_confident: int = 30
    min_confidence_threshold: float = 0.5
    execution_window_size: int = 50
    recent_window_size: int = 10
    auto_retrain: bool = True
    retrain_threshold: int = 100
    model_version: str = "1.0.0"


@dataclass
class ObserverConfig:
    """Observer mode configuration"""
    auto_detect_new_tests: bool = True
    update_coverage_graph: bool = True
    detect_drift: bool = True
    flaky_threshold: float = 0.15


@dataclass
class IntelligenceConfig:
    """Intelligence features configuration"""
    ai_enabled: bool = True
    detect_coverage_gaps: bool = True
    detect_redundant_tests: bool = True
    risk_based_recommendations: bool = True


@dataclass
class FrameworkConfig:
    """Framework-specific configuration"""
    enabled: bool = True
    auto_instrument_api_calls: bool = True
    auto_instrument_ui_interactions: bool = False
    capture_network_traffic: bool = True
    track_keywords: bool = True
    track_api_calls: bool = True


@dataclass
class FrameworksConfig:
    """All frameworks configuration"""
    pytest: FrameworkConfig = field(default_factory=FrameworkConfig)
    playwright: FrameworkConfig = field(default_factory=FrameworkConfig)
    robot: FrameworkConfig = field(default_factory=FrameworkConfig)
    cypress: FrameworkConfig = field(default_factory=FrameworkConfig)


@dataclass
class LoggingConfig:
    """Logging configuration"""
    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    level: str = "INFO"
    
    # Output format: simple, detailed, json
    format: str = "detailed"
    
    # Log to file
    log_to_file: bool = True
    log_file_path: str = "logs/crossbridge.log"
    
    # Log to console
    log_to_console: bool = True
    
    # Rotation settings
    max_file_size_mb: int = 10
    backup_count: int = 5
    
    # Component-specific log levels (optional overrides)
    translation_level: Optional[str] = None  # Override for translation module
    ai_level: Optional[str] = None           # Override for AI module
    database_level: Optional[str] = None     # Override for database module
    observer_level: Optional[str] = None     # Override for observer module


@dataclass
class CrossBridgeConfig:
    """Complete CrossBridge configuration"""
    # Core settings
    mode: str = "observer"  # migration, observer
    
    # Sub-configurations
    application: ApplicationConfig = field(default_factory=ApplicationConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    sidecar_hooks: SidecarHooksConfig = field(default_factory=SidecarHooksConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    flaky_detection: FlakyDetectionConfig = field(default_factory=FlakyDetectionConfig)
    observer: ObserverConfig = field(default_factory=ObserverConfig)
    intelligence: IntelligenceConfig = field(default_factory=IntelligenceConfig)
    frameworks: FrameworksConfig = field(default_factory=FrameworksConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Loaded from file flag
    _config_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrossBridgeConfig':
        """Create from dictionary with nested objects"""
        config = cls()
        
        # Application config
        if 'application' in data:
            app_data = data['application']
            config.application = ApplicationConfig(
                product_name=app_data.get('product_name', 'CrossBridgeApp'),
                application_version=app_data.get('application_version', 'v1.0.0'),
                environment=app_data.get('environment', 'test')
            )
        
        # Database config
        if 'database' in data:
            db_data = data['database']
            config.database = DatabaseConfig(
                enabled=db_data.get('enabled', True),
                host=db_data.get('host', '10.55.12.99'),
                port=db_data.get('port', 5432),
                database=db_data.get('database', 'udp-native-webservices-automation'),
                user=db_data.get('user', 'postgres'),
                password=db_data.get('password', 'admin')
            )
        
        # Sidecar hooks config
        if 'sidecar_hooks' in data:
            hooks_data = data['sidecar_hooks']
            config.sidecar_hooks = SidecarHooksConfig(
                enabled=hooks_data.get('enabled', True),
                auto_integrate=hooks_data.get('auto_integrate', True)
            )
        
        # Translation config
        if 'translation' in data:
            trans_data = data['translation']
            config.translation = TranslationConfig(
                mode=trans_data.get('mode', 'assistive'),
                use_ai=trans_data.get('use_ai', False),
                max_credits=trans_data.get('max_credits', 100),
                confidence_threshold=trans_data.get('confidence_threshold', 0.7),
                validation_level=trans_data.get('validation_level', 'strict'),
                preserve_comments=trans_data.get('preserve_comments', True),
                inject_todos=trans_data.get('inject_todos', True),
                max_workers=trans_data.get('max_workers', 10),
                commit_batch_size=trans_data.get('commit_batch_size', 10)
            )
        
        # AI config
        if 'ai' in data:
            ai_data = data['ai']
            config.ai = AIConfig(
                enabled=ai_data.get('enabled', False),
                provider=ai_data.get('provider', 'openai'),
                api_key=ai_data.get('api_key'),
                endpoint=ai_data.get('endpoint'),
                model=ai_data.get('model', 'gpt-3.5-turbo'),
                region=ai_data.get('region', 'US'),
                temperature=ai_data.get('temperature', 0.7),
                max_tokens=ai_data.get('max_tokens', 2048),
                timeout=ai_data.get('timeout', 60)
            )
        
        # Flaky detection config
        if 'flaky_detection' in data:
            flaky_data = data['flaky_detection']
            config.flaky_detection = FlakyDetectionConfig(
                enabled=flaky_data.get('enabled', True),
                n_estimators=flaky_data.get('n_estimators', 200),
                contamination=flaky_data.get('contamination', 0.1),
                random_state=flaky_data.get('random_state', 42),
                min_executions_reliable=flaky_data.get('min_executions_reliable', 15),
                min_executions_confident=flaky_data.get('min_executions_confident', 30),
                min_confidence_threshold=flaky_data.get('min_confidence_threshold', 0.5),
                execution_window_size=flaky_data.get('execution_window_size', 50),
                recent_window_size=flaky_data.get('recent_window_size', 10),
                auto_retrain=flaky_data.get('auto_retrain', True),
                retrain_threshold=flaky_data.get('retrain_threshold', 100),
                model_version=flaky_data.get('model_version', '1.0.0')
            )
        
        # Observer config
        if 'observer' in data:
            obs_data = data['observer']
            config.observer = ObserverConfig(
                auto_detect_new_tests=obs_data.get('auto_detect_new_tests', True),
                update_coverage_graph=obs_data.get('update_coverage_graph', True),
                detect_drift=obs_data.get('detect_drift', True),
                flaky_threshold=obs_data.get('flaky_threshold', 0.15)
            )
        
        # Intelligence config
        if 'intelligence' in data:
            intel_data = data['intelligence']
            config.intelligence = IntelligenceConfig(
                ai_enabled=intel_data.get('ai_enabled', True),
                detect_coverage_gaps=intel_data.get('detect_coverage_gaps', True),
                detect_redundant_tests=intel_data.get('detect_redundant_tests', True),
                risk_based_recommendations=intel_data.get('risk_based_recommendations', True)
            )
        
        # Frameworks config
        if 'frameworks' in data:
            frameworks_data = data['frameworks']
            config.frameworks = FrameworksConfig()
            
            for framework_name in ['pytest', 'playwright', 'robot', 'cypress']:
                if framework_name in frameworks_data:
                    fw_data = frameworks_data[framework_name]
                    fw_config = FrameworkConfig(
                        enabled=fw_data.get('enabled', True),
                        auto_instrument_api_calls=fw_data.get('auto_instrument_api_calls', True),
                        auto_instrument_ui_interactions=fw_data.get('auto_instrument_ui_interactions', False),
                        capture_network_traffic=fw_data.get('capture_network_traffic', True),
                        track_keywords=fw_data.get('track_keywords', True),
                        track_api_calls=fw_data.get('track_api_calls', True)
                    )
                    setattr(config.frameworks, framework_name, fw_config)
        
        # Logging config
        if 'logging' in data:
            log_data = data['logging']
            config.logging = LoggingConfig(
                level=log_data.get('level', 'INFO'),
                format=log_data.get('format', 'detailed'),
                log_to_file=log_data.get('log_to_file', True),
                log_file_path=log_data.get('log_file_path', 'logs/crossbridge.log'),
                log_to_console=log_data.get('log_to_console', True),
                max_file_size_mb=log_data.get('max_file_size_mb', 10),
                backup_count=log_data.get('backup_count', 5),
                translation_level=log_data.get('translation_level'),
                ai_level=log_data.get('ai_level'),
                database_level=log_data.get('database_level'),
                observer_level=log_data.get('observer_level')
            )
        
        # Core mode
        config.mode = data.get('mode', 'observer')
        
        return config


class ConfigLoader:
    """
    Loads and manages CrossBridge configuration.
    
    Loads from:
    1. crossbridge.yml in current directory
    2. crossbridge.yml in project root
    3. Environment variables (override file settings)
    4. Default values
    """
    
    DEFAULT_CONFIG_NAMES = ['crossbridge.yml', 'crossbridge.yaml', '.crossbridge.yml']
    
    @staticmethod
    def find_config_file(start_path: Optional[Path] = None) -> Optional[Path]:
        """
        Find crossbridge.yml file by searching up the directory tree.
        
        Args:
            start_path: Starting directory (defaults to current directory)
            
        Returns:
            Path to config file or None if not found
        """
        if start_path is None:
            start_path = Path.cwd()
        
        current = start_path.resolve()
        
        # Search up to 10 levels or root
        for _ in range(10):
            for config_name in ConfigLoader.DEFAULT_CONFIG_NAMES:
                config_path = current / config_name
                if config_path.exists():
                    logger.info(f"Found config file: {config_path}")
                    return config_path
            
            # Check if we've reached root
            parent = current.parent
            if parent == current:
                break
            current = parent
        
        logger.warning("No config file found, using defaults")
        return None
    
    @staticmethod
    def load(config_path: Optional[Union[str, Path]] = None) -> CrossBridgeConfig:
        """
        Load configuration from file and environment variables.
        
        Args:
            config_path: Explicit path to config file (optional)
            
        Returns:
            CrossBridgeConfig instance
        """
        # Find config file
        if config_path:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_path}, using defaults")
                config_file = None
        else:
            config_file = ConfigLoader.find_config_file()
        
        # Load from file
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    yaml_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded config from: {config_file}")
            except Exception as e:
                logger.error(f"Error loading config file: {e}")
                yaml_data = {}
        else:
            yaml_data = {}
        
        # Extract crossbridge section
        crossbridge_data = yaml_data.get('crossbridge', {})
        
        # Apply environment variable substitutions
        crossbridge_data = ConfigLoader._apply_env_vars(crossbridge_data)
        
        # Create config from data
        config = CrossBridgeConfig.from_dict(crossbridge_data)
        config._config_file = str(config_file) if config_file else None
        
        logger.info("Configuration loaded successfully")
        return config
    
    @staticmethod
    def _apply_env_vars(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Supports ${VAR_NAME:-default_value} syntax in YAML.
        """
        import re
        
        def replace_env_vars(value: Any) -> Any:
            """Recursively replace environment variables"""
            if isinstance(value, str):
                # Match ${VAR_NAME:-default} or ${VAR_NAME}
                pattern = r'\$\{([^:}]+)(?::(-[^}]+))?\}'
                
                def replacer(match):
                    var_name = match.group(1)
                    default_value = match.group(2)[1:] if match.group(2) else None
                    return os.getenv(var_name, default_value or '')
                
                return re.sub(pattern, replacer, value)
            elif isinstance(value, dict):
                return {k: replace_env_vars(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_env_vars(item) for item in value]
            else:
                return value
        
        return replace_env_vars(data)
    
    @staticmethod
    def save(config: CrossBridgeConfig, path: Union[str, Path]) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config: Configuration to save
            path: Path to save file
        """
        config_dict = {
            'crossbridge': config.to_dict()
        }
        
        # Remove internal fields
        if '_config_file' in config_dict['crossbridge']:
            del config_dict['crossbridge']['_config_file']
        
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration saved to: {path}")


# Singleton instance
_global_config: Optional[CrossBridgeConfig] = None


def get_config(reload: bool = False, config_path: Optional[str] = None) -> CrossBridgeConfig:
    """
    Get global configuration instance (singleton pattern).
    
    Args:
        reload: Force reload from file
        config_path: Optional explicit config path
        
    Returns:
        CrossBridgeConfig instance
    """
    global _global_config
    
    if _global_config is None or reload:
        _global_config = ConfigLoader.load(config_path)
    
    return _global_config


def reset_config() -> None:
    """Reset global configuration (useful for testing)"""
    global _global_config
    _global_config = None
