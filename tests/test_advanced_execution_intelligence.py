"""
Comprehensive Unit Tests for Advanced Execution Intelligence Capabilities

Tests confidence scoring, rule engine, flaky detection, and CI annotation systems.
Covers both with and without AI scenarios as requested.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path

# Import confidence system
from core.execution.intelligence.confidence.models import (
    ConfidenceComponents,
    ConfidenceBreakdown,
    ConfidenceThresholds
)
from core.execution.intelligence.confidence.scoring import (
    calculate_rule_score,
    calculate_signal_quality,
    calculate_history_score,
    calculate_log_completeness,
    build_confidence_breakdown,
    adjust_confidence_with_ai
)

# Import rules system
from core.execution.intelligence.rules.models import Rule, RulePack
from core.execution.intelligence.rules.engine import RuleEngine, load_rule_pack, apply_rules

# Import flaky detection
from core.execution.intelligence.flaky.models import (
    FailureNature,
    FailureSignature,
    FailureHistory,
    simplify_error_pattern
)
from core.execution.intelligence.flaky.detector import FlakyDetector

# Import CI annotation
from core.execution.intelligence.ci.models import (
    CIDecision,
    CodeReference,
    CIOutput,
    PRAnnotation,
    CIConfig
)
from core.execution.intelligence.ci.annotator import (
    CIAnnotator,
    GitHubAnnotator,
    BitbucketAnnotator,
    generate_ci_output,
    should_fail_ci,
    create_pr_comment,
    write_ci_output_file
)


# ============================================================================
# CONFIDENCE SCORING TESTS
# ============================================================================

class TestConfidenceScoring:
    """Comprehensive tests for confidence scoring system."""
    
    def test_rule_score_no_matches(self):
        """Test rule score with no matches."""
        score = calculate_rule_score(matched_rules=[])
        assert score == 0.0
    
    def test_rule_score_single_match(self):
        """Test rule score with single match."""
        rules = [Rule(
            id="TEST_001",
            description="Test rule",
            match_any=["error"],
            failure_type="PRODUCT_DEFECT",
            confidence=0.9,
            priority=10
        )]
        score = calculate_rule_score(matched_rules=rules)
        assert score >= 0.2  # Base score
        assert score <= 1.0
    
    def test_rule_score_multiple_matches(self):
        """Test rule score with multiple matches gets boost."""
        rules = [
            Rule(id="R1", description="", match_any=["error"], 
                 failure_type="PRODUCT_DEFECT", confidence=0.9, priority=10),
            Rule(id="R2", description="", match_any=["fail"], 
                 failure_type="PRODUCT_DEFECT", confidence=0.85, priority=15),
            Rule(id="R3", description="", match_any=["exception"], 
                 failure_type="PRODUCT_DEFECT", confidence=0.8, priority=20)
        ]
        score = calculate_rule_score(matched_rules=rules)
        assert score > calculate_rule_score([rules[0]])  # Higher with more rules
    
    def test_signal_quality_minimal(self):
        """Test signal quality with minimal information."""
        score = calculate_signal_quality(
            has_stacktrace=False,
            has_code_reference=False,
            signal_count=1
        )
        assert score == 0.0  # No quality signals
    
    def test_signal_quality_stacktrace_only(self):
        """Test signal quality with stacktrace."""
        score = calculate_signal_quality(
            has_stacktrace=True,
            has_code_reference=False,
            signal_count=1
        )
        assert score == 0.3  # Stacktrace adds 0.3
    
    def test_signal_quality_all_signals(self):
        """Test signal quality with all indicators."""
        score = calculate_signal_quality(
            has_stacktrace=True,
            has_code_reference=True,
            signal_count=3
        )
        assert score == 0.9  # 0.3 + 0.3 + 0.3
    
    def test_history_score_new_failure(self):
        """Test history score for new failure."""
        score = calculate_history_score(
            historical_occurrences=0,
            is_consistent_history=False
        )
        assert score == 0.2  # New failures get low score
    
    def test_history_score_inconsistent(self):
        """Test history score for inconsistent failure."""
        score = calculate_history_score(
            historical_occurrences=3,
            is_consistent_history=False
        )
        assert score == 0.4  # Some history but not consistent
    
    def test_history_score_consistent(self):
        """Test history score for consistent failure."""
        score = calculate_history_score(
            historical_occurrences=5,
            is_consistent_history=True
        )
        assert score == 0.9  # Consistent history = high score
    
    def test_log_completeness_automation_only(self):
        """Test log completeness with automation logs."""
        score = calculate_log_completeness(
            has_automation_logs=True,
            has_application_logs=False
        )
        assert score == 0.7  # Automation logs only
    
    def test_log_completeness_both_logs(self):
        """Test log completeness with both log types."""
        score = calculate_log_completeness(
            has_automation_logs=True,
            has_application_logs=True
        )
        assert score == 1.0  # Full logs = perfect score
    
    def test_log_completeness_no_logs(self):
        """Test log completeness with no logs."""
        score = calculate_log_completeness(
            has_automation_logs=False,
            has_application_logs=False
        )
        assert score == 0.0
    
    def test_build_confidence_breakdown_without_ai(self):
        """Test building confidence breakdown WITHOUT AI adjustment."""
        rules = [Rule(
            id="TEST_001",
            description="Test rule",
            match_any=["error"],
            failure_type="PRODUCT_DEFECT",
            confidence=0.9,
            priority=10
        )]
        
        breakdown = build_confidence_breakdown(
            matched_rules=rules,
            signals=[{"type": "error", "message": "Test error"}],
            has_stacktrace=True,
            has_code_reference=True,
            historical_occurrences=5,
            is_consistent_history=True,
            has_automation_logs=True,
            has_application_logs=True,
            ai_adjustment=0.0  # NO AI
        )
        
        assert isinstance(breakdown, ConfidenceBreakdown)
        assert breakdown.rule_score > 0.0
        assert breakdown.signal_quality_score > 0.0
        assert breakdown.history_score > 0.0
        assert breakdown.log_completeness_score > 0.0
        assert breakdown.ai_adjustment == 0.0  # NO AI
        
        final = breakdown.calculate_final_confidence()
        assert 0.0 <= final <= 1.0
        
        # Verify weighted calculation (35%, 25%, 20%, 20%)
        expected_base = (
            0.35 * breakdown.rule_score +
            0.25 * breakdown.signal_quality_score +
            0.20 * breakdown.history_score +
            0.20 * breakdown.log_completeness_score
        )
        assert abs(breakdown.calculate_base_confidence() - expected_base) < 0.01
    
    def test_build_confidence_breakdown_with_ai(self):
        """Test building confidence breakdown WITH AI adjustment."""
        rules = [Rule(
            id="TEST_001",
            description="Test rule",
            match_any=["error"],
            failure_type="PRODUCT_DEFECT",
            confidence=0.9,
            priority=10
        )]
        
        breakdown = build_confidence_breakdown(
            matched_rules=rules,
            signals=[{"type": "error"}],
            has_stacktrace=True,
            has_code_reference=False,
            historical_occurrences=2,
            is_consistent_history=False,
            has_automation_logs=True,
            has_application_logs=False,
            ai_adjustment=0.25  # AI boost
        )
        
        assert breakdown.ai_adjustment == 0.25
        
        final_with_ai = breakdown.calculate_final_confidence()
        base = breakdown.calculate_base_confidence()
        
        # AI should boost confidence
        assert final_with_ai > base
        assert final_with_ai <= 1.0  # Capped at 1.0
    
    def test_ai_adjustment_cannot_override(self):
        """Test that AI can only boost, never override low confidence."""
        rules = []  # No rules matched
        
        breakdown = build_confidence_breakdown(
            matched_rules=rules,
            signals=[],
            has_stacktrace=False,
            has_code_reference=False,
            historical_occurrences=0,
            is_consistent_history=False,
            has_automation_logs=False,
            has_application_logs=False,
            ai_adjustment=0.30  # Max AI boost
        )
        
        base = breakdown.calculate_base_confidence()
        final = breakdown.calculate_final_confidence()
        
        # Even with max AI, should be low confidence
        assert base < 0.3
        assert final < 0.6  # AI can't make this high confidence
    
    def test_confidence_thresholds(self):
        """Test confidence threshold classifications."""
        assert ConfidenceThresholds.HIGH == 0.85
        assert ConfidenceThresholds.MEDIUM == 0.65
        assert ConfidenceThresholds.LOW == 0.40
        
        # Test classification
        high_breakdown = ConfidenceBreakdown(
            rule_score=0.9, signal_quality_score=0.9,
            history_score=0.9, log_completeness_score=1.0,
            ai_adjustment=0.0
        )
        assert high_breakdown.calculate_final_confidence() >= ConfidenceThresholds.HIGH
    
    def test_confidence_explanation(self):
        """Test confidence explanation generation."""
        rules = [Rule(
            id="TEST_001",
            description="Test rule",
            match_any=["error"],
            failure_type="PRODUCT_DEFECT",
            confidence=0.9,
            priority=10
        )]
        
        breakdown = build_confidence_breakdown(
            matched_rules=rules,
            signals=[{"type": "error"}],
            has_stacktrace=True,
            has_code_reference=True,
            historical_occurrences=5,
            is_consistent_history=True,
            has_automation_logs=True,
            has_application_logs=True,
            ai_adjustment=0.15
        )
        
        explanation = breakdown.get_explanation()
        assert isinstance(explanation, str)
        assert "Rule match" in explanation
        assert "Signal quality" in explanation
        assert "Historical consistency" in explanation
        assert "Log completeness" in explanation
        assert "AI adjustment" in explanation


# ============================================================================
# RULE ENGINE TESTS
# ============================================================================

class TestRuleEngine:
    """Comprehensive tests for rule-based classification."""
    
    def test_rule_matches_simple(self):
        """Test simple rule matching."""
        rule = Rule(
            id="TEST_001",
            description="Test rule",
            match_any=["NullPointerException"],
            failure_type="PRODUCT_DEFECT",
            confidence=0.9,
            priority=10
        )
        
        signals = [{"message": "NullPointerException at line 42"}]
        assert rule.matches(signals) is True
        
        signals_no_match = [{"message": "Different error"}]
        assert rule.matches(signals_no_match) is False
    
    def test_rule_matches_requires_all(self):
        """Test rule with requires_all logic."""
        rule = Rule(
            id="TEST_002",
            description="Test rule",
            match_any=["error"],
            requires_all=["database", "connection"],
            failure_type="ENVIRONMENT_ISSUE",
            confidence=0.85,
            priority=15
        )
        
        signals_match = [{"message": "database connection error timeout"}]
        assert rule.matches(signals_match) is True
        
        signals_partial = [{"message": "database error"}]  # Missing "connection"
        assert rule.matches(signals_partial) is False
    
    def test_rule_matches_excludes(self):
        """Test rule with excludes logic."""
        rule = Rule(
            id="TEST_003",
            description="Test rule",
            match_any=["Exception"],
            excludes=["test", "mock"],
            failure_type="PRODUCT_DEFECT",
            confidence=0.8,
            priority=20
        )
        
        signals_match = [{"message": "RuntimeException in production code"}]
        assert rule.matches(signals_match) is True
        
        signals_excluded = [{"message": "Exception in test setup"}]
        assert rule.matches(signals_excluded) is False
    
    def test_rule_pack_loading_selenium(self):
        """Test loading Selenium rule pack."""
        rule_pack = load_rule_pack("selenium")
        assert rule_pack is not None
        assert len(rule_pack.rules) > 0
        assert any(rule.id.startswith("SEL_") for rule in rule_pack.rules)
    
    def test_rule_pack_loading_pytest(self):
        """Test loading Pytest rule pack."""
        rule_pack = load_rule_pack("pytest")
        assert rule_pack is not None
        assert len(rule_pack.rules) > 0
        assert any(rule.id.startswith("PYT_") for rule in rule_pack.rules)
    
    def test_rule_pack_loading_all_frameworks(self):
        """Test loading rule packs for ALL 12 frameworks."""
        frameworks = [
            "selenium", "pytest", "robot", "generic",
            "playwright", "restassured", "cypress",
            "cucumber", "behave", "junit", "testng",
            "specflow", "nunit"
        ]
        
        for framework in frameworks:
            rule_pack = load_rule_pack(framework)
            assert rule_pack is not None, f"Failed to load {framework}"
            assert len(rule_pack.rules) > 0, f"No rules in {framework}"
            print(f"✅ {framework}: {len(rule_pack.rules)} rules")
    
    def test_rule_engine_classify_selenium(self):
        """Test rule engine classification for Selenium."""
        engine = RuleEngine(framework="selenium")
        
        signals = [{
            "message": "NoSuchElementException: Unable to locate element #login-button"
        }]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        assert failure_type == "AUTOMATION_DEFECT"
        assert confidence > 0.8
        assert len(matched_rules) > 0
    
    def test_rule_engine_classify_playwright(self):
        """Test rule engine classification for Playwright."""
        engine = RuleEngine(framework="playwright")
        
        signals = [{
            "message": "page.click: Target closed"
        }]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        assert failure_type == "AUTOMATION_DEFECT"
        assert len(matched_rules) > 0
    
    def test_rule_engine_classify_restassured(self):
        """Test rule engine classification for RestAssured."""
        engine = RuleEngine(framework="restassured")
        
        signals = [{
            "message": "500 Internal Server Error - status code 500"
        }]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        assert failure_type == "PRODUCT_DEFECT"
        assert confidence > 0.9  # High confidence for 500 errors
    
    def test_rule_engine_priority_selection(self):
        """Test that higher priority rules are selected first."""
        rule_pack = RulePack(
            framework="test",
            rules=[
                Rule(id="LOW", description="", match_any=["error"],
                     failure_type="PRODUCT_DEFECT", confidence=0.5, priority=50),
                Rule(id="HIGH", description="", match_any=["error"],
                     failure_type="AUTOMATION_DEFECT", confidence=0.9, priority=10)
            ]
        )
        
        engine = RuleEngine(framework="test")
        engine.rule_pack = rule_pack
        
        signals = [{"message": "error occurred"}]
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        # Should select HIGH priority rule
        assert matched_rules[0].id == "HIGH"
        assert failure_type == "AUTOMATION_DEFECT"
    
    def test_rule_engine_fallback_to_generic(self):
        """Test fallback to generic rules when framework-specific don't match."""
        engine = RuleEngine(framework="selenium")
        
        # Generic error that's not Selenium-specific
        signals = [{"message": "NullPointerException: user object is null"}]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        # Should still classify using generic rules
        assert failure_type in ["PRODUCT_DEFECT", "AUTOMATION_DEFECT"]
        assert len(matched_rules) > 0


