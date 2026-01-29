"""
Repository for API Change Intelligence data access
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid

from .schema import APIChange, APIDiffRun, APITestCoverage, APIChangeAlert, AITokenUsage
from ..models.api_change import APIChangeEvent, DiffResult, ChangeType, EntityType, RiskLevel


class APIChangeRepository:
    """Data access layer for API Change Intelligence"""
    
    def __init__(self, session: Session):
        self.session = session
    
    # ===== Diff Run Management =====
    
    def create_diff_run(self, result: DiffResult) -> str:
        """Create a new diff run record"""
        run = APIDiffRun(
            id=uuid.UUID(result.run_id),
            started_at=result.started_at,
            completed_at=result.completed_at,
            status=result.status,
            old_spec_source=result.old_spec_source,
            new_spec_source=result.new_spec_source,
            old_spec_version=result.old_spec_version,
            new_spec_version=result.new_spec_version,
            total_changes=result.total_changes,
            breaking_changes=result.breaking_changes,
            high_risk_changes=result.high_risk_changes,
            added_endpoints=result.added_endpoints,
            modified_endpoints=result.modified_endpoints,
            removed_endpoints=result.removed_endpoints,
            ai_enabled=result.ai_enabled,
            ai_tokens_used=result.ai_tokens_used,
            ai_cost_usd=result.ai_cost_usd,
            duration_ms=result.duration_ms,
            error_message=result.error_message,
        )
        
        self.session.add(run)
        self.session.commit()
        
        return str(run.id)
    
    def update_diff_run(self, run_id: str, **kwargs):
        """Update diff run record"""
        run = self.session.query(APIDiffRun).filter_by(id=uuid.UUID(run_id)).first()
        if run:
            for key, value in kwargs.items():
                if hasattr(run, key):
                    setattr(run, key, value)
            self.session.commit()
    
    def get_diff_run(self, run_id: str) -> Optional[APIDiffRun]:
        """Get diff run by ID"""
        return self.session.query(APIDiffRun).filter_by(id=uuid.UUID(run_id)).first()
    
    # ===== API Change Management =====
    
    def save_changes(self, changes: List[APIChangeEvent], run_id: str):
        """Batch save API changes"""
        change_records = []
        
        for change in changes:
            record = APIChange(
                detected_at=change.detected_at,
                run_id=uuid.UUID(run_id),
                api_name=change.api_name,
                api_version=change.api_version,
                spec_source=change.spec_source,
                change_type=change.change_type.value,
                entity_type=change.entity_type.value,
                entity_name=change.entity_name,
                http_method=change.http_method,
                path=change.path,
                breaking=change.breaking,
                risk_level=change.risk_level.value,
                severity=change.severity.value if change.severity else None,
                change_details=change.change_details,
                old_value=change.old_value,
                new_value=change.new_value,
                ai_enhanced=change.ai_enhanced,
                ai_model=change.ai_model,
                ai_reasoning=change.ai_reasoning,
                recommended_tests=change.recommended_tests,
                impacted_areas=change.impacted_areas,
                edge_cases=change.edge_cases,
                tags=change.tags,
            )
            change_records.append(record)
        
        self.session.bulk_save_objects(change_records)
        self.session.commit()
    
    def get_changes_by_run(self, run_id: str) -> List[APIChange]:
        """Get all changes for a specific run"""
        return self.session.query(APIChange).filter_by(run_id=uuid.UUID(run_id)).all()
    
    def get_recent_changes(
        self,
        days: int = 7,
        breaking_only: bool = False,
        min_risk: Optional[str] = None
    ) -> List[APIChange]:
        """Get recent API changes with filters"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = self.session.query(APIChange).filter(APIChange.detected_at >= cutoff)
        
        if breaking_only:
            query = query.filter(APIChange.breaking == True)
        
        if min_risk:
            risk_levels = ["low", "medium", "high", "critical"]
            min_index = risk_levels.index(min_risk)
            allowed_risks = risk_levels[min_index:]
            query = query.filter(APIChange.risk_level.in_(allowed_risks))
        
        return query.order_by(APIChange.detected_at.desc()).all()
    
    def get_changes_by_api(self, api_name: str, limit: int = 100) -> List[APIChange]:
        """Get changes for a specific API"""
        return (
            self.session.query(APIChange)
            .filter_by(api_name=api_name)
            .order_by(APIChange.detected_at.desc())
            .limit(limit)
            .all()
        )
    
    def get_breaking_changes_count(self, days: int = 30) -> int:
        """Count breaking changes in time period"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            self.session.query(func.count(APIChange.id))
            .filter(APIChange.detected_at >= cutoff, APIChange.breaking == True)
            .scalar()
        )
    
    # ===== Test Coverage Management =====
    
    def save_test_coverage(self, coverage: APITestCoverage):
        """Save test coverage mapping"""
        # Check if already exists
        existing = (
            self.session.query(APITestCoverage)
            .filter_by(
                api_name=coverage.api_name,
                endpoint_path=coverage.endpoint_path,
                http_method=coverage.http_method,
                test_id=coverage.test_id,
            )
            .first()
        )
        
        if existing:
            # Update existing
            existing.confidence = coverage.confidence
            existing.last_verified = datetime.utcnow()
        else:
            # Create new
            self.session.add(coverage)
        
        self.session.commit()
    
    def get_tests_for_endpoint(
        self,
        endpoint_path: str,
        http_method: Optional[str] = None
    ) -> List[APITestCoverage]:
        """Get all tests covering an endpoint"""
        query = self.session.query(APITestCoverage).filter_by(endpoint_path=endpoint_path)
        
        if http_method:
            query = query.filter_by(http_method=http_method)
        
        return query.all()
    
    def get_tests_for_schema(self, schema_name: str) -> List[APITestCoverage]:
        """Get all tests using a schema"""
        return self.session.query(APITestCoverage).filter_by(schema_name=schema_name).all()
    
    def get_coverage_for_test(self, test_id: str) -> List[APITestCoverage]:
        """Get all API coverage for a test"""
        return self.session.query(APITestCoverage).filter_by(test_id=test_id).all()
    
    # ===== Alert Management =====
    
    def save_alert(
        self,
        change_id: int,
        run_id: str,
        alert_type: str,
        channel: str,
        recipient: str,
        status: str,
        subject: str = "",
        message_body: str = "",
        error_message: Optional[str] = None
    ) -> int:
        """Save alert record"""
        alert = APIChangeAlert(
            sent_at=datetime.utcnow(),
            change_id=change_id,
            run_id=uuid.UUID(run_id),
            alert_type=alert_type,
            channel=channel,
            recipient=recipient,
            status=status,
            subject=subject,
            message_body=message_body,
            error_message=error_message,
        )
        
        self.session.add(alert)
        self.session.commit()
        
        return alert.id
    
    def get_alerts_by_run(self, run_id: str) -> List[APIChangeAlert]:
        """Get all alerts for a run"""
        return self.session.query(APIChangeAlert).filter_by(run_id=uuid.UUID(run_id)).all()
    
    # ===== AI Token Usage =====
    
    def track_ai_usage(
        self,
        run_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        feature: str = "api_diff",
        organization_id: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        """Track AI token usage"""
        usage = AITokenUsage(
            timestamp=datetime.utcnow(),
            run_id=uuid.UUID(run_id),
            organization_id=organization_id,
            project_id=project_id,
            feature=feature,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost_usd,
        )
        
        self.session.add(usage)
        self.session.commit()
    
    def get_monthly_token_usage(
        self,
        organization_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current month's token usage"""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        query = self.session.query(
            func.sum(AITokenUsage.total_tokens).label("total_tokens"),
            func.sum(AITokenUsage.cost_usd).label("total_cost"),
            func.count(AITokenUsage.id).label("request_count")
        ).filter(AITokenUsage.timestamp >= start_of_month)
        
        if organization_id:
            query = query.filter(AITokenUsage.organization_id == organization_id)
        if project_id:
            query = query.filter(AITokenUsage.project_id == project_id)
        
        result = query.first()
        
        return {
            "total_tokens": result.total_tokens or 0,
            "total_cost_usd": float(result.total_cost or 0),
            "request_count": result.request_count or 0,
            "period_start": start_of_month.isoformat(),
        }
    
    # ===== Statistics & Analytics =====
    
    def get_change_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive change statistics"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        total = self.session.query(func.count(APIChange.id)).filter(
            APIChange.detected_at >= cutoff
        ).scalar()
        
        breaking = self.session.query(func.count(APIChange.id)).filter(
            APIChange.detected_at >= cutoff,
            APIChange.breaking == True
        ).scalar()
        
        high_risk = self.session.query(func.count(APIChange.id)).filter(
            APIChange.detected_at >= cutoff,
            APIChange.risk_level.in_(["high", "critical"])
        ).scalar()
        
        ai_enhanced = self.session.query(func.count(APIChange.id)).filter(
            APIChange.detected_at >= cutoff,
            APIChange.ai_enhanced == True
        ).scalar()
        
        # By type
        by_type = (
            self.session.query(APIChange.change_type, func.count(APIChange.id))
            .filter(APIChange.detected_at >= cutoff)
            .group_by(APIChange.change_type)
            .all()
        )
        
        # By risk level
        by_risk = (
            self.session.query(APIChange.risk_level, func.count(APIChange.id))
            .filter(APIChange.detected_at >= cutoff)
            .group_by(APIChange.risk_level)
            .all()
        )
        
        return {
            "period_days": days,
            "total_changes": total or 0,
            "breaking_changes": breaking or 0,
            "high_risk_changes": high_risk or 0,
            "ai_enhanced_changes": ai_enhanced or 0,
            "by_type": dict(by_type),
            "by_risk": dict(by_risk),
        }
