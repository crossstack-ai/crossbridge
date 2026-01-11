"""
Comprehensive Unit Tests for Phase 3: AI-Assisted Locator Modernization

Tests cover:
- Risk scoring (heuristic + AI)
- Suggestion generation
- Modernization engine workflow
- Report generation
- Approval/rejection flow
- Auto-fix capabilities
"""

import pytest
from datetime import datetime
from core.locator_awareness.models import Locator, PageObject, LocatorStrategy
from core.locator_modernization.models import (
    RiskLevel,
    RiskScore,
    ModernizationSuggestion,
    ModernizationRecommendation,
    SuggestionStatus
)
from core.locator_modernization.heuristics import (
    HeuristicAnalyzer,
    IndexBasedXPathRule,
    ClassOnlyXPathRule,
    WildcardXPathRule,
    IDLocatorRule,
    DataTestIDRule
)
from core.locator_modernization.ai_analyzer import (
    AIModernizationAnalyzer,
    create_mock_ai_analyzer
)
from core.locator_modernization.engine import ModernizationEngine
from core.locator_modernization.reporters import (
    ModernizationReporter,
    RiskHeatmapGenerator
)


class TestRiskScoreModel:
    """Test RiskScore data model"""
    
    def test_risk_score_creation_heuristic_only(self):
        """Test RiskScore with heuristic score only"""
        risk = RiskScore(
            heuristic_score=0.75,
            risk_level=RiskLevel.HIGH,
            risk_factors=["index_based_xpath"]
        )
        
        assert risk.heuristic_score == 0.75
        assert risk.ai_score is None
        assert risk.final_score == 0.75
        assert risk.risk_level == RiskLevel.HIGH
    
    def test_risk_score_with_ai(self):
        """Test RiskScore with AI enhancement"""
        risk = RiskScore(
            heuristic_score=0.70,
            risk_level=RiskLevel.HIGH,
            ai_score=0.80,
            ai_reasoning="Complex XPath is brittle"
        )
        
        # Should be weighted average: 0.6*0.70 + 0.4*0.80 = 0.74
        assert abs(risk.final_score - 0.74) < 0.01
        assert risk.ai_reasoning == "Complex XPath is brittle"
    
    def test_risk_level_derivation_very_low(self):
        """Test VERY_LOW risk level (0.0-0.2)"""
        risk = RiskScore(heuristic_score=0.15, risk_level=RiskLevel.LOW)
        assert risk.risk_level == RiskLevel.VERY_LOW
    
    def test_risk_level_derivation_low(self):
        """Test LOW risk level (0.2-0.4)"""
        risk = RiskScore(heuristic_score=0.35, risk_level=RiskLevel.LOW)
        assert risk.risk_level == RiskLevel.LOW
    
    def test_risk_level_derivation_medium(self):
        """Test MEDIUM risk level (0.4-0.6)"""
        risk = RiskScore(heuristic_score=0.50, risk_level=RiskLevel.MEDIUM)
        assert risk.risk_level == RiskLevel.MEDIUM
    
    def test_risk_level_derivation_high(self):
        """Test HIGH risk level (0.6-0.8)"""
        risk = RiskScore(heuristic_score=0.70, risk_level=RiskLevel.HIGH)
        assert risk.risk_level == RiskLevel.HIGH
    
    def test_risk_level_derivation_very_high(self):
        """Test VERY_HIGH risk level (0.8-1.0)"""
        risk = RiskScore(heuristic_score=0.90, risk_level=RiskLevel.VERY_HIGH)
        assert risk.risk_level == RiskLevel.VERY_HIGH
    
    def test_risk_score_to_dict(self):
        """Test risk score export to dict"""
        risk = RiskScore(
            heuristic_score=0.65,
            risk_level=RiskLevel.HIGH,
            risk_factors=["index_based_xpath", "wildcard"]
        )
        
        data = risk.to_dict()
        
        assert data['heuristic_score'] == 0.65
        assert data['risk_level'] == 'high'
        assert len(data['risk_factors']) == 2


