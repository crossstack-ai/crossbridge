"""
Unit tests for database models and persistence layer.

Tests CRUD operations, queries, and unified model format.
"""

import pytest
from datetime import datetime
from adapters.common.impact_models import MappingSource

# Check if SQLAlchemy is available
try:
    from adapters.common.db_models import (
        DatabaseManager, PageObjectModel, TestCaseModel, 
        TestPageMappingModel, SQLALCHEMY_AVAILABLE
    )
    SKIP_DB_TESTS = not SQLALCHEMY_AVAILABLE
    SKIP_REASON = "SQLAlchemy not installed"
except ImportError:
    SKIP_DB_TESTS = True
    SKIP_REASON = "db_models module not available"


@pytest.mark.skipif(SKIP_DB_TESTS, reason=SKIP_REASON)
class TestDatabaseModels:
    """Test SQLAlchemy ORM models."""
    
    @pytest.fixture
    def db_manager(self):
        """Create in-memory SQLite database for testing."""
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        return db
    
    def test_create_page_object(self, db_manager):
        """Test creating a Page Object entity."""
        with db_manager.get_session() as session:
            po = db_manager.add_page_object(
                session,
                name="LoginPage",
                file_path="src/pages/LoginPage.java",
                framework="selenium-java-junit",
                package="com.example.pages",
                base_class="BasePage"
            )
            
            assert po.name == "LoginPage"
            assert po.file_path == "src/pages/LoginPage.java"
            assert po.framework == "selenium-java-junit"
            assert po.package == "com.example.pages"
            assert po.base_class == "BasePage"
            assert po.id is not None
    
    def test_create_test_case(self, db_manager):
        """Test creating a test case entity."""
        with db_manager.get_session() as session:
            test = db_manager.add_test_case(
                session,
                test_id="LoginTest.testValidLogin",
                file_path="src/test/java/LoginTest.java",
                framework="selenium-java-junit",
                class_name="LoginTest",
                method_name="testValidLogin"
            )
            
            assert test.test_id == "LoginTest.testValidLogin"
            assert test.file_path == "src/test/java/LoginTest.java"
            assert test.class_name == "LoginTest"
            assert test.method_name == "testValidLogin"
            assert test.id is not None
    
    def test_create_mapping(self, db_manager):
        """Test creating a test-to-page-object mapping."""
        with db_manager.get_session() as session:
            # Create Page Object
            po = db_manager.add_page_object(
                session,
                name="LoginPage",
                file_path="src/pages/LoginPage.java",
                framework="selenium-java-junit"
            )
            
            # Create Test
            test = db_manager.add_test_case(
                session,
                test_id="LoginTest.testValidLogin",
                file_path="src/test/java/LoginTest.java",
                framework="selenium-java-junit"
            )
            
            # Create Mapping
            mapping = db_manager.add_mapping(
                session,
                test_case_id=test.id,
                page_object_id=po.id,
                source="static_ast",
                confidence=0.85,
                usage_type="instantiation",
                line_number="15,27"
            )
            
            assert mapping.source == "static_ast"
            assert mapping.confidence == 0.85
            assert mapping.usage_type == "instantiation"
            assert mapping.line_number == "15,27"
    
    def test_update_existing_page_object(self, db_manager):
        """Test updating an existing Page Object."""
        with db_manager.get_session() as session:
            # Create
            po1 = db_manager.add_page_object(
                session,
                name="LoginPage",
                file_path="src/pages/LoginPage.java",
                framework="selenium-java-junit"
            )
            po1_id = po1.id
            
            # Update
            po2 = db_manager.add_page_object(
                session,
                name="LoginPage",
                file_path="src/pages/LoginPage.java",
                framework="selenium-java-junit",
                package="com.example.pages"
            )
            
            # Should be same entity
            assert po2.id == po1_id
            assert po2.package == "com.example.pages"
    
    def test_update_mapping_confidence(self, db_manager):
        """Test that mapping confidence is updated to max value."""
        with db_manager.get_session() as session:
            po = db_manager.add_page_object(
                session, "LoginPage", "src/pages/LoginPage.java",
                "selenium-java-junit"
            )
            test = db_manager.add_test_case(
                session, "LoginTest.testValidLogin",
                "src/test/java/LoginTest.java", "selenium-java-junit"
            )
            
            # First mapping with confidence 0.7
            m1 = db_manager.add_mapping(
                session, test.id, po.id, "static_ast", 0.7
            )
            
            # Second mapping with confidence 0.9 (should update to max)
            m2 = db_manager.add_mapping(
                session, test.id, po.id, "static_ast", 0.9
            )
            
            assert m1.id == m2.id
            assert m2.confidence == 0.9


