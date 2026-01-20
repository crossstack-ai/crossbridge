"""
Database persistence layer for flaky test detection.

Handles storing test execution records and flaky detection results
to PostgreSQL database.
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from uuid import uuid4
import json

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime,
    Text, ARRAY, create_engine, and_, desc
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .models import (
    TestExecutionRecord, FlakyTestResult,
    TestFramework, TestStatus
)

Base = declarative_base()


class TestExecutionDB(Base):
    """Database model for test execution records."""
    
    __tablename__ = "test_execution"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Test identification
    test_id = Column(String, nullable=False, index=True)
    test_name = Column(String)
    test_file = Column(String)
    test_line = Column(Integer)
    framework = Column(String, nullable=False, index=True)
    
    # Execution outcome
    status = Column(String, nullable=False, index=True)
    duration_ms = Column(Float, nullable=False)
    executed_at = Column(DateTime, nullable=False, index=True)
    
    # Error details
    error_signature = Column(Text)
    error_full = Column(Text)
    error_type = Column(String)
    
    # Context
    retry_count = Column(Integer, default=0)
    git_commit = Column(String, index=True)
    environment = Column(String, default="unknown")
    build_id = Column(String)
    
    # Metadata
    tags = Column(ARRAY(String))
    test_metadata = Column(JSONB)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.now)
    
    @staticmethod
    def from_record(record: TestExecutionRecord) -> "TestExecutionDB":
        """Create database model from TestExecutionRecord."""
        return TestExecutionDB(
            test_id=record.test_id,
            test_name=record.test_name,
            test_file=record.test_file,
            test_line=record.test_line,
            framework=record.framework.value,
            status=record.status.value,
            duration_ms=record.duration_ms,
            executed_at=record.executed_at,
            error_signature=record.error_signature,
            error_full=record.error_full,
            error_type=record.get_error_type(),
            retry_count=record.retry_count,
            git_commit=record.git_commit,
            environment=record.environment,
            build_id=record.build_id,
            tags=record.tags,
            test_metadata=record.metadata
        )
    
    def to_record(self) -> TestExecutionRecord:
        """Convert database model to TestExecutionRecord."""
        return TestExecutionRecord(
            test_id=self.test_id,
            framework=TestFramework(self.framework),
            status=TestStatus(self.status),
            duration_ms=self.duration_ms,
            executed_at=self.executed_at,
            error_signature=self.error_signature,
            error_full=self.error_full,
            retry_count=self.retry_count,
            git_commit=self.git_commit,
            environment=self.environment,
            build_id=self.build_id,
            test_name=self.test_name,
            test_file=self.test_file,
            test_line=self.test_line,
            tags=self.tags or [],
            metadata=self.test_metadata or {}
        )


class FlakyTestDB(Base):
    """Database model for flaky test detection results."""
    
    __tablename__ = "flaky_test"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Test identification
    test_id = Column(String, nullable=False, unique=True, index=True)
    test_name = Column(String)
    framework = Column(String, nullable=False)
    
    # Flakiness scores
    flaky_score = Column(Float, nullable=False)
    is_flaky = Column(Boolean, nullable=False, index=True)
    confidence = Column(Float, nullable=False, index=True)
    classification = Column(String, nullable=False, index=True)
    severity = Column(String, index=True)
    
    # Features
    failure_rate = Column(Float)
    switch_rate = Column(Float)
    duration_variance = Column(Float)
    unique_error_count = Column(Integer)
    total_executions = Column(Integer)
    
    # Detection metadata
    primary_indicators = Column(ARRAY(String))
    detected_at = Column(DateTime, nullable=False)
    model_version = Column(String, nullable=False)
    last_updated = Column(DateTime, default=datetime.now)
    
    created_at = Column(DateTime, default=datetime.now)
    
    @staticmethod
    def from_result(result: FlakyTestResult) -> "FlakyTestDB":
        """Create database model from FlakyTestResult."""
        # Convert numpy types to Python native types
        def to_native(value):
            """Convert numpy types to Python native types."""
            if hasattr(value, 'item'):  # numpy scalar
                return value.item()
            return value
        
        return FlakyTestDB(
            test_id=result.test_id,
            test_name=result.test_name,
            framework=result.framework.value,
            flaky_score=float(to_native(result.flaky_score)),
            is_flaky=result.is_flaky,
            confidence=float(to_native(result.confidence)),
            classification=result.classification,
            severity=result.severity,
            failure_rate=float(to_native(result.features.failure_rate)),
            switch_rate=float(to_native(result.features.pass_fail_switch_rate)),
            duration_variance=float(to_native(result.features.duration_variance)),
            unique_error_count=int(to_native(result.features.unique_error_count)),
            total_executions=int(to_native(result.features.total_executions)),
            primary_indicators=result.primary_indicators,
            detected_at=result.detected_at,
            model_version=result.model_version
        )


class FlakyTestHistoryDB(Base):
    """Database model for flaky test detection history."""
    
    __tablename__ = "flaky_test_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    test_id = Column(String, nullable=False, index=True)
    flaky_score = Column(Float, nullable=False)
    is_flaky = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    classification = Column(String, nullable=False)
    failure_rate = Column(Float)
    total_executions = Column(Integer)
    detected_at = Column(DateTime, nullable=False, index=True)
    model_version = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.now)


class FlakyDetectionRepository:
    """Repository for flaky detection database operations."""
    
    def __init__(self, database_url: str):
        """
        Initialize repository.
        
        Args:
            database_url: PostgreSQL connection string
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    # Test Execution Operations
    
    def save_execution(self, record: TestExecutionRecord, session: Optional[Session] = None) -> None:
        """Save test execution record."""
        own_session = session is None
        if own_session:
            session = self.get_session()
        
        try:
            db_record = TestExecutionDB.from_record(record)
            session.add(db_record)
            
            if own_session:
                session.commit()
        except Exception as e:
            if own_session:
                session.rollback()
            raise e
        finally:
            if own_session:
                session.close()
    
    def save_executions_batch(self, records: List[TestExecutionRecord]) -> None:
        """Save multiple execution records in batch."""
        session = self.get_session()
        try:
            db_records = [TestExecutionDB.from_record(r) for r in records]
            session.bulk_save_objects(db_records)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_executions_by_test(
        self,
        test_id: str,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[TestExecutionRecord]:
        """Get execution records for a specific test."""
        session = self.get_session()
        try:
            query = session.query(TestExecutionDB).filter(
                TestExecutionDB.test_id == test_id
            )
            
            if since:
                query = query.filter(TestExecutionDB.executed_at >= since)
            
            query = query.order_by(desc(TestExecutionDB.executed_at))
            
            if limit:
                query = query.limit(limit)
            
            db_records = query.all()
            return [r.to_record() for r in db_records]
        finally:
            session.close()
    
    def get_all_test_executions(
        self,
        framework: Optional[TestFramework] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, List[TestExecutionRecord]]:
        """Get all execution records grouped by test_id."""
        session = self.get_session()
        try:
            query = session.query(TestExecutionDB)
            
            if framework:
                query = query.filter(TestExecutionDB.framework == framework.value)
            
            if since:
                query = query.filter(TestExecutionDB.executed_at >= since)
            
            query = query.order_by(TestExecutionDB.test_id, TestExecutionDB.executed_at)
            
            db_records = query.all()
            
            # Group by test_id
            grouped: Dict[str, List[TestExecutionRecord]] = {}
            for db_record in db_records:
                record = db_record.to_record()
                if record.test_id not in grouped:
                    grouped[record.test_id] = []
                grouped[record.test_id].append(record)
            
            return grouped
        finally:
            session.close()
    
    # Flaky Test Operations
    
    def save_flaky_result(self, result: FlakyTestResult) -> None:
        """Save or update flaky test detection result."""
        session = self.get_session()
        try:
            # Check if exists
            existing = session.query(FlakyTestDB).filter(
                FlakyTestDB.test_id == result.test_id
            ).first()
            
            if existing:
                # Update existing record - convert numpy types to Python native
                def to_native(value):
                    if hasattr(value, 'item'):  # numpy scalar
                        return value.item()
                    return value
                
                existing.flaky_score = float(to_native(result.flaky_score))
                existing.is_flaky = result.is_flaky
                existing.confidence = float(to_native(result.confidence))
                existing.classification = result.classification
                existing.severity = result.severity
                existing.failure_rate = float(to_native(result.features.failure_rate))
                existing.switch_rate = float(to_native(result.features.pass_fail_switch_rate))
                existing.duration_variance = float(to_native(result.features.duration_variance))
                existing.unique_error_count = int(to_native(result.features.unique_error_count))
                existing.total_executions = int(to_native(result.features.total_executions))
                existing.primary_indicators = result.primary_indicators
                existing.detected_at = result.detected_at
                existing.model_version = result.model_version
            else:
                # Insert new record
                db_result = FlakyTestDB.from_result(result)
                session.add(db_result)
            
            # Also save to history - convert numpy types
            def to_native(value):
                if hasattr(value, 'item'):
                    return value.item()
                return value
            
            history = FlakyTestHistoryDB(
                test_id=result.test_id,
                flaky_score=float(to_native(result.flaky_score)),
                is_flaky=result.is_flaky,
                confidence=float(to_native(result.confidence)),
                classification=result.classification,
                failure_rate=float(to_native(result.features.failure_rate)),
                total_executions=int(to_native(result.features.total_executions)),
                detected_at=result.detected_at,
                model_version=result.model_version
            )
            session.add(history)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_flaky_tests(
        self,
        is_flaky: Optional[bool] = None,
        min_confidence: Optional[float] = None,
        framework: Optional[TestFramework] = None
    ) -> List[dict]:
        """Get flaky test results."""
        session = self.get_session()
        try:
            query = session.query(FlakyTestDB)
            
            if is_flaky is not None:
                query = query.filter(FlakyTestDB.is_flaky == is_flaky)
            
            if min_confidence is not None:
                query = query.filter(FlakyTestDB.confidence >= min_confidence)
            
            if framework:
                query = query.filter(FlakyTestDB.framework == framework.value)
            
            query = query.order_by(
                desc(FlakyTestDB.is_flaky),
                desc(FlakyTestDB.severity),
                desc(FlakyTestDB.failure_rate)
            )
            
            results = query.all()
            
            return [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "framework": r.framework,
                    "is_flaky": r.is_flaky,
                    "confidence": r.confidence,
                    "classification": r.classification,
                    "severity": r.severity,
                    "failure_rate": r.failure_rate,
                    "switch_rate": r.switch_rate,
                    "unique_error_count": r.unique_error_count,
                    "total_executions": r.total_executions,
                    "primary_indicators": r.primary_indicators,
                    "detected_at": r.detected_at
                }
                for r in results
            ]
        finally:
            session.close()
    
    def cleanup_old_executions(self, days_to_keep: int = 90) -> int:
        """Remove old execution records."""
        session = self.get_session()
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            deleted = session.query(TestExecutionDB).filter(
                TestExecutionDB.executed_at < cutoff_date
            ).delete()
            
            session.commit()
            return deleted
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
