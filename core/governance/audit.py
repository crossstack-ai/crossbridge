"""
Audit trail for tracking policy-related actions and decisions.

Maintains a log of policy evaluations, violations, and remediation actions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum
import json


class AuditEventType(Enum):
    """Types of audit events."""
    POLICY_EVALUATED = "policy_evaluated"
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_DELETED = "policy_deleted"
    VIOLATION_DETECTED = "violation_detected"
    VIOLATION_ACKNOWLEDGED = "violation_acknowledged"
    VIOLATION_RESOLVED = "violation_resolved"
    VIOLATION_IGNORED = "violation_ignored"
    COMPLIANCE_CHECK = "compliance_check"
    ENFORCEMENT_ACTION = "enforcement_action"


@dataclass
class AuditEntry:
    """
    Single entry in the audit trail.
    
    Attributes:
        event_type: Type of event
        timestamp: When the event occurred
        actor: Who performed the action (user, system, etc.)
        policy_id: Related policy ID
        details: Additional event details
        severity: Event severity
        outcome: Outcome of the action
    """
    event_type: AuditEventType
    timestamp: datetime = field(default_factory=datetime.now)
    actor: str = "system"
    policy_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    outcome: str = "success"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'actor': self.actor,
            'policy_id': self.policy_id,
            'details': self.details,
            'severity': self.severity,
            'outcome': self.outcome,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEntry':
        """Create entry from dictionary."""
        return cls(
            event_type=AuditEventType(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            actor=data.get('actor', 'system'),
            policy_id=data.get('policy_id'),
            details=data.get('details', {}),
            severity=data.get('severity', 'info'),
            outcome=data.get('outcome', 'success'),
        )


class AuditTrail:
    """
    Audit trail for policy governance.
    
    Maintains a chronological log of all policy-related events.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize audit trail.
        
        Args:
            storage_path: Optional path to persist audit log
        """
        self.entries: List[AuditEntry] = []
        self.storage_path = storage_path
        
        if storage_path and storage_path.exists():
            self._load_from_storage()
    
    def log_event(
        self,
        event_type: AuditEventType,
        actor: str = "system",
        policy_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        outcome: str = "success"
    ) -> AuditEntry:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            actor: Who performed the action
            policy_id: Related policy ID
            details: Additional event details
            severity: Event severity
            outcome: Outcome of the action
            
        Returns:
            Created AuditEntry
        """
        entry = AuditEntry(
            event_type=event_type,
            actor=actor,
            policy_id=policy_id,
            details=details or {},
            severity=severity,
            outcome=outcome,
        )
        
        self.entries.append(entry)
        
        if self.storage_path:
            self._append_to_storage(entry)
        
        return entry
    
    def log_policy_evaluation(
        self,
        policy_id: str,
        result: Any,
        actor: str = "system"
    ) -> AuditEntry:
        """Log a policy evaluation event."""
        return self.log_event(
            event_type=AuditEventType.POLICY_EVALUATED,
            actor=actor,
            policy_id=policy_id,
            details={
                'compliant': result.compliant if hasattr(result, 'compliant') else None,
                'violations_count': len(result.violations) if hasattr(result, 'violations') else 0,
            },
            severity="warning" if not result.compliant else "info"
        )
    
    def log_violation(
        self,
        violation: Any,
        actor: str = "system"
    ) -> AuditEntry:
        """Log a policy violation."""
        return self.log_event(
            event_type=AuditEventType.VIOLATION_DETECTED,
            actor=actor,
            policy_id=violation.policy_id,
            details={
                'rule_id': violation.rule_id,
                'rule_name': violation.rule_name,
                'severity': violation.severity.value if hasattr(violation, 'severity') else 'unknown',
                'description': violation.description,
            },
            severity=violation.severity.value if hasattr(violation, 'severity') else 'warning'
        )
    
    def log_violation_status_change(
        self,
        violation: Any,
        old_status: str,
        new_status: str,
        actor: str = "system"
    ) -> AuditEntry:
        """Log a violation status change."""
        event_type_map = {
            'acknowledged': AuditEventType.VIOLATION_ACKNOWLEDGED,
            'resolved': AuditEventType.VIOLATION_RESOLVED,
            'ignored': AuditEventType.VIOLATION_IGNORED,
        }
        
        event_type = event_type_map.get(new_status, AuditEventType.VIOLATION_DETECTED)
        
        return self.log_event(
            event_type=event_type,
            actor=actor,
            policy_id=violation.policy_id,
            details={
                'rule_id': violation.rule_id,
                'old_status': old_status,
                'new_status': new_status,
            }
        )
    
    def get_entries(
        self,
        policy_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        actor: Optional[str] = None
    ) -> List[AuditEntry]:
        """
        Query audit entries with filters.
        
        Args:
            policy_id: Filter by policy ID
            event_type: Filter by event type
            start_time: Filter entries after this time
            end_time: Filter entries before this time
            actor: Filter by actor
            
        Returns:
            Filtered list of audit entries
        """
        filtered = self.entries
        
        if policy_id:
            filtered = [e for e in filtered if e.policy_id == policy_id]
        
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        
        if actor:
            filtered = [e for e in filtered if e.actor == actor]
        
        return filtered
    
    def get_policy_history(self, policy_id: str) -> List[AuditEntry]:
        """Get all audit entries for a specific policy."""
        return self.get_entries(policy_id=policy_id)
    
    def get_recent_entries(self, count: int = 100) -> List[AuditEntry]:
        """Get most recent audit entries."""
        return sorted(self.entries, key=lambda e: e.timestamp, reverse=True)[:count]
    
    def export_to_json(self, output_path: Path) -> None:
        """
        Export audit trail to JSON file.
        
        Args:
            output_path: Path to save JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'exported_at': datetime.now().isoformat(),
            'total_entries': len(self.entries),
            'entries': [e.to_dict() for e in self.entries]
        }
        
        output_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    def _load_from_storage(self) -> None:
        """Load audit trail from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            data = json.loads(self.storage_path.read_text(encoding='utf-8'))
            self.entries = [AuditEntry.from_dict(e) for e in data.get('entries', [])]
        except Exception:
            # If loading fails, start with empty trail
            self.entries = []
    
    def _append_to_storage(self, entry: AuditEntry) -> None:
        """Append entry to storage file."""
        if not self.storage_path:
            return
        
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # For simplicity, rewrite entire file
        # In production, consider append-only log format
        data = {
            'last_updated': datetime.now().isoformat(),
            'total_entries': len(self.entries),
            'entries': [e.to_dict() for e in self.entries]
        }
        
        self.storage_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    def clear(self) -> None:
        """Clear all audit entries."""
        self.entries.clear()
        if self.storage_path and self.storage_path.exists():
            self.storage_path.unlink()


class AuditLogger:
    """
    Convenient logger for common audit scenarios.
    
    Wraps AuditTrail with simpler interface for common operations.
    """
    
    def __init__(self, audit_trail: AuditTrail):
        """
        Initialize audit logger.
        
        Args:
            audit_trail: AuditTrail instance to use
        """
        self.audit_trail = audit_trail
    
    def log_compliance_check(
        self,
        policies_checked: int,
        violations_found: int,
        compliance_rate: float,
        actor: str = "system"
    ) -> AuditEntry:
        """Log a compliance check event."""
        return self.audit_trail.log_event(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            actor=actor,
            details={
                'policies_checked': policies_checked,
                'violations_found': violations_found,
                'compliance_rate': compliance_rate,
            },
            severity="warning" if violations_found > 0 else "info"
        )
    
    def log_enforcement_action(
        self,
        policy_id: str,
        action: str,
        reason: str,
        actor: str = "system"
    ) -> AuditEntry:
        """Log a policy enforcement action."""
        return self.audit_trail.log_event(
            event_type=AuditEventType.ENFORCEMENT_ACTION,
            actor=actor,
            policy_id=policy_id,
            details={
                'action': action,
                'reason': reason,
            },
            severity="warning"
        )
