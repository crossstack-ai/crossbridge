"""
Performance optimizations for large repository handling.

Provides parallel processing, batch operations, and memory-efficient
algorithms for repositories with 10,000+ test files.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Iterator, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import multiprocessing as mp
from functools import partial
import os

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result from test discovery."""
    file_path: str
    test_count: int
    framework: Optional[str] = None
    error: Optional[str] = None


class ParallelTestDiscovery:
    """
    Parallel test file discovery for large repositories.
    
    Features:
    - Multi-threaded file scanning
    - Worker pool management
    - Progress tracking
    - Error handling per file
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize parallel discovery.
        
        Args:
            max_workers: Number of worker threads (default: CPU count * 2)
        """
        self.max_workers = max_workers or (os.cpu_count() or 4) * 2
        logger.info(f"Initialized parallel discovery with {self.max_workers} workers")
    
    def discover_tests(
        self,
        root_dir: Path,
        patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[DiscoveryResult]:
        """
        Discover test files in parallel.
        
        Args:
            root_dir: Root directory to scan
            patterns: File patterns to match (default: ["test_*.py", "*_test.py"])
            exclude_patterns: Patterns to exclude
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            List of DiscoveryResult objects
            
        Example:
            >>> discovery = ParallelTestDiscovery()
            >>> results = discovery.discover_tests(
            ...     Path("/large/repo"),
            ...     patterns=["test_*.py"],
            ...     progress_callback=lambda cur, total: print(f"{cur}/{total}")
            ... )
        """
        if patterns is None:
            patterns = ["test_*.py", "*_test.py", "test*.py"]
        
        if exclude_patterns is None:
            exclude_patterns = ["**/node_modules/**", "**/.venv/**", "**/venv/**", "**/__pycache__/**"]
        
        logger.info(f"Starting parallel test discovery in {root_dir}")
        
        # First, collect all candidate files (fast, single-threaded)
        candidate_files = self._collect_candidate_files(
            root_dir,
            patterns,
            exclude_patterns
        )
        
        total_files = len(candidate_files)
        logger.info(f"Found {total_files} candidate test files")
        
        if total_files == 0:
            return []
        
        # Process files in parallel
        results = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._analyze_test_file, file_path): file_path
                for file_path in candidate_files
            }
            
            # Process completed tasks
            for future in as_completed(future_to_file):
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, total_files)
                
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    file_path = future_to_file[future]
                    logger.error(f"Error analyzing {file_path}: {e}")
                    results.append(DiscoveryResult(
                        file_path=str(file_path),
                        test_count=0,
                        error=str(e)
                    ))
        
        logger.info(f"Completed discovery: {len(results)} files analyzed")
        return results
    
    def _collect_candidate_files(
        self,
        root_dir: Path,
        patterns: List[str],
        exclude_patterns: List[str]
    ) -> List[Path]:
        """
        Collect candidate test files matching patterns.
        
        Fast single-threaded file system walk.
        """
        candidates = []
        
        for pattern in patterns:
            for file_path in root_dir.rglob(pattern):
                if file_path.is_file():
                    # Check exclusions
                    if any(file_path.match(ex) for ex in exclude_patterns):
                        continue
                    candidates.append(file_path)
        
        return candidates
    
    def _analyze_test_file(self, file_path: Path) -> DiscoveryResult:
        """
        Analyze a single test file to extract metadata.
        
        This method runs in worker thread/process.
        """
        try:
            # Quick analysis without full parsing
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Count test functions/methods
            test_count = self._count_tests(content)
            
            # Detect framework
            framework = self._detect_framework(content, file_path)
            
            return DiscoveryResult(
                file_path=str(file_path),
                test_count=test_count,
                framework=framework
            )
        except Exception as e:
            logger.debug(f"Error analyzing {file_path}: {e}")
            return DiscoveryResult(
                file_path=str(file_path),
                test_count=0,
                error=str(e)
            )
    
    def _count_tests(self, content: str) -> int:
        """Quick test count using pattern matching."""
        import re
        
        # Count test functions
        test_func_count = len(re.findall(r'\bdef\s+test_\w+\s*\(', content))
        
        # Count test methods in classes
        test_method_count = len(re.findall(r'^\s+def\s+test_\w+\s*\(', content, re.MULTILINE))
        
        return max(test_func_count, test_method_count)
    
    def _detect_framework(self, content: str, file_path: Path) -> Optional[str]:
        """Detect test framework from content and file structure."""
        content_lower = content.lower()
        
        if 'import pytest' in content_lower or '@pytest.' in content_lower:
            return 'pytest'
        elif 'import unittest' in content_lower or 'unittest.testcase' in content_lower:
            return 'unittest'
        elif 'from selenium' in content_lower:
            if 'behave' in content_lower:
                return 'selenium-behave'
            return 'selenium-pytest'
        elif 'from playwright' in content_lower:
            return 'playwright'
        elif 'from robot.' in content_lower or file_path.suffix == '.robot':
            return 'robot'
        elif '.feature' in file_path.suffix:
            return 'cucumber'
        
        return None


