"""
Configuration loader for production runtime features.

Loads rate limiting, retry policies, and health check configurations
from crossbridge.yml with validation and defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    defaults: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cleanup_threshold: int = 1000
    overrides: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)


@dataclass
class RetryPolicyConfig:
    """Retry policy configuration."""
    enabled: bool = True
    default_policy: Dict[str, Any] = field(default_factory=dict)
    expensive_policy: Dict[str, Any] = field(default_factory=dict)
    quick_policy: Dict[str, Any] = field(default_factory=dict)
    conservative_policy: Dict[str, Any] = field(default_factory=dict)
    retryable_codes: List[int] = field(default_factory=list)
    network_timeout: int = 30


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    enabled: bool = True
    interval: int = 30
    timeout: int = 10
    failure_threshold: int = 3
    providers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    degraded_mode: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeConfig:
    """Complete runtime configuration."""
    rate_limiting: RateLimitConfig
    retry: RetryPolicyConfig
    health_checks: HealthCheckConfig


class ConfigLoader:
    """Loads and validates runtime configuration from YAML."""
    
    DEFAULT_CONFIG_PATH = "crossbridge.yml"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to crossbridge.yml (defaults to current directory)
        """
        self.config_path = config_path or self._find_config_file()
        self._config_data: Optional[Dict[str, Any]] = None
    
    def _find_config_file(self) -> str:
        """Find crossbridge.yml in current or parent directories."""
        current = Path.cwd()
        
        # Check current directory
        config_file = current / self.DEFAULT_CONFIG_PATH
        if config_file.exists():
            return str(config_file)
        
        # Check parent directories (up to 3 levels)
        for _ in range(3):
            current = current.parent
            config_file = current / self.DEFAULT_CONFIG_PATH
            if config_file.exists():
                return str(config_file)
        
        # Fallback to default path
        return self.DEFAULT_CONFIG_PATH
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load and parse YAML configuration file."""
        if self._config_data is not None:
            return self._config_data
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
                return self._config_data
        except FileNotFoundError:
            # Return default configuration if file not found
            return {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse {self.config_path}: {e}")
    
    def _get_default_rate_limiting(self) -> RateLimitConfig:
        """Get default rate limiting configuration."""
        return RateLimitConfig(
            enabled=True,
            defaults={
                'search': {'capacity': 30, 'window_seconds': 60},
                'transform': {'capacity': 10, 'window_seconds': 60},
                'embed': {'capacity': 60, 'window_seconds': 60},
                'ai_generate': {'capacity': 20, 'window_seconds': 60},
                'health_check': {'capacity': 100, 'window_seconds': 60},
            },
            cleanup_threshold=1000,
            overrides={}
        )
    
    def _get_default_retry(self) -> RetryPolicyConfig:
        """Get default retry policy configuration."""
        return RetryPolicyConfig(
            enabled=True,
            default_policy={
                'max_attempts': 3,
                'base_delay': 0.5,
                'max_delay': 5.0,
                'exponential_base': 2.0,
                'jitter': True
            },
            expensive_policy={
                'max_attempts': 5,
                'base_delay': 1.0,
                'max_delay': 10.0,
                'exponential_base': 2.0,
                'jitter': True
            },
            quick_policy={
                'max_attempts': 2,
                'base_delay': 0.1,
                'max_delay': 1.0,
                'exponential_base': 2.0,
                'jitter': True
            },
            conservative_policy={
                'max_attempts': 3,
                'base_delay': 2.0,
                'max_delay': 30.0,
                'exponential_base': 3.0,
                'jitter': True
            },
            retryable_codes=[429, 500, 502, 503, 504],
            network_timeout=30
        )
    
    def _get_default_health_checks(self) -> HealthCheckConfig:
        """Get default health check configuration."""
        return HealthCheckConfig(
            enabled=True,
            interval=30,
            timeout=10,
            failure_threshold=3,
            providers={
                'ai_provider': {
                    'enabled': True,
                    'check_type': 'embed',
                    'interval': 60,
                    'timeout': 15
                },
                'embedding_provider': {
                    'enabled': True,
                    'check_type': 'embed',
                    'interval': 60,
                    'timeout': 10
                },
                'vector_store': {
                    'enabled': True,
                    'check_type': 'ping',
                    'interval': 30,
                    'timeout': 5
                },
                'database': {
                    'enabled': True,
                    'check_type': 'ping',
                    'interval': 20,
                    'timeout': 5
                }
            },
            degraded_mode={
                'continue_on_degraded': True,
                'disable_features': ['flaky_detection', 'coverage_analysis']
            }
        )
    
    def load_rate_limiting(self) -> RateLimitConfig:
        """Load rate limiting configuration."""
        config_data = self._load_yaml()
        runtime = config_data.get('runtime', {})
        rate_limiting = runtime.get('rate_limiting', {})
        
        if not rate_limiting:
            return self._get_default_rate_limiting()
        
        return RateLimitConfig(
            enabled=rate_limiting.get('enabled', True),
            defaults=rate_limiting.get('defaults', self._get_default_rate_limiting().defaults),
            cleanup_threshold=rate_limiting.get('cleanup_threshold', 1000),
            overrides=rate_limiting.get('overrides', {})
        )
    
    def load_retry(self) -> RetryPolicyConfig:
        """Load retry policy configuration."""
        config_data = self._load_yaml()
        runtime = config_data.get('runtime', {})
        retry = runtime.get('retry', {})
        
        if not retry:
            return self._get_default_retry()
        
        return RetryPolicyConfig(
            enabled=retry.get('enabled', True),
            default_policy=retry.get('default_policy', self._get_default_retry().default_policy),
            expensive_policy=retry.get('expensive_policy', self._get_default_retry().expensive_policy),
            quick_policy=retry.get('quick_policy', self._get_default_retry().quick_policy),
            conservative_policy=retry.get('conservative_policy', self._get_default_retry().conservative_policy),
            retryable_codes=retry.get('retryable_codes', [429, 500, 502, 503, 504]),
            network_timeout=retry.get('network_timeout', 30)
        )
    
    def load_health_checks(self) -> HealthCheckConfig:
        """Load health check configuration."""
        config_data = self._load_yaml()
        runtime = config_data.get('runtime', {})
        health_checks = runtime.get('health_checks', {})
        
        if not health_checks:
            return self._get_default_health_checks()
        
        return HealthCheckConfig(
            enabled=health_checks.get('enabled', True),
            interval=health_checks.get('interval', 30),
            timeout=health_checks.get('timeout', 10),
            failure_threshold=health_checks.get('failure_threshold', 3),
            providers=health_checks.get('providers', self._get_default_health_checks().providers),
            degraded_mode=health_checks.get('degraded_mode', self._get_default_health_checks().degraded_mode)
        )
    
    def load_all(self) -> RuntimeConfig:
        """Load complete runtime configuration."""
        return RuntimeConfig(
            rate_limiting=self.load_rate_limiting(),
            retry=self.load_retry(),
            health_checks=self.load_health_checks()
        )


# Global configuration instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Get global configuration loader instance.
    
    Args:
        config_path: Optional path to crossbridge.yml
    
    Returns:
        ConfigLoader instance
    """
    global _config_loader
    
    if _config_loader is None or config_path is not None:
        _config_loader = ConfigLoader(config_path)
    
    return _config_loader