# ============================================================================
# FLAKY DETECTION TESTS
# ============================================================================

class TestFlakyDetection:
    """Comprehensive tests for flaky detection system."""
    
    def test_failure_signature_generation(self):
        """Test failure signature generation."""
        sig = FailureSignature.generate(
            test_name="test_login",
            failure_type="PRODUCT_DEFECT",
            error_message="NullPointerException at line 42"
        )
        
        assert isinstance(sig.signature_hash, str)
        assert len(sig.signature_hash) == 64  # SHA256 hex
        assert sig.test_name == "test_login"
    
    def test_simplify_error_pattern(self):
        """Test error pattern simplification."""
        # Remove line numbers
        simplified = simplify_error_pattern("Error at line 42 in file.py:123")
        assert "42" not in simplified
        assert "123" not in simplified
        
        # Remove timestamps
        simplified = simplify_error_pattern("Error at 2024-01-30 14:30:15")
        assert "14:30:15" not in simplified
        
        # Remove memory addresses
        simplified = simplify_error_pattern("Object at 0x7f8b4c123456")
        assert "0x" not in simplified
    
    def test_flaky_detector_new_failure(self):
        """Test detecting new failure."""
        detector = FlakyDetector()
        
        nature, confidence, history = detector.analyze_failure(
            test_name="test_new",
            failure_type="PRODUCT_DEFECT",
            error_message="Error occurred",
            signals=[]
        )
        
        assert nature == FailureNature.UNKNOWN  # New failures are unknown
        assert history.occurrences == 1
        assert history.consecutive_failures == 1
    
    def test_flaky_detector_deterministic_failure(self):
        """Test detecting deterministic (consistent) failure."""
        detector = FlakyDetector()
        
        # Record 3 consecutive failures
        for i in range(3):
            nature, confidence, history = detector.analyze_failure(
                test_name="test_deterministic",
                failure_type="PRODUCT_DEFECT",
                error_message="Consistent error",
                signals=[]
            )
        
        assert nature == FailureNature.DETERMINISTIC
        assert history.consecutive_failures == 3
        assert history.pass_count == 0
    
    def test_flaky_detector_flaky_failure(self):
        """Test detecting flaky (intermittent) failure."""
        detector = FlakyDetector()
        
        # Fail -> Pass -> Fail pattern
        detector.analyze_failure(
            test_name="test_flaky",
            failure_type="ENVIRONMENT_ISSUE",
            error_message="Timeout",
            signals=[]
        )
        
        detector.record_pass("test_flaky")
        
        nature, confidence, history = detector.analyze_failure(
            test_name="test_flaky",
            failure_type="ENVIRONMENT_ISSUE",
            error_message="Timeout",
            signals=[]
        )
        
        assert nature == FailureNature.FLAKY
        assert history.pass_count > 0
        assert history.consecutive_failures < 3
    
    def test_flaky_detector_environment_issues_are_flaky(self):
        """Test that environment issues are classified as flaky."""
        detector = FlakyDetector()
        
        # Single environment failure
        nature, confidence, history = detector.analyze_failure(
            test_name="test_env",
            failure_type="ENVIRONMENT_ISSUE",
            error_message="Connection timeout",
            signals=[]
        )
        
        # Environment issues should lean toward flaky
        assert nature in [FailureNature.FLAKY, FailureNature.UNKNOWN]
    
    def test_flaky_detector_multiple_different_errors(self):
        """Test that multiple different errors indicate flakiness."""
        detector = FlakyDetector()
        
        # Different errors for same test
        detector.analyze_failure(
            test_name="test_multi_error",
            failure_type="AUTOMATION_DEFECT",
            error_message="Error type A",
            signals=[]
        )
        
        detector.analyze_failure(
            test_name="test_multi_error",
            failure_type="AUTOMATION_DEFECT",
            error_message="Error type B",
            signals=[]
        )
        
        nature, confidence, history = detector.analyze_failure(
            test_name="test_multi_error",
            failure_type="AUTOMATION_DEFECT",
            error_message="Error type C",
            signals=[]
        )
        
        assert history.different_errors_seen >= 3
        # Multiple different errors suggests flakiness
    
    def test_flaky_detector_is_flaky_method(self):
        """Test is_flaky() method."""
        detector = FlakyDetector()
        
        # Create flaky pattern
        detector.analyze_failure("test", "PRODUCT_DEFECT", "error", [])
        detector.record_pass("test")
        detector.analyze_failure("test", "PRODUCT_DEFECT", "error", [])
        
        assert detector.is_flaky("test") is True
    
    def test_flaky_detector_is_deterministic_method(self):
        """Test is_deterministic() method."""
        detector = FlakyDetector()
        
        # Create deterministic pattern
        for i in range(3):
            detector.analyze_failure("test", "PRODUCT_DEFECT", "error", [])
        
        assert detector.is_deterministic("test") is True
    
    def test_flaky_detector_get_flaky_tests(self):
        """Test getting all flaky tests."""
        detector = FlakyDetector()
        
        # Create multiple flaky tests
        for test in ["test1", "test2"]:
            detector.analyze_failure(test, "ENVIRONMENT_ISSUE", "timeout", [])
            detector.record_pass(test)
            detector.analyze_failure(test, "ENVIRONMENT_ISSUE", "timeout", [])
        
        flaky_tests = detector.get_flaky_tests()
        assert len(flaky_tests) == 2
    
    def test_flaky_detector_history_cleanup(self):
        """Test cleanup of old history."""
        detector = FlakyDetector(history_window_days=30)
        
        # Add old failure
        old_history = FailureHistory(
            test_name="test_old",
            signature=FailureSignature.generate("test_old", "PRODUCT_DEFECT", "error"),
            first_seen=datetime.now() - timedelta(days=35),
            last_seen=datetime.now() - timedelta(days=35),
            occurrences=1,
            consecutive_failures=1,
            pass_count=0
        )
        detector.failure_history[old_history.signature.signature_hash] = old_history
        
        # Cleanup should remove it
        detector.cleanup_old_history()
        assert len(detector.failure_history) == 0
    
    def test_flaky_detector_export_import(self):
        """Test export and import of history."""
        detector1 = FlakyDetector()
        
        # Add some history
        detector1.analyze_failure("test1", "PRODUCT_DEFECT", "error", [])
        detector1.analyze_failure("test2", "AUTOMATION_DEFECT", "timeout", [])
        
        # Export
        exported = detector1.export_history()
        assert isinstance(exported, list)
        assert len(exported) == 2
        
        # Import to new detector
        detector2 = FlakyDetector()
        detector2.import_history(exported)
        
        assert len(detector2.failure_history) == 2


