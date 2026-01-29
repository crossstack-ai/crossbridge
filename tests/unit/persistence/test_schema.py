"""
Unit tests for Persistence Schema

Tests the formal schema definitions and migration management.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from persistence.schema import (
    Base,
    TestExecution,
    TestCase,
    MemoryEmbedding,
    SimilarityCache,
    FlakyTestDetection,
    FlakyTestHistory,
    ProfilingEvent,
    CoverageRecord,
    MigrationRecord,
    SchemaVersion,
    TestExecutionStatus,
    MemoryType,
    create_all_schemas,
    verify_schema_version,
    apply_migration,
)


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session"""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestSchemaCreation:
    """Test schema creation and table structure"""

    def test_create_all_schemas(self, engine):
        """Test all schemas are created successfully"""
        # Drop and recreate
        Base.metadata.drop_all(engine)
        create_all_schemas(engine)
        
        # Verify tables exist
        assert engine.dialect.has_table(engine.connect(), "test_execution")
        assert engine.dialect.has_table(engine.connect(), "test_case")
        assert engine.dialect.has_table(engine.connect(), "memory_embedding")
        assert engine.dialect.has_table(engine.connect(), "flaky_test")

    def test_all_tables_created(self, engine):
        """Test all expected tables are created"""
        expected_tables = [
            "test_execution",
            "test_case",
            "memory_embedding",
            "similarity_cache",
            "flaky_test",
            "flaky_test_history",
            "profiling_event",
            "coverage_record",
            "migration_record",
            "schema_version",
        ]
        
        inspector = engine.dialect
        for table_name in expected_tables:
            assert inspector.has_table(engine.connect(), table_name), \
                f"Table {table_name} not found"


