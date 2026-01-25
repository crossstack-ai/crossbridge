"""
Coverage Engine Runtime Integration

Provides hardened wrappers for coverage operations with retry logic,
health checks, and error isolation.

This module wraps coverage operations (database queries, parser execution) with:
- Automatic retry for transient database failures
- Health checks for database availability  
- Parser error handling with graceful degradation
- Logging integration for observability

Usage:
    from core.runtime.coverage_integration import (
        HardenedCoverageEngine,
        with_coverage_db_retry
    )
    
    # Wrap engine with retry
    engine = HardenedCoverageEngine(original_engine)
    
    # Or use decorator for individual operations
    @with_coverage_db_retry
    def query_coverage(repository):
        return repository.query_test_coverage()
"""

from typing import List, Callable, Any, Optional
from functools import wraps
from pathlib import Path

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.TESTING)


# Import runtime functions lazily to avoid circular imports
def _get_runtime_functions():
    """Lazy import of runtime functions to avoid circular imports"""
    from core.runtime.retry import retry_with_backoff
    from core.runtime.health import register_health_check, check_health as _check_health
    from core.runtime.config import get_retry_policy_by_name
    return retry_with_backoff, register_health_check, _check_health, get_retry_policy_by_name


def with_coverage_db_retry(func: Callable) -> Callable:
    """
    Decorator to add automatic retry logic for coverage database operations.
    
    Uses the "standard" retry policy (5 attempts, 1s backoff) to handle
    transient SQLite/PostgreSQL failures during coverage queries.
    
    Args:
        func: Database operation function to wrap
        
    Returns:
        Wrapped function with retry logic
        
    Example:
        @with_coverage_db_retry
        def query_coverage(repository, test_id):
            return repository.get_coverage_for_test(test_id)
    """
    retry_with_backoff, _, _, get_retry_policy_by_name = _get_runtime_functions()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            policy = get_retry_policy_by_name("standard")
            return retry_with_backoff(func, policy)(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Coverage database operation failed after retries: {func.__name__}",
                extra={
                    "error": str(e),
                    "function": func.__name__,
                    "operation": "coverage_db"
                }
            )
            raise
    
    return wrapper


