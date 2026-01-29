"""
Formal Persistence Schema Definitions for CrossBridge

Defines all database schemas with proper versioning and migration support.
Addresses standardization requirements for production-grade persistence.

Schema Categories:
1. Test Execution & Results
2. Embeddings & Memory
3. Flaky Test Detection
4. Performance Profiling
5. Coverage Analysis
6. Migration Tracking
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.exc import IntegrityError, OperationalError
import uuid

from core.logging import get_logger, LogCategory
from core.runtime.retry import retry_with_backoff, RetryPolicy, RetryableError

logger = get_logger(__name__, category=LogCategory.PERSISTENCE)

Base = declarative_base()


# ============================================================================
# 1. Test Execution & Results Schema
# ============================================================================


class TestExecutionStatus(str, Enum):
    """Test execution status enumeration."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    BLOCKED = "blocked"


class TestExecution(Base):
    """
    Core test execution record.
    
    Tracks every test execution with full context and results.
    """
    __tablename__ = "test_execution"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_case.id"), nullable=False, index=True)
    
    # Execution metadata
    framework = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    duration_ms = Column(Integer, nullable=False)
    
    # Timing breakdown
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    setup_duration_ms = Column(Integer)
    teardown_duration_ms = Column(Integer)
    
    # Failure details
    error_message = Column(Text)
    error_type = Column(String(100))
    stack_trace = Column(Text)
    screenshot_path = Column(String(500))
    
    # Environment
    environment = Column(String(50))  # dev, staging, prod
    application_version = Column(String(50))
    browser = Column(String(50))
    os = Column(String(50))
    
    # CI/CD context
    build_id = Column(String(100), index=True)
    pipeline_id = Column(String(100))
    branch = Column(String(100))
    commit_sha = Column(String(100))
    
    # Additional metadata
    extra_metadata = Column(JSONB)
    tags = Column(ARRAY(String))
    
    # Retry information
    retry_count = Column(Integer, default=0)
    is_retry = Column(Boolean, default=False)
    original_execution_id = Column(UUID(as_uuid=True))
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    test_case = relationship("TestCase", back_populates="executions")
    profiling_events = relationship("ProfilingEvent", back_populates="execution")
    
    __table_args__ = (
        Index("idx_execution_test_start", "test_case_id", "start_time"),
        Index("idx_execution_status_framework", "status", "framework"),
        Index("idx_execution_build", "build_id", "start_time"),
    )


class TestCase(Base):
    """
    Test case definition and metadata.
    
    Represents a unique test across framework and version.
    """
    __tablename__ = "test_case"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identification
    name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    framework = Column(String(50), nullable=False, index=True)
    
    # Classification
    test_type = Column(String(50))  # unit, integration, e2e, api
    suite = Column(String(200))
    tags = Column(ARRAY(String))
    
    # Source code
    source_code = Column(Text)
    line_number = Column(Integer)
    
    # External references
    external_test_id = Column(String(100))  # TestRail, Zephyr, qTest
    jira_issue = Column(String(50))
    
    # Metadata
    extra_metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    executions = relationship("TestExecution", back_populates="test_case")
    coverage_records = relationship("CoverageRecord", back_populates="test_case")
    memory_records = relationship("MemoryEmbedding", back_populates="test_case")
    
    __table_args__ = (
        Index("idx_testcase_framework_name", "framework", "name"),
        Index("idx_testcase_file", "file_path"),
        UniqueConstraint("name", "file_path", "framework", name="uq_test_case"),
    )


# ============================================================================
# 2. Embeddings & Memory Schema
# ============================================================================


class MemoryType(str, Enum):
    """Memory record type enumeration."""
    TEST = "test"
    SCENARIO = "scenario"
    STEP = "step"
    PAGE_OBJECT = "page_object"
    FAILURE = "failure"
    ASSERTION = "assertion"
    LOCATOR = "locator"


