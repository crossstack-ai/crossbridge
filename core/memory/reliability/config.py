"""
Configuration loader for embedding reliability subsystem.

Loads reliability settings from crossbridge.yml and provides
typed access to configuration values with defaults.

Usage:
    from core.memory.reliability.config import get_reliability_config
    
    config = get_reliability_config()
    if config.enabled:
        max_age = config.staleness.max_age_days
        threshold = config.drift.threshold
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class StalenessConfig:
    """Staleness detection configuration."""
    enabled: bool = True
    max_age_days: int = 90
    check_interval_hours: int = 24
    check_fingerprint: bool = True
    fingerprint_algorithm: str = "sha256"
    check_version: bool = True
    auto_upgrade: bool = True
    allow_manual_marking: bool = True


@dataclass
class DriftConfig:
    """Semantic drift detection configuration."""
    enabled: bool = True
    threshold: float = 0.85
    check_on_update: bool = True
    check_interval_days: int = 30
    alert_threshold: float = 0.70


@dataclass
class QueueConfig:
    """Reindex queue configuration."""
    max_size: int = 10000
    process_batch_size: int = 100
    deduplication: bool = True


@dataclass
class PrioritiesConfig:
    """Reindex job priorities (0-100, higher = more urgent)."""
    version_mismatch: int = 80
    drift_detected: int = 70
    manual_request: int = 70
    content_changed: int = 60
    no_embedding: int = 50
    no_version: int = 40
    age_threshold: int = 30


@dataclass
class WorkerConfig:
    """Background reindex worker configuration."""
    enabled: bool = True
    interval_seconds: int = 60
    max_concurrent_jobs: int = 5
    retry_failed: bool = True
    max_retries: int = 3


@dataclass
class RateLimitConfig:
    """Reindexing rate limits."""
    max_per_hour: int = 1000
    max_per_day: int = 10000


@dataclass
class ReindexConfig:
    """Reindexing pipeline configuration."""
    enabled: bool = True
    queue: QueueConfig = field(default_factory=QueueConfig)
    priorities: PrioritiesConfig = field(default_factory=PrioritiesConfig)
    worker: WorkerConfig = field(default_factory=WorkerConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)


@dataclass
class MetricsConfig:
    """Observability and metrics configuration."""
    enabled: bool = True
    track: list = field(default_factory=lambda: [
        'embeddings_total',
        'embeddings_stale',
        'embeddings_reindexed',
        'embedding_drift_detected',
        'embedding_avg_age_days',
        'reindex_queue_size',
        'reindex_success_rate'
    ])
    log_stale_embeddings: bool = True
    log_drift_events: bool = True
    log_reindex_jobs: bool = True
    export_prometheus: bool = False
    export_grafana: bool = True


@dataclass
class SchemaConfig:
    """Database schema configuration."""
    use_dedicated_columns: bool = True
    migration_path: str = "migration/sql/embedding_reliability.sql"


@dataclass
class ReliabilityConfig:
    """Main reliability configuration."""
    enabled: bool = True
    version_format: str = "schema::content::model"
    current_version: str = "v1::text-only::openai"
    
    staleness: StalenessConfig = field(default_factory=StalenessConfig)
    drift: DriftConfig = field(default_factory=DriftConfig)
    reindex: ReindexConfig = field(default_factory=ReindexConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    schema: SchemaConfig = field(default_factory=SchemaConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReliabilityConfig':
        """Load configuration from dictionary."""
        config = cls()
        
        if not data:
            return config
        
        # Top-level settings
        config.enabled = data.get('enabled', config.enabled)
        config.version_format = data.get('version_format', config.version_format)
        config.current_version = data.get('current_version', config.current_version)
        
        # Staleness config
        if 'staleness' in data:
            staleness_data = data['staleness']
            config.staleness = StalenessConfig(
                enabled=staleness_data.get('enabled', True),
                max_age_days=staleness_data.get('max_age_days', 90),
                check_interval_hours=staleness_data.get('check_interval_hours', 24),
                check_fingerprint=staleness_data.get('check_fingerprint', True),
                fingerprint_algorithm=staleness_data.get('fingerprint_algorithm', 'sha256'),
                check_version=staleness_data.get('check_version', True),
                auto_upgrade=staleness_data.get('auto_upgrade', True),
                allow_manual_marking=staleness_data.get('allow_manual_marking', True)
            )
        
        # Drift config
        if 'drift' in data:
            drift_data = data['drift']
            config.drift = DriftConfig(
                enabled=drift_data.get('enabled', True),
                threshold=drift_data.get('threshold', 0.85),
                check_on_update=drift_data.get('check_on_update', True),
                check_interval_days=drift_data.get('check_interval_days', 30),
                alert_threshold=drift_data.get('alert_threshold', 0.70)
            )
        
        # Reindex config
        if 'reindex' in data:
            reindex_data = data['reindex']
            
            # Queue config
            queue_config = QueueConfig()
            if 'queue' in reindex_data:
                queue_data = reindex_data['queue']
                queue_config = QueueConfig(
                    max_size=queue_data.get('max_size', 10000),
                    process_batch_size=queue_data.get('process_batch_size', 100),
                    deduplication=queue_data.get('deduplication', True)
                )
            
            # Priorities config
            priorities_config = PrioritiesConfig()
            if 'priorities' in reindex_data:
                priorities_data = reindex_data['priorities']
                priorities_config = PrioritiesConfig(
                    version_mismatch=priorities_data.get('version_mismatch', 80),
                    drift_detected=priorities_data.get('drift_detected', 70),
                    manual_request=priorities_data.get('manual_request', 70),
                    content_changed=priorities_data.get('content_changed', 60),
                    no_embedding=priorities_data.get('no_embedding', 50),
                    no_version=priorities_data.get('no_version', 40),
                    age_threshold=priorities_data.get('age_threshold', 30)
                )
            
            # Worker config
            worker_config = WorkerConfig()
            if 'worker' in reindex_data:
                worker_data = reindex_data['worker']
                worker_config = WorkerConfig(
                    enabled=worker_data.get('enabled', True),
                    interval_seconds=worker_data.get('interval_seconds', 60),
                    max_concurrent_jobs=worker_data.get('max_concurrent_jobs', 5),
                    retry_failed=worker_data.get('retry_failed', True),
                    max_retries=worker_data.get('max_retries', 3)
                )
            
            # Rate limit config
            rate_limit_config = RateLimitConfig()
            if 'rate_limit' in reindex_data:
                rate_data = reindex_data['rate_limit']
                rate_limit_config = RateLimitConfig(
                    max_per_hour=rate_data.get('max_per_hour', 1000),
                    max_per_day=rate_data.get('max_per_day', 10000)
                )
            
            config.reindex = ReindexConfig(
                enabled=reindex_data.get('enabled', True),
                queue=queue_config,
                priorities=priorities_config,
                worker=worker_config,
                rate_limit=rate_limit_config
            )
        
        # Metrics config
        if 'metrics' in data:
            metrics_data = data['metrics']
            config.metrics = MetricsConfig(
                enabled=metrics_data.get('enabled', True),
                track=metrics_data.get('track', config.metrics.track),
                log_stale_embeddings=metrics_data.get('log_stale_embeddings', True),
                log_drift_events=metrics_data.get('log_drift_events', True),
                log_reindex_jobs=metrics_data.get('log_reindex_jobs', True),
                export_prometheus=metrics_data.get('export', {}).get('prometheus', {}).get('enabled', False),
                export_grafana=metrics_data.get('export', {}).get('grafana', {}).get('enabled', True)
            )
        
        # Schema config
        if 'schema' in data:
            schema_data = data['schema']
            config.schema = SchemaConfig(
                use_dedicated_columns=schema_data.get('use_dedicated_columns', True),
                migration_path=schema_data.get('migration_path', config.schema.migration_path)
            )
        
        return config


def get_reliability_config() -> ReliabilityConfig:
    """
    Load reliability configuration from crossbridge.yml.
    
    Returns:
        ReliabilityConfig with loaded or default values
    """
    try:
        from core.config.settings import load_config
        
        config_data = load_config()
        semantic_search = config_data.get('semantic_search', {})
        reliability_data = semantic_search.get('reliability', {})
        
        config = ReliabilityConfig.from_dict(reliability_data)
        
        if config.enabled:
            logger.info("✓ Embedding reliability enabled")
            logger.debug(f"  Version: {config.current_version}")
            logger.debug(f"  Staleness: max_age={config.staleness.max_age_days}d")
            logger.debug(f"  Drift: threshold={config.drift.threshold}")
            logger.debug(f"  Reindex: enabled={config.reindex.enabled}")
        else:
            logger.info("⚠ Embedding reliability disabled")
        
        return config
        
    except Exception as e:
        logger.warning(f"⚠ Could not load reliability config: {e}")
        logger.warning("  Using default configuration")
        return ReliabilityConfig()


def validate_config(config: ReliabilityConfig) -> bool:
    """
    Validate reliability configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        True if valid, False otherwise
    """
    issues = []
    
    # Validate staleness settings
    if config.staleness.max_age_days < 1:
        issues.append("staleness.max_age_days must be >= 1")
    
    if config.staleness.check_interval_hours < 1:
        issues.append("staleness.check_interval_hours must be >= 1")
    
    # Validate drift settings
    if not (0.0 <= config.drift.threshold <= 1.0):
        issues.append("drift.threshold must be between 0.0 and 1.0")
    
    if not (0.0 <= config.drift.alert_threshold <= 1.0):
        issues.append("drift.alert_threshold must be between 0.0 and 1.0")
    
    if config.drift.threshold < config.drift.alert_threshold:
        issues.append("drift.threshold should be >= drift.alert_threshold")
    
    # Validate reindex settings
    if config.reindex.queue.max_size < 1:
        issues.append("reindex.queue.max_size must be >= 1")
    
    if config.reindex.queue.process_batch_size < 1:
        issues.append("reindex.queue.process_batch_size must be >= 1")
    
    if config.reindex.worker.interval_seconds < 1:
        issues.append("reindex.worker.interval_seconds must be >= 1")
    
    if config.reindex.worker.max_concurrent_jobs < 1:
        issues.append("reindex.worker.max_concurrent_jobs must be >= 1")
    
    # Validate priorities (0-100)
    priorities = config.reindex.priorities
    for field_name in ['version_mismatch', 'drift_detected', 'manual_request', 
                       'content_changed', 'no_embedding', 'no_version', 'age_threshold']:
        value = getattr(priorities, field_name)
        if not (0 <= value <= 100):
            issues.append(f"reindex.priorities.{field_name} must be between 0 and 100")
    
    # Log issues
    if issues:
        logger.error("Configuration validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    
    logger.info("✓ Configuration validation passed")
    return True


# Singleton instance (lazy loaded)
_config_instance: Optional[ReliabilityConfig] = None


def get_config() -> ReliabilityConfig:
    """Get singleton configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = get_reliability_config()
    return _config_instance


def reload_config() -> ReliabilityConfig:
    """Force reload configuration from file."""
    global _config_instance
    _config_instance = None
    return get_config()