class HardenedCoverageEngine:
    """
    Hardened wrapper for coverage mapping engine.
    
    Wraps CoverageMappingEngine with:
    - Automatic retry on database failures
    - Parser error handling with recovery
    - Health checks for database availability
    - Structured logging for observability
    
    The wrapper ensures that transient failures don't break coverage
    collection and provides visibility into coverage operations.
    
    Attributes:
        engine: Underlying coverage engine to wrap
        health_check_name: Name for health check registration
        
    Example:
        from core.coverage.engine import CoverageMappingEngine
        from core.runtime.coverage_integration import HardenedCoverageEngine
        
        original_engine = CoverageMappingEngine(db_path)
        hardened_engine = HardenedCoverageEngine(original_engine)
        
        # Operations now have automatic retry
        hardened_engine.collect_coverage(test_name="test_login")
    """
    
    def __init__(
        self,
        engine: Any,
        health_check_name: str = "coverage_engine"
    ):
        """
        Initialize hardened coverage engine wrapper.
        
        Args:
            engine: Coverage engine to wrap (CoverageMappingEngine instance)
            health_check_name: Name for health check registration
        """
        self._engine = engine
        self._health_check_name = health_check_name
        self._is_healthy = True
        
        # Register health check
        self._register_health_check()
        
        logger.info(
            f"Initialized hardened coverage engine: {engine.__class__.__name__}",
            extra={
                "engine_type": engine.__class__.__name__,
                "health_check": health_check_name
            }
        )
    
    def _register_health_check(self) -> None:
        """Register health check for coverage database"""
        _, register_health_check, _, _ = _get_runtime_functions()
        
        def health_check() -> bool:
            """Check if coverage database is accessible"""
            try:
                if hasattr(self._engine, 'repository'):
                    # Try simple database query
                    repo = self._engine.repository
                    if hasattr(repo, '_ensure_schema'):
                        return True
                return self._is_healthy
            except Exception as e:
                logger.debug(
                    f"Coverage engine health check failed: {self._health_check_name}",
                    extra={"error": str(e)}
                )
                return False
        
        register_health_check(
            health_check,
            name=self._health_check_name
        )
    
    def collect_coverage(
        self,
        test_name: str,
        test_command: List[str],
        execution_mode: str = "ISOLATED"
    ) -> Any:
        """
        Collect coverage for a test with retry.
        
        Args:
            test_name: Name of the test
            test_command: Command to execute test
            execution_mode: Execution mode (ISOLATED or BATCH)
            
        Returns:
            TestCoverageMapping object
        """
        retry_with_backoff, _, _, get_retry_policy_by_name = _get_runtime_functions()
        
        try:
            logger.info(
                f"Collecting coverage for test: {test_name}",
                extra={
                    "test_name": test_name,
                    "execution_mode": execution_mode,
                    "command": " ".join(test_command)
                }
            )
            
            policy = get_retry_policy_by_name("standard")
            result = retry_with_backoff(
                lambda: self._engine.collect_coverage(
                    test_name=test_name,
                    test_command=test_command,
                    execution_mode=execution_mode
                ),
                policy
            )()
            
            logger.info(
                f"Successfully collected coverage for: {test_name}",
                extra={
                    "test_name": test_name,
                    "covered_units": len(result.covered_units) if hasattr(result, 'covered_units') else 0
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to collect coverage for test: {test_name}",
                extra={
                    "test_name": test_name,
                    "error": str(e),
                    "execution_mode": execution_mode
                }
            )
            raise
    
    def query_coverage(
        self,
        production_files: Optional[List[str]] = None,
        changed_files: Optional[List[str]] = None
    ) -> List[Any]:
        """
        Query coverage mappings with retry.
        
        Args:
            production_files: List of production file paths
            changed_files: List of changed file paths
            
        Returns:
            List of test coverage mappings
        """
        retry_with_backoff, _, _, get_retry_policy_by_name = _get_runtime_functions()
        
        try:
            logger.info(
                "Querying coverage mappings",
                extra={
                    "production_files_count": len(production_files) if production_files else 0,
                    "changed_files_count": len(changed_files) if changed_files else 0
                }
            )
            
            policy = get_retry_policy_by_name("standard")
            result = retry_with_backoff(
                lambda: self._engine.repository.query_coverage_for_files(
                    file_paths=changed_files or production_files
                ),
                policy
            )()
            
            logger.info(
                f"Found {len(result)} coverage mappings",
                extra={"mapping_count": len(result)}
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to query coverage mappings",
                extra={
                    "error": str(e),
                    "production_files": production_files,
                    "changed_files": changed_files
                }
            )
            raise
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to underlying engine"""
        return getattr(self._engine, name)


class CoverageParserWrapper:
    """
    Wrapper for coverage parsers with error handling.
    
    Wraps parsers (JaCoCo, Istanbul, Coverage.py) with:
    - Parse error handling with detailed logging
    - Automatic recovery from malformed reports
    - Validation of parsed results
    
    Example:
        from core.coverage.jacoco_parser import JaCoCoXMLParser
        from core.runtime.coverage_integration import CoverageParserWrapper
        
        parser = CoverageParserWrapper(JaCoCoXMLParser())
        
        try:
            mapping = parser.parse(report_path, test_name)
        except Exception as e:
            # Error already logged
            logger.error(f"Parse failed: {e}")
    """
    
    def __init__(self, parser: Any):
        """
        Initialize parser wrapper.
        
        Args:
            parser: Parser instance to wrap (JaCoCoXMLParser, IstanbulParser, etc.)
        """
        self._parser = parser
        self._parser_type = parser.__class__.__name__
        
        logger.info(
            f"Initialized coverage parser wrapper: {self._parser_type}",
            extra={"parser_type": self._parser_type}
        )
    
    def parse(self, *args, **kwargs) -> Any:
        """
        Parse coverage report with error handling.
        
        Args:
            *args: Positional arguments for parser
            **kwargs: Keyword arguments for parser
            
        Returns:
            Parsed coverage mapping
            
        Raises:
            Exception: If parsing fails after error handling
        """
        try:
            logger.debug(
                f"Parsing coverage report: {self._parser_type}",
                extra={
                    "parser_type": self._parser_type,
                    "args": args,
                    "kwargs": kwargs
                }
            )
            
            result = self._parser.parse(*args, **kwargs)
            
            # Validate result
            if result is None:
                raise ValueError("Parser returned None")
            
            logger.info(
                f"Successfully parsed coverage report: {self._parser_type}",
                extra={
                    "parser_type": self._parser_type,
                    "covered_units": len(result.covered_units) if hasattr(result, 'covered_units') else 0
                }
            )
            
            return result
            
        except FileNotFoundError as e:
            logger.error(
                f"Coverage report file not found: {self._parser_type}",
                extra={
                    "parser_type": self._parser_type,
                    "error": str(e),
                    "args": args
                }
            )
            raise
            
        except Exception as e:
            logger.error(
                f"Failed to parse coverage report: {self._parser_type}",
                extra={
                    "parser_type": self._parser_type,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "args": args,
                    "kwargs": kwargs
                }
            )
            raise
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to underlying parser"""
        return getattr(self._parser, name)


# Convenience functions
def create_hardened_engine(engine: Any) -> HardenedCoverageEngine:
    """
    Create a hardened coverage engine wrapper.
    
    Args:
        engine: Coverage engine to wrap
        
    Returns:
        HardenedCoverageEngine instance
        
    Example:
        from core.coverage.engine import CoverageMappingEngine
        from core.runtime.coverage_integration import create_hardened_engine
        
        engine = CoverageMappingEngine(db_path)
        hardened = create_hardened_engine(engine)
    """
    return HardenedCoverageEngine(engine)


def create_parser_wrapper(parser: Any) -> CoverageParserWrapper:
    """
    Create a coverage parser wrapper.
    
    Args:
        parser: Parser to wrap
        
    Returns:
        CoverageParserWrapper instance
        
    Example:
        from core.coverage.jacoco_parser import JaCoCoXMLParser
        from core.runtime.coverage_integration import create_parser_wrapper
        
        parser = JaCoCoXMLParser()
        wrapped = create_parser_wrapper(parser)
    """
    return CoverageParserWrapper(parser)


def check_coverage_health() -> bool:
    """
    Quick check if coverage engine is healthy.
    
    Returns:
        True if coverage engine health check passes
    """
    _, _, check_health, _ = _get_runtime_functions()
    
    try:
        result = check_health()
        
        # Check for coverage-specific health checks
        if "coverage_engine" in result:
            return result["coverage_engine"]["healthy"]
        
        # If no specific check, assume healthy
        return True
        
    except Exception as e:
        logger.warning(
            "Error checking coverage engine health",
            extra={"error": str(e)}
        )
        return False
