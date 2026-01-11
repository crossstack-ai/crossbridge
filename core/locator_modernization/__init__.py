"""
Phase 3: AI-Assisted Locator Modernization

Opt-in, explainable, confidence-driven modernization of locators.
Built on Phase 2's semantic metadata.

Core Principles:
- AI never changes code without explicit user approval
- All suggestions are explainable and reversible
- Deterministic heuristics run first, AI is optional
- Risk + Confidence scoring for informed decisions
- Enterprise trust through transparency

This is NOT "magic AI rewrites" - it's guided, safe modernization.
"""

from .models import (
    RiskLevel,
    RiskScore,
    ModernizationSuggestion,
    ModernizationRecommendation,
    SuggestionStatus
)

from .heuristics import (
    HeuristicAnalyzer,
    LocatorQualityRule
)

from .ai_analyzer import AIModernizationAnalyzer

from .engine import ModernizationEngine

from .reporters import (
    ModernizationReporter,
    RiskHeatmapGenerator
)

__all__ = [
    # Models
    'RiskLevel',
    'RiskScore',
    'ModernizationSuggestion',
    'ModernizationRecommendation',
    'SuggestionStatus',
    
    # Analyzers
    'HeuristicAnalyzer',
    'LocatorQualityRule',
    'AIModernizationAnalyzer',
    
    # Engine
    'ModernizationEngine',
    
    # Reporters
    'ModernizationReporter',
    'RiskHeatmapGenerator',
]