class BatchDatabaseOperations:
    """
    Batch database operations for improved performance.
    
    Features:
    - Bulk inserts with single transaction
    - Configurable batch sizes
    - Error handling and retry logic
    - Progress tracking
    """
    
    def __init__(self, db_adapter, batch_size: int = 1000):
        """
        Initialize batch operations.
        
        Args:
            db_adapter: Database adapter instance
            batch_size: Number of records per batch
        """
        self.db_adapter = db_adapter
        self.batch_size = batch_size
        logger.info(f"Initialized batch operations with batch_size={batch_size}")
    
    def bulk_insert_test_results(
        self,
        results: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Insert test results in batches.
        
        Args:
            results: List of test result dictionaries
            progress_callback: Optional progress callback
            
        Returns:
            True if all batches succeeded
            
        Example:
            >>> batch_ops = BatchDatabaseOperations(db_adapter, batch_size=500)
            >>> success = batch_ops.bulk_insert_test_results(
            ...     large_result_list,
            ...     progress_callback=lambda cur, total: print(f"Progress: {cur}/{total}")
            ... )
        """
        total_records = len(results)
        logger.info(f"Starting bulk insert of {total_records} test results")
        
        if total_records == 0:
            return True
        
        # Process in batches
        batches = self._create_batches(results, self.batch_size)
        total_batches = len(batches)
        
        successful_batches = 0
        failed_batches = 0
        
        for i, batch in enumerate(batches, 1):
            try:
                self._insert_batch(batch)
                successful_batches += 1
                
                if progress_callback:
                    progress_callback(i * len(batch), total_records)
            
            except Exception as e:
                logger.error(f"Failed to insert batch {i}/{total_batches}: {e}")
                failed_batches += 1
                
                # Try individual inserts for failed batch
                self._fallback_individual_inserts(batch)
        
        logger.info(
            f"Bulk insert complete: {successful_batches} successful, "
            f"{failed_batches} failed out of {total_batches} batches"
        )
        
        return failed_batches == 0
    
    def _create_batches(
        self,
        items: List[Any],
        batch_size: int
    ) -> List[List[Any]]:
        """Split items into batches."""
        return [
            items[i:i + batch_size]
            for i in range(0, len(items), batch_size)
        ]
    
    def _insert_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Insert a batch of records in single transaction.
        
        Uses database-specific bulk insert for best performance.
        """
        if hasattr(self.db_adapter, 'bulk_insert'):
            # Use native bulk insert if available
            self.db_adapter.bulk_insert('test_results', batch)
        else:
            # Fall back to executemany
            conn = self.db_adapter.get_connection()
            cursor = conn.cursor()
            
            try:
                # Build INSERT query
                if batch:
                    columns = batch[0].keys()
                    placeholders = ', '.join(['%s'] * len(columns))
                    query = f"INSERT INTO test_results ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    # Execute many
                    values = [tuple(row[col] for col in columns) for row in batch]
                    cursor.executemany(query, values)
                    
                    conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                self.db_adapter.release_connection(conn)
    
    def _fallback_individual_inserts(self, batch: List[Dict[str, Any]]) -> None:
        """Insert records individually when batch fails."""
        logger.warning(f"Falling back to individual inserts for {len(batch)} records")
        
        for record in batch:
            try:
                self.db_adapter.insert('test_results', record)
            except Exception as e:
                logger.error(f"Failed to insert record {record.get('test_id')}: {e}")


class StreamingTestParser:
    """
    Memory-efficient streaming parser for large test files.
    
    Parses tests one at a time without loading entire file into memory.
    """
    
    def __init__(self, chunk_size: int = 8192):
        """
        Initialize streaming parser.
        
        Args:
            chunk_size: Bytes to read per chunk
        """
        self.chunk_size = chunk_size
    
    def parse_large_file(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """
        Parse large test file in streaming fashion.
        
        Args:
            file_path: Path to test file
            
        Yields:
            Test metadata dictionaries one at a time
            
        Example:
            >>> parser = StreamingTestParser()
            >>> for test in parser.parse_large_file(Path("huge_test.py")):
            ...     process_test(test)  # Process immediately without storing all
        """
        current_test = []
        in_test_function = False
        indent_level = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Detect test function start
                if line.strip().startswith('def test_'):
                    if current_test:
                        # Yield previous test
                        yield self._parse_test_block(current_test)
                        current_test = []
                    
                    in_test_function = True
                    indent_level = len(line) - len(line.lstrip())
                    current_test.append(line)
                
                elif in_test_function:
                    current_line_indent = len(line) - len(line.lstrip())
                    
                    # Check if we're still in the function
                    if line.strip() and current_line_indent <= indent_level:
                        # Function ended
                        yield self._parse_test_block(current_test)
                        current_test = []
                        in_test_function = False
                    else:
                        current_test.append(line)
        
        # Don't forget last test
        if current_test:
            yield self._parse_test_block(current_test)
    
    def _parse_test_block(self, lines: List[str]) -> Dict[str, Any]:
        """Parse test function from lines."""
        import re
        
        # Extract function name
        func_line = lines[0]
        func_match = re.search(r'def\s+(test_\w+)\s*\(', func_line)
        func_name = func_match.group(1) if func_match else "unknown"
        
        # Extract docstring if present
        docstring = None
        if len(lines) > 1:
            second_line = lines[1].strip()
            if second_line.startswith('"""') or second_line.startswith("'''"):
                docstring = second_line.strip('"\' ')
        
        return {
            'test_name': func_name,
            'docstring': docstring,
            'line_count': len(lines)
        }


class CachingFrameworkDetector:
    """
    Cache framework detection results to avoid re-scanning.
    
    Uses file modification time to invalidate cache.
    """
    
    def __init__(self, cache_file: Optional[Path] = None):
        """
        Initialize caching detector.
        
        Args:
            cache_file: Optional cache file path (default: .crossbridge_cache.json)
        """
        self.cache_file = cache_file or Path.cwd() / ".crossbridge_cache.json"
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
    
    def detect_framework(self, project_dir: Path) -> Optional[str]:
        """
        Detect framework with caching.
        
        Args:
            project_dir: Project directory
            
        Returns:
            Framework name or None
        """
        cache_key = str(project_dir.absolute())
        
        # Check cache
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            
            # Check if any marker files changed
            if self._is_cache_valid(project_dir, cached_entry):
                logger.debug(f"Using cached framework detection for {project_dir}")
                return cached_entry['framework']
        
        # Perform detection
        framework = self._perform_detection(project_dir)
        
        # Update cache
        self.cache[cache_key] = {
            'framework': framework,
            'timestamp': Path(project_dir).stat().st_mtime,
            'marker_files': self._get_marker_files(project_dir)
        }
        self._save_cache()
        
        return framework
    
    def _load_cache(self) -> None:
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                import json
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            import json
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _is_cache_valid(self, project_dir: Path, cached_entry: Dict[str, Any]) -> bool:
        """Check if cached entry is still valid."""
        # Check if project directory was modified
        current_mtime = project_dir.stat().st_mtime
        cached_mtime = cached_entry.get('timestamp', 0)
        
        return current_mtime <= cached_mtime
    
    def _get_marker_files(self, project_dir: Path) -> List[str]:
        """Get list of framework marker files."""
        markers = [
            'pytest.ini', 'setup.py', 'pyproject.toml',
            'package.json', 'pom.xml', 'build.gradle'
        ]
        
        found = []
        for marker in markers:
            if (project_dir / marker).exists():
                found.append(marker)
        
        return found
    
    def _perform_detection(self, project_dir: Path) -> Optional[str]:
        """Actual framework detection logic."""
        # Check for pytest
        if (project_dir / 'pytest.ini').exists():
            return 'pytest'
        
        # Check for Robot Framework
        if list(project_dir.rglob('*.robot')):
            return 'robot'
        
        # Check for Playwright
        if (project_dir / 'playwright.config.ts').exists():
            return 'playwright'
        
        # Check for Java/Maven
        if (project_dir / 'pom.xml').exists():
            return 'selenium-java'
        
        return None


# Export main classes
__all__ = [
    'ParallelTestDiscovery',
    'BatchDatabaseOperations',
    'StreamingTestParser',
    'CachingFrameworkDetector'
]
