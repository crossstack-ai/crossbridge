"""
CrossBridge Unified Configuration Module
=========================================

Single source of truth for all CrossBridge configuration.

Usage:
    >>> from core.config import get_config
    >>> 
    >>> config = get_config()
    >>> print(config.database.host)
    >>> print(config.translation.mode)
    >>> print(config.ai.provider)

Configuration File:
    Place 'crossbridge.yml' in your project root or any parent directory.
    The config loader will automatically search up the directory tree.

Environment Variables:
    Override any config value using environment variables:
    
    export CROSSBRIDGE_DB_HOST=my-db-server.com
    export OPENAI_API_KEY=sk-...
    export APP_VERSION=$(git describe --tags)

Example crossbridge.yml:
    ```yaml
    crossbridge:
      mode: observer
      database:
        host: ${CROSSBRIDGE_DB_HOST:-localhost}
        port: 5432
      ai:
        api_key: ${OPENAI_API_KEY}
        model: gpt-4
    ```
"""

from .loader import (
    # Configuration classes
    CrossBridgeConfig,
    DatabaseConfig,
    ApplicationConfig,
    SidecarHooksConfig,
    TranslationConfig,
    AIConfig,
    FlakyDetectionConfig,
    ObserverConfig,
    IntelligenceConfig,
    FrameworkConfig,
    FrameworksConfig,
    LoggingConfig,
    
    # Configuration loader
    ConfigLoader,
    
    # Global singleton functions
    get_config,
    reset_config,
)

__all__ = [
    # Main config class
    "CrossBridgeConfig",
    
    # Sub-configuration classes
    "DatabaseConfig",
    "ApplicationConfig",
    "SidecarHooksConfig",
    "TranslationConfig",
    "AIConfig",
    "FlakyDetectionConfig",
    "ObserverConfig",
    "IntelligenceConfig",
    "FrameworkConfig",
    "FrameworksConfig",
    "LoggingConfig",
    
    # Loader
    "ConfigLoader",
    
    # Singleton access (most common usage)
    "get_config",
    "reset_config",
]
