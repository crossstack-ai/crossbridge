"""
Database models for persisting test and Page Object mappings.

Supports PostgreSQL with SQLAlchemy ORM for multi-phase mapping storage
(static AST, code coverage, AI-based mappings).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

try:
    from sqlalchemy import (
        Column, String, Float, DateTime, ForeignKey, Text, create_engine
    )
    from sqlalchemy.dialects.postgresql import UUID as PGUUID
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import relationship, sessionmaker, Session
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = object


class MappingSource(str, Enum):
    """Source of test-to-page-object mapping."""
    STATIC_AST = "static_ast"
    COVERAGE = "coverage"
    AI = "ai"
    RUNTIME_TRACE = "runtime_trace"
    MANUAL = "manual"


if SQLALCHEMY_AVAILABLE:
    class PageObjectModel(Base):
        """
        Page Object entity.
        
        Represents a Page Object class in the codebase.
        """
        __tablename__ = "page_object"
        
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
        name = Column(Text, nullable=False, index=True)
        file_path = Column(Text, nullable=False)
        framework = Column(Text, nullable=False, index=True)  # pytest, selenium-java-junit, etc.
        package = Column(Text)  # e.g., "com.example.pages" or "pages.login"
        base_class = Column(Text)  # e.g., "BasePage"
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Relationships
        mappings = relationship("TestPageMappingModel", back_populates="page_object")
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary."""
            return {
                "id": str(self.id),
                "name": self.name,
                "file_path": self.file_path,
                "framework": self.framework,
                "package": self.package,
                "base_class": self.base_class,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            }
    
    
    class TestCaseModel(Base):
        """
        Test case entity.
        
        Represents a test method/function in the test suite.
        """
        __tablename__ = "test_case"
        
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
        test_id = Column(Text, nullable=False, unique=True, index=True)
        file_path = Column(Text, nullable=False)
        framework = Column(Text, nullable=False, index=True)
        class_name = Column(Text)  # For class-based tests
        method_name = Column(Text)  # Test method name
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Relationships
        mappings = relationship("TestPageMappingModel", back_populates="test_case")
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary."""
            return {
                "id": str(self.id),
                "test_id": self.test_id,
                "file_path": self.file_path,
                "framework": self.framework,
                "class_name": self.class_name,
                "method_name": self.method_name,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            }
    
    
    class TestPageMappingModel(Base):
        """
        Test-to-Page-Object mapping.
        
        Unified model supporting multiple mapping sources (static AST, coverage, AI).
        """
        __tablename__ = "test_page_mapping"
        
        id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
        test_case_id = Column(PGUUID(as_uuid=True), ForeignKey("test_case.id"), nullable=False, index=True)
        page_object_id = Column(PGUUID(as_uuid=True), ForeignKey("page_object.id"), nullable=False, index=True)
        source = Column(Text, nullable=False, index=True)  # static_ast, coverage, ai, etc.
        confidence = Column(Float, nullable=False, default=1.0)
        observed_at = Column(DateTime, default=datetime.utcnow, index=True)
        
        # Optional metadata
        usage_type = Column(Text)  # import, instantiation, method_call, fixture, etc.
        line_number = Column(Text)  # Line numbers where usage occurs
        
        # Relationships
        test_case = relationship("TestCaseModel", back_populates="mappings")
        page_object = relationship("PageObjectModel", back_populates="mappings")
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary for unified model."""
            return {
                "id": str(self.id),
                "test_id": self.test_case.test_id if self.test_case else None,
                "page_object": self.page_object.name if self.page_object else None,
                "source": self.source,
                "confidence": self.confidence,
                "observed_at": self.observed_at.isoformat() if self.observed_at else None,
                "usage_type": self.usage_type,
                "line_number": self.line_number
            }
        
        def to_unified_model(self) -> Dict[str, Any]:
            """Convert to unified data model format."""
            return {
                "test_id": self.test_case.test_id if self.test_case else None,
                "page_object": self.page_object.name if self.page_object else None,
                "source": self.source,
                "confidence": self.confidence
            }


