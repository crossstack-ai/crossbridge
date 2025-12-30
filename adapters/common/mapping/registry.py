"""
Signal registry for step-to-code-path mapping.

Adapters register signals during discovery to build the mapping database.
Deterministic matching: exact match first, then contains.
"""
from typing import List, Dict, Tuple
from .models import StepSignal


class StepSignalRegistry:
    """
    Registry for step signals contributed by framework adapters.
    
    During test discovery, adapters register signals that link step patterns
    to code elements (Page Objects, methods, file paths). The resolver uses
    this registry to build step-to-code mappings.
    
    Matching Strategy:
    1. Exact match (step text == pattern)
    2. Contains match (pattern in step text)
    3. Order preserved (first registered = first matched)
    
    No regex, no NLP, no heuristics - only explicit signal registration.
    
    Example:
        >>> registry = StepSignalRegistry()
        >>> registry.register_signal(
        ...     "user logs in",
        ...     StepSignal(type=SignalType.CODE_PATH,
        ...               value="pages/login_page.py::LoginPage.login")
        ... )
        >>> signals = registry.get_signals_for_step("when user logs in with admin")
        >>> len(signals)
        1
    """
    
    def __init__(self):
        """Initialize empty registry."""
        # Store as list of (pattern, signal) tuples to preserve insertion order
        self._exact_matches: Dict[str, List[StepSignal]] = {}
        self._contains_matches: List[Tuple[str, StepSignal]] = []
    
    def register_signal(self, step_pattern: str, signal: StepSignal) -> None:
        """
        Register a signal for a step pattern.
        
        Args:
            step_pattern: Step text pattern (normalized lowercase, no Given/When/Then)
            signal: StepSignal to associate with this pattern
            
        Example:
            >>> registry.register_signal(
            ...     "user logs in",
            ...     StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
            ... )
        """
        # Normalize pattern: lowercase, strip whitespace
        normalized_pattern = step_pattern.lower().strip()
        
        # Store in exact match dict (for O(1) lookup)
        if normalized_pattern not in self._exact_matches:
            self._exact_matches[normalized_pattern] = []
        self._exact_matches[normalized_pattern].append(signal)
        
        # Also store in contains list (for substring matching)
        self._contains_matches.append((normalized_pattern, signal))
    
    def get_signals_for_step(self, step_text: str) -> List[StepSignal]:
        """
        Get all signals matching the given step text.
        
        Matching strategy:
        1. Try exact match first (fast O(1) lookup)
        2. Try contains matches (preserves registration order)
        3. Return all matches, deduplicated
        
        Args:
            step_text: Step text to match (will be normalized)
            
        Returns:
            List of matching StepSignals in order of relevance/registration
            
        Example:
            >>> signals = registry.get_signals_for_step("when user logs in")
            >>> [s.value for s in signals]
            ['LoginPage.login', 'pages/login_page.py::LoginPage.login']
        """
        # Normalize step text: lowercase, strip whitespace, remove BDD keywords
        normalized_step = self._normalize_step_text(step_text)
        
        matched_signals: List[StepSignal] = []
        seen = set()  # Track seen signals for deduplication
        
        # 1. Try exact match first
        if normalized_step in self._exact_matches:
            for signal in self._exact_matches[normalized_step]:
                signal_key = (signal.type, signal.value)
                if signal_key not in seen:
                    matched_signals.append(signal)
                    seen.add(signal_key)
        
        # 2. Try contains matches (in registration order)
        for pattern, signal in self._contains_matches:
            if pattern in normalized_step:
                signal_key = (signal.type, signal.value)
                if signal_key not in seen:
                    matched_signals.append(signal)
                    seen.add(signal_key)
        
        return matched_signals
    
    def _normalize_step_text(self, step_text: str) -> str:
        """
        Normalize step text for matching.
        
        Removes BDD keywords (Given/When/Then/And/But) and normalizes whitespace.
        
        Args:
            step_text: Raw step text
            
        Returns:
            Normalized text suitable for matching
            
        Example:
            >>> registry._normalize_step_text("  When user logs in  ")
            'user logs in'
            >>> registry._normalize_step_text("Given user is on login page")
            'user is on login page'
        """
        # Convert to lowercase and strip
        normalized = step_text.lower().strip()
        
        # Remove BDD keywords at the start
        bdd_keywords = ["given ", "when ", "then ", "and ", "but "]
        for keyword in bdd_keywords:
            if normalized.startswith(keyword):
                normalized = normalized[len(keyword):].strip()
                break
        
        # Normalize multiple spaces to single space
        normalized = " ".join(normalized.split())
        
        return normalized
    
    def clear(self) -> None:
        """Clear all registered signals (useful for testing)."""
        self._exact_matches.clear()
        self._contains_matches.clear()
    
    def count(self) -> int:
        """Get total number of registered signals."""
        return sum(len(signals) for signals in self._exact_matches.values())
    
    def get_all_patterns(self) -> List[str]:
        """
        Get all registered patterns (for debugging).
        
        Returns:
            List of all registered patterns in registration order
        """
        return list(self._exact_matches.keys())