class MemoryEmbedding(Base):
    """
    Semantic embeddings for intelligent test discovery.
    
    Enables natural language search and similarity detection.
    """
    __tablename__ = "memory_embedding"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Record identification
    record_id = Column(String(200), nullable=False, unique=True, index=True)
    record_type = Column(String(50), nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    normalized_content = Column(Text)
    
    # Embedding vector (pgvector extension)
    # Note: Actual implementation uses pgvector's vector type
    # This is simplified for SQLAlchemy compatibility
    embedding = Column(JSONB, nullable=False)  # Stores vector as JSON
    embedding_dimension = Column(Integer, nullable=False)
    
    # Metadata
    framework = Column(String(50), index=True)
    file_path = Column(String(1000))
    language = Column(String(50))
    tags = Column(ARRAY(String))
    
    # Foreign keys
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_case.id"), index=True)
    
    # Embedding metadata
    embedding_model = Column(String(100))
    embedding_provider = Column(String(50))
    embedding_version = Column(String(50))
    
    # Additional context
    extra_metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    test_case = relationship("TestCase", back_populates="memory_records")
    
    __table_args__ = (
        Index("idx_memory_type_framework", "record_type", "framework"),
        Index("idx_memory_test_case", "test_case_id"),
    )


class SimilarityCache(Base):
    """
    Cache for computed similarity scores.
    
    Improves performance of repeated similarity queries.
    """
    __tablename__ = "similarity_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    record_id_1 = Column(UUID(as_uuid=True), nullable=False, index=True)
    record_id_2 = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    similarity_score = Column(Float, nullable=False)
    
    # Computation metadata
    algorithm = Column(String(50))  # cosine, euclidean, dot_product
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("record_id_1", "record_id_2", name="uq_similarity_pair"),
        Index("idx_similarity_score", "similarity_score"),
    )


# ============================================================================
# 3. Flaky Test Detection Schema
# ============================================================================


class FlakyTestDetection(Base):
    """
    Flaky test detection results from ML model.
    
    Stores flakiness scores, confidence, and severity.
    """
    __tablename__ = "flaky_test"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_case.id"), nullable=False, unique=True, index=True)
    
    # Flakiness metrics
    flaky_score = Column(Float, nullable=False, index=True)  # 0.0 to 1.0
    confidence = Column(Float, nullable=False)  # Model confidence
    severity = Column(String(20), nullable=False, index=True)  # critical, high, medium, low
    
    # Statistical features (used by ML model)
    failure_rate = Column(Float, nullable=False)
    pass_fail_switch_rate = Column(Float)
    timing_variance = Column(Float)
    error_type_diversity = Column(Float)
    consecutive_passes = Column(Integer)
    consecutive_failures = Column(Integer)
    
    # Patterns
    common_error_types = Column(ARRAY(String))
    time_patterns = Column(JSONB)  # Time-of-day, day-of-week patterns
    environment_patterns = Column(JSONB)  # Browser, OS patterns
    
    # ML model info
    model_version = Column(String(50))
    features_used = Column(JSONB)
    
    # Status
    is_flaky = Column(Boolean, nullable=False, default=False, index=True)
    last_analyzed = Column(DateTime, nullable=False, index=True)
    
    # History tracking
    detection_history = Column(JSONB)  # Historical flaky scores
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    test_case = relationship("TestCase")
    
    __table_args__ = (
        Index("idx_flaky_score_severity", "flaky_score", "severity"),
        Index("idx_flaky_is_flaky", "is_flaky", "last_analyzed"),
    )


class FlakyTestHistory(Base):
    """
    Historical flakiness detection results.
    
    Tracks how flakiness changes over time.
    """
    __tablename__ = "flaky_test_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_case.id"), nullable=False, index=True)
    
    flaky_score = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False)
    is_flaky = Column(Boolean, nullable=False)
    
    # Analysis metadata
    analysis_window_start = Column(DateTime, nullable=False)
    analysis_window_end = Column(DateTime, nullable=False)
    executions_analyzed = Column(Integer, nullable=False)
    
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_history_test_analyzed", "test_case_id", "analyzed_at"),
    )


# ============================================================================
# 4. Performance Profiling Schema
# ============================================================================


