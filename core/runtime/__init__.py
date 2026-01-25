"""
Production Runtime Module

Provides rate limiting, retry logic, and health checks for production robustness.
Configured via crossbridge.yml.
"""

from .rate_limit import (
    RateLimit,
    TokenBucket,
    RateLimiter,
    RateLimitExceeded,
    get_rate_limiter,
    check_rate_limit,
)

from .retry import (
    RetryPolicy,
    RetryStats,
    RetryableError,
    NetworkError,
    RateLimitError,
    ServerError,
    NonRetryableError,
    AuthenticationError,
    ValidationError,
    calculate_delay,
    should_retry,
    retry_with_backoff,
    retryable,
    convert_http_error_to_retry,
)

from .health import (
    HealthStatus,
    HealthResult,
    HealthCheck,
    SimpleHealthCheck,
    PingHealthCheck,
    AIProviderHealthCheck,
    VectorStoreHealthCheck,
    HealthRegistry,
    get_health_registry,
)

from .config import (
    RuntimeConfig,
    RateLimitConfig,
    RetryPolicyConfig,
    HealthCheckConfig,
    ConfigLoader,
    load_runtime_config,
    get_config_loader,
    get_rate_limit_for_operation,
    get_retry_policy_by_name,
)

from .ai_integration import (
    HardenedAIProvider,
    harden_ai_provider,
)

from .embedding_integration import (
    HardenedEmbeddingProvider,
    harden_embedding_provider,
)

from .database_integration import (
    with_database_retry,
    register_database_health_check,
    HardenedDatabaseConnection,
    harden_database_connection,
)

from .flaky_integration import (
    with_flaky_db_retry,
    register_flaky_db_health_check,
    HardenedFlakyDetector,
    harden_flaky_detector,
)

from .profiling_integration import (
    with_profiling_storage_retry,
    HardenedProfilingStorage,
    create_hardened_storage,
    check_profiling_health,
)

from .coverage_integration import (
    with_coverage_db_retry,
    HardenedCoverageEngine,
    CoverageParserWrapper,
    create_hardened_engine,
    create_parser_wrapper,
    check_coverage_health,
)

from .execution_integration import (
    with_execution_retry,
    HardenedTestExecutor,
    AdapterHealthMonitor,
    create_hardened_executor,
    check_execution_health,
)

__all__ = [
    # Rate limiting
    'RateLimit',
    'TokenBucket',
    'RateLimiter',
    'RateLimitExceeded',
    'get_rate_limiter',
    'check_rate_limit',
    
    # Retry logic
    'RetryPolicy',
    'RetryStats',
    'RetryableError',
    'NetworkError',
    'RateLimitError',
    'ServerError',
    'NonRetryableError',
    'AuthenticationError',
    'ValidationError',
    'calculate_delay',
    'should_retry',
    'retry_with_backoff',
    'retryable',
    'convert_http_error_to_retry',
    
    # Health checks
    'HealthStatus',
    'HealthResult',
    'HealthCheck',
    'SimpleHealthCheck',
    'PingHealthCheck',
    'AIProviderHealthCheck',
    'VectorStoreHealthCheck',
    'HealthRegistry',
    'get_health_registry',
    
    # Configuration
    'RuntimeConfig',
    'RateLimitConfig',
    'RetryPolicyConfig',
    'HealthCheckConfig',
    'ConfigLoader',
    'load_runtime_config',
    'get_config_loader',
    'get_rate_limit_for_operation',
    'get_retry_policy_by_name',
    
    # Integration wrappers
    'HardenedAIProvider',
    'harden_ai_provider',
    'HardenedEmbeddingProvider',
    'harden_embedding_provider',
    'with_database_retry',
    'register_database_health_check',
    'HardenedDatabaseConnection',
    'harden_database_connection',
    'with_flaky_db_retry',
    'register_flaky_db_health_check',
    'HardenedFlakyDetector',
    'harden_flaky_detector',
    
    # Profiling integration
    'with_profiling_storage_retry',
    'HardenedProfilingStorage',
    'create_hardened_storage',
    'check_profiling_health',
    
    # Coverage integration
    'with_coverage_db_retry',
    'HardenedCoverageEngine',
    'CoverageParserWrapper',
    'create_hardened_engine',
    'create_parser_wrapper',
    'check_coverage_health',
    
    # Execution integration
    'with_execution_retry',
    'HardenedTestExecutor',
    'AdapterHealthMonitor',
    'create_hardened_executor',
    'check_execution_health',
]
