"""
Database schema for API Change Intelligence
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, TIMESTAMP, Text, Numeric,
    Index, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from persistence.base import Base


class APIChange(Base):
    """API change events table"""
    
    __tablename__ = "api_changes"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Timestamps
    detected_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    
    # Run reference
    run_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Source information
    api_name = Column(String(255), nullable=False)
    api_version = Column(String(50))
    spec_source = Column(String(255))
    
    # Change details
    change_type = Column(String(50), nullable=False)  # added, modified, removed
    entity_type = Column(String(50), nullable=False)  # endpoint, schema, parameter
    entity_name = Column(String(255), nullable=False)
    http_method = Column(String(10))
    path = Column(String(500))
    
    # Classification
    breaking = Column(Boolean, nullable=False, default=False)
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    severity = Column(String(20))  # minor, major, critical
    
    # Change content
    change_details = Column(JSONB, nullable=False, default={})
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    
    # Intelligence
    ai_enhanced = Column(Boolean, nullable=False, default=False)
    ai_model = Column(String(50))
    ai_reasoning = Column(Text)
    
    # Recommendations
    recommended_tests = Column(ARRAY(Text))
    impacted_areas = Column(ARRAY(Text))
    edge_cases = Column(ARRAY(Text))
    
    # Metadata
    created_by = Column(String(100))
    project_id = Column(String(100))
    tags = Column(ARRAY(Text))
    
    # Indexes
    __table_args__ = (
        Index("idx_api_changes_detected_at", "detected_at"),
        Index("idx_api_changes_api_name", "api_name"),
        Index("idx_api_changes_breaking", "breaking"),
        Index("idx_api_changes_risk_level", "risk_level"),
        Index("idx_api_changes_change_type", "change_type"),
        Index("idx_api_changes_run_id", "run_id"),
    )


class APIDiffRun(Base):
    """API diff run execution tracking"""
    
    __tablename__ = "api_diff_runs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Timestamps
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))
    
    # Status
    status = Column(String(20), nullable=False)  # running, completed, failed
    
    # Spec information
    old_spec_source = Column(String(500))
    new_spec_source = Column(String(500))
    old_spec_version = Column(String(50))
    new_spec_version = Column(String(50))
    
    # Results
    total_changes = Column(Integer, nullable=False, default=0)
    breaking_changes = Column(Integer, nullable=False, default=0)
    high_risk_changes = Column(Integer, nullable=False, default=0)
    added_endpoints = Column(Integer, nullable=False, default=0)
    modified_endpoints = Column(Integer, nullable=False, default=0)
    removed_endpoints = Column(Integer, nullable=False, default=0)
    
    # AI usage
    ai_enabled = Column(Boolean, nullable=False, default=False)
    ai_tokens_used = Column(Integer, default=0)
    ai_cost_usd = Column(Numeric(10, 4), default=0)
    
    # Execution details
    duration_ms = Column(Integer)
    error_message = Column(Text)
    
    # Metadata
    project_id = Column(String(100))
    created_by = Column(String(100))
    
    # Indexes
    __table_args__ = (
        Index("idx_api_diff_runs_started_at", "started_at"),
        Index("idx_api_diff_runs_status", "status"),
        Index("idx_api_diff_runs_project", "project_id"),
    )


class APITestCoverage(Base):
    """API to test coverage mapping"""
    
    __tablename__ = "api_test_coverage"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # API reference
    api_name = Column(String(255), nullable=False)
    endpoint_path = Column(String(500), nullable=False)
    http_method = Column(String(10))
    schema_name = Column(String(255))
    
    # Test reference
    test_id = Column(String(255), nullable=False)
    test_name = Column(String(500), nullable=False)
    test_file = Column(String(500))
    test_framework = Column(String(50))
    
    # Coverage type
    coverage_type = Column(String(50))  # direct, indirect, schema-based
    confidence = Column(Numeric(3, 2))  # 0.00 to 1.00
    
    # Metadata
    discovered_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    last_verified = Column(TIMESTAMP(timezone=True))
    source = Column(String(50))  # static, runtime, ai-inferred
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_api_test_coverage_endpoint", "endpoint_path", "http_method"),
        Index("idx_api_test_coverage_test", "test_id"),
        Index("idx_api_test_coverage_api_name", "api_name"),
        UniqueConstraint("api_name", "endpoint_path", "http_method", "test_id", name="uq_api_test_coverage"),
    )


class APIChangeAlert(Base):
    """Alert history for API changes"""
    
    __tablename__ = "api_change_alerts"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Timestamps
    sent_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    
    # Reference
    change_id = Column(Integer, ForeignKey("api_changes.id"))
    run_id = Column(UUID(as_uuid=True))
    
    # Alert details
    alert_type = Column(String(50))  # breaking_change, high_risk, new_endpoint
    channel = Column(String(50))  # email, slack, webhook
    recipient = Column(String(255))
    
    # Status
    status = Column(String(20))  # sent, failed, pending
    error_message = Column(Text)
    
    # Content
    subject = Column(String(500))
    message_body = Column(Text)
    
    # Indexes
    __table_args__ = (
        Index("idx_api_change_alerts_sent_at", "sent_at"),
        Index("idx_api_change_alerts_change_id", "change_id"),
        Index("idx_api_change_alerts_status", "status"),
    )


class AITokenUsage(Base):
    """AI token usage tracking for billing"""
    
    __tablename__ = "ai_token_usage"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Timestamp
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    
    # Run reference
    run_id = Column(UUID(as_uuid=True), ForeignKey("api_diff_runs.id"))
    
    # Usage details
    organization_id = Column(String(100))
    project_id = Column(String(100))
    feature = Column(String(50))  # risk_analysis, test_recommendation, etc.
    
    # Token consumption
    model = Column(String(50), nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(10, 6))
    
    # Rate limiting
    monthly_total = Column(Integer)
    
    # Indexes
    __table_args__ = (
        Index("idx_ai_token_usage_timestamp", "timestamp"),
        Index("idx_ai_token_usage_org_project", "organization_id", "project_id"),
        Index("idx_ai_token_usage_monthly", func.date_trunc('month', "timestamp")),
        Index("idx_ai_token_usage_run_id", "run_id"),
    )
