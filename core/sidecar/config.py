"""
Runtime Configuration for Sidecar

Provides:
- Configuration loading from file/dict
- Runtime reloading without restart
- Configuration validation
- Default values
"""

import os
import yaml
import threading
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from core.logging import get_logger, LogCategory
from cli.errors import ConfigurationError

logger = get_logger(__name__, category=LogCategory.GENERAL)


@dataclass
class SamplingConfig:
    """Sampling configuration"""
    enabled: bool = True
    events: float = 0.1
    traces: float = 0.05
    profiling: float = 0.01
    test_events: float = 0.2
    perf_metrics: float = 0.05
    debug_logs: float = 0.01


@dataclass
class ResourceBudgetConfig:
    """Resource budget configuration"""
    max_queue_size: int = 10_000
    max_cpu_percent: float = 5.0
    max_memory_mb: float = 100.0
    drop_on_full: bool = True


@dataclass
class ProfilingConfig:
    """Profiling configuration"""
    enabled: bool = True
    sampling_interval: float = 1.0
    deep_profiling: bool = False
    deep_duration_sec: float = 30.0


@dataclass
class HealthCheckConfig:
    """Health check configuration"""
    enabled: bool = True
    interval_sec: float = 30.0
    failure_threshold: int = 3


@dataclass
class SidecarConfig:
    """
    Complete sidecar configuration
    
    Can be loaded from:
    - YAML file
    - Dictionary
    - Environment variables
    """
    
    enabled: bool = True
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    resources: ResourceBudgetConfig = field(default_factory=ResourceBudgetConfig)
    profiling: ProfilingConfig = field(default_factory=ProfilingConfig)
    health_checks: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    
    # Dynamic reload support
    _config_path: Optional[Path] = None
    _lock: threading.RLock = field(default_factory=threading.RLock)
    
    @classmethod
    def from_file(cls, path: str) -> 'SidecarConfig':
        """Load configuration from YAML file"""
        try:
            path_obj = Path(path)
            
            if not path_obj.exists():
                logger.error(f"Config file not found: {path}")
                raise ConfigurationError(
                    f"Sidecar config file not found: {path}",
                    suggestion="Ensure crossbridge.yml exists in the project root"
                )
            
            with open(path_obj, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"Empty config file: {path}, using defaults")
                return cls()
            
            # Navigate to runtime.sidecar section if present
            runtime_config = data.get('runtime', {})
            sidecar_data = runtime_config.get('sidecar', data.get('sidecar', {}))
            
            config = cls.from_dict(sidecar_data)
            config._config_path = path_obj
            logger.debug(f"Loaded sidecar config from {path}")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML config: {e}", exc_info=True)
            raise ConfigurationError(
                f"Invalid YAML in sidecar config: {e}",
                suggestion="Check YAML syntax in crossbridge.yml"
            )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SidecarConfig':
        """Load configuration from dictionary"""
        config = cls(
            enabled=data.get('enabled', True)
        )
        
        # Sampling config
        if 'sampling' in data:
            sampling_data = data['sampling']
            config.sampling = SamplingConfig(
                enabled=sampling_data.get('enabled', True),
                events=sampling_data.get('events', 0.1),
                traces=sampling_data.get('traces', 0.05),
                profiling=sampling_data.get('profiling', 0.01),
                test_events=sampling_data.get('test_events', 0.2),
                perf_metrics=sampling_data.get('perf_metrics', 0.05),
                debug_logs=sampling_data.get('debug_logs', 0.01),
            )
        
        # Resources config
        if 'resources' in data:
            resources_data = data['resources']
            config.resources = ResourceBudgetConfig(
                max_queue_size=resources_data.get('max_queue_size', 10_000),
                max_cpu_percent=resources_data.get('max_cpu_percent', 5.0),
                max_memory_mb=resources_data.get('max_memory_mb', 100.0),
                drop_on_full=resources_data.get('drop_on_full', True),
            )
        
        # Profiling config
        if 'profiling' in data:
            profiling_data = data['profiling']
            config.profiling = ProfilingConfig(
                enabled=profiling_data.get('enabled', True),
                sampling_interval=profiling_data.get('sampling_interval', 1.0),
                deep_profiling=profiling_data.get('deep_profiling', False),
                deep_duration_sec=profiling_data.get('deep_duration_sec', 30.0),
            )
        
        # Health checks config
        if 'health_checks' in data:
            health_data = data['health_checks']
            config.health_checks = HealthCheckConfig(
                enabled=health_data.get('enabled', True),
                interval_sec=health_data.get('interval_sec', 30.0),
                failure_threshold=health_data.get('failure_threshold', 3),
            )
        
        return config
    
    @classmethod
    def from_env(cls) -> 'SidecarConfig':
        """Load configuration from environment variables"""
        config = cls()
        
        # Main enable flag
        if 'SIDECAR_ENABLED' in os.environ:
            config.enabled = os.environ['SIDECAR_ENABLED'].lower() == 'true'
        
        # Sampling rates
        if 'SIDECAR_SAMPLE_EVENTS' in os.environ:
            config.sampling.events = float(os.environ['SIDECAR_SAMPLE_EVENTS'])
        if 'SIDECAR_SAMPLE_TRACES' in os.environ:
            config.sampling.traces = float(os.environ['SIDECAR_SAMPLE_TRACES'])
        if 'SIDECAR_SAMPLE_PROFILING' in os.environ:
            config.sampling.profiling = float(os.environ['SIDECAR_SAMPLE_PROFILING'])
        
        # Resource budgets
        if 'SIDECAR_MAX_QUEUE_SIZE' in os.environ:
            config.resources.max_queue_size = int(os.environ['SIDECAR_MAX_QUEUE_SIZE'])
        if 'SIDECAR_CPU_BUDGET' in os.environ:
            config.resources.max_cpu_percent = float(os.environ['SIDECAR_CPU_BUDGET'])
        if 'SIDECAR_MEMORY_BUDGET_MB' in os.environ:
            config.resources.max_memory_mb = float(os.environ['SIDECAR_MEMORY_BUDGET_MB'])
        
        return config
    
    def reload(self) -> bool:
        """
        Reload configuration from file (if loaded from file)
        
        Returns:
            True if reloaded successfully, False otherwise
        """
        if not self._config_path:
            return False
        
        try:
            with self._lock:
                new_config = self.from_file(str(self._config_path))
                
                # Update self with new values
                self.enabled = new_config.enabled
                self.sampling = new_config.sampling
                self.resources = new_config.resources
                self.profiling = new_config.profiling
                self.health_checks = new_config.health_checks
                
                return True
        except Exception:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'enabled': self.enabled,
            'sampling': {
                'enabled': self.sampling.enabled,
                'events': self.sampling.events,
                'traces': self.sampling.traces,
                'profiling': self.sampling.profiling,
                'test_events': self.sampling.test_events,
                'perf_metrics': self.sampling.perf_metrics,
                'debug_logs': self.sampling.debug_logs,
            },
            'resources': {
                'max_queue_size': self.resources.max_queue_size,
                'max_cpu_percent': self.resources.max_cpu_percent,
                'max_memory_mb': self.resources.max_memory_mb,
                'drop_on_full': self.resources.drop_on_full,
            },
            'profiling': {
                'enabled': self.profiling.enabled,
                'sampling_interval': self.profiling.sampling_interval,
                'deep_profiling': self.profiling.deep_profiling,
                'deep_duration_sec': self.profiling.deep_duration_sec,
            },
            'health_checks': {
                'enabled': self.health_checks.enabled,
                'interval_sec': self.health_checks.interval_sec,
                'failure_threshold': self.health_checks.failure_threshold,
            },
        }
    
    def validate(self) -> bool:
        """Validate configuration"""
        # Validate sampling rates
        for rate_name in ['events', 'traces', 'profiling', 'test_events', 'perf_metrics', 'debug_logs']:
            rate = getattr(self.sampling, rate_name)
            if not (0.0 <= rate <= 1.0):
                raise ValueError(f"Sampling rate {rate_name} must be between 0.0 and 1.0, got {rate}")
        
        # Validate resource budgets
        if self.resources.max_queue_size < 100:
            raise ValueError(f"max_queue_size must be >= 100, got {self.resources.max_queue_size}")
        if self.resources.max_cpu_percent < 1.0 or self.resources.max_cpu_percent > 100.0:
            raise ValueError(f"max_cpu_percent must be between 1.0 and 100.0, got {self.resources.max_cpu_percent}")
        if self.resources.max_memory_mb < 10.0:
            raise ValueError(f"max_memory_mb must be >= 10.0, got {self.resources.max_memory_mb}")
        
        return True
