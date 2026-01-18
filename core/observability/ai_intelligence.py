"""
Phase 3 AI Intelligence Layer

AI-powered features that operate on metadata, not code:
- Flaky test detection (predictive)
- Missing coverage suggestions
- Test refactor recommendations
- Risk-based execution prioritization
- Auto-generation of tests (explicit opt-in only)

Design Contract:
- CrossBridge NEVER owns test execution
- CrossBridge NEVER regenerates tests post-migration
- AI suggestions are recommendations only
- Auto-generation requires explicit user approval
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
import psycopg2

logger = logging.getLogger(__name__)


@dataclass
class FlakyPrediction:
    """Prediction of test flakiness"""
    test_id: str
    flaky_probability: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    contributing_factors: List[str]
    historical_pass_rate: float
    recommendation: str


@dataclass
class CoverageGap:
    """Missing coverage suggestion"""
    gap_type: str  # uncovered_api | uncovered_page | uncovered_feature
    target_id: str  # API endpoint, page, or feature ID
    severity: str  # high | medium | low
    usage_frequency: int  # How often the API/page is used
    suggested_tests: List[str]  # Similar tests that could be extended
    reasoning: str


@dataclass
class RefactorRecommendation:
    """Test refactor suggestion"""
    test_id: str
    recommendation_type: str  # duplicate | fragile | slow | complex
    severity: str  # high | medium | low
    current_metrics: Dict[str, float]
    suggested_action: str
    expected_benefit: str


@dataclass
class RiskScore:
    """Risk-based execution priority"""
    test_id: str
    risk_score: float  # 0.0 (low risk) - 1.0 (high risk)
    risk_factors: List[str]
    priority: str  # critical | high | medium | low
    recommendation: str  # run_always | run_often | run_occasionally


@dataclass
class TestGenerationSuggestion:
    """Auto-generation suggestion (requires approval)"""
    target_type: str  # api | page | feature
    target_id: str
    suggested_test_name: str
    test_template: str  # Framework-specific template
    reasoning: str
    requires_approval: bool  # Always True


class AIIntelligence:
    """
    AI-powered intelligence layer for continuous optimization.
    
    CRITICAL: All AI features operate on metadata only. No code generation
    without explicit user approval.
    """
    
    def __init__(self, db_host: str, db_port: int, db_name: str, 
                 db_user: str, db_password: str):
        self.db_config = {
            'host': db_host,
            'port': db_port,
            'database': db_name,
            'user': db_user,
            'password': db_password
        }
    
    # =========================================================================
    # Flaky Test Prediction
    # =========================================================================
    
    def predict_flaky_tests(self, lookback_days: int = 30) -> List[FlakyPrediction]:
        """
        Predict which tests are likely to become flaky.
        
        Uses historical data to identify patterns:
        - Status oscillation (pass/fail alternation)
        - Duration variance
        - Error message patterns
        - Environmental correlations
        
        Args:
            lookback_days: Days of history to analyze
        
        Returns:
            List of flaky predictions
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            # Get test execution history
            cursor.execute("""
                SELECT 
                    test_id,
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passes,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures,
                    STDDEV(duration_seconds) as duration_variance,
                    AVG(duration_seconds) as avg_duration
                FROM test_execution_event
                WHERE event_timestamp > NOW() - INTERVAL '%s days'
                GROUP BY test_id
                HAVING COUNT(*) >= 10  -- Need sufficient history
            """, (lookback_days,))
            
            predictions = []
            
            for row in cursor.fetchall():
                test_id, total_runs, passes, failures, duration_variance, avg_duration = row
                
                if passes is None or failures is None:
                    continue
                
                pass_rate = passes / total_runs if total_runs > 0 else 1.0
                fail_rate = failures / total_runs if total_runs > 0 else 0.0
                
                # Calculate flakiness indicators
                status_oscillation = self._calculate_status_oscillation(cursor, test_id, lookback_days)
                duration_instability = (duration_variance or 0) / (avg_duration or 1)
                
                # Flaky if:
                # - Pass rate between 20% and 80% (oscillating)
                # - High status oscillation
                # - High duration variance
                flaky_probability = 0.0
                factors = []
                
                if 0.2 < pass_rate < 0.8:
                    flaky_probability += 0.4
                    factors.append(f"Unstable pass rate: {pass_rate:.1%}")
                
                if status_oscillation > 0.3:
                    flaky_probability += 0.3
                    factors.append(f"High status oscillation: {status_oscillation:.2f}")
                
                if duration_instability > 0.5:
                    flaky_probability += 0.2
                    factors.append(f"Duration variance: {duration_instability:.2f}")
                
                if flaky_probability > 0.4:  # Threshold for reporting
                    confidence = min(total_runs / 50, 1.0)  # More runs = higher confidence
                    
                    if flaky_probability > 0.7:
                        recommendation = "Investigate immediately - high flakiness probability"
                    elif flaky_probability > 0.5:
                        recommendation = "Monitor closely - moderate flakiness risk"
                    else:
                        recommendation = "Consider stabilizing - low flakiness risk"
                    
                    predictions.append(FlakyPrediction(
                        test_id=test_id,
                        flaky_probability=min(flaky_probability, 1.0),
                        confidence=confidence,
                        contributing_factors=factors,
                        historical_pass_rate=pass_rate,
                        recommendation=recommendation
                    ))
            
            return sorted(predictions, key=lambda p: p.flaky_probability, reverse=True)
            
        finally:
            cursor.close()
            conn.close()
    
    def _calculate_status_oscillation(self, cursor, test_id: str, lookback_days: int) -> float:
        """Calculate status oscillation rate (how often status changes)"""
        cursor.execute("""
            WITH ordered_tests AS (
                SELECT status, event_timestamp,
                       LAG(status) OVER (ORDER BY event_timestamp) as prev_status
                FROM test_execution_event
                WHERE test_id = %s
                  AND event_timestamp > NOW() - INTERVAL '%s days'
                ORDER BY event_timestamp
            )
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status != prev_status THEN 1 ELSE 0 END) as changes
            FROM ordered_tests
            WHERE prev_status IS NOT NULL
        """, (test_id, lookback_days))
        
        row = cursor.fetchone()
        if row and row[0] > 0:
            return row[1] / row[0]
        return 0.0
    
    # =========================================================================
    # Missing Coverage Detection
    # =========================================================================
    
    def find_coverage_gaps(self, min_usage_threshold: int = 5) -> List[CoverageGap]:
        """
        Identify APIs, pages, or features with insufficient test coverage.
        
        Strategy:
        - Find APIs/pages used in production but not covered by tests
        - Identify frequently-used endpoints with low coverage
        - Suggest similar tests that could be extended
        
        Args:
            min_usage_threshold: Minimum usage count to be considered important
        
        Returns:
            List of coverage gaps ordered by severity
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            gaps = []
            
            # Find uncovered APIs
            cursor.execute("""
                WITH api_coverage AS (
                    SELECT 
                        n.node_id as api_endpoint,
                        n.metadata->>'usage_count' as usage_count,
                        COUNT(DISTINCT e.from_node) as test_count
                    FROM coverage_graph_nodes n
                    LEFT JOIN coverage_graph_edges e 
                        ON n.node_id = e.to_node AND e.edge_type = 'calls_api'
                    WHERE n.node_type = 'api'
                    GROUP BY n.node_id, n.metadata
                )
                SELECT 
                    api_endpoint,
                    COALESCE(usage_count::int, 0) as usage,
                    test_count
                FROM api_coverage
                WHERE test_count < 2  -- Less than 2 tests
                ORDER BY usage DESC
                LIMIT 20
            """)
            
            for row in cursor.fetchall():
                api_endpoint, usage, test_count = row
                
                if usage >= min_usage_threshold:
                    severity = "high"
                elif usage >= min_usage_threshold / 2:
                    severity = "medium"
                else:
                    severity = "low"
                
                # Find similar tests
                similar_tests = self._find_similar_tests(cursor, api_endpoint, 'api')
                
                gaps.append(CoverageGap(
                    gap_type='uncovered_api',
                    target_id=api_endpoint,
                    severity=severity,
                    usage_frequency=usage,
                    suggested_tests=similar_tests,
                    reasoning=f"API used {usage} times but only covered by {test_count} test(s)"
                ))
            
            # Find uncovered pages
            cursor.execute("""
                WITH page_coverage AS (
                    SELECT 
                        n.node_id as page,
                        COUNT(DISTINCT e.from_node) as test_count
                    FROM coverage_graph_nodes n
                    LEFT JOIN coverage_graph_edges e 
                        ON n.node_id = e.to_node AND e.edge_type = 'visits_page'
                    WHERE n.node_type = 'page'
                    GROUP BY n.node_id
                )
                SELECT page, test_count
                FROM page_coverage
                WHERE test_count = 0
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                page, test_count = row
                
                similar_tests = self._find_similar_tests(cursor, page, 'page')
                
                gaps.append(CoverageGap(
                    gap_type='uncovered_page',
                    target_id=page,
                    severity='medium',
                    usage_frequency=0,
                    suggested_tests=similar_tests,
                    reasoning=f"Page '{page}' has no test coverage"
                ))
            
            return gaps
            
        finally:
            cursor.close()
            conn.close()
    
    def _find_similar_tests(self, cursor, target_id: str, target_type: str, limit: int = 3) -> List[str]:
        """Find tests that cover similar APIs/pages"""
        # Extract base path (e.g., /api/users/123 -> /api/users)
        if target_type == 'api':
            base_path = '/'.join(target_id.split('/')[:3])
            
            cursor.execute("""
                SELECT DISTINCT e.from_node
                FROM coverage_graph_edges e
                WHERE e.to_node LIKE %s || '%%'
                  AND e.edge_type = 'calls_api'
                LIMIT %s
            """, (base_path, limit))
        else:
            cursor.execute("""
                SELECT DISTINCT e.from_node
                FROM coverage_graph_edges e
                JOIN coverage_graph_nodes n ON e.to_node = n.node_id
                WHERE n.node_type = %s
                  AND e.from_node != %s
                LIMIT %s
            """, (target_type, target_id, limit))
        
        return [row[0] for row in cursor.fetchall()]
    
    # =========================================================================
    # Test Refactor Recommendations
    # =========================================================================
    
    def get_refactor_recommendations(self) -> List[RefactorRecommendation]:
        """
        Recommend tests that should be refactored.
        
        Detection criteria:
        - Duplicate tests (same API calls, same assertions)
        - Slow tests (duration > 10x median)
        - Complex tests (too many steps)
        - Fragile tests (high maintenance cost)
        
        Returns:
            List of refactor recommendations
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            recommendations = []
            
            # Find slow tests
            cursor.execute("""
                WITH test_stats AS (
                    SELECT 
                        test_id,
                        AVG(duration_seconds) as avg_duration,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_seconds) 
                            OVER () as median_duration
                    FROM test_execution_event
                    WHERE event_timestamp > NOW() - INTERVAL '30 days'
                    GROUP BY test_id
                )
                SELECT test_id, avg_duration, median_duration
                FROM test_stats
                WHERE avg_duration > median_duration * 5  -- 5x slower than median
                ORDER BY avg_duration DESC
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                test_id, avg_duration, median_duration = row
                
                slowdown_factor = avg_duration / median_duration if median_duration > 0 else 0
                
                recommendations.append(RefactorRecommendation(
                    test_id=test_id,
                    recommendation_type='slow',
                    severity='high' if slowdown_factor > 10 else 'medium',
                    current_metrics={
                        'avg_duration': avg_duration,
                        'median_duration': median_duration,
                        'slowdown_factor': slowdown_factor
                    },
                    suggested_action=f"Optimize test - {slowdown_factor:.1f}x slower than median",
                    expected_benefit=f"Could reduce execution time by {avg_duration - median_duration:.1f}s"
                ))
            
            # Find complex tests (too many API calls)
            cursor.execute("""
                SELECT 
                    e.from_node as test_id,
                    COUNT(DISTINCT e.to_node) as api_count
                FROM coverage_graph_edges e
                WHERE e.edge_type = 'calls_api'
                GROUP BY e.from_node
                HAVING COUNT(DISTINCT e.to_node) > 10  -- More than 10 APIs
                ORDER BY api_count DESC
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                test_id, api_count = row
                
                recommendations.append(RefactorRecommendation(
                    test_id=test_id,
                    recommendation_type='complex',
                    severity='medium',
                    current_metrics={'api_call_count': api_count},
                    suggested_action=f"Split test - calls {api_count} different APIs",
                    expected_benefit="Improved maintainability and isolation"
                ))
            
            return recommendations
            
        finally:
            cursor.close()
            conn.close()
    
    # =========================================================================
    # Risk-Based Execution Prioritization
    # =========================================================================
    
    def calculate_risk_scores(self) -> List[RiskScore]:
        """
        Calculate risk scores for tests to prioritize execution.
        
        Risk factors:
        - Flakiness history
        - Recent failures
        - Critical path coverage (APIs/features)
        - Change frequency
        - Business impact
        
        Returns:
            List of risk scores for all tests
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                WITH test_metrics AS (
                    SELECT 
                        test_id,
                        COUNT(*) as total_runs,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures,
                        MAX(event_timestamp) as last_run,
                        AVG(CASE WHEN status = 'failed' THEN 1.0 ELSE 0.0 END) as failure_rate
                    FROM test_execution_event
                    WHERE event_timestamp > NOW() - INTERVAL '30 days'
                    GROUP BY test_id
                ),
                critical_coverage AS (
                    SELECT 
                        e.from_node as test_id,
                        COUNT(DISTINCT e.to_node) as critical_api_count
                    FROM coverage_graph_edges e
                    JOIN coverage_graph_nodes n ON e.to_node = n.node_id
                    WHERE n.node_type = 'api'
                      AND n.metadata->>'critical' = 'true'
                    GROUP BY e.from_node
                )
                SELECT 
                    tm.test_id,
                    tm.total_runs,
                    tm.failures,
                    tm.failure_rate,
                    COALESCE(cc.critical_api_count, 0) as critical_apis
                FROM test_metrics tm
                LEFT JOIN critical_coverage cc ON tm.test_id = cc.test_id
                ORDER BY tm.failure_rate DESC, critical_apis DESC
            """)
            
            risk_scores = []
            
            for row in cursor.fetchall():
                test_id, total_runs, failures, failure_rate, critical_apis = row
                
                # Calculate risk score (0.0 - 1.0)
                risk_score = 0.0
                risk_factors = []
                
                # Factor 1: Recent failures (0-0.4)
                if failure_rate > 0.3:
                    risk_score += 0.4
                    risk_factors.append(f"High failure rate: {failure_rate:.1%}")
                elif failure_rate > 0.1:
                    risk_score += 0.2
                    risk_factors.append(f"Moderate failure rate: {failure_rate:.1%}")
                
                # Factor 2: Critical path coverage (0-0.3)
                if critical_apis > 5:
                    risk_score += 0.3
                    risk_factors.append(f"Covers {critical_apis} critical APIs")
                elif critical_apis > 0:
                    risk_score += 0.15
                    risk_factors.append(f"Covers {critical_apis} critical API(s)")
                
                # Factor 3: Flakiness (0-0.3)
                flaky_signals = self._check_flaky_signals(cursor, test_id)
                if flaky_signals > 0:
                    risk_score += min(0.3, flaky_signals * 0.1)
                    risk_factors.append(f"Flaky ({flaky_signals} signals)")
                
                # Determine priority
                if risk_score >= 0.7:
                    priority = "critical"
                    recommendation = "run_always"
                elif risk_score >= 0.5:
                    priority = "high"
                    recommendation = "run_often"
                elif risk_score >= 0.3:
                    priority = "medium"
                    recommendation = "run_occasionally"
                else:
                    priority = "low"
                    recommendation = "run_occasionally"
                
                risk_scores.append(RiskScore(
                    test_id=test_id,
                    risk_score=min(risk_score, 1.0),
                    risk_factors=risk_factors,
                    priority=priority,
                    recommendation=recommendation
                ))
            
            return sorted(risk_scores, key=lambda r: r.risk_score, reverse=True)
            
        finally:
            cursor.close()
            conn.close()
    
    def _check_flaky_signals(self, cursor, test_id: str) -> int:
        """Check how many flaky signals exist for this test"""
        cursor.execute("""
            SELECT COUNT(*)
            FROM drift_signals
            WHERE test_id = %s
              AND signal_type = 'flaky'
              AND detected_at > NOW() - INTERVAL '30 days'
        """, (test_id,))
        
        row = cursor.fetchone()
        return row[0] if row else 0
    
    # =========================================================================
    # Auto-Generation Suggestions (Requires Approval)
    # =========================================================================
    
    def suggest_test_generation(self, max_suggestions: int = 5) -> List[TestGenerationSuggestion]:
        """
        Suggest tests that could be auto-generated.
        
        CRITICAL: These are SUGGESTIONS only. Actual generation requires
        explicit user approval and happens outside CrossBridge.
        
        Suggestions based on:
        - Uncovered APIs with high usage
        - Similar test patterns
        - Framework templates
        
        Args:
            max_suggestions: Maximum number of suggestions
        
        Returns:
            List of generation suggestions (all require approval)
        """
        gaps = self.find_coverage_gaps(min_usage_threshold=10)
        
        suggestions = []
        
        for gap in gaps[:max_suggestions]:
            if gap.gap_type == 'uncovered_api':
                # Suggest API test
                framework = self._detect_framework_preference()
                template = self._get_test_template(framework, 'api', gap.target_id)
                
                suggestions.append(TestGenerationSuggestion(
                    target_type='api',
                    target_id=gap.target_id,
                    suggested_test_name=f"test_{gap.target_id.replace('/', '_').replace('-', '_')}",
                    test_template=template,
                    reasoning=f"API has {gap.usage_frequency} usages but minimal coverage",
                    requires_approval=True  # ALWAYS True
                ))
            
            elif gap.gap_type == 'uncovered_page':
                # Suggest page test
                framework = self._detect_framework_preference()
                template = self._get_test_template(framework, 'page', gap.target_id)
                
                suggestions.append(TestGenerationSuggestion(
                    target_type='page',
                    target_id=gap.target_id,
                    suggested_test_name=f"test_{gap.target_id}_page",
                    test_template=template,
                    reasoning=f"Page '{gap.target_id}' has no test coverage",
                    requires_approval=True  # ALWAYS True
                ))
        
        return suggestions
    
    def _detect_framework_preference(self) -> str:
        """Detect which framework is most commonly used"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT framework, COUNT(*) as count
                FROM test_execution_event
                WHERE event_timestamp > NOW() - INTERVAL '30 days'
                GROUP BY framework
                ORDER BY count DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            return row[0] if row else 'pytest'
            
        finally:
            cursor.close()
            conn.close()
    
    def _get_test_template(self, framework: str, target_type: str, target_id: str) -> str:
        """Get test template for framework"""
        if framework == 'pytest':
            if target_type == 'api':
                return f'''def test_{target_id.replace('/', '_')}():
    """Test {target_id} API endpoint"""
    # TODO: Add test implementation
    response = requests.get("{target_id}")
    assert response.status_code == 200
'''
            elif target_type == 'page':
                return f'''def test_{target_id}_page():
    """Test {target_id} page"""
    # TODO: Add test implementation
    page.goto("/{target_id}")
    assert page.is_visible("body")
'''
        
        elif framework == 'robot':
            if target_type == 'api':
                return f'''*** Test Cases ***
Test {target_id}
    [Documentation]    Test {target_id} API endpoint
    ${{response}}=    GET    {target_id}
    Should Be Equal As Numbers    ${{response.status_code}}    200
'''
        
        return "# Template not available for this framework"
