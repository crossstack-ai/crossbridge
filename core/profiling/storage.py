"""
Storage Backend Abstraction

Pluggable storage backends for performance profiling data.
Supports local, PostgreSQL, and InfluxDB (on-prem).
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from core.profiling.models import PerformanceEvent, ProfileConfig, StorageBackendType
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class StorageBackend(ABC):
    """Abstract storage backend for performance events"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize storage backend. Returns True if successful."""
        pass
    
    @abstractmethod
    def write_events(self, events: List[PerformanceEvent]) -> bool:
        """Write events to storage. Returns True if successful."""
        pass
    
    @abstractmethod
    def flush(self) -> bool:
        """Flush any buffered events. Returns True if successful."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Clean shutdown of storage backend."""
        pass


class NoOpStorageBackend(StorageBackend):
    """No-op storage backend when profiling is disabled"""
    
    def initialize(self) -> bool:
        return True
    
    def write_events(self, events: List[PerformanceEvent]) -> bool:
        return True
    
    def flush(self) -> bool:
        return True
    
    def shutdown(self) -> None:
        pass


class LocalStorageBackend(StorageBackend):
    """
    Local file-based storage using JSONL format.
    
    Use case: Local development, debugging, CI artifacts
    """
    
    def __init__(self, path: str = ".crossbridge/profiles"):
        self.base_path = Path(path)
        self.current_file: Optional[Path] = None
        self.file_handle = None
    
    def initialize(self) -> bool:
        """Create storage directory"""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Create new file for this run
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            self.current_file = self.base_path / f"run_{timestamp}.jsonl"
            
            logger.info(f"Initialized local storage: {self.current_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize local storage: {e}")
            return False
    
    def write_events(self, events: List[PerformanceEvent]) -> bool:
        """Write events to JSONL file"""
        if not self.current_file:
            return False
        
        try:
            with open(self.current_file, "a") as f:
                for event in events:
                    json.dump(event.to_dict(), f)
                    f.write("\n")
            return True
        except Exception as e:
            logger.error(f"Failed to write events to local storage: {e}")
            return False
    
    def flush(self) -> bool:
        """Flush is handled by file system"""
        return True
    
    def shutdown(self) -> None:
        """Close file handle"""
        if self.file_handle:
            try:
                self.file_handle.close()
            except:
                pass


