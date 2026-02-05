"""
Main Execution Analyzer

Orchestrates the complete analysis pipeline:
1. Log normalization (adapters)
2. Signal extraction
3. Rule-based classification
4. Code reference resolution
5. Optional AI enhancement

This is the main entry point for execution intelligence.
"""

from typing import List, Optional, Dict, Any
import logging

from core.execution.intelligence.models import (
    ExecutionEvent,
    FailureSignal,
    FailureClassification,
    AnalysisResult,
    FailureType,
    CodeReference,
)
from core.execution.intelligence.adapters import parse_logs
from core.execution.intelligence.extractor import CompositeExtractor
from core.execution.intelligence.classifier import RuleBasedClassifier
from core.execution.intelligence.resolver import CodeReferenceResolver
from core.logging import get_logger

logger = get_logger(__name__)


class ExecutionAnalyzer:
    """
    Main execution intelligence analyzer.
    
    Provides framework-agnostic failure analysis with:
    - Deterministic classification (works without AI)
    - Optional AI enhancement
    - Code reference resolution
    - Structured output for CI/CD
    
    Example:
        analyzer = ExecutionAnalyzer(workspace_root="/path/to/project")
        result = analyzer.analyze(
            raw_log=log_content,
            test_name="test_login",
            framework="pytest"
        )
        
        if result.is_product_defect():
            print(f"Product bug: {result.classification.reason}")
    """
    
    def __init__(
        self,
        workspace_root: Optional[str] = None,
        enable_ai: bool = False,
        ai_provider: Optional[Any] = None
    ):
        """
        Initialize analyzer.
        
        Args:
            workspace_root: Root directory of test project
            enable_ai: Enable AI reasoning enhancement
            ai_provider: AI provider instance (optional)
        """
        self.workspace_root = workspace_root
        self.enable_ai = enable_ai
        self.ai_provider = ai_provider
        
        # Initialize components
        self.extractor = CompositeExtractor()
        self.classifier = RuleBasedClassifier()
        self.resolver = CodeReferenceResolver(workspace_root)
        
        logger.info(
            f"ExecutionAnalyzer initialized (AI: {enable_ai}, workspace: {workspace_root})"
        )
    
    def analyze(
        self,
        raw_log: str,
        test_name: str,
        framework: str = "unknown",
        test_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Analyze test execution logs.
        
        Args:
            raw_log: Raw log content
            test_name: Name of the test
            framework: Framework name (pytest, selenium, robot, etc.)
            test_file: Path to test file
            context: Additional context (environment, metadata, etc.)
            
        Returns:
            AnalysisResult with classification and details
        """
        context = context or {}
        
        try:
            # Step 1: Normalize logs
            logger.debug(f"Parsing logs for test: {test_name}")
            events = parse_logs(raw_log)
            logger.info(f"Parsed {len(events)} events for {test_name[:50]}")
            if events:
                logger.info(f"First event: level={events[0].level}, message={events[0].message[:100]}")
            
            # Step 2: Extract failure signals
            logger.debug("Extracting failure signals")
            signals = self.extractor.extract_all(events)
            logger.debug(f"Extracted {len(signals)} failure signals")
            
            # Step 3: Classify failure (deterministic)
            logger.debug("Classifying failure")
            classification = self.classifier.classify(signals, context)
            
            # Step 4: Resolve code reference (for automation defects)
            if classification and classification.failure_type == FailureType.AUTOMATION_DEFECT:
                logger.debug("Resolving code reference")
                code_ref = self._resolve_code_reference(signals)
                if code_ref:
                    classification.code_reference = code_ref
                    logger.debug(f"Code reference: {code_ref.file}:{code_ref.line}")
            
            # Step 5: Optional AI enhancement
            if self.enable_ai and self.ai_provider and classification:
                logger.debug("Applying AI enhancement")
                classification = self._enhance_with_ai(
                    classification, signals, events, context
                )
            
            # Build result
            result = AnalysisResult(
                test_name=test_name,
                test_file=test_file,
                status="FAILED",
                classification=classification,
                signals=signals,
                events=events,
                framework=framework,
                metadata=context
            )
            
            logger.info(
                f"Analysis complete: {test_name} -> {classification.failure_type.value if classification else 'UNKNOWN'} "
                f"(confidence: {classification.confidence if classification else 0.0:.2f})"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Analysis failed for {test_name}: {str(e)}", exc_info=True)
            
            # Return minimal result with error
            return AnalysisResult(
                test_name=test_name,
                test_file=test_file,
                status="ERROR",
                framework=framework,
                metadata={"error": str(e)}
            )
    
    def analyze_batch(
        self,
        test_logs: List[Dict[str, Any]]
    ) -> List[AnalysisResult]:
        """
        Analyze multiple test executions in batch.
        
        Args:
            test_logs: List of dicts with keys: raw_log, test_name, framework, etc.
            
        Returns:
            List of AnalysisResult objects
        """
        results = []
        
        for i, log_entry in enumerate(test_logs):
            logger.info(f"Analyzing test {i+1}/{len(test_logs)}: {log_entry.get('test_name')}")
            
            result = self.analyze(
                raw_log=log_entry.get('raw_log', ''),
                test_name=log_entry.get('test_name', f'test_{i}'),
                framework=log_entry.get('framework', 'unknown'),
                test_file=log_entry.get('test_file'),
                context=log_entry.get('context', {})
            )
            
            results.append(result)
        
        return results
    
    def get_summary(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """
        Get summary statistics for batch analysis.
        
        Args:
            results: List of analysis results
            
        Returns:
            Summary dictionary
        """
        total = len(results)
        
        # Count by failure type
        by_type = {
            FailureType.PRODUCT_DEFECT: 0,
            FailureType.AUTOMATION_DEFECT: 0,
            FailureType.ENVIRONMENT_ISSUE: 0,
            FailureType.CONFIGURATION_ISSUE: 0,
            FailureType.UNKNOWN: 0,
        }
        
        for result in results:
            if result.classification:
                by_type[result.classification.failure_type] += 1
            else:
                by_type[FailureType.UNKNOWN] += 1
        
        # Calculate percentages
        by_type_pct = {
            ft.value: (count / total * 100 if total > 0 else 0)
            for ft, count in by_type.items()
        }
        
        # Average confidence
        confidences = [
            r.classification.confidence
            for r in results
            if r.classification
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "total_tests": total,
            "by_type": {ft.value: count for ft, count in by_type.items()},
            "by_type_percentage": by_type_pct,
            "average_confidence": avg_confidence,
            "product_defects": by_type[FailureType.PRODUCT_DEFECT],
            "automation_defects": by_type[FailureType.AUTOMATION_DEFECT],
            "environment_issues": by_type[FailureType.ENVIRONMENT_ISSUE],
            "configuration_issues": by_type[FailureType.CONFIGURATION_ISSUE],
            "unknown": by_type[FailureType.UNKNOWN],
        }
    
    def _resolve_code_reference(self, signals: List[FailureSignal]) -> Optional[CodeReference]:
        """Resolve code reference from signals"""
        # Try each signal that has a stacktrace
        for signal in signals:
            if signal.stacktrace:
                code_ref = self.resolver.resolve(signal)
                if code_ref:
                    return code_ref
        
        return None
    
    def _enhance_with_ai(
        self,
        classification: FailureClassification,
        signals: List[FailureSignal],
        events: List[ExecutionEvent],
        context: Dict[str, Any]
    ) -> FailureClassification:
        """
        Enhance classification with AI reasoning.
        
        AI can:
        - Adjust confidence based on historical data
        - Provide more detailed explanation
        - Suggest fixes (never auto-fix)
        - Correlate with similar failures
        """
        try:
            from core.execution.intelligence.ai_enhancement import AIEnhancer
            
            enhancer = AIEnhancer(self.ai_provider)
            enhanced = enhancer.enhance(classification, signals, events, context)
            
            return enhanced
        
        except ImportError:
            logger.warning("AI enhancement not available (missing dependencies)")
            return classification
        
        except Exception as e:
            logger.error(f"AI enhancement failed: {str(e)}")
            # Return original classification on error
            return classification
    
    def should_fail_ci(
        self,
        results: List[AnalysisResult],
        fail_on: List[FailureType]
    ) -> bool:
        """
        Determine if CI should fail based on failure types.
        
        Args:
            results: Analysis results
            fail_on: List of failure types that should fail CI
            
        Returns:
            True if CI should fail
        """
        for result in results:
            if result.should_fail_ci(fail_on):
                return True
        
        return False
    
    def analyze_batch(
        self,
        test_logs: List[Dict[str, Any]],
        parallel: bool = True,
        max_workers: int = 4
    ) -> List[AnalysisResult]:
        """
        Analyze multiple test logs in batch.
        
        This is significantly faster than calling analyze() in a loop
        for large test suites (100+ tests).
        
        Args:
            test_logs: List of test log dictionaries with keys:
                - log_content: Raw log text (required)
                - test_name: Test name (required)
                - framework: Framework name (required)
                - test_file: Test file path (optional)
                - context: Additional context (optional)
            parallel: Use parallel processing (default True)
            max_workers: Max parallel workers (default 4)
        
        Returns:
            List of AnalysisResult objects (same order as input)
        
        Example:
            test_logs = [
                {
                    "log_content": log1,
                    "test_name": "test_login",
                    "framework": "pytest"
                },
                {
                    "log_content": log2,
                    "test_name": "test_checkout",
                    "framework": "selenium"
                }
            ]
            
            results = analyzer.analyze_batch(test_logs, parallel=True)
            
            # Filter failures
            failures = [r for r in results if r.is_failure()]
            product_bugs = [r for r in results if r.is_product_defect()]
        """
        logger.info(f"Batch analyzing {len(test_logs)} tests (parallel={parallel})")
        
        if parallel and len(test_logs) > 1:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all jobs
                future_to_idx = {}
                for idx, test_log in enumerate(test_logs):
                    future = executor.submit(
                        self.analyze,
                        raw_log=test_log.get('raw_log') or test_log.get('log_content'),
                        test_name=test_log['test_name'],
                        framework=test_log.get('framework', 'unknown'),
                        test_file=test_log.get('test_file'),
                        context=test_log.get('context', {})
                    )
                    future_to_idx[future] = idx
                
                # Collect results in order
                results = [None] * len(test_logs)
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        logger.error(f"Batch analysis failed for test {idx}: {str(e)}")
                        # Return error result
                        results[idx] = AnalysisResult(
                            test_name=test_logs[idx]['test_name'],
                            framework=test_logs[idx].get('framework', 'unknown'),
                            status='ERROR',
                            metadata={'error': str(e)}
                        )
                
                return results
        else:
            # Sequential processing
            results = []
            for test_log in test_logs:
                try:
                    result = self.analyze(
                        raw_log=test_log.get('raw_log') or test_log.get('log_content'),
                        test_name=test_log['test_name'],
                        framework=test_log.get('framework', 'unknown'),
                        test_file=test_log.get('test_file'),
                        context=test_log.get('context', {})
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch analysis failed for {test_log['test_name']}: {str(e)}")
                    results.append(AnalysisResult(
                        test_name=test_log['test_name'],
                        framework=test_log.get('framework', 'unknown'),
                        status='ERROR',
                        metadata={'error': str(e)}
                    ))
            
            return results