@pytest.mark.skipif(SKIP_DB_TESTS, reason=SKIP_REASON)
class TestDatabaseQueries:
    """Test database query operations."""
    
    @pytest.fixture
    def populated_db(self):
        """Create database with sample data."""
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        
        with db.get_session() as session:
            # Create Page Objects
            login_po = db.add_page_object(
                session, "LoginPage", "src/pages/LoginPage.java",
                "selenium-java-junit"
            )
            home_po = db.add_page_object(
                session, "HomePage", "src/pages/HomePage.java",
                "selenium-java-junit"
            )
            
            # Create Tests
            test1 = db.add_test_case(
                session, "LoginTest.testValidLogin",
                "src/test/java/LoginTest.java", "selenium-java-junit"
            )
            test2 = db.add_test_case(
                session, "LoginTest.testInvalidLogin",
                "src/test/java/LoginTest.java", "selenium-java-junit"
            )
            test3 = db.add_test_case(
                session, "HomeTest.testNavigation",
                "src/test/java/HomeTest.java", "selenium-java-junit"
            )
            
            # Create Mappings
            db.add_mapping(session, test1.id, login_po.id, "static_ast", 0.85)
            db.add_mapping(session, test2.id, login_po.id, "static_ast", 0.92)
            db.add_mapping(session, test3.id, home_po.id, "static_ast", 0.78)
            db.add_mapping(session, test3.id, login_po.id, "coverage", 0.65)
        
        return db
    
    def test_get_impacted_tests(self, populated_db):
        """Test querying impacted tests for a Page Object."""
        with populated_db.get_session() as session:
            # LoginPage should impact 2 tests
            impacted = populated_db.get_impacted_tests(
                session, "LoginPage", min_confidence=0.5
            )
            
            assert len(impacted) == 3  # 2 from static_ast + 1 from coverage
            test_ids = [m["test_id"] for m in impacted]
            assert "LoginTest.testValidLogin" in test_ids
            assert "LoginTest.testInvalidLogin" in test_ids
            assert "HomeTest.testNavigation" in test_ids
    
    def test_get_impacted_tests_with_min_confidence(self, populated_db):
        """Test confidence filtering in impact queries."""
        with populated_db.get_session() as session:
            # High confidence threshold
            impacted = populated_db.get_impacted_tests(
                session, "LoginPage", min_confidence=0.8
            )
            
            # Should only get high confidence mappings
            assert len(impacted) == 2
            for m in impacted:
                assert m["confidence"] >= 0.8
    
    def test_get_page_objects_for_test(self, populated_db):
        """Test querying Page Objects used by a test."""
        with populated_db.get_session() as session:
            # HomeTest uses both HomePage and LoginPage
            pos = populated_db.get_page_objects_for_test(
                session, "HomeTest.testNavigation", min_confidence=0.5
            )
            
            assert len(pos) == 2
            po_names = [m["page_object"] for m in pos]
            assert "HomePage" in po_names
            assert "LoginPage" in po_names
    
    def test_get_mappings_by_source(self, populated_db):
        """Test querying mappings by source type."""
        with populated_db.get_session() as session:
            # Get static_ast mappings
            static_mappings = populated_db.get_mappings_by_source(
                session, "static_ast"
            )
            assert len(static_mappings) == 3
            
            # Get coverage mappings
            coverage_mappings = populated_db.get_mappings_by_source(
                session, "coverage"
            )
            assert len(coverage_mappings) == 1
    
    def test_get_statistics(self, populated_db):
        """Test database statistics query."""
        with populated_db.get_session() as session:
            stats = populated_db.get_statistics(session)
            
            assert stats["total_page_objects"] == 2
            assert stats["total_tests"] == 3
            assert stats["total_mappings"] == 4
            assert "mappings_by_source" in stats