class PostgresStorageBackend(StorageBackend):
    """
    PostgreSQL storage backend with Grafana-friendly schema.
    
    Use case: Primary relational storage, Grafana dashboards
    """
    
    def __init__(self, config: ProfileConfig):
        self.config = config
        self.pool = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize PostgreSQL connection pool and create schema"""
        try:
            import psycopg2
            from psycopg2 import pool
            
            # Create connection pool
            self.pool = pool.SimpleConnectionPool(
                1, 10,
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_database,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
            )
            
            # Create schema and tables
            conn = self.pool.getconn()
            try:
                cursor = conn.cursor()
                
                # Create schema
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.config.postgres_schema}")
                
                # Create runs table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config.postgres_schema}.runs (
                        run_id UUID PRIMARY KEY,
                        started_at TIMESTAMPTZ,
                        environment TEXT,
                        framework TEXT,
                        created_at TIMESTAMPTZ DEFAULT now()
                    )
                """)
                
                # Create tests table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config.postgres_schema}.tests (
                        id BIGSERIAL PRIMARY KEY,
                        run_id UUID,
                        test_id TEXT,
                        duration_ms INTEGER,
                        status TEXT,
                        framework TEXT,
                        created_at TIMESTAMPTZ DEFAULT now()
                    )
                """)
                
                # Create steps table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config.postgres_schema}.steps (
                        id BIGSERIAL PRIMARY KEY,
                        run_id UUID,
                        test_id TEXT,
                        step_name TEXT,
                        duration_ms INTEGER,
                        event_type TEXT,
                        framework TEXT,
                        created_at TIMESTAMPTZ DEFAULT now()
                    )
                """)
                
                # Create http_calls table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config.postgres_schema}.http_calls (
                        id BIGSERIAL PRIMARY KEY,
                        run_id UUID,
                        test_id TEXT,
                        endpoint TEXT,
                        method TEXT,
                        status_code INTEGER,
                        duration_ms INTEGER,
                        created_at TIMESTAMPTZ DEFAULT now()
                    )
                """)
                
                # Create driver_commands table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config.postgres_schema}.driver_commands (
                        id BIGSERIAL PRIMARY KEY,
                        run_id UUID,
                        test_id TEXT,
                        command TEXT,
                        duration_ms INTEGER,
                        retry_count INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT now()
                    )
                """)
                
                # Create system_metrics table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config.postgres_schema}.system_metrics (
                        id BIGSERIAL PRIMARY KEY,
                        run_id UUID,
                        test_id TEXT,
                        cpu_percent FLOAT,
                        memory_mb FLOAT,
                        created_at TIMESTAMPTZ DEFAULT now()
                    )
                """)
                
                # Create indexes for common queries
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_tests_test_id 
                    ON {self.config.postgres_schema}.tests(test_id)
                """)
                
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_tests_created_at 
                    ON {self.config.postgres_schema}.tests(created_at)
                """)
                
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_http_calls_endpoint 
                    ON {self.config.postgres_schema}.http_calls(endpoint)
                """)
                
                conn.commit()
                self._initialized = True
                logger.info("Initialized PostgreSQL storage backend")
                return True
                
            finally:
                cursor.close()
                self.pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL storage: {e}")
            return False
    
    def write_events(self, events: List[PerformanceEvent]) -> bool:
        """Write events to PostgreSQL"""
        if not self._initialized or not self.pool:
            return False
        
        try:
            conn = self.pool.getconn()
            try:
                cursor = conn.cursor()
                
                for event in events:
                    # Route to appropriate table based on event type
                    if event.event_type.value == "test_end":
                        cursor.execute(f"""
                            INSERT INTO {self.config.postgres_schema}.tests 
                            (run_id, test_id, duration_ms, status, framework, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            event.run_id,
                            event.test_id,
                            int(event.duration_ms),
                            event.metadata.get("status", "unknown"),
                            event.framework,
                            event.created_at,
                        ))
                    
                    elif event.event_type.value in ["step_end", "setup_end", "teardown_end"]:
                        cursor.execute(f"""
                            INSERT INTO {self.config.postgres_schema}.steps 
                            (run_id, test_id, step_name, duration_ms, event_type, framework, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            event.run_id,
                            event.test_id,
                            event.step_name or "unknown",
                            int(event.duration_ms),
                            event.event_type.value,
                            event.framework,
                            event.created_at,
                        ))
                    
                    elif event.event_type.value in ["http_request", "api_call"]:
                        cursor.execute(f"""
                            INSERT INTO {self.config.postgres_schema}.http_calls 
                            (run_id, test_id, endpoint, method, status_code, duration_ms, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            event.run_id,
                            event.test_id,
                            event.metadata.get("endpoint", "unknown"),
                            event.metadata.get("method", "GET"),
                            event.metadata.get("status_code", 0),
                            int(event.duration_ms),
                            event.created_at,
                        ))
                    
                    elif event.event_type.value == "driver_command":
                        cursor.execute(f"""
                            INSERT INTO {self.config.postgres_schema}.driver_commands 
                            (run_id, test_id, command, duration_ms, retry_count, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            event.run_id,
                            event.test_id,
                            event.metadata.get("command", "unknown"),
                            int(event.duration_ms),
                            event.metadata.get("retry_count", 0),
                            event.created_at,
                        ))
                    
                    elif event.event_type.value == "resource_usage":
                        cursor.execute(f"""
                            INSERT INTO {self.config.postgres_schema}.system_metrics 
                            (run_id, test_id, cpu_percent, memory_mb, created_at)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            event.run_id,
                            event.test_id,
                            event.metadata.get("cpu_percent", 0.0),
                            event.metadata.get("memory_mb", 0.0),
                            event.created_at,
                        ))
                
                conn.commit()
                return True
                
            finally:
                cursor.close()
                self.pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Failed to write events to PostgreSQL: {e}")
            return False
    
    def flush(self) -> bool:
        """Flush is handled by commit"""
        return True
    
    def shutdown(self) -> None:
        """Close connection pool"""
        if self.pool:
            try:
                self.pool.closeall()
            except:
                pass


class InfluxDBStorageBackend(StorageBackend):
    """
    InfluxDB time-series storage backend (on-prem).
    
    Use case: High-cardinality, long-term trends, time-series analysis
    """
    
    def __init__(self, config: ProfileConfig):
        self.config = config
        self.client = None
        self.write_api = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize InfluxDB client"""
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import SYNCHRONOUS
            
            self.client = InfluxDBClient(
                url=self.config.influxdb_url,
                token=self.config.influxdb_token,
                org=self.config.influxdb_org,
            )
            
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self._initialized = True
            
            logger.info("Initialized InfluxDB storage backend")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB storage: {e}")
            return False
    
    def write_events(self, events: List[PerformanceEvent]) -> bool:
        """Write events to InfluxDB"""
        if not self._initialized or not self.write_api:
            return False
        
        try:
            points = [event.to_influx_point() for event in events]
            self.write_api.write(
                bucket=self.config.influxdb_bucket,
                org=self.config.influxdb_org,
                record=points,
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to write events to InfluxDB: {e}")
            return False
    
    def flush(self) -> bool:
        """Flush write API"""
        if self.write_api:
            try:
                self.write_api.flush()
                return True
            except Exception as e:
                logger.error(f"Failed to flush InfluxDB: {e}")
                return False
        return True
    
    def shutdown(self) -> None:
        """Close InfluxDB client"""
        if self.client:
            try:
                self.client.close()
            except:
                pass


class StorageFactory:
    """Factory for creating storage backends"""
    
    @staticmethod
    def from_config(config: ProfileConfig) -> StorageBackend:
        """Create storage backend from configuration"""
        if not config.enabled or config.backend == StorageBackendType.NONE:
            return NoOpStorageBackend()
        
        elif config.backend == StorageBackendType.LOCAL:
            return LocalStorageBackend(config.local_path or ".crossbridge/profiles")
        
        elif config.backend == StorageBackendType.POSTGRES:
            return PostgresStorageBackend(config)
        
        elif config.backend == StorageBackendType.INFLUXDB:
            return InfluxDBStorageBackend(config)
        
        else:
            logger.warning(f"Unknown storage backend: {config.backend}")
            return NoOpStorageBackend()