class ProfilingEvent(Base):
    """
    Individual performance profiling events.
    
    Tracks timing of specific operations during test execution.
    """
    __tablename__ = "profiling_event"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("test_execution.id"), nullable=False, index=True)
    
    # Event identification
    event_type = Column(String(50), nullable=False, index=True)  # webdriver, http, database, etc.
    operation = Column(String(100), nullable=False)  # click, get, post, query, etc.
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_ms = Column(Integer, nullable=False)
    
    # Event details
    target = Column(String(500))  # URL, element, query, etc.
    method = Column(String(50))
    status_code = Column(Integer)
    
    # Additional data
    extra_metadata = Column(JSONB)
    
    # Parent event (for nested operations)
    parent_event_id = Column(UUID(as_uuid=True), ForeignKey("profiling_event.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    execution = relationship("TestExecution", back_populates="profiling_events")
    
    __table_args__ = (
        Index("idx_profiling_execution_type", "execution_id", "event_type"),
        Index("idx_profiling_start_time", "start_time"),
    )


# ============================================================================
# 5. Coverage Analysis Schema
# ============================================================================


class CoverageRecord(Base):
    """
    Test coverage tracking at multiple levels.
    
    Tracks functional, behavioral, and code coverage.
    """
    __tablename__ = "coverage_record"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_case.id"), nullable=False, index=True)
    
    # Coverage type
    coverage_type = Column(String(50), nullable=False)  # functional, behavioral, code
    
    # Coverage target
    target_type = Column(String(50), nullable=False)  # feature, user_story, class, method
    target_id = Column(String(200), nullable=False, index=True)
    target_name = Column(String(500), nullable=False)
    
    # Coverage metrics
    lines_covered = Column(Integer)
    lines_total = Column(Integer)
    coverage_percentage = Column(Float)
    
    # Metadata
    extra_metadata = Column(JSONB)
    
    # Timestamps
    measured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    test_case = relationship("TestCase", back_populates="coverage_records")
    
    __table_args__ = (
        Index("idx_coverage_target", "target_type", "target_id"),
        Index("idx_coverage_test", "test_case_id", "coverage_type"),
    )


# ============================================================================
# 6. Migration Tracking Schema
# ============================================================================


class MigrationRecord(Base):
    """
    Tracks test migration/transformation history.
    
    Maintains audit trail for all migrations.
    """
    __tablename__ = "migration_record"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Migration identification
    migration_id = Column(String(100), nullable=False, unique=True, index=True)
    migration_type = Column(String(50), nullable=False)  # framework_change, modernization, refactor
    
    # Source and target
    source_framework = Column(String(50), nullable=False)
    target_framework = Column(String(50), nullable=False)
    source_file = Column(String(1000), nullable=False)
    target_file = Column(String(1000), nullable=False)
    
    # Migration details
    transformation_mode = Column(String(50))  # manual, enhanced, hybrid
    ai_assisted = Column(Boolean, default=False)
    
    # Quality metrics
    confidence_score = Column(Float)
    quality_score = Column(Float)
    validation_passed = Column(Boolean)
    
    # Issues
    issues_count = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    issues = Column(JSONB)
    
    # AI cost tracking
    tokens_used = Column(Integer)
    cost_usd = Column(Float)
    model_used = Column(String(100))
    
    # Status
    status = Column(String(50), nullable=False, index=True)  # pending, completed, failed, rolled_back
    
    # Review
    reviewed_by = Column(String(100))
    approved = Column(Boolean)
    review_comments = Column(Text)
    
    # Timestamps
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_migration_frameworks", "source_framework", "target_framework"),
        Index("idx_migration_status", "status", "started_at"),
    )


# ============================================================================
# Schema Migration Management
# ============================================================================


class SchemaVersion(Base):
    """
    Database schema version tracking.
    
    Enables schema migrations and version compatibility checks.
    """
    __tablename__ = "schema_version"

    id = Column(Integer, primary_key=True)
    version = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    
    # Migration script
    migration_script = Column(String(200))
    rollback_script = Column(String(200))
    
    # Status
    applied = Column(Boolean, default=False)
    applied_at = Column(DateTime)
    
    # Metadata
    extra_metadata = Column(JSONB)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ============================================================================
# Schema Creation and Migration Functions
# ============================================================================


def create_all_schemas(engine):
    """
    Create all database schemas with retry logic.
    
    Args:
        engine: SQLAlchemy engine
        
    Raises:
        RetryableError: If schema creation fails after retries
    """
    logger.info("Creating database schemas...")
    
    def _create_schemas():
        try:
            Base.metadata.create_all(engine)
            logger.info("✓ All schemas created successfully", extra={
                "table_count": len(Base.metadata.tables),
                "tables": list(Base.metadata.tables.keys())
            })
        except OperationalError as e:
            logger.error(f"Database operational error during schema creation: {e}")
            raise RetryableError(f"Failed to create schemas: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during schema creation: {e}", exc_info=True)
            raise
    
    # Retry with backoff for transient failures
    retry_with_backoff(
        _create_schemas,
        RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=10.0)
    )