class DatabaseManager:
    """
    Database manager for Page Object mapping persistence.
    
    Handles connection, session management, and CRUD operations.
    """
    
    def __init__(self, connection_string: str):
        """
        Initialize database manager.
        
        Args:
            connection_string: PostgreSQL connection string
                              e.g., "postgresql://user:pass@localhost:5432/crossbridge"
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy is required for database persistence. "
                            "Install with: pip install sqlalchemy psycopg2-binary")
        
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def add_page_object(self, session: Session, name: str, file_path: str, 
                       framework: str, package: Optional[str] = None,
                       base_class: Optional[str] = None) -> PageObjectModel:
        """Add or update a Page Object."""
        # Check if exists
        po = session.query(PageObjectModel).filter_by(
            name=name, file_path=file_path
        ).first()
        
        if po:
            # Update
            po.framework = framework
            po.package = package
            po.base_class = base_class
            po.updated_at = datetime.utcnow()
        else:
            # Create
            po = PageObjectModel(
                name=name,
                file_path=file_path,
                framework=framework,
                package=package,
                base_class=base_class
            )
            session.add(po)
        
        session.commit()
        return po
    
    def add_test_case(self, session: Session, test_id: str, file_path: str,
                     framework: str, class_name: Optional[str] = None,
                     method_name: Optional[str] = None) -> TestCaseModel:
        """Add or update a test case."""
        # Check if exists
        test = session.query(TestCaseModel).filter_by(test_id=test_id).first()
        
        if test:
            # Update
            test.file_path = file_path
            test.framework = framework
            test.class_name = class_name
            test.method_name = method_name
            test.updated_at = datetime.utcnow()
        else:
            # Create
            test = TestCaseModel(
                test_id=test_id,
                file_path=file_path,
                framework=framework,
                class_name=class_name,
                method_name=method_name
            )
            session.add(test)
        
        session.commit()
        return test
    
    def add_mapping(self, session: Session, test_case_id: UUID, 
                   page_object_id: UUID, source: str, confidence: float,
                   usage_type: Optional[str] = None,
                   line_number: Optional[str] = None) -> TestPageMappingModel:
        """Add a test-to-page-object mapping."""
        # Check if exists
        mapping = session.query(TestPageMappingModel).filter_by(
            test_case_id=test_case_id,
            page_object_id=page_object_id,
            source=source
        ).first()
        
        if mapping:
            # Update confidence (take max)
            mapping.confidence = max(mapping.confidence, confidence)
            mapping.observed_at = datetime.utcnow()
            if usage_type:
                mapping.usage_type = usage_type
            if line_number:
                mapping.line_number = line_number
        else:
            # Create
            mapping = TestPageMappingModel(
                test_case_id=test_case_id,
                page_object_id=page_object_id,
                source=source,
                confidence=confidence,
                usage_type=usage_type,
                line_number=line_number
            )
            session.add(mapping)
        
        session.commit()
        return mapping
    
    def get_impacted_tests(self, session: Session, page_object_name: str,
                          min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get tests impacted by a Page Object change.
        
        Args:
            session: Database session
            page_object_name: Name of the Page Object
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of test mappings in unified format
        """
        mappings = (
            session.query(TestPageMappingModel)
            .join(PageObjectModel)
            .join(TestCaseModel)
            .filter(
                PageObjectModel.name == page_object_name,
                TestPageMappingModel.confidence >= min_confidence
            )
            .all()
        )
        
        return [m.to_unified_model() for m in mappings]
    
    def get_page_objects_for_test(self, session: Session, test_id: str,
                                  min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get Page Objects used by a test.
        
        Args:
            session: Database session
            test_id: Test identifier
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of mappings in unified format
        """
        mappings = (
            session.query(TestPageMappingModel)
            .join(TestCaseModel)
            .join(PageObjectModel)
            .filter(
                TestCaseModel.test_id == test_id,
                TestPageMappingModel.confidence >= min_confidence
            )
            .all()
        )
        
        return [m.to_unified_model() for m in mappings]
    
    def get_mappings_by_source(self, session: Session, source: str) -> List[Dict[str, Any]]:
        """Get all mappings from a specific source."""
        mappings = (
            session.query(TestPageMappingModel)
            .filter(TestPageMappingModel.source == source)
            .all()
        )
        
        return [m.to_dict() for m in mappings]
    
    def get_statistics(self, session: Session) -> Dict[str, Any]:
        """Get mapping statistics."""
        return {
            "total_page_objects": session.query(PageObjectModel).count(),
            "total_tests": session.query(TestCaseModel).count(),
            "total_mappings": session.query(TestPageMappingModel).count(),
            "mappings_by_source": {
                source: session.query(TestPageMappingModel)
                       .filter_by(source=source)
                       .count()
                for source in MappingSource
            }
        }


# SQL Schema for manual creation
SQL_SCHEMA = """
-- Page Object entity
CREATE TABLE IF NOT EXISTS page_object (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    framework TEXT NOT NULL,
    package TEXT,
    base_class TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_page_object_name ON page_object(name);
CREATE INDEX idx_page_object_framework ON page_object(framework);

-- Test Case entity
CREATE TABLE IF NOT EXISTS test_case (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    framework TEXT NOT NULL,
    class_name TEXT,
    method_name TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_test_case_test_id ON test_case(test_id);
CREATE INDEX idx_test_case_framework ON test_case(framework);

-- Test-to-Page-Object mapping
CREATE TABLE IF NOT EXISTS test_page_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id UUID NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    page_object_id UUID NOT NULL REFERENCES page_object(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0,
    observed_at TIMESTAMP DEFAULT now(),
    usage_type TEXT,
    line_number TEXT
);

CREATE INDEX idx_mapping_test ON test_page_mapping(test_case_id);
CREATE INDEX idx_mapping_page_object ON test_page_mapping(page_object_id);
CREATE INDEX idx_mapping_source ON test_page_mapping(source);
CREATE INDEX idx_mapping_observed ON test_page_mapping(observed_at);

-- Unique constraint: one mapping per test-page-source combination
CREATE UNIQUE INDEX idx_mapping_unique ON test_page_mapping(test_case_id, page_object_id, source);
"""


def export_sql_schema(output_file: str = "schema.sql"):
    """Export SQL schema to a file."""
    with open(output_file, "w") as f:
        f.write(SQL_SCHEMA)
    print(f"SQL schema exported to {output_file}")


# Example usage
if __name__ == "__main__":
    # Example: Create database manager
    db = DatabaseManager("postgresql://user:password@localhost:5432/crossbridge")
    
    # Create tables
    db.create_tables()
    
    # Add data
    with db.get_session() as session:
        # Add Page Object
        po = db.add_page_object(
            session,
            name="LoginPage",
            file_path="src/pages/LoginPage.java",
            framework="selenium-java-junit",
            package="com.example.pages",
            base_class="BasePage"
        )
        
        # Add Test
        test = db.add_test_case(
            session,
            test_id="LoginTest.testValidLogin",
            file_path="src/test/java/LoginTest.java",
            framework="selenium-java-junit",
            class_name="LoginTest",
            method_name="testValidLogin"
        )
        
        # Add mapping
        mapping = db.add_mapping(
            session,
            test_case_id=test.id,
            page_object_id=po.id,
            source="static_ast",
            confidence=0.85,
            usage_type="instantiation",
            line_number="15,27"
        )
        
        # Query impacted tests
        impacted = db.get_impacted_tests(session, "LoginPage", min_confidence=0.5)
        print("Impacted tests:", impacted)
        
        # Get statistics
        stats = db.get_statistics(session)
        print("Statistics:", stats)