@pytest.mark.skipif(SKIP_DB_TESTS, reason=SKIP_REASON)
class TestUnifiedModelFormat:
    """Test unified data model format conversions."""
    
    @pytest.fixture
    def db_with_mapping(self):
        """Create database with a single mapping."""
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        
        with db.get_session() as session:
            po = db.add_page_object(
                session, "LoginPage", "src/pages/LoginPage.java",
                "selenium-java-junit"
            )
            test = db.add_test_case(
                session, "LoginTest.testValidLogin",
                "src/test/java/LoginTest.java", "selenium-java-junit"
            )
            db.add_mapping(
                session, test.id, po.id, "static_ast", 0.85
            )
        
        return db
    
    def test_unified_model_format(self, db_with_mapping):
        """Test conversion to unified model format."""
        with db_with_mapping.get_session() as session:
            impacted = db_with_mapping.get_impacted_tests(
                session, "LoginPage"
            )
            
            assert len(impacted) == 1
            unified = impacted[0]
            
            # Verify unified format
            assert "test_id" in unified
            assert "page_object" in unified
            assert "source" in unified
            assert "confidence" in unified
            
            assert unified["test_id"] == "LoginTest.testValidLogin"
            assert unified["page_object"] == "LoginPage"
            assert unified["source"] == "static_ast"
            assert unified["confidence"] == 0.85
    
    def test_model_to_dict(self, db_with_mapping):
        """Test model to_dict() conversion."""
        with db_with_mapping.get_session() as session:
            po = session.query(PageObjectModel).first()
            po_dict = po.to_dict()
            
            assert "id" in po_dict
            assert "name" in po_dict
            assert "file_path" in po_dict
            assert po_dict["name"] == "LoginPage"
    
    def test_mapping_to_unified_model(self, db_with_mapping):
        """Test mapping to_unified_model() conversion."""
        with db_with_mapping.get_session() as session:
            mapping = session.query(TestPageMappingModel).first()
            unified = mapping.to_unified_model()
            
            # Should have exactly 4 fields
            assert len(unified) == 4
            assert set(unified.keys()) == {
                "test_id", "page_object", "source", "confidence"
            }


@pytest.mark.skipif(SKIP_DB_TESTS, reason=SKIP_REASON)
class TestMultiPhaseSupport:
    """Test multi-phase mapping support."""
    
    def test_multiple_sources_for_same_mapping(self):
        """Test storing same mapping from different sources."""
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        
        with db.get_session() as session:
            po = db.add_page_object(
                session, "LoginPage", "src/pages/LoginPage.java",
                "selenium-java-junit"
            )
            test = db.add_test_case(
                session, "LoginTest.testValidLogin",
                "src/test/java/LoginTest.java", "selenium-java-junit"
            )
            
            # Phase 1: Static AST
            m1 = db.add_mapping(
                session, test.id, po.id, "static_ast", 0.85
            )
            
            # Phase 2: Code Coverage
            m2 = db.add_mapping(
                session, test.id, po.id, "coverage", 0.95
            )
            
            # Phase 3: AI
            m3 = db.add_mapping(
                session, test.id, po.id, "ai", 0.72
            )
            
            # Should have 3 separate mappings
            mappings = session.query(TestPageMappingModel).all()
            assert len(mappings) == 3
            
            sources = [m.source for m in mappings]
            assert "static_ast" in sources
            assert "coverage" in sources
            assert "ai" in sources
    
    def test_query_by_source_phase(self):
        """Test querying mappings by phase/source."""
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        
        with db.get_session() as session:
            po = db.add_page_object(
                session, "LoginPage", "src/pages/LoginPage.java",
                "selenium-java-junit"
            )
            test = db.add_test_case(
                session, "LoginTest.testValidLogin",
                "src/test/java/LoginTest.java", "selenium-java-junit"
            )
            
            db.add_mapping(session, test.id, po.id, "static_ast", 0.85)
            db.add_mapping(session, test.id, po.id, "coverage", 0.95)
            db.add_mapping(session, test.id, po.id, "ai", 0.72)
            
            # Query by source
            static_mappings = db.get_mappings_by_source(session, "static_ast")
            assert len(static_mappings) == 1
            assert static_mappings[0]["source"] == "static_ast"
            
            coverage_mappings = db.get_mappings_by_source(session, "coverage")
            assert len(coverage_mappings) == 1
            assert coverage_mappings[0]["confidence"] == 0.95


def test_missing_sqlalchemy():
    """Test graceful handling when SQLAlchemy is not installed."""
    # This test verifies the module can be imported even without SQLAlchemy
    from adapters.common import db_models
    
    if not db_models.SQLALCHEMY_AVAILABLE:
        with pytest.raises(ImportError, match="SQLAlchemy is required"):
            DatabaseManager("postgresql://localhost/test")
