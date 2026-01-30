"""
Rule Models

Data models for rule-based classification.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class FailureType(Enum):
    """Standard failure types"""
    PRODUCT_DEFECT = "PRODUCT_DEFECT"
    AUTOMATION_DEFECT = "AUTOMATION_DEFECT"
    ENVIRONMENT_ISSUE = "ENVIRONMENT_ISSUE"
    CONFIGURATION_ISSUE = "CONFIGURATION_ISSUE"


@dataclass
class Rule:
    """
    Classification rule that matches against failure signals.
    
    Rules are pattern-based and provide confidence scores for matches.
    """
    
    id: str                              # Unique rule ID (e.g., "SEL_001")
    match_any: List[str]                # Keywords to match (OR logic)
    failure_type: str                   # Failure classification
    confidence: float                    # Confidence if rule matches (0.0-1.0)
    priority: int = 100                  # Lower = higher priority
    description: str = ""               # Human-readable description
    framework: Optional[str] = None     # Framework this rule applies to (None = all)
    requires_all: List[str] = field(default_factory=list)  # Keywords that must ALL be present
    excludes: List[str] = field(default_factory=list)      # If present, rule doesn't match
    
    def matches(self, message: str) -> bool:
        """
        Check if this rule matches a failure message.
        
        Args:
            message: Failure message to check
            
        Returns:
            True if rule matches
        """
        # Handle different signal formats
        if isinstance(message, str):
            message_lower = message.lower()
        elif isinstance(message, list):
            messages = []
            for s in message:
                if isinstance(s, dict):
                    messages.append(s.get('message', ''))
                elif isinstance(s, str):
                    messages.append(s)
                else:
                    messages.append(str(getattr(s, 'message', '')))
            message_lower = ' '.join(messages).lower()
        else:
            message_lower = str(message).lower()
        
        # Check exclusions first
        if self.excludes:
            if any(excl.lower() in message_lower for excl in self.excludes):
                return False
        
        # Check required keywords (AND logic)
        if self.requires_all:
            if not all(req.lower() in message_lower for req in self.requires_all):
                return False
        
        # Check match_any keywords (OR logic)
        if self.match_any:
            return any(keyword.lower() in message_lower for keyword in self.match_any)
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'match_any': self.match_any,
            'failure_type': self.failure_type,
            'confidence': self.confidence,
            'priority': self.priority,
            'description': self.description,
            'framework': self.framework,
            'requires_all': self.requires_all,
            'excludes': self.excludes
        }


@dataclass
class RulePack:
    """
    Collection of rules for a specific framework or context.
    
    Rule packs are loaded from YAML files and provide framework-specific
    classification rules.
    """
    
    name: str                           # Rule pack name (e.g., "selenium")
    rules: List[Rule] = field(default_factory=list)
    version: str = "1.0.0"
    description: str = ""
    
    def add_rule(self, rule: Rule):
        """Add a rule to this pack"""
        self.rules.append(rule)
    
    def get_sorted_rules(self) -> List[Rule]:
        """Get rules sorted by priority (lower priority number = higher priority)"""
        return sorted(self.rules, key=lambda r: (r.priority, r.id))
    
    def find_matching_rules(self, message: str) -> List[Rule]:
        """
        Find all rules that match a message.
        
        Args:
            message: Failure message
            
        Returns:
            List of matching rules, sorted by priority
        """
        matching = [r for r in self.rules if r.matches(message)]
        return sorted(matching, key=lambda r: (r.priority, -r.confidence))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'rules': [r.to_dict() for r in self.rules]
        }
