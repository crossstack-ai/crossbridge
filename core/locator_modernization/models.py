"""
Phase 3 Data Models

Models for AI-assisted locator modernization with risk + confidence scoring.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime


class RiskLevel(Enum):
    """Locator brittleness risk levels"""
    VERY_LOW = "very_low"      # 0.0 - 0.2
    LOW = "low"                # 0.2 - 0.4
    MEDIUM = "medium"          # 0.4 - 0.6
    HIGH = "high"              # 0.6 - 0.8
    VERY_HIGH = "very_high"    # 0.8 - 1.0


class SuggestionStatus(Enum):
    """Status of modernization suggestion"""
    PENDING = "pending"              # Not reviewed
    APPROVED = "approved"            # User approved
    REJECTED = "rejected"            # User rejected
    APPLIED = "applied"              # Code changed
    DEFERRED = "deferred"            # Review later


@dataclass
class RiskScore:
    """
    Risk assessment for a locator
    
    Combines deterministic heuristics with optional AI analysis
    """
    # Heuristic score (always present, deterministic)
    heuristic_score: float  # 0.0 (safe) to 1.0 (very brittle)
    
    # Risk level derived from score
    risk_level: RiskLevel
    
    # Reasons for risk (explainable)
    risk_factors: List[str] = field(default_factory=list)
    
    # Optional AI-enhanced score
    ai_score: Optional[float] = None
    ai_reasoning: Optional[str] = None
    
    # Combined final score
    final_score: float = 0.0
    
    def __post_init__(self):
        """Calculate final score and risk level"""
        if self.ai_score is not None:
            # Weighted average: 60% heuristic, 40% AI
            self.final_score = (0.6 * self.heuristic_score) + (0.4 * self.ai_score)
        else:
            self.final_score = self.heuristic_score
        
        # Derive risk level from final score
        if self.final_score < 0.2:
            self.risk_level = RiskLevel.VERY_LOW
        elif self.final_score < 0.4:
            self.risk_level = RiskLevel.LOW
        elif self.final_score < 0.6:
            self.risk_level = RiskLevel.MEDIUM
        elif self.final_score < 0.8:
            self.risk_level = RiskLevel.HIGH
        else:
            self.risk_level = RiskLevel.VERY_HIGH
    
    def to_dict(self) -> Dict:
        """Export to dict for reporting"""
        return {
            'heuristic_score': round(self.heuristic_score, 3),
            'ai_score': round(self.ai_score, 3) if self.ai_score else None,
            'final_score': round(self.final_score, 3),
            'risk_level': self.risk_level.value,
            'risk_factors': self.risk_factors,
            'ai_reasoning': self.ai_reasoning
        }


@dataclass
class ModernizationSuggestion:
    """
    AI-assisted suggestion for modernizing a locator
    
    CRITICAL: This is a suggestion, NOT an automatic change
    """
    # Original locator info
    locator_name: str
    page_object: str
    current_strategy: str
    current_value: str
    
    # Suggested modernization
    suggested_strategy: str
    suggested_value: str
    
    # Confidence in suggestion (0.0 - 1.0)
    confidence: float
    
    # Explanation (human-readable)
    reason: str
    
    # Source of suggestion
    source: str  # "heuristic" or "ai" or "hybrid"
    
    # Risk assessment
    current_risk: RiskScore
    
    # Usage context
    usage_count: int = 0
    used_in_tests: List[str] = field(default_factory=list)
    
    # Review status
    status: SuggestionStatus = SuggestionStatus.PENDING
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    
    def approve(self, reviewer: str = "user"):
        """Mark suggestion as approved"""
        self.status = SuggestionStatus.APPROVED
        self.reviewed_at = datetime.now()
        self.reviewed_by = reviewer
    
    def reject(self, reviewer: str = "user"):
        """Mark suggestion as rejected"""
        self.status = SuggestionStatus.REJECTED
        self.reviewed_at = datetime.now()
        self.reviewed_by = reviewer
    
    def defer(self):
        """Mark for later review"""
        self.status = SuggestionStatus.DEFERRED
        self.reviewed_at = datetime.now()
    
    def mark_applied(self):
        """Mark as applied to code"""
        self.status = SuggestionStatus.APPLIED
    
    def to_dict(self) -> Dict:
        """Export to dict for reporting"""
        return {
            'locator_name': self.locator_name,
            'page_object': self.page_object,
            'current': {
                'strategy': self.current_strategy,
                'value': self.current_value
            },
            'suggested': {
                'strategy': self.suggested_strategy,
                'value': self.suggested_value
            },
            'confidence': round(self.confidence, 3),
            'reason': self.reason,
            'source': self.source,
            'risk': self.current_risk.to_dict(),
            'usage': {
                'count': self.usage_count,
                'tests': self.used_in_tests
            },
            'status': self.status.value,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by
        }
    
    def format_cli_display(self) -> str:
        """Format for CLI review"""
        risk_emoji = {
            RiskLevel.VERY_LOW: "🟢",
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🔴",
            RiskLevel.VERY_HIGH: "🔴"
        }
        
        lines = []
        lines.append(f"\n{'='*70}")
        lines.append(f"Locator: {self.locator_name} ({self.page_object})")
        lines.append(f"Current: {self.current_strategy}={self.current_value}")
        lines.append(f"Risk: {risk_emoji[self.current_risk.risk_level]} {self.current_risk.risk_level.value.upper()} ({self.current_risk.final_score:.2f})")
        
        if self.current_risk.risk_factors:
            lines.append(f"\nRisk Factors:")
            for factor in self.current_risk.risk_factors:
                lines.append(f"  • {factor}")
        
        lines.append(f"\n💡 Suggested ({self.source}):")
        lines.append(f"   {self.suggested_value}")
        lines.append(f"   Confidence: {self.confidence:.2f}")
        
        lines.append(f"\nReason:")
        lines.append(f"  {self.reason}")
        
        if self.usage_count > 0:
            lines.append(f"\n📊 Usage: {self.usage_count} test(s)")
        
        lines.append(f"\n{'='*70}")
        
        return "\n".join(lines)


@dataclass
class ModernizationRecommendation:
    """
    Complete modernization recommendation for a Page Object
    
    Aggregates all suggestions for a single Page Object
    """
    page_object: str
    file_path: str
    
    # All suggestions for this Page Object
    suggestions: List[ModernizationSuggestion] = field(default_factory=list)
    
    # Statistics
    total_locators: int = 0
    high_risk_locators: int = 0
    medium_risk_locators: int = 0
    low_risk_locators: int = 0
    
    # Overall recommendation
    modernization_priority: str = "low"  # low, medium, high, critical
    
    def add_suggestion(self, suggestion: ModernizationSuggestion):
        """Add a suggestion and update statistics"""
        self.suggestions.append(suggestion)
        
        # Update risk counts
        if suggestion.current_risk.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            self.high_risk_locators += 1
        elif suggestion.current_risk.risk_level == RiskLevel.MEDIUM:
            self.medium_risk_locators += 1
        else:
            self.low_risk_locators += 1
        
        # Update priority
        self._calculate_priority()
    
    def _calculate_priority(self):
        """Calculate modernization priority"""
        if self.high_risk_locators >= 3:
            self.modernization_priority = "critical"
        elif self.high_risk_locators >= 1:
            self.modernization_priority = "high"
        elif self.medium_risk_locators >= 3:
            self.modernization_priority = "medium"
        else:
            self.modernization_priority = "low"
    
    def get_pending_suggestions(self) -> List[ModernizationSuggestion]:
        """Get suggestions awaiting review"""
        return [s for s in self.suggestions if s.status == SuggestionStatus.PENDING]
    
    def get_approved_suggestions(self) -> List[ModernizationSuggestion]:
        """Get approved suggestions ready to apply"""
        return [s for s in self.suggestions if s.status == SuggestionStatus.APPROVED]
    
    def to_dict(self) -> Dict:
        """Export to dict for reporting"""
        return {
            'page_object': self.page_object,
            'file_path': self.file_path,
            'statistics': {
                'total_locators': self.total_locators,
                'high_risk': self.high_risk_locators,
                'medium_risk': self.medium_risk_locators,
                'low_risk': self.low_risk_locators
            },
            'priority': self.modernization_priority,
            'suggestions': [s.to_dict() for s in self.suggestions]
        }
    
    def generate_summary(self) -> str:
        """Generate human-readable summary"""
        lines = []
        lines.append(f"\n{'='*70}")
        lines.append(f"Page Object: {self.page_object}")
        lines.append(f"File: {self.file_path}")
        lines.append(f"\nModernization Priority: {self.modernization_priority.upper()}")
        lines.append(f"\nRisk Distribution:")
        lines.append(f"  🔴 High Risk: {self.high_risk_locators}")
        lines.append(f"  🟡 Medium Risk: {self.medium_risk_locators}")
        lines.append(f"  🟢 Low Risk: {self.low_risk_locators}")
        lines.append(f"\nTotal Suggestions: {len(self.suggestions)}")
        lines.append(f"  Pending: {len(self.get_pending_suggestions())}")
        lines.append(f"  Approved: {len(self.get_approved_suggestions())}")
        lines.append(f"{'='*70}")
        
        return "\n".join(lines)
