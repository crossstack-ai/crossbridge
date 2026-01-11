"""
AI-Assisted Locator Modernization Analyzer

Optional, LLM-based semantic analysis for locator improvement suggestions.
CRITICAL: This is OPT-IN and suggestions are NEVER auto-applied.

Requires AI configuration to be enabled by user.
"""

import json
from typing import Optional, Dict, List
from core.locator_awareness.models import Locator, LocatorStrategy
from .models import RiskScore, ModernizationSuggestion, SuggestionStatus


class AIModernizationAnalyzer:
    """
    AI-powered locator modernization analyzer
    
    Uses LLM to suggest Playwright-native alternatives with semantic understanding.
    All suggestions require explicit user approval.
    """
    
    def __init__(self, ai_client=None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize AI analyzer
        
        Args:
            ai_client: Optional AI client (Anthropic, OpenAI, etc.)
            model: Model to use for analysis
        """
        self.ai_client = ai_client
        self.model = model
        self.enabled = ai_client is not None
    
    def is_enabled(self) -> bool:
        """Check if AI analysis is available"""
        return self.enabled
    
    def analyze_locator(
        self, 
        locator: Locator, 
        current_risk: RiskScore,
        context: Optional[Dict] = None
    ) -> Optional[ModernizationSuggestion]:
        """
        Analyze locator and suggest Playwright-native alternative
        
        Args:
            locator: Locator to analyze
            current_risk: Risk assessment from heuristic analyzer
            context: Optional context (Page Object name, usage, etc.)
        
        Returns:
            ModernizationSuggestion if AI is enabled, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            # Build prompt for AI
            prompt = self._build_analysis_prompt(locator, current_risk, context)
            
            # Call AI (placeholder - would use actual AI client)
            ai_response = self._call_ai(prompt)
            
            # Parse AI response
            suggestion = self._parse_ai_response(locator, current_risk, ai_response)
            
            return suggestion
            
        except Exception as e:
            # AI failures should not break the pipeline
            print(f"AI analysis failed: {e}")
            return None
    
    def _build_analysis_prompt(
        self, 
        locator: Locator, 
        risk: RiskScore,
        context: Optional[Dict]
    ) -> str:
        """Build prompt for AI analysis"""
        
        prompt = f"""You are an expert in test automation and Playwright best practices.

Analyze this Selenium locator and suggest a modern Playwright alternative.

LOCATOR INFO:
- Name: {locator.name}
- Strategy: {locator.strategy.value}
- Value: {locator.value}
- Page Object: {locator.page_object}

CURRENT RISK ASSESSMENT:
- Risk Score: {risk.final_score:.2f}
- Risk Level: {risk.risk_level.value}
- Risk Factors: {', '.join(risk.risk_factors)}

"""
        
        if context:
            prompt += f"\nCONTEXT:\n"
            if 'usage_count' in context:
                prompt += f"- Used in {context['usage_count']} test(s)\n"
            if 'page_object_type' in context:
                prompt += f"- Page Object type: {context['page_object_type']}\n"
        
        prompt += """
TASK:
Suggest a Playwright-native alternative that is:
1. More resilient to DOM changes
2. Follows Playwright best practices
3. Improves test readability
4. Maintains the same semantic intent

Prefer in order:
1. Role-based selectors: page.getByRole()
2. Text-based: page.getByText()
3. Accessible attributes: page.getByLabel(), page.getByPlaceholder()
4. data-testid: page.getByTestId()
5. CSS selectors (if necessary)

Respond in JSON format:
{
  "suggested_strategy": "playwright_role" | "playwright_text" | "playwright_testid" | "css",
  "suggested_value": "the Playwright locator code",
  "confidence": 0.0-1.0,
  "reason": "explanation of why this is better",
  "additional_notes": "optional implementation notes"
}

If no better alternative exists, set confidence to 0.0.
"""
        
        return prompt
    
    def _call_ai(self, prompt: str) -> Dict:
        """
        Call AI service (placeholder implementation)
        
        In production, this would call Anthropic Claude, OpenAI GPT, etc.
        For now, returns mock responses for testing.
        """
        if not self.enabled:
            raise ValueError("AI client not configured")
        
        # Mock response for testing
        # In production: response = self.ai_client.messages.create(...)
        
        # Simulate AI decision based on prompt content
        if "//div[" in prompt and "]" in prompt:
            # Index-based XPath - suggest role-based
            return {
                "suggested_strategy": "playwright_role",
                "suggested_value": 'page.getByRole("button", name="Login")',
                "confidence": 0.82,
                "reason": "Role-based selectors are resilient to DOM restructuring and improve accessibility testing",
                "additional_notes": "Verify button has accessible name attribute"
            }
        elif "[@class=" in prompt:
            # Class-based - suggest data-testid
            return {
                "suggested_strategy": "playwright_testid",
                "suggested_value": 'page.getByTestId("login-button")',
                "confidence": 0.78,
                "reason": "data-testid attributes are stable and purpose-built for testing",
                "additional_notes": "Add data-testid='login-button' to element"
            }
        else:
            # Already decent - low confidence change
            return {
                "suggested_strategy": "css",
                "suggested_value": 'page.locator("#login")',
                "confidence": 0.45,
                "reason": "Current locator is reasonable, minimal improvement available"
            }
    
    def _parse_ai_response(
        self, 
        locator: Locator,
        risk: RiskScore,
        ai_response: Dict
    ) -> Optional[ModernizationSuggestion]:
        """Parse AI response into ModernizationSuggestion"""
        
        confidence = ai_response.get('confidence', 0.0)
        
        # Only return suggestion if confidence is reasonable
        if confidence < 0.5:
            return None
        
        suggestion = ModernizationSuggestion(
            locator_name=locator.name,
            page_object=locator.page_object,
            current_strategy=locator.strategy.value,
            current_value=locator.value,
            suggested_strategy=ai_response['suggested_strategy'],
            suggested_value=ai_response['suggested_value'],
            confidence=confidence,
            reason=ai_response['reason'],
            source="ai",
            current_risk=risk,
            usage_count=locator.usage_count,
            used_in_tests=locator.used_in_tests,
            status=SuggestionStatus.PENDING
        )
        
        return suggestion
    
    def batch_analyze(
        self,
        locators: List[Locator],
        risks: List[RiskScore],
        context: Optional[Dict] = None
    ) -> List[ModernizationSuggestion]:
        """
        Analyze multiple locators
        
        Only analyzes high-risk locators to avoid unnecessary AI calls
        """
        if not self.enabled:
            return []
        
        suggestions = []
        
        for locator, risk in zip(locators, risks):
            # Only use AI for medium+ risk locators
            if risk.final_score >= 0.4:
                suggestion = self.analyze_locator(locator, risk, context)
                if suggestion:
                    suggestions.append(suggestion)
        
        return suggestions


def create_mock_ai_analyzer() -> AIModernizationAnalyzer:
    """Create AI analyzer with mock client for testing"""
    # Mock client that returns predefined responses
    class MockAIClient:
        pass
    
    return AIModernizationAnalyzer(ai_client=MockAIClient())


def create_ai_analyzer_from_config(config: Dict) -> Optional[AIModernizationAnalyzer]:
    """
    Create AI analyzer from configuration
    
    Args:
        config: Configuration dict with 'ai_enabled', 'ai_api_key', 'ai_model'
    
    Returns:
        AIModernizationAnalyzer if enabled, None otherwise
    """
    if not config.get('ai_enabled', False):
        return None
    
    # In production, initialize actual AI client here
    # For now, return mock
    return create_mock_ai_analyzer()