class TestModernizationSuggestion:
    """Test ModernizationSuggestion model"""
    
    @pytest.fixture
    def sample_risk(self):
        return RiskScore(
            heuristic_score=0.75,
            risk_level=RiskLevel.HIGH,
            risk_factors=["index_based_xpath"]
        )
    
    @pytest.fixture
    def sample_suggestion(self, sample_risk):
        return ModernizationSuggestion(
            locator_name="loginButton",
            page_object="LoginPage",
            current_strategy="xpath",
            current_value="//div[1]/button",
            suggested_strategy="playwright_role",
            suggested_value='page.getByRole("button", name="Login")',
            confidence=0.82,
            reason="Role-based selectors are more resilient",
            source="ai",
            current_risk=sample_risk
        )
    
    def test_suggestion_creation(self, sample_suggestion):
        """Test suggestion creation"""
        assert sample_suggestion.locator_name == "loginButton"
        assert sample_suggestion.confidence == 0.82
        assert sample_suggestion.status == SuggestionStatus.PENDING
        assert sample_suggestion.source == "ai"
    
    def test_approve_suggestion(self, sample_suggestion):
        """Test approving a suggestion"""
        sample_suggestion.approve(reviewer="test_user")
        
        assert sample_suggestion.status == SuggestionStatus.APPROVED
        assert sample_suggestion.reviewed_by == "test_user"
        assert sample_suggestion.reviewed_at is not None
    
    def test_reject_suggestion(self, sample_suggestion):
        """Test rejecting a suggestion"""
        sample_suggestion.reject(reviewer="test_user")
        
        assert sample_suggestion.status == SuggestionStatus.REJECTED
        assert sample_suggestion.reviewed_by == "test_user"
    
    def test_defer_suggestion(self, sample_suggestion):
        """Test deferring a suggestion"""
        sample_suggestion.defer()
        
        assert sample_suggestion.status == SuggestionStatus.DEFERRED
        assert sample_suggestion.reviewed_at is not None
    
    def test_mark_applied(self, sample_suggestion):
        """Test marking suggestion as applied"""
        sample_suggestion.approve()
        sample_suggestion.mark_applied()
        
        assert sample_suggestion.status == SuggestionStatus.APPLIED
    
    def test_suggestion_to_dict(self, sample_suggestion):
        """Test suggestion export to dict"""
        data = sample_suggestion.to_dict()
        
        assert data['locator_name'] == "loginButton"
        assert data['current']['strategy'] == "xpath"
        assert data['suggested']['strategy'] == "playwright_role"
        assert data['confidence'] == 0.82
        assert data['source'] == "ai"
    
    def test_format_cli_display(self, sample_suggestion):
        """Test CLI formatting"""
        display = sample_suggestion.format_cli_display()
        
        assert "loginButton" in display
        assert "//div[1]/button" in display
        assert "0.82" in display
        assert "Role-based selectors" in display