# ============================================================================
# CI ANNOTATION TESTS
# ============================================================================

class TestCIAnnotation:
    """Comprehensive tests for CI annotation system."""
    
    def test_ci_decision_enum(self):
        """Test CI decision enumeration."""
        assert CIDecision.FAIL.value == "FAIL"
        assert CIDecision.WARN.value == "WARN"
        assert CIDecision.PASS.value == "PASS"
    
    def test_code_reference_creation(self):
        """Test code reference object."""
        ref = CodeReference(
            file="src/user.py",
            line=42,
            column=10
        )
        
        assert ref.file == "src/user.py"
        assert ref.line == 42
        assert ref.column == 10
    
    def test_ci_config_defaults(self):
        """Test CI configuration defaults."""
        config = CIConfig()
        
        assert config.fail_on_product_defect is True
        assert config.fail_on_automation_defect is False
        assert config.fail_on_flaky is False
        assert config.min_confidence_to_fail == 0.85
    
    def test_ci_output_creation(self):
        """Test CI output object creation."""
        output = CIOutput(
            test_name="test_user_login",
            failure_type="PRODUCT_DEFECT",
            confidence=0.92,
            nature="DETERMINISTIC",
            summary="NullPointerException in UserService",
            recommendation="Fix null check in getUserById method",
            ci_decision=CIDecision.FAIL
        )
        
        assert output.test_name == "test_user_login"
        assert output.confidence_percent == "92%"
        assert output.ci_decision == CIDecision.FAIL
    
    def test_ci_output_to_json(self):
        """Test CI output JSON conversion."""
        output = CIOutput(
            test_name="test_api",
            failure_type="PRODUCT_DEFECT",
            confidence=0.95,
            nature="DETERMINISTIC",
            summary="500 Internal Server Error",
            recommendation="Check server logs",
            ci_decision=CIDecision.FAIL,
            code_reference=CodeReference(file="api.py", line=100)
        )
        
        json_str = output.to_json()
        data = json.loads(json_str)
        
        assert data["test"] == "test_api"
        assert data["failure_type"] == "PRODUCT_DEFECT"
        assert data["confidence"] == 0.95
        assert data["ci_decision"] == "FAIL"
        assert data["code_reference"]["file"] == "api.py"
    
    def test_ci_output_to_markdown(self):
        """Test CI output Markdown conversion."""
        output = CIOutput(
            test_name="test_checkout",
            failure_type="AUTOMATION_DEFECT",
            confidence=0.88,
            nature="DETERMINISTIC",
            summary="Element not found: #checkout-button",
            recommendation="Update selector or wait for element",
            ci_decision=CIDecision.WARN
        )
        
        markdown = output.to_markdown()
        
        assert "test_checkout" in markdown
        assert "AUTOMATION_DEFECT" in markdown
        assert "88%" in markdown
        assert "⚠️" in markdown or "WARN" in markdown
    
    def test_should_fail_ci_product_defect_high_confidence(self):
        """Test CI should fail on high-confidence product defect."""
        analysis_result = {
            "failure_type": "PRODUCT_DEFECT",
            "confidence": 0.92,
            "nature": "DETERMINISTIC"
        }
        
        decision = should_fail_ci(analysis_result, CIConfig())
        assert decision == CIDecision.FAIL
    
    def test_should_fail_ci_automation_defect(self):
        """Test CI should warn (not fail) on automation defect."""
        analysis_result = {
            "failure_type": "AUTOMATION_DEFECT",
            "confidence": 0.90,
            "nature": "DETERMINISTIC"
        }
        
        decision = should_fail_ci(analysis_result, CIConfig())
        assert decision == CIDecision.WARN
    
    def test_should_fail_ci_flaky(self):
        """Test CI should pass (not fail) on flaky test."""
        analysis_result = {
            "failure_type": "PRODUCT_DEFECT",
            "confidence": 0.85,
            "nature": "FLAKY"
        }
        
        decision = should_fail_ci(analysis_result, CIConfig())
        assert decision == CIDecision.PASS
    
    def test_should_fail_ci_low_confidence(self):
        """Test CI should warn on low confidence."""
        analysis_result = {
            "failure_type": "PRODUCT_DEFECT",
            "confidence": 0.60,  # Below 0.85 threshold
            "nature": "DETERMINISTIC"
        }
        
        decision = should_fail_ci(analysis_result, CIConfig())
        assert decision == CIDecision.WARN
    
    def test_github_annotator_comment_format(self):
        """Test GitHub PR comment formatting."""
        annotator = GitHubAnnotator(CIConfig())
        
        output = CIOutput(
            test_name="test_payment",
            failure_type="PRODUCT_DEFECT",
            confidence=0.95,
            nature="DETERMINISTIC",
            summary="Payment processing failed",
            recommendation="Check payment gateway integration",
            ci_decision=CIDecision.FAIL
        )
        
        comment = annotator.create_github_comment([output])
        
        assert "test_payment" in comment
        assert "95%" in comment
        assert "FAIL" in comment or "❌" in comment
    
    def test_bitbucket_annotator_payload(self):
        """Test Bitbucket API payload generation."""
        annotator = BitbucketAnnotator(CIConfig())
        
        output = CIOutput(
            test_name="test_checkout",
            failure_type="PRODUCT_DEFECT",
            confidence=0.90,
            nature="DETERMINISTIC",
            summary="Checkout failed",
            recommendation="Debug checkout flow",
            ci_decision=CIDecision.FAIL,
            code_reference=CodeReference(file="checkout.py", line=50)
        )
        
        payload = annotator.create_api_payload([output])
        
        assert "text" in payload
        assert "checkout" in payload["text"].lower()
    
    def test_write_ci_output_file(self, tmp_path):
        """Test writing CI output to file."""
        output = CIOutput(
            test_name="test_example",
            failure_type="PRODUCT_DEFECT",
            confidence=0.88,
            nature="DETERMINISTIC",
            summary="Example failure",
            recommendation="Fix example",
            ci_decision=CIDecision.FAIL
        )
        
        output_file = tmp_path / "ci-output.json"
        write_ci_output_file([output], str(output_file))
        
        assert output_file.exists()
        
        data = json.loads(output_file.read_text())
        assert data["summary"]["total"] == 1
        assert len(data["failures"]) == 1
        assert data["failures"][0]["test"] == "test_example"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """End-to-end integration tests combining all systems."""
    
    def test_full_flow_without_ai(self):
        """Test complete flow WITHOUT AI assistance."""
        # 1. Load rules for Selenium
        engine = RuleEngine(framework="selenium")
        
        # 2. Classify failure
        signals = [{
            "message": "NoSuchElementException: Unable to locate element #login",
            "stacktrace": "at LoginPage.clickLogin(LoginPage.java:42)"
        }]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        # 3. Build confidence breakdown (NO AI)
        breakdown = build_confidence_breakdown(
            matched_rules=matched_rules,
            signals=signals,
            has_stacktrace=True,
            has_code_reference=True,
            historical_occurrences=0,
            is_consistent_history=False,
            has_automation_logs=True,
            has_application_logs=False,
            ai_adjustment=0.0  # NO AI
        )
        
        # 4. Detect flaky vs deterministic
        detector = FlakyDetector()
        nature, _, history = detector.analyze_failure(
            test_name="test_login",
            failure_type=failure_type,
            error_message=signals[0]["message"],
            signals=signals
        )
        
        # 5. Generate CI output
        ci_output = CIOutput(
            test_name="test_login",
            failure_type=failure_type,
            confidence=breakdown.calculate_final_confidence(),
            nature=nature.value,
            summary="Element locator issue in login test",
            recommendation=breakdown.get_explanation(),
            ci_decision=should_fail_ci({
                "failure_type": failure_type,
                "confidence": breakdown.calculate_final_confidence(),
                "nature": nature.value
            }, CIConfig())
        )
        
        # Assertions
        assert failure_type == "AUTOMATION_DEFECT"
        assert 0.0 <= breakdown.calculate_final_confidence() <= 1.0
        assert breakdown.ai_adjustment == 0.0  # Verified NO AI
        assert ci_output.ci_decision in [CIDecision.WARN, CIDecision.FAIL]
    
    def test_full_flow_with_ai(self):
        """Test complete flow WITH AI assistance."""
        # 1. Load rules
        engine = RuleEngine(framework="pytest")
        
        # 2. Classify failure
        signals = [{
            "message": "AssertionError: assert user.email == 'test@example.com'",
            "stacktrace": "test_user.py:25 in test_user_email"
        }]
        
        failure_type, confidence, matched_rules = engine.classify(signals)
        
        # 3. Build confidence WITH AI boost
        breakdown = build_confidence_breakdown(
            matched_rules=matched_rules,
            signals=signals,
            has_stacktrace=True,
            has_code_reference=True,
            historical_occurrences=5,
            is_consistent_history=True,
            has_automation_logs=True,
            has_application_logs=True,
            ai_adjustment=0.20  # AI agrees and boosts
        )
        
        # 4. Flaky detection
        detector = FlakyDetector()
        for i in range(3):  # 3 consecutive failures
            detector.analyze_failure(
                test_name="test_user_email",
                failure_type=failure_type,
                error_message=signals[0]["message"],
                signals=signals
            )
        
        nature = FailureNature.DETERMINISTIC  # Consistent failures
        
        # 5. CI output
        ci_output = CIOutput(
            test_name="test_user_email",
            failure_type=failure_type,
            confidence=breakdown.calculate_final_confidence(),
            nature=nature.value,
            summary="User email assertion failure",
            recommendation=breakdown.get_explanation(),
            ci_decision=should_fail_ci({
                "failure_type": failure_type,
                "confidence": breakdown.calculate_final_confidence(),
                "nature": nature.value
            }, CIConfig())
        )
        
        # Assertions
        assert failure_type == "PRODUCT_DEFECT"
        assert breakdown.ai_adjustment == 0.20  # Verified AI used
        assert breakdown.calculate_final_confidence() > breakdown.calculate_base_confidence()
        assert ci_output.ci_decision == CIDecision.FAIL  # High confidence product defect


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
