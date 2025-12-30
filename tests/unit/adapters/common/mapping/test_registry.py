"""
Unit tests for StepSignalRegistry.

Tests signal registration and deterministic matching.
"""
import pytest
from adapters.common.mapping.models import StepSignal, SignalType
from adapters.common.mapping.registry import StepSignalRegistry


class TestSignalRegistration:
    """Test basic signal registration functionality."""
    
    def test_register_single_signal(self):
        """Should successfully register a signal for a step pattern."""
        registry = StepSignalRegistry()
        signal = StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        
        registry.register_signal("user logs in", signal)
        
        signals = registry.get_signals_for_step("user logs in")
        assert len(signals) == 1
        assert signals[0].value == "LoginPage"
    
    def test_register_multiple_signals_same_pattern(self):
        """Multiple signals can be registered for the same pattern."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.METHOD, value="login")
        )
        
        signals = registry.get_signals_for_step("user logs in")
        assert len(signals) == 2
    
    def test_register_signals_different_patterns(self):
        """Signals for different patterns should be independent."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        registry.register_signal(
            "user logs out",
            StepSignal(type=SignalType.PAGE_OBJECT, value="HeaderPage")
        )
        
        login_signals = registry.get_signals_for_step("user logs in")
        logout_signals = registry.get_signals_for_step("user logs out")
        
        assert len(login_signals) == 1
        assert login_signals[0].value == "LoginPage"
        assert len(logout_signals) == 1
        assert logout_signals[0].value == "HeaderPage"
    
    def test_count_registered_signals(self):
        """count() should return total number of registered signals."""
        registry = StepSignalRegistry()
        
        assert registry.count() == 0
        
        registry.register_signal(
            "step1",
            StepSignal(type=SignalType.PAGE_OBJECT, value="Page1")
        )
        assert registry.count() == 1
        
        registry.register_signal(
            "step1",
            StepSignal(type=SignalType.METHOD, value="method1")
        )
        assert registry.count() == 2
        
        registry.register_signal(
            "step2",
            StepSignal(type=SignalType.PAGE_OBJECT, value="Page2")
        )
        assert registry.count() == 3


class TestDeterministicMatching:
    """Test deterministic signal matching behavior."""
    
    def test_exact_match_priority(self):
        """Exact match should be found first."""
        registry = StepSignalRegistry()
        
        # Register exact match
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="ExactMatch")
        )
        
        # Register substring that would also match
        registry.register_signal(
            "logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="SubstringMatch")
        )
        
        signals = registry.get_signals_for_step("user logs in")
        
        # Both should be found, but exact match first
        assert len(signals) >= 1
        assert signals[0].value == "ExactMatch"
    
    def test_contains_match(self):
        """Pattern contained in step should match."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        # Should match steps containing "logs in"
        signals = registry.get_signals_for_step("user logs in with admin")
        assert len(signals) == 1
        assert signals[0].value == "LoginPage"
    
    def test_no_match_returns_empty(self):
        """Unknown pattern should return empty list."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        signals = registry.get_signals_for_step("user registers")
        assert signals == []
    
    def test_case_insensitive_matching(self):
        """Matching should be case-insensitive."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        # Different cases should all match
        assert len(registry.get_signals_for_step("USER LOGS IN")) == 1
        assert len(registry.get_signals_for_step("User Logs In")) == 1
        assert len(registry.get_signals_for_step("user logs in")) == 1
    
    def test_whitespace_normalization(self):
        """Whitespace should be normalized."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        # Extra whitespace should still match
        signals = registry.get_signals_for_step("  user   logs   in  ")
        assert len(signals) == 1


