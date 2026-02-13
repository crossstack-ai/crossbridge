"""
Execution Orchestrator

The main entry point for test execution orchestration.
Coordinates strategies, adapters, and execution flow.

This is the "conductor" - it doesn't execute tests itself,
but coordinates all the pieces:
1. Strategy determines WHAT to run
2. Adapter determines HOW to run it
3. Orchestrator ties it all together
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from .api import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionPlan,
    ExecutionContext,
    ExecutionStatus,
)
from .strategies import create_strategy
from .adapters import create_adapter
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)


class ExecutionOrchestrator:
    """
    Orchestrates test execution from request to result.
    
    Flow:
    1. Build execution context (git, memory, history)
    2. Apply strategy to select tests
    3. Use adapter to execute tests
    4. Return standardized result
    """
    
    def __init__(self, workspace: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize orchestrator.
        
        Args:
            workspace: Path to project workspace
            config: Configuration dict (from crossbridge.yml)
        """
        self.workspace = workspace
        self.config = config or {}
        
        # Components (can be injected for testing)
        self.git_analyzer = None  # Will be lazy-loaded
        self.memory_service = None  # Will be lazy-loaded
        self.results_service = None  # Will be lazy-loaded
    
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute tests based on request.
        
        This is the main entry point.
        
        Args:
            request: Execution request with strategy, framework, etc.
            
        Returns:
            ExecutionResult with standardized metrics
        """
        logger.info(
            f"Starting execution: framework={request.framework}, "
            f"strategy={request.strategy.value}, env={request.environment}"
        )
        
        try:
            # Step 1: Plan execution (strategy)
            plan = self.plan(request)
            
            logger.info(
                f"Execution plan: {plan.total_tests()} tests selected "
                f"(confidence: {plan.confidence_score:.2f})"
            )
            
            # Dry run - return plan only
            if request.dry_run:
                logger.info("Dry run - skipping execution")
                return self._plan_to_dry_run_result(plan)
            
            # Step 2: Execute plan (adapter)
            result = self.run(plan)
            
            logger.info(
                f"Execution complete: {len(result.passed_tests)} passed, "
                f"{len(result.failed_tests)} failed, "
                f"{result.execution_time_seconds:.1f}s"
            )
            
            # Step 2.5: Process structured log artifacts (if enabled)
            if self.config.get('log_analysis', {}).get('enabled', False):
                result = self._process_log_artifacts(result)
            
            # Step 3: Store results (for future analysis)
            self._store_result(result, plan)
            
            return result
            
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            raise
    
    def plan(self, request: ExecutionRequest) -> ExecutionPlan:
        """
        Create execution plan (strategy selection).
        
        Args:
            request: Execution request
            
        Returns:
            ExecutionPlan with selected tests
        """
        # Build context
        context = self._build_context(request)
        
        logger.info(
            f"Built context: {len(context.available_tests)} tests available, "
            f"{len(context.changed_files)} files changed"
        )
        
        # Apply strategy
        strategy = create_strategy(request.strategy)
        plan = strategy.select_tests(context)
        
        reduction = plan.reduction_percentage(len(context.available_tests))
        logger.info(f"Test reduction: {reduction:.1f}%")
        
        return plan
    
    def run(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute plan using framework adapter.
        
        Args:
            plan: Execution plan
            
        Returns:
            ExecutionResult
        """
        # Get adapter
        adapter = create_adapter(plan.framework)
        
        logger.info(f"Using {adapter.framework_name} adapter")
        
        # Execute
        result = adapter.execute(plan, self.workspace)
        
        return result
    
    def _build_context(self, request: ExecutionRequest) -> ExecutionContext:
        """
        Build execution context.
        
        Aggregates data from multiple sources:
        - Available tests (from framework adapter)
        - Git changes (from git analyzer)
        - Test history (from results service)
        - Memory graph (from memory service)
        - Coverage data (from coverage service)
        """
        # Get available tests
        available_tests = self._discover_tests(request.framework)
        test_metadata = self._load_test_metadata(request.framework)
        
        # Get git context
        changed_files = request.changed_files or self._analyze_git_changes(request)
        
        # Get historical data
        test_history = self._load_test_history()
        flaky_tests = self._identify_flaky_tests()
        failure_rates = self._calculate_failure_rates()
        
        # Get coverage data
        test_to_code_mapping = self._load_coverage_mapping()
        code_to_test_mapping = self._invert_mapping(test_to_code_mapping)
        
        # Get memory graph (if available)
        memory_graph = self._load_memory_graph()
        
        return ExecutionContext(
            request=request,
            available_tests=available_tests,
            test_metadata=test_metadata,
            changed_files=changed_files,
            test_history=test_history,
            flaky_tests=flaky_tests,
            failure_rates=failure_rates,
            test_to_code_mapping=test_to_code_mapping,
            code_to_test_mapping=code_to_test_mapping,
            memory_graph=memory_graph,
            ci_environment=request.ci_mode,
        )
    
    def _discover_tests(self, framework: str) -> List[str]:
        """Discover available tests for framework"""
        # This would use framework-specific discovery
        # For now, placeholder
        logger.debug(f"Discovering tests for {framework}")
        
        # TODO: Integrate with existing framework adapters
        # from adapters.{framework} import discover_tests
        # return discover_tests(self.workspace)
        
        return []  # Placeholder
    
    def _load_test_metadata(self, framework: str) -> Dict[str, Dict[str, Any]]:
        """Load test metadata (tags, priority, etc.)"""
        # This would parse test files for annotations/tags
        # For now, placeholder
        return {}
    
    def _analyze_git_changes(self, request: ExecutionRequest) -> List[str]:
        """Analyze git changes"""
        if not request.base_branch:
            return []
        
        # This would use git service
        # For now, placeholder
        logger.debug(f"Analyzing git changes from {request.base_branch}")
        return []
    
    def _load_test_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load historical test results"""
        # This would query results database
        # For now, placeholder
        return {}
    
    def _identify_flaky_tests(self) -> List[str]:
        """Identify known flaky tests"""
        # This would use flaky detection service
        # For now, placeholder
        return []
    
    def _calculate_failure_rates(self) -> Dict[str, float]:
        """Calculate failure rates for tests"""
        # This would analyze historical results
        # For now, placeholder
        return {}
    
    def _load_coverage_mapping(self) -> Dict[str, List[str]]:
        """Load test-to-code coverage mapping"""
        # This would load from coverage database
        # For now, placeholder
        return {}
    
    def _invert_mapping(self, mapping: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Invert mapping (test->code to code->test)"""
        inverted = {}
        for test, files in mapping.items():
            for file in files:
                if file not in inverted:
                    inverted[file] = []
                inverted[file].append(test)
        return inverted
    
    def _load_memory_graph(self) -> Optional[Any]:
        """Load Crossbridge memory graph"""
        # This would load from memory service
        # For now, placeholder
        return None
    
    def _store_result(self, result: ExecutionResult, plan: ExecutionPlan):
        """Store execution result for future analysis"""
        # This would persist to results database
        logger.debug("Storing execution result")
    
    def _process_log_artifacts(self, result: ExecutionResult) -> ExecutionResult:
        """
        Process structured log artifacts (TestNG, framework logs).
        
        Args:
            result: Execution result with report/log paths
            
        Returns:
            Enhanced result with structured failures
        """
        try:
            from core.log_analysis.ingestion import (
                LogArtifacts,
                TestNGParser,
                FrameworkLogParser,
                CorrelationEngine
            )
            
            logger.info("Processing structured log artifacts")
            
            # Collect available artifacts
            artifacts = self._collect_log_artifacts(result)
            
            if not artifacts.validate():
                logger.warning("No valid log artifacts found for structured analysis")
                return result
            
            logger.info(f"Found artifacts: {', '.join(artifacts.available_sources())}")
            
            # Parse TestNG XML (if available)
            structured_failures = []
            if artifacts.testng_xml_path:
                parser = TestNGParser()
                structured_failures = parser.parse(artifacts.testng_xml_path)
                logger.info(f"Parsed {len(structured_failures)} TestNG test results")
            
            # Parse framework logs (if available)
            framework_parser = None
            if artifacts.framework_log_path:
                framework_parser = FrameworkLogParser()
                framework_parser.parse(artifacts.framework_log_path)
                logger.info(
                    f"Parsed framework logs: "
                    f"{len(framework_parser.get_errors())} errors, "
                    f"{len(framework_parser.get_warnings())} warnings"
                )
            
            # Correlate failures with logs
            if structured_failures:
                engine = CorrelationEngine()
                correlated = engine.correlate(structured_failures, framework_parser)
                
                summary = engine.get_summary()
                logger.info(
                    f"Correlation complete: {summary['total_failures']} failures, "
                    f"{summary['with_logs']} with framework logs, "
                    f"{summary['infra_related']} infra-related"
                )
                
                # Attach to result
                result.log_artifacts = artifacts
                result.structured_failures = correlated
            
            return result
            
        except ImportError:
            logger.warning("Log ingestion module not available, skipping structured analysis")
            return result
        except Exception as e:
            logger.error(f"Failed to process log artifacts: {e}", exc_info=True)
            return result
    
    def _collect_log_artifacts(self, result: ExecutionResult) -> 'LogArtifacts':
        """
        Collect log artifact paths from execution result.
        
        Args:
            result: Execution result
            
        Returns:
            LogArtifacts with available paths
        """
        from core.log_analysis.ingestion import LogArtifacts
        
        config = self.config.get('log_analysis', {})
        
        # Find TestNG XML
        testng_xml = None
        testng_path = config.get('testng', {}).get('path', 'test-output/testng-results.xml')
        
        # Check in report paths
        for report in result.report_paths:
            if 'testng' in report.lower() and report.endswith('.xml'):
                testng_xml = Path(report)
                break
        
        # Check default location
        if not testng_xml:
            default_path = self.workspace / testng_path
            if default_path.exists():
                testng_xml = default_path
        
        # Find framework log
        framework_log = None
        framework_log_path = config.get('framework_log', {}).get('path', 'logs/framework.log')
        
        # Check in log paths
        for log in result.log_paths:
            if 'framework' in log.lower() or log.endswith('.log'):
                framework_log = Path(log)
                break
        
        # Check default location
        if not framework_log:
            default_path = self.workspace / framework_log_path
            if default_path.exists():
                framework_log = default_path
        
        # Driver logs (optional)
        driver_logs = []
        if config.get('driver_logs', {}).get('enabled', False):
            driver_dir = self.workspace / config.get('driver_logs', {}).get('directory', 'logs/drivers')
            if driver_dir.exists():
                driver_logs = list(driver_dir.glob('*.log'))
        
        return LogArtifacts(
            testng_xml_path=testng_xml,
            framework_log_path=framework_log,
            driver_log_paths=driver_logs
        )
    
    def _plan_to_dry_run_result(self, plan: ExecutionPlan) -> ExecutionResult:
        """Convert plan to dry-run result"""
        from datetime import datetime
        
        return ExecutionResult(
            executed_tests=[],
            passed_tests=[],
            failed_tests=[],
            skipped_tests=plan.selected_tests,
            error_tests=[],
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[],
            log_paths=[],
            framework=plan.framework,
            environment=plan.environment,
            status=ExecutionStatus.COMPLETED,
        )


def create_orchestrator(
    workspace: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None
) -> ExecutionOrchestrator:
    """
    Factory function to create orchestrator.
    
    Args:
        workspace: Path to project workspace (defaults to current directory)
        config: Configuration dict (defaults to loading from crossbridge.yml)
        
    Returns:
        ExecutionOrchestrator instance
    """
    if workspace is None:
        workspace = Path.cwd()
    
    if config is None:
        # Load config from crossbridge.yml
        config = _load_config(workspace)
    
    return ExecutionOrchestrator(workspace, config)


def _load_config(workspace: Path) -> Dict[str, Any]:
    """Load configuration from crossbridge.yml"""
    import yaml
    
    config_path = workspace / "crossbridge.yml"
    if not config_path.exists():
        logger.warning("crossbridge.yml not found, using defaults")
        return {}
    
    with open(config_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config.get("execution", {})
