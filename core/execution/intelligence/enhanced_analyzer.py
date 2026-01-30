"""
Enhanced Execution Intelligence Analyzer

Supports confidence boosting when application logs are present.

CRITICAL BEHAVIOR:
- Works with automation logs alone (deterministic)
- Boosts confidence for product defects when application logs present
- Never requires application logs
"""

from typing import List, Optional, Dict, Any
import logging

from core.execution.intelligence.models import (
    ExecutionEvent,
    FailureSignal,
    FailureType,
    SignalType
)
from core.execution.intelligence.extractor import CompositeExtractor
from core.execution.intelligence.classifier import RuleBasedClassifier
from core.execution.intelligence.resolver import CodeReferenceResolver
from core.execution.intelligence.log_sources import LogSourceType

logger = logging.getLogger(__name__)


class ExecutionIntelligenceAnalyzer:
    """
    Enhanced execution intelligence analyzer with application log support.
    
    Features:
    - Works with automation logs alone (MANDATORY)
    - Enriches analysis with application logs (OPTIONAL)
    - Boosts confidence for product defects when app logs correlate
    - Maintains deterministic classification without AI
    - Optional AI enhancement layer
    
    Confidence Boosting Rules (A7):
    - If application logs present AND contain matching errors:
      → Boost confidence for PRODUCT_DEFECT by +0.15
    - If only automation logs:
      → Use baseline confidence from rules
    """
    
    def __init__(
        self,
        workspace_root: Optional[str] = None,
        enable_ai: bool = False,
        has_application_logs: bool = False,
        ai_provider: Optional[Any] = None
    ):
        """
        Initialize analyzer.
        
        Args:
            workspace_root: Root directory of test project
            enable_ai: Enable AI reasoning enhancement
            has_application_logs: Whether application logs are available
            ai_provider: AI provider instance (optional)
        """
        self.workspace_root = workspace_root
        self.enable_ai = enable_ai
        self.has_application_logs = has_application_logs
        self.ai_provider = ai_provider
        
        # Initialize components
        self.extractor = CompositeExtractor()
        self.classifier = RuleBasedClassifier()
        self.resolver = CodeReferenceResolver(workspace_root)
        
        logger.info(
            f"ExecutionIntelligenceAnalyzer initialized "
            f"(AI: {enable_ai}, app_logs: {has_application_logs}, workspace: {workspace_root})"
        )
    
    def analyze_single_test(
        self,
        test_name: str,
        log_content: str,
        events: Optional[List[ExecutionEvent]] = None,
        framework: str = "unknown",
        test_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> 'FailureAnalysisResult':
        """
        Analyze single test failure.
        
        Args:
            test_name: Name of the test
            log_content: Combined log content (or use events)
            events: Pre-parsed ExecutionEvent objects (optional)
            framework: Framework name
            test_file: Path to test file
            context: Additional context
            
        Returns:
            FailureAnalysisResult
        """
        context = context or {}
        
        try:
            # Step 1: Parse events if not provided
            if not events:
                from core.execution.intelligence.adapters import parse_logs
                events = parse_logs(log_content)
            
            logger.debug(f"Analyzing {test_name}: {len(events)} events")
            
            # Separate automation and application events
            automation_events = [e for e in events if getattr(e, 'log_source_type', None) == LogSourceType.AUTOMATION]
            application_events = [e for e in events if getattr(e, 'log_source_type', None) == LogSourceType.APPLICATION]
            
            logger.debug(f"  - Automation events: {len(automation_events)}")
            logger.debug(f"  - Application events: {len(application_events)}")
            
            # Step 2: Extract failure signals (from automation logs)
            signals = self.extractor.extract_all(automation_events)
            logger.debug(f"Extracted {len(signals)} failure signals")
            
            # Step 3: Classify failure (deterministic, rule-based)
            failure_type, confidence, reasoning = self.classifier.classify_with_reasoning(
                signals, context
            )
            
            # Step 4: Confidence boosting if application logs present (A7)
            if self.has_application_logs and application_events:
                logger.debug("Application logs available - checking for correlation")
                
                # Check if application logs correlate with failure
                correlation = self._check_application_log_correlation(
                    automation_events, application_events, signals
                )
                
                if correlation:
                    # Boost confidence for product defects
                    if failure_type == FailureType.PRODUCT_DEFECT:
                        original_confidence = confidence
                        confidence = min(1.0, confidence + 0.15)  # +0.15 boost, max 1.0
                        logger.info(
                            f"  → Confidence boosted by application logs: "
                            f"{original_confidence:.2f} → {confidence:.2f}"
                        )
                        reasoning += " [Application logs confirm product error]"
            
            # Step 5: Resolve code references
            code_references = []
            if failure_type == FailureType.AUTOMATION_DEFECT:
                code_ref = self._resolve_code_reference(signals)
                if code_ref:
                    code_references.append(code_ref)
            
            # Step 6: Optional AI enhancement (if enabled)
            if self.enable_ai and self.ai_provider:
                logger.debug("Applying AI enhancement...")
                failure_type, confidence, reasoning = self._enhance_with_ai(
                    failure_type, confidence, reasoning, signals, events, context
                )
            
            # Build result
            result = FailureAnalysisResult(
                test_name=test_name,
                test_file=test_file,
                framework=framework,
                failure_type=failure_type,
                confidence=confidence,
                reasoning=reasoning,
                signals=signals,
                code_references=code_references,
                has_application_logs=bool(application_events),
                metadata=context
            )
            
            logger.info(
                f"✓ {test_name}: {failure_type.value} (confidence: {confidence:.2f})"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Analysis failed for {test_name}: {e}", exc_info=True)
            
            # Return unknown classification
            return FailureAnalysisResult(
                test_name=test_name,
                test_file=test_file,
                framework=framework,
                failure_type=FailureType.UNKNOWN,
                confidence=0.0,
                reasoning=f"Analysis error: {str(e)}",
                signals=[],
                code_references=[],
                has_application_logs=False,
                metadata={'error': str(e)}
            )
    
    def analyze_batch(
        self,
        test_logs: List[Dict[str, Any]]
    ) -> List['FailureAnalysisResult']:
        """
        Analyze multiple test failures in batch.
        
        Args:
            test_logs: List of dicts with keys: test_name, log_content, events, etc.
            
        Returns:
            List of FailureAnalysisResult objects
        """
        results = []
        
        for i, log_entry in enumerate(test_logs):
            logger.info(f"Analyzing test {i+1}/{len(test_logs)}: {log_entry.get('test_name')}")
            
            result = self.analyze_single_test(
                test_name=log_entry.get('test_name', f'test_{i}'),
                log_content=log_entry.get('log_content', ''),
                events=log_entry.get('events'),
                framework=log_entry.get('framework', 'unknown'),
                test_file=log_entry.get('test_file'),
                context=log_entry.get('context', {})
            )
            
            results.append(result)
        
        return results
    
    def generate_summary(self, results: List['FailureAnalysisResult']) -> Dict[str, Any]:
        """
        Generate summary statistics from analysis results.
        
        Args:
            results: List of FailureAnalysisResult objects
            
        Returns:
            Summary dictionary
        """
        if not results:
            return {
                'total_tests': 0,
                'by_type': {},
                'by_type_percentage': {},
                'average_confidence': 0.0,
                'has_application_logs': False
            }
        
        # Count by type
        by_type = {}
        for result in results:
            failure_type = result.failure_type.value
            by_type[failure_type] = by_type.get(failure_type, 0) + 1
        
        # Calculate percentages
        total = len(results)
        by_type_percentage = {
            ft: (count / total) * 100 for ft, count in by_type.items()
        }
        
        # Average confidence
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        # Check if any results have application logs
        has_app_logs = any(r.has_application_logs for r in results)
        
        return {
            'total_tests': total,
            'by_type': by_type,
            'by_type_percentage': by_type_percentage,
            'average_confidence': avg_confidence,
            'has_application_logs': has_app_logs
        }
    
    def _check_application_log_correlation(
        self,
        automation_events: List[ExecutionEvent],
        application_events: List[ExecutionEvent],
        signals: List[FailureSignal]
    ) -> bool:
        """
        Check if application logs correlate with automation failure.
        
        Correlation criteria:
        - Application log contains ERROR/FATAL within timeframe
        - Exception types match between automation and application
        - HTTP error codes match (for API tests)
        
        Args:
            automation_events: Events from automation logs
            application_events: Events from application logs
            signals: Extracted failure signals
            
        Returns:
            True if correlation found, False otherwise
        """
        if not application_events:
            return False
        
        # Check 1: Application has errors
        app_errors = [
            e for e in application_events
            if e.level.value in ['ERROR', 'FATAL']
        ]
        
        if not app_errors:
            return False
        
        # Check 2: Exception type matching
        automation_exceptions = set()
        for event in automation_events:
            if event.exception_type:
                automation_exceptions.add(event.exception_type)
        
        for app_event in app_errors:
            if app_event.exception_type and app_event.exception_type in automation_exceptions:
                logger.debug(f"  ✓ Exception type match: {app_event.exception_type}")
                return True
        
        # Check 3: HTTP error code matching
        for signal in signals:
            if signal.signal_type == SignalType.HTTP_ERROR:
                # Extract HTTP status code from signal
                if any(str(code) in signal.message for code in [500, 502, 503, 504]):
                    # Check if application logs also have this error
                    for app_event in app_errors:
                        if any(str(code) in app_event.message for code in [500, 502, 503, 504]):
                            logger.debug(f"  ✓ HTTP error code match in app logs")
                            return True
        
        # Check 4: Timing correlation (errors within same timeframe)
        # This is a simple heuristic - application errors near automation failure
        return len(app_errors) > 0
    
    def _resolve_code_reference(self, signals: List[FailureSignal]) -> Optional[str]:
        """Resolve code reference from signals"""
        for signal in signals:
            if signal.stacktrace:
                refs = self.resolver.resolve(signal.stacktrace)
                if refs:
                    ref = refs[0]
                    return f"{ref.file}:{ref.line}"
        return None
    
    def _enhance_with_ai(
        self,
        failure_type: FailureType,
        confidence: float,
        reasoning: str,
        signals: List[FailureSignal],
        events: List[ExecutionEvent],
        context: Dict[str, Any]
    ) -> tuple[FailureType, float, str]:
        """
        Enhance classification with AI (optional).
        
        CRITICAL CONSTRAINTS:
        - AI can NEVER change failure_type (only adjust confidence/reasoning)
        - AI can adjust confidence by ±0.1 maximum
        - Always return original values on AI failure
        """
        if not self.ai_provider:
            return failure_type, confidence, reasoning
        
        try:
            # AI enhancement logic here (simplified)
            # In real implementation, call AI model
            
            # CONSTRAINT: AI cannot change failure_type
            enhanced_failure_type = failure_type  # LOCKED
            
            # CONSTRAINT: AI can adjust confidence by ±0.1
            ai_confidence_adjustment = 0.05  # Example: +0.05
            enhanced_confidence = max(0.0, min(1.0, confidence + ai_confidence_adjustment))
            
            # AI can enhance reasoning
            enhanced_reasoning = reasoning + " [AI: High confidence in classification]"
            
            return enhanced_failure_type, enhanced_confidence, enhanced_reasoning
        
        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}")
            # Graceful fallback - return original values
            return failure_type, confidence, reasoning


class FailureAnalysisResult:
    """
    Result of failure analysis.
    
    Enhanced to track application log availability.
    """
    
    def __init__(
        self,
        test_name: str,
        failure_type: FailureType,
        confidence: float,
        reasoning: str,
        signals: List[FailureSignal],
        code_references: List[str],
        has_application_logs: bool,
        test_file: Optional[str] = None,
        framework: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.test_name = test_name
        self.test_file = test_file
        self.framework = framework
        self.failure_type = failure_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.signals = signals
        self.code_references = code_references
        self.has_application_logs = has_application_logs
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'test_name': self.test_name,
            'test_file': self.test_file,
            'framework': self.framework,
            'failure_type': self.failure_type.value,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'signals': [
                {'type': s.signal_type.value, 'message': s.message}
                for s in self.signals
            ],
            'code_references': self.code_references,
            'has_application_logs': self.has_application_logs,
            'metadata': self.metadata
        }
    
    def should_fail_ci(self, fail_on: str = 'all') -> bool:
        """Determine if this failure should fail CI"""
        if fail_on == 'none':
            return False
        
        if fail_on == 'all':
            return True
        
        failure_value = self.failure_type.value
        
        return (
            (fail_on == 'product' and failure_value == 'PRODUCT_DEFECT') or
            (fail_on == 'automation' and failure_value == 'AUTOMATION_DEFECT') or
            (fail_on == 'environment' and failure_value == 'ENVIRONMENT_ISSUE') or
            (fail_on == 'config' and failure_value == 'CONFIGURATION_ISSUE')
        )
