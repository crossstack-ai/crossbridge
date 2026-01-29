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
class AITransformationConfig:
    """AI Transformation Validation configuration"""
    enabled: Union[bool, str] = "auto"  # true, false, auto (auto-enable in migration mode)
    
    # Storage
    storage_directory: str = ".crossbridge/transformations"
    backup_enabled: bool = True
    backup_directory: str = ".crossbridge/transformations/backups"
    
    # Confidence scoring
    confidence_threshold: float = 0.8
    high_confidence_level: float = 0.8
    medium_confidence_level: float = 0.5
    
    # Confidence signals
    diff_size_small_threshold: int = 20
    diff_size_medium_threshold: int = 50
    diff_size_large_threshold: int = 100
    diff_size_very_large_penalty: float = -0.3
    rule_violations_penalty: float = -0.1
    rule_violations_max_penalty: float = -0.3
    similarity_low_threshold: float = 0.6
    similarity_medium_threshold: float = 0.8
    syntax_validation_penalty: float = -0.4
    test_coverage_penalty: float = -0.2
    
    # Review workflow
    require_reviewer: bool = True
    require_rejection_reason: bool = True
    allow_rereview: bool = False
    expire_pending_days: int = 30
    
    # Apply & rollback
    git_commit: bool = True
    git_commit_prefix: str = "AI Transform:"
    verify_syntax: bool = True
    run_linting: bool = False
    linting_command: str = "flake8"
    run_tests: bool = False
    test_command: str = "pytest"
    
    # Rollback
    max_rollback_history: int = 10
    require_rollback_confirmation: bool = True
    rollback_git_commit: bool = True
    rollback_git_commit_prefix: str = "Rollback AI Transform:"
    
    # Audit
    audit_enabled: bool = True
    hash_prompts: bool = True
    log_all_events: bool = True
    export_audit_logs: bool = True
    audit_export_path: str = ".crossbridge/transformations/audit.jsonl"
    
    # CLI defaults
    cli_default_format: str = "table"
    cli_show_diff_default: bool = False
    cli_auto_apply_default: bool = False
    
    # Migration mode overrides
    migration_enabled: Optional[bool] = True
    migration_confidence_threshold: Optional[float] = 0.85
    migration_require_reviewer: Optional[bool] = True
    migration_git_commit: Optional[bool] = True
    migration_verify_syntax: Optional[bool] = True
    migration_audit_enabled: Optional[bool] = True
    
    def is_enabled(self, mode: str = "observer") -> bool:
        """Check if AI transformation is enabled based on mode"""
        if self.enabled == "auto":
            return mode == "migration"
        return self.enabled
    
    def get_effective_config(self, mode: str = "observer") -> Dict[str, Any]:
        """Get effective configuration with migration overrides applied"""
        config = {
            "enabled": self.is_enabled(mode),
            "storage_directory": self.storage_directory,
            "confidence_threshold": self.confidence_threshold,
            "require_reviewer": self.require_reviewer,
            "git_commit": self.git_commit,
            "verify_syntax": self.verify_syntax,
            "audit_enabled": self.audit_enabled,
        }
        
        # Apply migration overrides if in migration mode
        if mode == "migration":
            if self.migration_enabled is not None:
                config["enabled"] = self.migration_enabled
            if self.migration_confidence_threshold is not None:
                config["confidence_threshold"] = self.migration_confidence_threshold
            if self.migration_require_reviewer is not None:
                config["require_reviewer"] = self.migration_require_reviewer
            if self.migration_git_commit is not None:
                config["git_commit"] = self.migration_git_commit
            if self.migration_verify_syntax is not None:
                config["verify_syntax"] = self.migration_verify_syntax
            if self.migration_audit_enabled is not None:
                config["audit_enabled"] = self.migration_audit_enabled
        
        return config


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
class SemanticSearchConfig:
    """Semantic search (embeddings & vector similarity) configuration"""
    # Enable/disable semantic search (auto = enable in migration mode)
    enabled: Union[bool, str] = "auto"
    
    # Embedding provider: openai, anthropic, local
    provider_type: str = "openai"
    
    # OpenAI configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "text-embedding-3-large"
    openai_dimensions: int = 3072
    
    # Anthropic configuration (Voyage AI)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "voyage-large-2"
    
    # Local embedding configuration
    local_model: str = "all-MiniLM-L6-v2"
    local_device: str = "cpu"
    
    # Search configuration
    max_tokens: int = 8000
    min_similarity_score: float = 0.7
    default_top_k: int = 10
    api_timeout: int = 30
    retry_attempts: int = 3
    batch_size: int = 100
    
    # Vector store configuration
    vector_store_type: str = "pgvector"
    index_type: str = "ivfflat"
    index_lists: int = 100
    create_index_threshold: int = 1000
    
    # Migration mode overrides
    migration_enabled: bool = True
    migration_provider_type: str = "openai"
    migration_model: str = "text-embedding-3-large"
    migration_max_tokens: int = 8000
    migration_min_similarity_score: float = 0.6
    
    def get_effective_config(self, mode: str) -> 'SemanticSearchConfig':
        """Get effective configuration based on execution mode"""
        if mode == "migration" and self.migration_enabled:
            # Apply migration overrides
            config = SemanticSearchConfig()
            config.__dict__.update(self.__dict__)
            config.enabled = True
            config.provider_type = self.migration_provider_type
            if self.migration_provider_type == "openai":
                config.openai_model = self.migration_model
            elif self.migration_provider_type == "anthropic":
                config.anthropic_model = self.migration_model
            config.max_tokens = self.migration_max_tokens
            config.min_similarity_score = self.migration_min_similarity_score
            return config
        return self


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
    ai_transformation: AITransformationConfig = field(default_factory=AITransformationConfig)
    flaky_detection: FlakyDetectionConfig = field(default_factory=FlakyDetectionConfig)
    observer: ObserverConfig = field(default_factory=ObserverConfig)
    intelligence: IntelligenceConfig = field(default_factory=IntelligenceConfig)
    frameworks: FrameworksConfig = field(default_factory=FrameworksConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    semantic_search: SemanticSearchConfig = field(default_factory=SemanticSearchConfig)
    
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
        
        # AI Transformation config
        if 'ai_transformation' in data:
            ai_trans_data = data['ai_transformation']
            storage_data = ai_trans_data.get('storage', {})
            confidence_data = ai_trans_data.get('confidence', {})
            signals_data = confidence_data.get('signals', {})
            review_data = ai_trans_data.get('review', {})
            apply_data = ai_trans_data.get('apply', {})
            rollback_data = ai_trans_data.get('rollback', {})
            audit_data = ai_trans_data.get('audit', {})
            cli_data = ai_trans_data.get('cli', {})
            migration_data = ai_trans_data.get('migration_overrides', {})
            
            config.ai_transformation = AITransformationConfig(
                enabled=ai_trans_data.get('enabled', 'auto'),
                # Storage
                storage_directory=storage_data.get('directory', '.crossbridge/transformations'),
                backup_enabled=storage_data.get('backup_enabled', True),
                backup_directory=storage_data.get('backup_directory', '.crossbridge/transformations/backups'),
                # Confidence
                confidence_threshold=confidence_data.get('threshold', 0.8),
                high_confidence_level=confidence_data.get('levels', {}).get('high', 0.8),
                medium_confidence_level=confidence_data.get('levels', {}).get('medium', 0.5),
                # Signals
                diff_size_small_threshold=signals_data.get('diff_size', {}).get('small_threshold', 20),
                diff_size_medium_threshold=signals_data.get('diff_size', {}).get('medium_threshold', 50),
                diff_size_large_threshold=signals_data.get('diff_size', {}).get('large_threshold', 100),
                diff_size_very_large_penalty=signals_data.get('diff_size', {}).get('very_large_penalty', -0.3),
                rule_violations_penalty=signals_data.get('rule_violations', {}).get('penalty_per_violation', -0.1),
                rule_violations_max_penalty=signals_data.get('rule_violations', {}).get('max_penalty', -0.3),
                similarity_low_threshold=signals_data.get('similarity_to_existing', {}).get('low_threshold', 0.6),
                similarity_medium_threshold=signals_data.get('similarity_to_existing', {}).get('medium_threshold', 0.8),
                syntax_validation_penalty=signals_data.get('syntax_validation', {}).get('penalty', -0.4),
                test_coverage_penalty=signals_data.get('test_coverage', {}).get('penalty', -0.2),
                # Review
                require_reviewer=review_data.get('require_reviewer', True),
                require_rejection_reason=review_data.get('require_rejection_reason', True),
                allow_rereview=review_data.get('allow_rereview', False),
                expire_pending_days=review_data.get('expire_pending_days', 30),
                # Apply
                git_commit=apply_data.get('git_commit', True),
                git_commit_prefix=apply_data.get('git_commit_prefix', 'AI Transform:'),
                verify_syntax=apply_data.get('verify_syntax', True),
                run_linting=apply_data.get('run_linting', False),
                linting_command=apply_data.get('linting_command', 'flake8'),
                run_tests=apply_data.get('run_tests', False),
                test_command=apply_data.get('test_command', 'pytest'),
                # Rollback
                max_rollback_history=rollback_data.get('max_history', 10),
                require_rollback_confirmation=rollback_data.get('require_confirmation', True),
                rollback_git_commit=rollback_data.get('git_commit', True),
                rollback_git_commit_prefix=rollback_data.get('git_commit_prefix', 'Rollback AI Transform:'),
                # Audit
                audit_enabled=audit_data.get('enabled', True),
                hash_prompts=audit_data.get('hash_prompts', True),
                log_all_events=audit_data.get('log_all_events', True),
                export_audit_logs=audit_data.get('export_logs', True),
                audit_export_path=audit_data.get('export_path', '.crossbridge/transformations/audit.jsonl'),
                # CLI
                cli_default_format=cli_data.get('default_format', 'table'),
                cli_show_diff_default=cli_data.get('show_diff_default', False),
                cli_auto_apply_default=cli_data.get('auto_apply_default', False),
                # Migration overrides
                migration_enabled=migration_data.get('enabled', True),
                migration_confidence_threshold=migration_data.get('confidence_threshold', 0.85),
                migration_require_reviewer=migration_data.get('review_require_reviewer', True),
                migration_git_commit=migration_data.get('apply_git_commit', True),
                migration_verify_syntax=migration_data.get('apply_verify_syntax', True),
                migration_audit_enabled=migration_data.get('audit_enabled', True)
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
        
        # Semantic search config
        if 'semantic_search' in data:
            sem_data = data['semantic_search']
            
            # Parse nested OpenAI config
            openai_config = sem_data.get('openai', {})
            openai_api_key = openai_config.get('api_key')
            if openai_api_key and openai_api_key.startswith('${') and openai_api_key.endswith('}'):
                env_var = openai_api_key[2:-1]
                openai_api_key = os.environ.get(env_var)
            
            # Parse nested Anthropic config
            anthropic_config = sem_data.get('anthropic', {})
            anthropic_api_key = anthropic_config.get('api_key')
            if anthropic_api_key and anthropic_api_key.startswith('${') and anthropic_api_key.endswith('}'):
                env_var = anthropic_api_key[2:-1]
                anthropic_api_key = os.environ.get(env_var)
            
            # Parse nested local config
            local_config = sem_data.get('local', {})
            
            # Parse search config
            search_config = sem_data.get('search', {})
            
            # Parse vector store config
            vector_config = sem_data.get('vector_store', {})
            
            # Parse migration overrides
            migration_config = sem_data.get('migration_overrides', {})
            
            config.semantic_search = SemanticSearchConfig(
                enabled=sem_data.get('enabled', 'auto'),
                provider_type=sem_data.get('provider_type', 'openai'),
                openai_api_key=openai_api_key,
                openai_model=openai_config.get('model', 'text-embedding-3-large'),
                openai_dimensions=openai_config.get('dimensions', 3072),
                anthropic_api_key=anthropic_api_key,
                anthropic_model=anthropic_config.get('model', 'voyage-large-2'),
                local_model=local_config.get('model', 'all-MiniLM-L6-v2'),
                local_device=local_config.get('device', 'cpu'),
                max_tokens=search_config.get('max_tokens', 8000),
                min_similarity_score=search_config.get('min_similarity_score', 0.7),
                default_top_k=search_config.get('default_top_k', 10),
                api_timeout=search_config.get('api_timeout', 30),
                retry_attempts=search_config.get('retry_attempts', 3),
                batch_size=search_config.get('batch_size', 100),
                vector_store_type=vector_config.get('type', 'pgvector'),
                index_type=vector_config.get('index_type', 'ivfflat'),
                index_lists=vector_config.get('index_lists', 100),
                create_index_threshold=vector_config.get('create_index_threshold', 1000),
                migration_enabled=migration_config.get('enabled', True),
                migration_provider_type=migration_config.get('provider_type', 'openai'),
                migration_model=migration_config.get('model', 'text-embedding-3-large'),
                migration_max_tokens=migration_config.get('max_tokens', 8000),
                migration_min_similarity_score=migration_config.get('min_similarity_score', 0.6)
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