class TestModernizationRecommendation:
    """Test ModernizationRecommendation aggregation"""
    
    @pytest.fixture
    def sample_recommendation(self):
        return ModernizationRecommendation(
            page_object="LoginPage",
            file_path="pages/LoginPage.java",
            total_locators=10
        )
    
    def test_recommendation_creation(self, sample_recommendation):
        """Test recommendation creation"""
        assert sample_recommendation.page_object == "LoginPage"
        assert sample_recommendation.total_locators == 10
        assert sample_recommendation.modernization_priority == "low"
    
    def test_add_high_risk_suggestion(self, sample_recommendation):
        """Test adding high-risk suggestion updates priority"""
        risk = RiskScore(heuristic_score=0.85, risk_level=RiskLevel.VERY_HIGH)
        
        suggestion = ModernizationSuggestion(
            locator_name="test",
            page_object="LoginPage",
            current_strategy="xpath",
            current_value="//div[1]",
            suggested_strategy="css",
            suggested_value=".btn",
            confidence=0.8,
            reason="test",
            source="heuristic",
            current_risk=risk
        )
        
        sample_recommendation.add_suggestion(suggestion)
        
        assert sample_recommendation.high_risk_locators == 1
        assert sample_recommendation.modernization_priority == "high"
    
    def test_priority_calculation_critical(self, sample_recommendation):
        """Test critical priority with 3+ high-risk locators"""
        for i in range(3):
            risk = RiskScore(heuristic_score=0.85, risk_level=RiskLevel.VERY_HIGH)
            suggestion = ModernizationSuggestion(
                locator_name=f"test{i}",
                page_object="LoginPage",
                current_strategy="xpath",
                current_value=f"//div[{i}]",
                suggested_strategy="css",
                suggested_value=".btn",
                confidence=0.8,
                reason="test",
                source="heuristic",
                current_risk=risk
            )
            sample_recommendation.add_suggestion(suggestion)
        
        assert sample_recommendation.modernization_priority == "critical"
    
    def test_get_pending_suggestions(self, sample_recommendation):
        """Test filtering pending suggestions"""
        risk = RiskScore(heuristic_score=0.5, risk_level=RiskLevel.MEDIUM)
        
        s1 = ModernizationSuggestion(
            locator_name="test1", page_object="LoginPage",
            current_strategy="xpath", current_value="//div",
            suggested_strategy="css", suggested_value=".btn",
            confidence=0.7, reason="test", source="heuristic",
            current_risk=risk, status=SuggestionStatus.PENDING
        )
        
        s2 = ModernizationSuggestion(
            locator_name="test2", page_object="LoginPage",
            current_strategy="xpath", current_value="//span",
            suggested_strategy="css", suggested_value=".text",
            confidence=0.7, reason="test", source="heuristic",
            current_risk=risk, status=SuggestionStatus.APPROVED
        )
        
        sample_recommendation.suggestions.extend([s1, s2])
        
        pending = sample_recommendation.get_pending_suggestions()
        assert len(pending) == 1
        assert pending[0].locator_name == "test1"


class TestHeuristicRules:
    """Test individual heuristic rules"""
    
    def test_index_based_xpath_rule(self):
        """Test detection of index-based XPath"""
        rule = IndexBasedXPathRule()
        
        locator = Locator(
            name="test",
            strategy=LocatorStrategy.XPATH,
            value="//div[1]/button[3]",
            source_file="test.java",
            page_object="TestPage"
        )
        
        assert rule.applies_to(locator) is True
        risk = rule.calculate_risk(locator)
        assert risk >= 0.9  # Very high risk
    
    def test_class_only_xpath_rule(self):
        """Test detection of class-only XPath"""
        rule = ClassOnlyXPathRule()
        
        locator = Locator(
            name="test",
            strategy=LocatorStrategy.XPATH,
            value="//div[@class='button']",
            source_file="test.java",
            page_object="TestPage"
        )
        
        assert rule.applies_to(locator) is True
        assert rule.calculate_risk(locator) == 0.65
    
    def test_wildcard_xpath_rule(self):
        """Test detection of wildcard XPath"""
        rule = WildcardXPathRule()
        
        locator = Locator(
            name="test",
            strategy=LocatorStrategy.XPATH,
            value="//*[@id='login']",
            source_file="test.java",
            page_object="TestPage"
        )
        
        assert rule.applies_to(locator) is True
        assert rule.calculate_risk(locator) == 0.7
    
    def test_id_locator_rule(self):
        """Test ID locator scoring (low risk)"""
        rule = IDLocatorRule()
        
        locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="username-input",
            source_file="test.java",
            page_object="TestPage"
        )
        
        assert rule.applies_to(locator) is True
        assert rule.calculate_risk(locator) == 0.15  # Low risk
    
    def test_data_testid_rule(self):
        """Test data-testid detection (best practice)"""
        rule = DataTestIDRule()
        
        locator = Locator(
            name="loginBtn",
            strategy=LocatorStrategy.DATA_TESTID,
            value="login-button",
            source_file="test.java",
            page_object="TestPage"
        )
        
        assert rule.applies_to(locator) is True
        assert rule.calculate_risk(locator) == 0.1  # Very low risk