class TestTestCaseModel:
    """Test TestCase model"""

    def test_create_test_case(self, session):
        """Test creating a test case"""
        test_case = TestCase(
            name="test_login_valid",
            file_path="/tests/test_login.py",
            framework="pytest",
            test_type="e2e",
            suite="login_suite",
            tags=["smoke", "critical"],
        )
        
        session.add(test_case)
        session.commit()
        
        assert test_case.id is not None
        assert test_case.created_at is not None
        assert test_case.updated_at is not None

    def test_test_case_unique_constraint(self, session):
        """Test unique constraint on test case"""
        test_case1 = TestCase(
            name="test_login",
            file_path="/tests/test_login.py",
            framework="pytest"
        )
        session.add(test_case1)
        session.commit()
        
        # Try to add duplicate
        test_case2 = TestCase(
            name="test_login",
            file_path="/tests/test_login.py",
            framework="pytest"
        )
        session.add(test_case2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            session.commit()

    def test_test_case_relationships(self, session):
        """Test test case relationships"""
        test_case = TestCase(
            name="test_example",
            file_path="/tests/test.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        # Add execution
        execution = TestExecution(
            test_case_id=test_case.id,
            framework="pytest",
            status="passed",
            duration_ms=1000,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        session.add(execution)
        session.commit()
        
        # Verify relationship
        assert len(test_case.executions) == 1
        assert test_case.executions[0].status == "passed"


class TestTestExecutionModel:
    """Test TestExecution model"""

    def test_create_test_execution(self, session):
        """Test creating a test execution"""
        # Create test case first
        test_case = TestCase(
            name="test_login",
            file_path="/tests/test_login.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        # Create execution
        execution = TestExecution(
            test_case_id=test_case.id,
            framework="pytest",
            status=TestExecutionStatus.PASSED.value,
            duration_ms=1500,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            environment="staging",
            application_version="v2.0.0",
            browser="chrome",
            build_id="build-123"
        )
        
        session.add(execution)
        session.commit()
        
        assert execution.id is not None
        assert execution.test_case_id == test_case.id
        assert execution.status == "passed"

    def test_execution_with_failure_details(self, session):
        """Test execution with failure details"""
        test_case = TestCase(
            name="test_fail",
            file_path="/tests/test.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        execution = TestExecution(
            test_case_id=test_case.id,
            framework="pytest",
            status=TestExecutionStatus.FAILED.value,
            duration_ms=500,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            error_message="AssertionError: Expected True, got False",
            error_type="AssertionError",
            stack_trace="Traceback...",
            screenshot_path="/screenshots/fail.png"
        )
        
        session.add(execution)
        session.commit()
        
        assert execution.error_message is not None
        assert execution.error_type == "AssertionError"

    def test_execution_retry_tracking(self, session):
        """Test retry tracking in execution"""
        test_case = TestCase(
            name="test_flaky",
            file_path="/tests/test.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        # Original execution
        original = TestExecution(
            test_case_id=test_case.id,
            framework="pytest",
            status="failed",
            duration_ms=1000,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            retry_count=0
        )
        session.add(original)
        session.commit()
        
        # Retry execution
        retry = TestExecution(
            test_case_id=test_case.id,
            framework="pytest",
            status="passed",
            duration_ms=1100,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            retry_count=1,
            is_retry=True,
            original_execution_id=original.id
        )
        session.add(retry)
        session.commit()
        
        assert retry.is_retry is True
        assert retry.original_execution_id == original.id


class TestMemoryEmbeddingModel:
    """Test MemoryEmbedding model"""

    def test_create_memory_embedding(self, session):
        """Test creating memory embedding"""
        test_case = TestCase(
            name="test_login",
            file_path="/tests/test_login.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        embedding = MemoryEmbedding(
            record_id="test-login-001",
            record_type=MemoryType.TEST.value,
            content="Test valid user login with correct credentials",
            embedding=[0.1] * 3072,  # Mock embedding vector
            embedding_dimension=3072,
            framework="pytest",
            test_case_id=test_case.id,
            embedding_model="text-embedding-3-large",
            embedding_provider="openai"
        )
        
        session.add(embedding)
        session.commit()
        
        assert embedding.id is not None
        assert embedding.embedding_dimension == 3072
        assert len(embedding.embedding) == 3072

    def test_memory_embedding_types(self, session):
        """Test different memory embedding types"""
        types = [
            MemoryType.TEST,
            MemoryType.SCENARIO,
            MemoryType.STEP,
            MemoryType.PAGE_OBJECT,
        ]
        
        for mem_type in types:
            embedding = MemoryEmbedding(
                record_id=f"record-{mem_type.value}",
                record_type=mem_type.value,
                content=f"Content for {mem_type.value}",
                embedding=[0.1] * 1536,
                embedding_dimension=1536,
                framework="pytest"
            )
            session.add(embedding)
        
        session.commit()
        
        # Query by type
        test_embeddings = session.query(MemoryEmbedding).filter(
            MemoryEmbedding.record_type == MemoryType.TEST.value
        ).all()
        
        assert len(test_embeddings) == 1


class TestFlakyDetectionModel:
    """Test FlakyTestDetection model"""

    def test_create_flaky_detection(self, session):
        """Test creating flaky detection record"""
        test_case = TestCase(
            name="test_flaky",
            file_path="/tests/test.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        flaky = FlakyTestDetection(
            test_case_id=test_case.id,
            flaky_score=0.85,
            confidence=0.92,
            severity="high",
            failure_rate=0.35,
            pass_fail_switch_rate=0.45,
            timing_variance=0.25,
            is_flaky=True,
            last_analyzed=datetime.utcnow(),
            model_version="1.0.0"
        )
        
        session.add(flaky)
        session.commit()
        
        assert flaky.id is not None
        assert flaky.is_flaky is True
        assert flaky.flaky_score == 0.85

    def test_flaky_detection_unique_per_test(self, session):
        """Test unique constraint on flaky detection per test case"""
        test_case = TestCase(
            name="test_unique",
            file_path="/tests/test.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        flaky1 = FlakyTestDetection(
            test_case_id=test_case.id,
            flaky_score=0.8,
            confidence=0.9,
            severity="high",
            failure_rate=0.3,
            is_flaky=True,
            last_analyzed=datetime.utcnow()
        )
        session.add(flaky1)
        session.commit()
        
        # Try to add another for same test
        flaky2 = FlakyTestDetection(
            test_case_id=test_case.id,
            flaky_score=0.9,
            confidence=0.95,
            severity="critical",
            failure_rate=0.4,
            is_flaky=True,
            last_analyzed=datetime.utcnow()
        )
        session.add(flaky2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            session.commit()


class TestProfilingEventModel:
    """Test ProfilingEvent model"""

    def test_create_profiling_event(self, session):
        """Test creating profiling event"""
        test_case = TestCase(
            name="test_profile",
            file_path="/tests/test.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        execution = TestExecution(
            test_case_id=test_case.id,
            framework="pytest",
            status="passed",
            duration_ms=2000,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        session.add(execution)
        session.commit()
        
        event = ProfilingEvent(
            execution_id=execution.id,
            event_type="webdriver",
            operation="click",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=150,
            target="button#login",
            method="POST"
        )
        
        session.add(event)
        session.commit()
        
        assert event.id is not None
        assert event.event_type == "webdriver"

    def test_profiling_event_nested(self, session):
        """Test nested profiling events"""
        test_case = TestCase(
            name="test_nested",
            file_path="/tests/test.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        execution = TestExecution(
            test_case_id=test_case.id,
            framework="pytest",
            status="passed",
            duration_ms=3000,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        session.add(execution)
        session.commit()
        
        # Parent event
        parent = ProfilingEvent(
            execution_id=execution.id,
            event_type="http",
            operation="request",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=1000
        )
        session.add(parent)
        session.commit()
        
        # Child event
        child = ProfilingEvent(
            execution_id=execution.id,
            event_type="database",
            operation="query",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=200,
            parent_event_id=parent.id
        )
        session.add(child)
        session.commit()
        
        assert child.parent_event_id == parent.id


class TestMigrationRecordModel:
    """Test MigrationRecord model"""

    def test_create_migration_record(self, session):
        """Test creating migration record"""
        migration = MigrationRecord(
            migration_id="migration-001",
            migration_type="framework_change",
            source_framework="selenium_java",
            target_framework="robot",
            source_file="/src/LoginTest.java",
            target_file="/tests/login_test.robot",
            transformation_mode="hybrid",
            ai_assisted=True,
            confidence_score=0.85,
            quality_score=0.90,
            validation_passed=True,
            tokens_used=15000,
            cost_usd=0.03,
            model_used="gpt-3.5-turbo",
            status="completed",
            started_at=datetime.utcnow()
        )
        
        session.add(migration)
        session.commit()
        
        assert migration.id is not None
        assert migration.ai_assisted is True
        assert migration.status == "completed"

    def test_migration_with_review(self, session):
        """Test migration record with review information"""
        migration = MigrationRecord(
            migration_id="migration-review-001",
            migration_type="modernization",
            source_framework="pytest",
            target_framework="robot",
            source_file="/tests/test_old.py",
            target_file="/tests/test_new.robot",
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            reviewed_by="test_reviewer",
            approved=True,
            review_comments="Looks good, approved for deployment"
        )
        
        session.add(migration)
        session.commit()
        
        assert migration.reviewed_by == "test_reviewer"
        assert migration.approved is True


class TestSchemaVersionManagement:
    """Test schema version management"""

    def test_verify_schema_version_none(self, session):
        """Test verify_schema_version with no migrations"""
        version = verify_schema_version(session)
        assert version == "0.0.0"

    def test_verify_schema_version_applied(self, session):
        """Test verify_schema_version with applied migration"""
        schema_version = SchemaVersion(
            version="1.0.0",
            description="Initial schema",
            applied=True,
            applied_at=datetime.utcnow()
        )
        session.add(schema_version)
        session.commit()
        
        version = verify_schema_version(session)
        assert version == "1.0.0"

    def test_apply_migration_success(self, session):
        """Test successful migration application"""
        def test_migration(session):
            # Mock migration function
            pass
        
        apply_migration(
            session,
            "1.0.0",
            "Test migration",
            test_migration
        )
        
        # Verify migration recorded
        migration = session.query(SchemaVersion).filter(
            SchemaVersion.version == "1.0.0"
        ).first()
        
        assert migration is not None
        assert migration.applied is True

    def test_apply_migration_already_applied(self, session):
        """Test applying already-applied migration"""
        # Apply first time
        def test_migration(session):
            pass
        
        apply_migration(session, "1.0.0", "Test", test_migration)
        
        # Try to apply again (should skip)
        apply_migration(session, "1.0.0", "Test", test_migration)
        
        # Should only have one record
        count = session.query(SchemaVersion).filter(
            SchemaVersion.version == "1.0.0"
        ).count()
        
        assert count == 1


class TestSchemaIntegrity:
    """Test schema integrity and constraints"""

    def test_foreign_key_constraints(self, session):
        """Test foreign key relationships"""
        # Create test case
        test_case = TestCase(
            name="test_fk",
            file_path="/tests/test.py",
            framework="pytest"
        )
        session.add(test_case)
        session.commit()
        
        # Create related records
        execution = TestExecution(
            test_case_id=test_case.id,
            framework="pytest",
            status="passed",
            duration_ms=1000,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        session.add(execution)
        session.commit()
        
        # Verify relationships work
        assert execution.test_case.name == "test_fk"
        assert test_case.executions[0].status == "passed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
