"""
Modernization Engine

Orchestrates the Phase 3 locator modernization pipeline:
1. Heuristic analysis (always)
2. AI analysis (optional)
3. Suggestion generation
4. Optional auto-fix (with approval)

This is the main entry point for Phase 3.
"""

from typing import List, Optional, Dict
from core.locator_awareness.models import Locator, PageObject
from .models import (
    RiskScore,
    ModernizationSuggestion,
    ModernizationRecommendation,
    SuggestionStatus
)
from .heuristics import HeuristicAnalyzer
from .ai_analyzer import AIModernizationAnalyzer


class ModernizationEngine:
    """
    Phase 3 Modernization Engine
    
    Orchestrates locator quality analysis and modernization suggestions.
    """
    
    def __init__(
        self,
        enable_ai: bool = False,
        ai_analyzer: Optional[AIModernizationAnalyzer] = None,
        min_confidence_threshold: float = 0.7,
        auto_fix_enabled: bool = False
    ):
        """
        Initialize modernization engine
        
        Args:
            enable_ai: Enable AI-assisted analysis
            ai_analyzer: Optional AI analyzer instance
            min_confidence_threshold: Minimum confidence for suggestions
            auto_fix_enabled: Enable automatic code fixes (requires approval)
        """
        self.heuristic_analyzer = HeuristicAnalyzer()
        self.ai_analyzer = ai_analyzer if enable_ai else None
        self.min_confidence_threshold = min_confidence_threshold
        self.auto_fix_enabled = auto_fix_enabled
        
        # Results cache
        self.analyzed_locators: Dict[str, RiskScore] = {}
        self.all_suggestions: List[ModernizationSuggestion] = []
        self.recommendations_by_page: Dict[str, ModernizationRecommendation] = {}
    
    def analyze_locator(
        self, 
        locator: Locator,
        context: Optional[Dict] = None
    ) -> RiskScore:
        """
        Analyze single locator using heuristics (and optionally AI)
        
        Args:
            locator: Locator to analyze
            context: Optional context information
        
        Returns:
            RiskScore with combined assessment
        """
        # Step 1: Always run heuristic analysis
        risk_score = self.heuristic_analyzer.analyze(locator)
        
        # Step 2: Optionally enhance with AI
        if self.ai_analyzer and self.ai_analyzer.is_enabled():
            try:
                # AI can provide additional risk insights
                ai_suggestion = self.ai_analyzer.analyze_locator(
                    locator, 
                    risk_score, 
                    context
                )
                
                if ai_suggestion and ai_suggestion.confidence >= self.min_confidence_threshold:
                    # AI provided valuable input
                    risk_score.ai_reasoning = ai_suggestion.reason
                    # AI score could influence final score if desired
                    
            except Exception as e:
                # AI failures don't break the pipeline
                print(f"AI analysis failed for {locator.name}: {e}")
        
        # Cache result
        cache_key = f"{locator.page_object}.{locator.name}"
        self.analyzed_locators[cache_key] = risk_score
        
        return risk_score
    
    def analyze_page_object(
        self, 
        page_object: PageObject,
        generate_suggestions: bool = True
    ) -> ModernizationRecommendation:
        """
        Analyze all locators in a Page Object
        
        Args:
            page_object: PageObject to analyze
            generate_suggestions: Whether to generate modernization suggestions
        
        Returns:
            ModernizationRecommendation with all suggestions
        """
        recommendation = ModernizationRecommendation(
            page_object=page_object.name,
            file_path=page_object.file_path,
            total_locators=len(page_object.locators)
        )
        
        for locator in page_object.locators:
            # Analyze risk
            risk_score = self.analyze_locator(locator)
            
            # Generate suggestion if requested and risk is significant
            if generate_suggestions and risk_score.final_score >= 0.4:
                suggestion = self._generate_suggestion(locator, risk_score)
                
                if suggestion:
                    recommendation.add_suggestion(suggestion)
                    self.all_suggestions.append(suggestion)
        
        # Cache recommendation
        self.recommendations_by_page[page_object.name] = recommendation
        
        return recommendation
    
    def analyze_batch(
        self,
        page_objects: List[PageObject],
        generate_suggestions: bool = True
    ) -> List[ModernizationRecommendation]:
        """
        Analyze multiple Page Objects
        
        Returns:
            List of ModernizationRecommendation
        """
        recommendations = []
        
        for page_object in page_objects:
            recommendation = self.analyze_page_object(page_object, generate_suggestions)
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_suggestion(
        self,
        locator: Locator,
        risk_score: RiskScore
    ) -> Optional[ModernizationSuggestion]:
        """
        Generate modernization suggestion
        
        Uses heuristics first, then AI if enabled
        """
        # Try AI first if enabled
        if self.ai_analyzer and self.ai_analyzer.is_enabled():
            ai_suggestion = self.ai_analyzer.analyze_locator(
                locator, 
                risk_score
            )
            
            if ai_suggestion and ai_suggestion.confidence >= self.min_confidence_threshold:
                return ai_suggestion
        
        # Fallback to heuristic-based suggestions
        return self._generate_heuristic_suggestion(locator, risk_score)
    
    def _generate_heuristic_suggestion(
        self,
        locator: Locator,
        risk_score: RiskScore
    ) -> Optional[ModernizationSuggestion]:
        """
        Generate suggestion using heuristic rules
        
        Simple, deterministic suggestions based on locator type
        """
        # Only suggest for high-risk locators
        if risk_score.final_score < 0.6:
            return None
        
        suggested_value = None
        reason = None
        confidence = 0.7  # Heuristic suggestions have moderate confidence
        
        # Pattern-based suggestions
        if "index_based_xpath" in [rf for rf in risk_score.risk_factors]:
            suggested_value = f'page.getByTestId("{locator.name.lower()}")'
            reason = "Replace index-based XPath with data-testid for stability"
        
        elif "class_only_xpath" in str(risk_score.risk_factors):
            suggested_value = f'page.getByTestId("{locator.name.lower()}")'
            reason = "Replace class-only selector with data-testid attribute"
        
        elif "text_based" in str(risk_score.risk_factors):
            suggested_value = f'page.getByRole("button", name="{locator.name}")'
            reason = "Use role-based selector for better accessibility and i18n support"
        
        if suggested_value:
            return ModernizationSuggestion(
                locator_name=locator.name,
                page_object=locator.page_object,
                current_strategy=locator.strategy.value,
                current_value=locator.value,
                suggested_strategy="playwright_enhanced",
                suggested_value=suggested_value,
                confidence=confidence,
                reason=reason,
                source="heuristic",
                current_risk=risk_score,
                usage_count=locator.usage_count,
                used_in_tests=locator.used_in_tests
            )
        
        return None
    
    def get_pending_suggestions(self) -> List[ModernizationSuggestion]:
        """Get all pending suggestions awaiting review"""
        return [s for s in self.all_suggestions if s.status == SuggestionStatus.PENDING]
    
    def get_high_priority_recommendations(self) -> List[ModernizationRecommendation]:
        """Get Page Objects with high/critical modernization priority"""
        return [
            rec for rec in self.recommendations_by_page.values()
            if rec.modernization_priority in ["high", "critical"]
        ]
    
    def approve_suggestion(self, locator_name: str, page_object: str) -> bool:
        """
        Approve a suggestion for application
        
        Returns:
            True if suggestion found and approved
        """
        for suggestion in self.all_suggestions:
            if (suggestion.locator_name == locator_name and 
                suggestion.page_object == page_object):
                suggestion.approve()
                return True
        return False
    
    def apply_approved_suggestions(
        self,
        page_object: PageObject,
        dry_run: bool = True
    ) -> Dict:
        """
        Apply approved suggestions to Page Object code
        
        Args:
            page_object: PageObject to update
            dry_run: If True, only show what would change
        
        Returns:
            Dict with changes preview or application results
        """
        if not self.auto_fix_enabled and not dry_run:
            raise ValueError("Auto-fix not enabled. Set auto_fix_enabled=True or use dry_run=True")
        
        recommendation = self.recommendations_by_page.get(page_object.name)
        if not recommendation:
            return {'error': 'No recommendations found for this Page Object'}
        
        approved = recommendation.get_approved_suggestions()
        if not approved:
            return {'message': 'No approved suggestions to apply'}
        
        changes = []
        for suggestion in approved:
            change = {
                'locator_name': suggestion.locator_name,
                'current': suggestion.current_value,
                'suggested': suggestion.suggested_value,
                'confidence': suggestion.confidence,
                'applied': False
            }
            
            if not dry_run:
                # Actually modify the Page Object
                locator = page_object.get_locator(suggestion.locator_name)
                if locator:
                    # Store original for rollback
                    change['original_value'] = locator.value
                    change['original_strategy'] = locator.strategy.value
                    
                    # Apply change (in real implementation, modify source code)
                    locator.suggested_alternative = suggestion.suggested_value
                    suggestion.mark_applied()
                    change['applied'] = True
            
            changes.append(change)
        
        return {
            'page_object': page_object.name,
            'dry_run': dry_run,
            'changes': changes,
            'total_approved': len(approved),
            'total_applied': sum(1 for c in changes if c.get('applied', False))
        }
    
    def generate_summary(self) -> Dict:
        """Generate summary of modernization analysis"""
        total_locators = len(self.analyzed_locators)
        high_risk = sum(1 for r in self.analyzed_locators.values() if r.final_score >= 0.6)
        total_suggestions = len(self.all_suggestions)
        pending = len(self.get_pending_suggestions())
        approved = sum(1 for s in self.all_suggestions if s.status == SuggestionStatus.APPROVED)
        
        return {
            'total_locators_analyzed': total_locators,
            'high_risk_locators': high_risk,
            'total_suggestions': total_suggestions,
            'pending_review': pending,
            'approved': approved,
            'ai_enabled': self.ai_analyzer is not None and self.ai_analyzer.is_enabled(),
            'page_objects_analyzed': len(self.recommendations_by_page),
            'high_priority_pages': len(self.get_high_priority_recommendations())
        }