class TestBDDKeywordRemoval:
    """Test removal of BDD keywords from step text."""
    
    def test_given_keyword_removed(self):
        """'Given' keyword should be removed from step text."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user is on login page",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        signals = registry.get_signals_for_step("Given user is on login page")
        assert len(signals) == 1
    
    def test_when_keyword_removed(self):
        """'When' keyword should be removed from step text."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        signals = registry.get_signals_for_step("When user logs in")
        assert len(signals) == 1
    
    def test_then_keyword_removed(self):
        """'Then' keyword should be removed from step text."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user sees dashboard",
            StepSignal(type=SignalType.PAGE_OBJECT, value="DashboardPage")
        )
        
        signals = registry.get_signals_for_step("Then user sees dashboard")
        assert len(signals) == 1
    
    def test_and_keyword_removed(self):
        """'And' keyword should be removed from step text."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user enters password",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        signals = registry.get_signals_for_step("And user enters password")
        assert len(signals) == 1
    
    def test_but_keyword_removed(self):
        """'But' keyword should be removed from step text."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "error is not displayed",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        signals = registry.get_signals_for_step("But error is not displayed")
        assert len(signals) == 1


class TestOrderPreservation:
    """Test that signal order is preserved."""
    
    def test_registration_order_preserved(self):
        """Signals should be returned in registration order."""
        registry = StepSignalRegistry()
        
        # Register in specific order
        registry.register_signal(
            "user performs action",
            StepSignal(type=SignalType.PAGE_OBJECT, value="FirstPage")
        )
        registry.register_signal(
            "user performs action",
            StepSignal(type=SignalType.PAGE_OBJECT, value="SecondPage")
        )
        registry.register_signal(
            "user performs action",
            StepSignal(type=SignalType.PAGE_OBJECT, value="ThirdPage")
        )
        
        signals = registry.get_signals_for_step("user performs action")
        
        assert len(signals) == 3
        assert signals[0].value == "FirstPage"
        assert signals[1].value == "SecondPage"
        assert signals[2].value == "ThirdPage"
    
    def test_contains_matches_preserve_order(self):
        """Contains matches should preserve registration order."""
        registry = StepSignalRegistry()
        
        # Register patterns that will all match via contains
        registry.register_signal(
            "user",
            StepSignal(type=SignalType.PAGE_OBJECT, value="First")
        )
        registry.register_signal(
            "logs",
            StepSignal(type=SignalType.PAGE_OBJECT, value="Second")
        )
        registry.register_signal(
            "in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="Third")
        )
        
        signals = registry.get_signals_for_step("user logs in")
        
        # All should match, order preserved
        assert len(signals) == 3
        values = [s.value for s in signals]
        assert values == ["First", "Second", "Third"]


class TestDeduplication:
    """Test deduplication of signals."""
    
    def test_duplicate_signals_deduplicated(self):
        """Duplicate signals should only appear once in results."""
        registry = StepSignalRegistry()
        
        signal = StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        
        # Register same signal multiple times with different patterns
        registry.register_signal("user logs in", signal)
        registry.register_signal("logs in", signal)  # Will also match via contains
        
        signals = registry.get_signals_for_step("user logs in")
        
        # Should be deduplicated
        assert len(signals) == 1
        assert signals[0].value == "LoginPage"
    
    def test_similar_but_different_signals_not_deduplicated(self):
        """Similar but different signals should not be deduplicated."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.METHOD, value="login")
        )
        
        signals = registry.get_signals_for_step("user logs in")
        
        # Different types, should both be present
        assert len(signals) == 2


class TestRegistryManagement:
    """Test registry management operations."""
    
    def test_clear_removes_all_signals(self):
        """clear() should remove all registered signals."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "step1",
            StepSignal(type=SignalType.PAGE_OBJECT, value="Page1")
        )
        registry.register_signal(
            "step2",
            StepSignal(type=SignalType.PAGE_OBJECT, value="Page2")
        )
        
        assert registry.count() == 2
        
        registry.clear()
        
        assert registry.count() == 0
        assert registry.get_signals_for_step("step1") == []
        assert registry.get_signals_for_step("step2") == []
    
    def test_get_all_patterns(self):
        """get_all_patterns() should return all registered patterns."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        registry.register_signal(
            "user logs out",
            StepSignal(type=SignalType.PAGE_OBJECT, value="HeaderPage")
        )
        
        patterns = registry.get_all_patterns()
        
        assert "user logs in" in patterns
        assert "user logs out" in patterns
        assert len(patterns) == 2


class TestEdgeCases:
    """Test edge cases and unusual inputs."""
    
    def test_empty_step_text(self):
        """Empty step text should not crash."""
        registry = StepSignalRegistry()
        
        signals = registry.get_signals_for_step("")
        assert signals == []
    
    def test_empty_pattern(self):
        """Empty pattern should be handled gracefully."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "",
            StepSignal(type=SignalType.PAGE_OBJECT, value="Page")
        )
        
        # Should match steps with empty normalized text
        signals = registry.get_signals_for_step("Given")  # Becomes empty after keyword removal
        assert len(signals) >= 0  # Should not crash
    
    def test_special_characters_in_pattern(self):
        """Special characters should be handled correctly."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user enters email test@example.com",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        signals = registry.get_signals_for_step("user enters email test@example.com")
        assert len(signals) == 1
    
    def test_very_long_step_text(self):
        """Very long step text should not cause performance issues."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user performs action",
            StepSignal(type=SignalType.PAGE_OBJECT, value="Page")
        )
        
        # Create very long step text
        long_step = "user performs action " + "with many parameters " * 100
        
        signals = registry.get_signals_for_step(long_step)
        assert len(signals) >= 0  # Should complete without timeout
