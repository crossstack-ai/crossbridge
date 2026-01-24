"""
Performance Profiling Data Models

Unified event model for capturing performance metrics across all frameworks.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
import uuid
import time


class EventType(str, Enum):
    """Performance event types"""
    # Test lifecycle events
    TEST_START = "test_start"
    TEST_END = "test_end"
    STEP_START = "step_start"
    STEP_END = "step_end"
    SETUP_START = "setup_start"
    SETUP_END = "setup_end"
    TEARDOWN_START = "teardown_start"
    TEARDOWN_END = "teardown_end"
    
    # Automation overhead events
    DRIVER_COMMAND = "driver_command"
    API_CALL = "api_call"
    HTTP_REQUEST = "http_request"
    WAIT_EVENT = "wait_event"
    RETRY_EVENT = "retry_event"
    
    # Application interaction events
    PAGE_LOAD = "page_load"
    ELEMENT_INTERACTION = "element_interaction"
    
    # System events
    RESOURCE_USAGE = "resource_usage"
    FRAMEWORK_OVERHEAD = "framework_overhead"


class StorageBackendType(str, Enum):
    """Storage backend types"""
    NONE = "none"
    LOCAL = "local"
    POSTGRES = "postgres"
    INFLUXDB = "influxdb"


@dataclass
class PerformanceEvent:
    """
    Unified performance event capturing timing and context.
    
    This model is framework-agnostic and captures all performance
    metrics across pytest, Selenium, Cypress, Robot, etc.
    """
    # Identity
    run_id: str
    test_id: str
    event_type: EventType
    
    # Timing (use monotonic clock)
    start_time: float
    end_time: float
    duration_ms: float
    
    # Context
    framework: str
    step_name: Optional[str] = None
    
    # Metadata (extensible)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps (for storage)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create(
        cls,
        run_id: str,
        test_id: str,
        event_type: EventType,
        framework: str,
        start_time: Optional[float] = None,
        duration_ms: Optional[float] = None,
        step_name: Optional[str] = None,
        **metadata
    ) -> "PerformanceEvent":
        """Create a performance event with automatic timing"""
        now = time.monotonic()
        start = start_time or now
        end = now
        duration = duration_ms or ((end - start) * 1000)
        
        return cls(
            run_id=run_id,
            test_id=test_id,
            event_type=event_type,
            framework=framework,
            start_time=start,
            end_time=end,
            duration_ms=duration,
            step_name=step_name,
            metadata=metadata,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["created_at"] = self.created_at.isoformat()
        return data
    
    def to_influx_point(self) -> Dict[str, Any]:
        """Convert to InfluxDB line protocol format"""
        return {
            "measurement": self.event_type.value,
            "tags": {
                "test_id": self.test_id,
                "framework": self.framework,
                "run_id": self.run_id,
                **({"step_name": self.step_name} if self.step_name else {}),
            },
            "fields": {
                "duration_ms": self.duration_ms,
                **self.metadata,
            },
            "time": self.created_at,
        }


@dataclass
class ProfileConfig:
    """Performance profiling configuration"""
    # Core settings
    enabled: bool = False
    mode: str = "passive"
    sampling_rate: float = 1.0
    
    # Collectors
    test_lifecycle: bool = True
    webdriver: bool = True
    http: bool = True
    system_metrics: bool = False
    
    # Storage
    backend: StorageBackendType = StorageBackendType.NONE
    
    # Backend-specific configs
    local_path: Optional[str] = None
    
    postgres_host: Optional[str] = None
    postgres_port: int = 5432
    postgres_database: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_schema: str = "profiling"
    
    influxdb_url: Optional[str] = None
    influxdb_org: Optional[str] = None
    influxdb_bucket: Optional[str] = None
    influxdb_token: Optional[str] = None
    
    # Grafana
    grafana_enabled: bool = False
    grafana_datasource: str = "postgres"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileConfig":
        """Create config from dictionary"""
        profiling = data.get("profiling", {})
        collectors = profiling.get("collectors", {})
        storage = profiling.get("storage", {})
        postgres = storage.get("postgres", {})
        influxdb = storage.get("influxdb", {})
        grafana = profiling.get("grafana", {})
        
        backend_str = storage.get("backend", "none")
        backend = StorageBackendType(backend_str) if backend_str else StorageBackendType.NONE
        
        return cls(
            enabled=profiling.get("enabled", False),
            mode=profiling.get("mode", "passive"),
            sampling_rate=profiling.get("sampling_rate", 1.0),
            
            test_lifecycle=collectors.get("test_lifecycle", True),
            webdriver=collectors.get("webdriver", True),
            http=collectors.get("http", True),
            system_metrics=collectors.get("system_metrics", False),
            
            backend=backend,
            local_path=storage.get("local", {}).get("path"),
            
            postgres_host=postgres.get("host"),
            postgres_port=postgres.get("port", 5432),
            postgres_database=postgres.get("database"),
            postgres_user=postgres.get("user"),
            postgres_password=postgres.get("password"),
            postgres_schema=postgres.get("schema", "profiling"),
            
            influxdb_url=influxdb.get("url"),
            influxdb_org=influxdb.get("org"),
            influxdb_bucket=influxdb.get("bucket"),
            influxdb_token=influxdb.get("token"),
            
            grafana_enabled=grafana.get("enabled", False),
            grafana_datasource=grafana.get("datasource", "postgres"),
        )


@dataclass
class PerformanceInsight:
    """Performance analysis insight"""
    test_id: str
    insight_type: str  # slow_test, regression, slow_endpoint, etc.
    message: str
    severity: str  # info, warning, critical
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
