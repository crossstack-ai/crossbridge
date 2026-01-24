"""
LLM-Enhanced Test Analysis and Summarization.

Provides AI-powered test intelligence including:
- Test purpose and intent summarization
- Pattern recognition across frameworks
- Intelligent test recommendations
- Code quality insights
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.intelligence.models import UnifiedTestMemory, TestType, Priority

logger = logging.getLogger(__name__)


class LLMTestAnalyzer:
    """
    LLM-powered test analysis and summarization.
    
    Uses language models to provide intelligent insights about tests
    beyond what can be extracted from AST/pattern matching.
    """
    
    def __init__(self, model: str = "gpt-4", api_key: Optional[str] = None):
        """
        Initialize LLM analyzer.
        
        Args:
            model: Model name (gpt-4, gpt-3.5-turbo, claude-3, etc.)
            api_key: API key for LLM service
        """
        self.model = model
        self.api_key = api_key
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LLM client based on model."""
        if not self.api_key:
            logger.warning("No API key provided, LLM features disabled")
            self._client = None
            self._provider = None
            return
            
        if self.model.startswith("gpt"):
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
                self._provider = "openai"
            except ImportError:
                logger.warning("OpenAI library not installed. Install with: pip install openai")
                self._client = None
                self._provider = None
        elif self.model.startswith("claude"):
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
                self._provider = "anthropic"
            except ImportError:
                logger.warning("Anthropic library not installed. Install with: pip install anthropic")
                self._client = None
                self._provider = None
        else:
            logger.warning(f"Unknown model: {self.model}")
            self._client = None
            self._provider = None
    
    def summarize_test(
        self,
        unified: UnifiedTestMemory,
        source_code: Optional[str] = None,
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate an intelligent summary of a test.
        
        Args:
            unified: UnifiedTestMemory object
            source_code: Optional source code for deeper analysis
            include_recommendations: Include improvement recommendations
            
        Returns:
            Dictionary with summary, intent, patterns, and recommendations
        """
        if not self._client:
            return self._fallback_summary(unified)
        
        prompt = self._build_test_summary_prompt(unified, source_code, include_recommendations)
        
        try:
            if self._provider == "openai":
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert test automation engineer analyzing test code."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                summary_text = response.choices[0].message.content
            elif self._provider == "anthropic":
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
                summary_text = response.content[0].text
            else:
                return self._fallback_summary(unified)
            
            return self._parse_summary_response(summary_text, unified)
            
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            return self._fallback_summary(unified)
    
    def _build_test_summary_prompt(
        self,
        unified: UnifiedTestMemory,
        source_code: Optional[str],
        include_recommendations: bool
    ) -> str:
        """Build prompt for test summarization."""
        prompt_parts = [
            f"Analyze this {unified.framework} test in {unified.language}:",
            f"\nTest ID: {unified.test_id}",
            f"Priority: {unified.metadata.priority}",
            f"Tags: {', '.join(unified.metadata.tags) if unified.metadata.tags else 'None'}",
            f"Type: {unified.metadata.test_type if unified.metadata else 'Unknown'}",
        ]
        
        if unified.structural:
            if unified.structural.api_calls:
                prompt_parts.append(f"\nAPI Calls: {len(unified.structural.api_calls)}")
                for call in unified.structural.api_calls[:3]:
                    prompt_parts.append(f"  - {call.method} {call.endpoint}")
            
            if unified.structural.assertions:
                prompt_parts.append(f"\nAssertions: {len(unified.structural.assertions)}")
            
            if unified.structural.ui_interactions:
                prompt_parts.append(f"\nUI Interactions: {', '.join(unified.structural.ui_interactions[:5])}")
        
        if source_code:
            prompt_parts.append(f"\nSource Code:\n```{unified.language}\n{source_code[:1000]}\n```")
        
        prompt_parts.append("\nProvide:")
        prompt_parts.append("1. One-sentence test purpose")
        prompt_parts.append("2. What this test validates")
        prompt_parts.append("3. Key patterns used")
        
        if include_recommendations:
            prompt_parts.append("4. Improvement suggestions (if any)")
        
        return "\n".join(prompt_parts)
    
    def _parse_summary_response(self, response: str, unified: UnifiedTestMemory) -> Dict[str, Any]:
        """Parse LLM response into structured summary."""
        return {
            "test_id": unified.test_id,
            "framework": unified.framework,
            "summary": response,
            "generated_at": datetime.utcnow().isoformat(),
            "model": self.model,
            "confidence": "high"  # Could be extracted from response
        }
    
    def _fallback_summary(self, unified: UnifiedTestMemory) -> Dict[str, Any]:
        """Generate basic summary without LLM."""
        test_type = unified.metadata.test_type if unified.metadata else "unknown"
        
        summary_parts = [
            f"This is a {test_type} test",
            f"written in {unified.language}",
            f"using {unified.framework} framework",
        ]
        
        if unified.metadata.priority:
            summary_parts.append(f"with {unified.metadata.priority} priority")
        
        if unified.structural:
            if unified.structural.api_calls:
                summary_parts.append(f"making {len(unified.structural.api_calls)} API call(s)")
            if unified.structural.ui_interactions:
                summary_parts.append(f"with {len(unified.structural.ui_interactions)} UI interaction(s)")
        
        return {
            "test_id": unified.test_id,
            "framework": unified.framework,
            "summary": " ".join(summary_parts) + ".",
            "generated_at": datetime.utcnow().isoformat(),
            "model": "fallback",
            "confidence": "low"
        }
    
    def batch_summarize(
        self,
        tests: List[UnifiedTestMemory],
        max_tests: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Summarize multiple tests efficiently.
        
        Args:
            tests: List of UnifiedTestMemory objects
            max_tests: Maximum number of tests to summarize
            
        Returns:
            List of summary dictionaries
        """
        summaries = []
        
        for test in tests[:max_tests]:
            summary = self.summarize_test(test, include_recommendations=False)
            summaries.append(summary)
        
        return summaries
    
    def compare_tests(
        self,
        test1: UnifiedTestMemory,
        test2: UnifiedTestMemory
    ) -> Dict[str, Any]:
        """
        Compare two tests and identify similarities/differences.
        
        Args:
            test1: First test
            test2: Second test
            
        Returns:
            Comparison analysis
        """
        if not self._client:
            return self._fallback_comparison(test1, test2)
        
        prompt = f"""
Compare these two tests:

Test 1: {test1.test_id}
Framework: {test1.framework}
Type: {test1.metadata.test_type if test1.metadata else 'Unknown'}
Priority: {test1.metadata.priority}

Test 2: {test2.test_id}
Framework: {test2.framework}
Type: {test2.metadata.test_type if test2.metadata else 'Unknown'}
Priority: {test2.metadata.priority}

Provide:
1. Key similarities
2. Major differences
3. Which test is more comprehensive
4. Potential for consolidation
"""
        
        try:
            if self._provider == "openai":
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert test automation engineer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=400
                )
                analysis = response.choices[0].message.content
            else:
                analysis = "Comparison not available"
            
            return {
                "test1_id": test1.test_id,
                "test2_id": test2.test_id,
                "analysis": analysis,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Test comparison failed: {e}")
            return self._fallback_comparison(test1, test2)
    
    def _fallback_comparison(
        self,
        test1: UnifiedTestMemory,
        test2: UnifiedTestMemory
    ) -> Dict[str, Any]:
        """Simple comparison without LLM."""
        similarities = []
        differences = []
        
        if test1.framework == test2.framework:
            similarities.append(f"Both use {test1.framework} framework")
        else:
            differences.append(f"Different frameworks: {test1.framework} vs {test2.framework}")
        
        if test1.language == test2.language:
            similarities.append(f"Both written in {test1.language}")
        else:
            differences.append(f"Different languages: {test1.language} vs {test2.language}")
        
        if test1.metadata.priority == test2.metadata.priority:
            similarities.append(f"Same priority: {test1.metadata.priority}")
        else:
            differences.append(f"Different priorities: {test1.metadata.priority} vs {test2.metadata.priority}")
        
        return {
            "test1_id": test1.test_id,
            "test2_id": test2.test_id,
            "similarities": similarities,
            "differences": differences,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def suggest_test_improvements(
        self,
        unified: UnifiedTestMemory,
        source_code: Optional[str] = None
    ) -> List[str]:
        """
        Suggest improvements for a test.
        
        Args:
            unified: UnifiedTestMemory object
            source_code: Optional source code
            
        Returns:
            List of improvement suggestions
        """
        if not self._client:
            return self._fallback_suggestions(unified)
        
        prompt = f"""
Review this {unified.framework} test and suggest improvements:

Test: {unified.test_id}
Priority: {unified.metadata.priority}
Type: {unified.metadata.test_type if unified.metadata else 'Unknown'}

Structural Info:
- API Calls: {len(unified.structural.api_calls) if unified.structural else 0}
- Assertions: {len(unified.structural.assertions) if unified.structural else 0}
- UI Interactions: {len(unified.structural.ui_interactions) if unified.structural else 0}

Provide 3-5 specific, actionable improvement suggestions.
"""
        
        try:
            if self._provider == "openai":
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert test automation engineer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=300
                )
                suggestions_text = response.choices[0].message.content
                
                # Parse suggestions (simple line split)
                suggestions = [
                    line.strip() 
                    for line in suggestions_text.split('\n') 
                    if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('-'))
                ]
                return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
        
        return self._fallback_suggestions(unified)
    
    def _fallback_suggestions(self, unified: UnifiedTestMemory) -> List[str]:
        """Generate basic suggestions without LLM."""
        suggestions = []
        
        if not unified.metadata.tags:
            suggestions.append("Add descriptive tags for better test organization")
        
        if unified.metadata.priority == Priority.P3:
            suggestions.append("Review if this test should have higher priority")
        
        if unified.structural:
            if not unified.structural.assertions:
                suggestions.append("Add assertions to validate expected behavior")
            
            if unified.metadata and unified.metadata.test_type == TestType.E2E and not unified.structural.ui_interactions:
                suggestions.append("E2E test should include UI interaction validations")
        
        if not suggestions:
            suggestions.append("Test appears well-structured, continue monitoring for patterns")
        
        return suggestions


class LLMTestSummaryCache:
    """Cache for LLM-generated summaries to reduce API calls."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get cached summary for test."""
        return self._cache.get(test_id)
    
    def set(self, test_id: str, summary: Dict[str, Any]):
        """Cache summary for test."""
        self._cache[test_id] = summary
    
    def clear(self):
        """Clear all cached summaries."""
        self._cache.clear()
    
    def size(self) -> int:
        """Get cache size."""
        return len(self._cache)