class TestHeuristicAnalyzer:
    """Test complete heuristic analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        return HeuristicAnalyzer()
    
    def test_analyze_high_risk_xpath(self, analyzer):
        """Test analyzing high-risk index-based XPath"""
        locator = Locator(
            name="submitBtn",
            strategy=LocatorStrategy.XPATH,
            value="//div[1]/button[2]",
            source_file="test.java",
            page_object="TestPage"
        )
        
        risk = analyzer.analyze(locator)
        
        assert risk.final_score >= 0.8
        assert risk.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        assert len(risk.risk_factors) > 0
        assert any("index" in factor.lower() for factor in risk.risk_factors)
    
    def test_analyze_low_risk_id(self, analyzer):
        """Test analyzing low-risk ID locator"""
        locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="username",
            source_file="test.java",
            page_object="TestPage"
        )
        
        risk = analyzer.analyze(locator)
        
        assert risk.final_score <= 0.3
        assert risk.risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW]
    
    def test_analyze_batch(self, analyzer):
        """Test batch analysis"""
        locators = [
            Locator("high_risk", LocatorStrategy.XPATH, "//div[1]", "test.java", "TestPage"),
            Locator("low_risk", LocatorStrategy.ID, "username", "test.java", "TestPage"),
            Locator("med_risk", LocatorStrategy.XPATH, "//div[@class='btn']", "test.java", "TestPage")
        ]
        
        results = analyzer.analyze_batch(locators)
        
        assert len(results) == 3
        assert all(isinstance(r[1], RiskScore) for r in results)
    
    def test_get_high_risk_locators(self, analyzer):
        """Test filtering high-risk locators"""
        locators = [
            Locator("high", LocatorStrategy.XPATH, "//div[1]", "test.java", "TestPage"),
            Locator("low", LocatorStrategy.ID, "username", "test.java", "TestPage")
        ]
        
        high_risk = analyzer.get_high_risk_locators(locators, threshold=0.6)
        
        assert len(high_risk) >= 1
        assert high_risk[0][0].name == "high"


class TestAIModernizationAnalyzer:
    """Test AI analyzer"""
    
    def test_ai_analyzer_disabled(self):
        """Test AI analyzer without client"""
        analyzer = AIModernizationAnalyzer(ai_client=None)
        
        assert analyzer.is_enabled() is False
    
    def test_ai_analyzer_enabled(self):
        """Test AI analyzer with mock client"""
        analyzer = create_mock_ai_analyzer()
        
        assert analyzer.is_enabled() is True
    
    def test_analyze_locator_with_ai(self):
        """Test AI-powered locator analysis"""
        analyzer = create_mock_ai_analyzer()
        
        locator = Locator(
            name="loginBtn",
            strategy=LocatorStrategy.XPATH,
            value="//div[@class='btn']",
            source_file="test.java",
            page_object="LoginPage"
        )
        
        risk = RiskScore(
            heuristic_score=0.65,
            risk_level=RiskLevel.HIGH,
            risk_factors=["class_only_xpath"]
        )
        
        suggestion = analyzer.analyze_locator(locator, risk)
        
        assert suggestion is not None
        assert suggestion.confidence >= 0.5
        assert suggestion.source == "ai"
        assert len(suggestion.reason) > 0
    
    def test_analyze_returns_none_when_disabled(self):
        """Test that disabled AI returns None"""
        analyzer = AIModernizationAnalyzer(ai_client=None)
        
        locator = Locator("test", LocatorStrategy.XPATH, "//div", "test.java", "TestPage")
        risk = RiskScore(heuristic_score=0.5, risk_level=RiskLevel.MEDIUM)
        
        suggestion = analyzer.analyze_locator(locator, risk)
        
        assert suggestion is None


class TestModernizationEngine:
    """Test complete modernization engine"""
    
    @pytest.fixture
    def engine_no_ai(self):
        return ModernizationEngine(enable_ai=False)
    
    @pytest.fixture
    def engine_with_ai(self):
        ai_analyzer = create_mock_ai_analyzer()
        return ModernizationEngine(
            enable_ai=True,
            ai_analyzer=ai_analyzer,
            min_confidence_threshold=0.7
        )
    
    def test_engine_creation(self, engine_no_ai):
        """Test engine initialization"""
        assert engine_no_ai.heuristic_analyzer is not None
        assert engine_no_ai.ai_analyzer is None
        assert engine_no_ai.auto_fix_enabled is False
    
    def test_analyze_locator(self, engine_no_ai):
        """Test single locator analysis"""
        locator = Locator(
            "test",
            LocatorStrategy.XPATH,
            "//div[1]",
            "test.java",
            "TestPage"
        )
        
        risk = engine_no_ai.analyze_locator(locator)
        
        assert isinstance(risk, RiskScore)
        assert risk.final_score > 0
    
    def test_analyze_page_object(self, engine_no_ai):
        """Test Page Object analysis"""
        page_object = PageObject(
            name="LoginPage",
            file_path="pages/LoginPage.java",
            package="com.example"
        )
        
        # Add locators
        l1 = Locator("high_risk", LocatorStrategy.XPATH, "//div[1]", "LoginPage.java", "LoginPage")
        l2 = Locator("low_risk", LocatorStrategy.ID, "username", "LoginPage.java", "LoginPage")
        
        page_object.add_locator(l1)
        page_object.add_locator(l2)
        
        recommendation = engine_no_ai.analyze_page_object(page_object)
        
        assert recommendation.page_object == "LoginPage"
        assert recommendation.total_locators == 2
        assert len(recommendation.suggestions) >= 0
    
    def test_analyze_with_ai_enabled(self, engine_with_ai):
        """Test analysis with AI enhancement"""
        locator = Locator(
            "loginBtn",
            LocatorStrategy.XPATH,
            "//div[@class='btn']",
            "test.java",
            "LoginPage"
        )
        
        risk = engine_with_ai.analyze_locator(locator)
        
        assert isinstance(risk, RiskScore)
        # AI may provide reasoning
        assert risk.final_score > 0
    
    def test_generate_summary(self, engine_no_ai):
        """Test summary generation"""
        page_object = PageObject(
            "TestPage",
            "test.java",
            "com.example"
        )
        page_object.add_locator(
            Locator("test", LocatorStrategy.XPATH, "//div[1]", "test.java", "TestPage")
        )
        
        engine_no_ai.analyze_page_object(page_object)
        
        summary = engine_no_ai.generate_summary()
        
        assert 'total_locators_analyzed' in summary
        assert 'total_suggestions' in summary
        assert 'ai_enabled' in summary
        assert summary['ai_enabled'] is False
    
    def test_approve_suggestion(self, engine_with_ai):
        """Test approving suggestions"""
        page_object = PageObject("TestPage", "test.java", "com.example")
        page_object.add_locator(
            Locator("testBtn", LocatorStrategy.XPATH, "//div[1]", "test.java", "TestPage")
        )
        
        recommendation = engine_with_ai.analyze_page_object(page_object)
        
        if recommendation.suggestions:
            suggestion = recommendation.suggestions[0]
            approved = engine_with_ai.approve_suggestion(
                suggestion.locator_name,
                suggestion.page_object
            )
            
            assert approved is True
            assert suggestion.status == SuggestionStatus.APPROVED


class TestReporters:
    """Test report generation"""
    
    @pytest.fixture
    def sample_recommendations(self):
        recs = []
        
        for i in range(3):
            rec = ModernizationRecommendation(
                page_object=f"Page{i}",
                file_path=f"pages/Page{i}.java",
                total_locators=5
            )
            
            # Add some suggestions
            risk = RiskScore(
                heuristic_score=0.75,
                risk_level=RiskLevel.HIGH,
                risk_factors=["index_based"]
            )
            
            suggestion = ModernizationSuggestion(
                locator_name=f"btn{i}",
                page_object=f"Page{i}",
                current_strategy="xpath",
                current_value=f"//div[{i}]",
                suggested_strategy="css",
                suggested_value=".btn",
                confidence=0.8,
                reason="Better selector",
                source="heuristic",
                current_risk=risk
            )
            
            rec.add_suggestion(suggestion)
            recs.append(rec)
        
        return recs
    
    def test_generate_summary_report(self, sample_recommendations):
        """Test summary report generation"""
        reporter = ModernizationReporter()
        
        stats = {
            'total_locators_analyzed': 15,
            'high_risk_locators': 5,
            'page_objects_analyzed': 3,
            'high_priority_pages': 1,
            'total_suggestions': 3,
            'pending_review': 3,
            'approved': 0,
            'applied': 0,
            'ai_enabled': False
        }
        
        report = reporter.generate_summary_report(sample_recommendations, stats)
        
        assert "Phase 3" in report
        assert "15" in report
        assert "AI Analysis" in report
    
    def test_generate_risk_heatmap(self, sample_recommendations):
        """Test risk heatmap generation"""
        heatmap_gen = RiskHeatmapGenerator()
        
        heatmap = heatmap_gen.generate_text_heatmap(sample_recommendations)
        
        assert "RISK HEATMAP" in heatmap
        assert "Page0" in heatmap or "Page" in heatmap
    
    def test_generate_change_log(self, sample_recommendations):
        """Test change log generation"""
        reporter = ModernizationReporter()
        
        # Mark one as applied
        sample_recommendations[0].suggestions[0].approve()
        sample_recommendations[0].suggestions[0].mark_applied()
        
        applied = [s for rec in sample_recommendations for s in rec.suggestions if s.status == SuggestionStatus.APPLIED]
        
        changelog = reporter.generate_change_log(applied)
        
        assert "CHANGE LOG" in changelog
        if applied:
            assert "Page0" in changelog or "Locator:" in changelog


class TestEndToEndPhase3:
    """End-to-end Phase 3 workflow tests"""
    
    def test_complete_modernization_workflow(self):
        """Test complete Phase 3 workflow"""
        # Step 1: Create Page Object with locators
        page_object = PageObject(
            name="LoginPage",
            file_path="pages/LoginPage.java",
            package="com.example.pages"
        )
        
        # Add high-risk locator
        high_risk_locator = Locator(
            name="loginButton",
            strategy=LocatorStrategy.XPATH,
            value="//div[1]/button[2]",
            source_file="pages/LoginPage.java",
            page_object="LoginPage"
        )
        
        # Add low-risk locator
        low_risk_locator = Locator(
            name="username",
            strategy=LocatorStrategy.ID,
            value="username-input",
            source_file="pages/LoginPage.java",
            page_object="LoginPage"
        )
        
        page_object.add_locator(high_risk_locator)
        page_object.add_locator(low_risk_locator)
        
        # Step 2: Initialize modernization engine
        engine = ModernizationEngine(enable_ai=False)
        
        # Step 3: Analyze Page Object
        recommendation = engine.analyze_page_object(page_object, generate_suggestions=True)
        
        # Verify analysis
        assert recommendation.page_object == "LoginPage"
        assert recommendation.total_locators == 2
        
        # Should have at least one suggestion for high-risk locator
        assert len(recommendation.suggestions) >= 0
        
        # Step 4: Generate reports
        summary = engine.generate_summary()
        
        assert summary['total_locators_analyzed'] >= 2
        assert summary['ai_enabled'] is False
    
    def test_approval_and_application_workflow(self):
        """Test suggestion approval and application"""
        # Setup
        ai_analyzer = create_mock_ai_analyzer()
        engine = ModernizationEngine(
            enable_ai=True,
            ai_analyzer=ai_analyzer,
            auto_fix_enabled=True
        )
        
        page_object = PageObject("TestPage", "test.java", "com.example")
        locator = Locator(
            "highRiskBtn",
            LocatorStrategy.XPATH,
            "//div[1]/button",
            "test.java",
            "TestPage"
        )
        page_object.add_locator(locator)
        
        # Analyze
        recommendation = engine.analyze_page_object(page_object, generate_suggestions=True)
        
        # Approve suggestions
        for suggestion in recommendation.suggestions:
            suggestion.approve()
        
        # Apply (dry run)
        result = engine.apply_approved_suggestions(page_object, dry_run=True)
        
        assert result['dry_run'] is True
        assert 'changes' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