def verify_schema_version(session: Session) -> str:
    """
    Verify current schema version with retry logic.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        Current schema version
        
    Raises:
        RetryableError: If version check fails after retries
    """
    logger.debug("Verifying schema version...")
    
    def _get_version():
        try:
            latest = session.query(SchemaVersion).filter(
                SchemaVersion.applied == True
            ).order_by(SchemaVersion.id.desc()).first()
            
            version = latest.version if latest else "0.0.0"
            logger.info(f"Current schema version: {version}", extra={
                "version": version,
                "has_migrations": latest is not None
            })
            return version
        except OperationalError as e:
            logger.warning(f"Database error during version check: {e}")
            raise RetryableError(f"Failed to verify schema version: {e}") from e
    
    return retry_with_backoff(
        _get_version,
        RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=5.0)
    )


def apply_migration(session: Session, version: str, description: str, migration_func):
    """
    Apply a schema migration with comprehensive error handling.
    
    Args:
        session: SQLAlchemy session
        version: Migration version (e.g., "1.0.0")
        description: Migration description
        migration_func: Function to execute migration
        
    Raises:
        IntegrityError: If migration violates constraints
        OperationalError: If database operation fails
        Exception: For other migration failures
    """
    logger.info(f"Applying migration {version}: {description}")
    
    # Check if already applied
    try:
        existing = session.query(SchemaVersion).filter(
            SchemaVersion.version == version
        ).first()
        
        if existing and existing.applied:
            logger.warning(f"⚠ Migration {version} already applied", extra={
                "version": version,
                "applied_at": existing.applied_at.isoformat() if existing.applied_at else None
            })
            return
    except OperationalError as e:
        logger.error(f"Failed to check migration status for {version}: {e}")
        raise
    
    # Apply migration with transaction
    try:
        logger.info(f"Executing migration function for {version}...")
        migration_func(session)
        session.commit()
        logger.info(f"Migration {version} executed successfully")
        
        # Record migration
        if existing:
            existing.applied = True
            existing.applied_at = datetime.utcnow()
        else:
            schema_version = SchemaVersion(
                version=version,
                description=description,
                applied=True,
                applied_at=datetime.utcnow(),
                extra_metadata={"applied_by": "crossbridge", "auto_applied": True}
            )
            session.add(schema_version)
        
        session.commit()
        logger.info(f"✓ Migration {version} applied and recorded successfully", extra={
            "version": version,
            "description": description
        })
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"✗ Migration {version} failed - integrity constraint violated: {e}", extra={
            "version": version,
            "error_type": "IntegrityError"
        })
        raise
    except OperationalError as e:
        session.rollback()
        logger.error(f"✗ Migration {version} failed - database operational error: {e}", extra={
            "version": version,
            "error_type": "OperationalError"
        })
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"✗ Migration {version} failed unexpectedly: {e}", extra={
            "version": version,
            "error_type": type(e).__name__
        }, exc_info=True)
        raise