def load_runtime_config(config_path: Optional[str] = None) -> RuntimeConfig:
    """
    Load complete runtime configuration from YAML.
    
    Args:
        config_path: Optional path to crossbridge.yml
    
    Returns:
        RuntimeConfig with all settings
    
    Example:
        >>> config = load_runtime_config()
        >>> if config.rate_limiting.enabled:
        ...     print("Rate limiting enabled")
    """
    loader = get_config_loader(config_path)
    return loader.load_all()


def get_rate_limit_for_operation(operation: str, config: Optional[RuntimeConfig] = None) -> Dict[str, Any]:
    """
    Get rate limit configuration for specific operation.
    
    Args:
        operation: Operation type (search, transform, embed, etc.)
        config: Optional runtime config (loads from YAML if not provided)
    
    Returns:
        Dict with 'capacity' and 'window_seconds'
    
    Example:
        >>> limits = get_rate_limit_for_operation('search')
        >>> print(f"Search: {limits['capacity']} per {limits['window_seconds']}s")
    """
    if config is None:
        config = load_runtime_config()
    
    return config.rate_limiting.defaults.get(
        operation,
        {'capacity': 30, 'window_seconds': 60}  # Default fallback
    )


def get_retry_policy_by_name(policy_name: str, config: Optional[RuntimeConfig] = None) -> Dict[str, Any]:
    """
    Get retry policy by name.
    
    Args:
        policy_name: Policy name (default, expensive, quick, conservative)
        config: Optional runtime config (loads from YAML if not provided)
    
    Returns:
        Dict with retry policy settings
    
    Example:
        >>> policy = get_retry_policy_by_name('expensive')
        >>> print(f"Max attempts: {policy['max_attempts']}")
    """
    if config is None:
        config = load_runtime_config()
    
    policy_attr = f"{policy_name}_policy"
    return getattr(config.retry, policy_attr, config.retry.default_policy)
