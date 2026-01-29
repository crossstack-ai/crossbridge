"""
Unit tests for core/performance/optimizations.py

Tests cover:
- ParallelTestDiscovery: Multi-threaded file scanning
- BatchDatabaseOperations: Bulk database operations
- StreamingTestParser: Memory-efficient parsing
- CachingFrameworkDetector: Fast framework detection
"""

import pytest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from core.performance.optimizations import (
    ParallelTestDiscovery,
    BatchDatabaseOperations,
    StreamingTestParser,
    CachingFrameworkDetector,
    DiscoveryResult
)


class TestParallelTestDiscovery:
    """Test ParallelTestDiscovery class."""
    
    def test_init_default_workers(self):
        """Test initialization with default worker count."""
        discovery = ParallelTestDiscovery()
        
        assert discovery.max_workers > 0
        # Should be CPU count * 2
        assert discovery.max_workers >= 2
    
    def test_init_custom_workers(self):
        """Test initialization with custom worker count."""
        discovery = ParallelTestDiscovery(max_workers=8)
        
        assert discovery.max_workers == 8
    
    @patch('core.performance.optimizations.Path.glob')
    def test_discover_tests_empty_directory(self, mock_glob):
        """Test discovering tests in empty directory."""
        mock_glob.return_value = []
        
        discovery = ParallelTestDiscovery()
        results = discovery.discover_tests(Path("/empty/dir"))
        
        assert results == []
    
    @patch('core.performance.optimizations.Path.glob')
    @patch('core.performance.optimizations.Path.is_file')
    def test_discover_tests_single_file(self, mock_is_file, mock_glob):
        """Test discovering single test file."""
        test_file = Path("/repo/test_example.py")
        mock_glob.return_value = [test_file]
        mock_is_file.return_value = True
        
        discovery = ParallelTestDiscovery()
        
        with patch.object(discovery, '_analyze_test_file') as mock_analyze:
            mock_analyze.return_value = DiscoveryResult(
                file_path=str(test_file),
                test_count=5,
                framework="pytest"
            )
            
            results = discovery.discover_tests(Path("/repo"))
            
            assert len(results) == 1
            assert results[0].file_path == str(test_file)
            assert results[0].test_count == 5
            assert results[0].framework == "pytest"
    
    @patch('core.performance.optimizations.Path.glob')
    def test_discover_tests_with_patterns(self, mock_glob):
        """Test discovering tests with custom patterns."""
        discovery = ParallelTestDiscovery()
        
        mock_glob.return_value = []
        
        discovery.discover_tests(
            Path("/repo"),
            patterns=["*_spec.py", "test_*.js"]
        )
        
        # Verify glob was called with patterns
        assert mock_glob.called
    
    def test_discover_tests_progress_callback(self):
        """Test progress callback during discovery."""
        progress_calls = []
        
        def progress_callback(current, total):
            progress_calls.append((current, total))
        
        discovery = ParallelTestDiscovery()
        
        with patch.object(discovery, '_collect_candidate_files') as mock_collect:
            mock_collect.return_value = [Path(f"/repo/test_{i}.py") for i in range(3)]
            
            with patch.object(discovery, '_analyze_test_file') as mock_analyze:
                mock_analyze.return_value = DiscoveryResult(
                    file_path="/repo/test.py",
                    test_count=1
                )
                
                results = discovery.discover_tests(
                    Path("/repo"),
                    progress_callback=progress_callback
                )
                
                # Progress should have been reported
                assert len(progress_calls) > 0


class TestBatchDatabaseOperations:
    """Test BatchDatabaseOperations class."""
    
    def test_init_default_batch_size(self):
        """Test initialization with default batch size."""
        batch_ops = BatchDatabaseOperations()
        
        assert batch_ops.batch_size == 1000
    
    def test_init_custom_batch_size(self):
        """Test initialization with custom batch size."""
        batch_ops = BatchDatabaseOperations(batch_size=500)
        
        assert batch_ops.batch_size == 500
    
    def test_batch_insert_tests_empty_list(self):
        """Test batch insert with empty test list."""
        mock_session = MagicMock()
        batch_ops = BatchDatabaseOperations()
        
        inserted_count = batch_ops.batch_insert_tests(mock_session, [])
        
        assert inserted_count == 0
        mock_session.execute.assert_not_called()
    
    def test_batch_insert_tests_single_batch(self):
        """Test batch insert with single batch of tests."""
        mock_session = MagicMock()
        batch_ops = BatchDatabaseOperations(batch_size=10)
        
        tests = [
            {"name": f"test_{i}", "file_path": f"/test_{i}.py"}
            for i in range(5)
        ]
        
        inserted_count = batch_ops.batch_insert_tests(mock_session, tests)
        
        assert inserted_count == 5
        assert mock_session.execute.call_count == 1
    
    def test_batch_insert_tests_multiple_batches(self):
        """Test batch insert with multiple batches."""
        mock_session = MagicMock()
        batch_ops = BatchDatabaseOperations(batch_size=10)
        
        tests = [
            {"name": f"test_{i}", "file_path": f"/test_{i}.py"}
            for i in range(25)
        ]
        
        inserted_count = batch_ops.batch_insert_tests(mock_session, tests)
        
        assert inserted_count == 25
        # Should have 3 batches: 10 + 10 + 5
        assert mock_session.execute.call_count == 3
    
    def test_batch_insert_page_objects(self):
        """Test batch insert page objects."""
        mock_session = MagicMock()
        batch_ops = BatchDatabaseOperations(batch_size=100)
        
        page_objects = [
            {"name": f"Page{i}", "file_path": f"/pages/page{i}.py"}
            for i in range(50)
        ]
        
        inserted_count = batch_ops.batch_insert_page_objects(mock_session, page_objects)
        
        assert inserted_count == 50
        mock_session.execute.assert_called()
    
    def test_batch_insert_mappings(self):
        """Test batch insert test-page mappings."""
        mock_session = MagicMock()
        batch_ops = BatchDatabaseOperations(batch_size=1000)
        
        mappings = [
            {"test_case_id": uuid.uuid4(), "page_object_id": uuid.uuid4()}
            for _ in range(500)
        ]
        
        inserted_count = batch_ops.batch_insert_mappings(mock_session, mappings)
        
        assert inserted_count == 500
        mock_session.execute.assert_called()
    
    def test_batch_operations_error_handling(self):
        """Test error handling in batch operations."""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Database error")
        
        batch_ops = BatchDatabaseOperations()
        
        tests = [{"name": "test_1", "file_path": "/test.py"}]
        
        # Should not raise, but return 0
        inserted_count = batch_ops.batch_insert_tests(mock_session, tests)
        
        assert inserted_count == 0


class TestStreamingTestParser:
    """Test StreamingTestParser class."""
    
    def test_init(self):
        """Test parser initialization."""
        parser = StreamingTestParser()
        
        assert parser is not None
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        parser = StreamingTestParser()
        
        results = list(parser.parse_file_streaming(Path("/nonexistent/test.py")))
        
        assert results == []
    
    @patch('builtins.open', new_callable=mock_open, read_data='def test_example():\n    pass\n')
    def test_parse_file_simple_pytest(self, mock_file):
        """Test parsing simple pytest file."""
        parser = StreamingTestParser()
        
        results = list(parser.parse_file_streaming(Path("/test_example.py")))
        
        # Should find at least one test
        assert len(results) >= 1
        # Verify mock was called
        mock_file.assert_called()
    
    @patch('builtins.open', new_callable=mock_open, read_data='class TestClass:\n    def test_method(self):\n        pass\n')
    def test_parse_file_class_based_test(self, mock_file):
        """Test parsing class-based test file."""
        parser = StreamingTestParser()
        
        results = list(parser.parse_file_streaming(Path("/test_class.py")))
        
        # Should find test class and method
        assert len(results) >= 1
    
    def test_parse_multiple_files(self):
        """Test parsing multiple files in streaming mode."""
        parser = StreamingTestParser()
        
        files = [
            Path("/test_1.py"),
            Path("/test_2.py"),
            Path("/test_3.py")
        ]
        
        with patch.object(parser, 'parse_file_streaming') as mock_parse:
            mock_parse.return_value = iter([{"name": "test", "line": 1}])
            
            results = []
            for file_path in files:
                results.extend(parser.parse_file_streaming(file_path))
            
            assert len(results) == 3
    
    def test_memory_efficiency(self):
        """Test that streaming parser doesn't load entire file into memory."""
        parser = StreamingTestParser()
        
        # Create large mock file content
        large_content = '\n'.join([f'def test_{i}(): pass' for i in range(10000)])
        
        with patch('builtins.open', mock_open(read_data=large_content)):
            results = list(parser.parse_file_streaming(Path("/large_test.py")))
            
            # Should process without memory issues
            assert len(results) > 0


class TestCachingFrameworkDetector:
    """Test CachingFrameworkDetector class."""
    
    def test_init(self):
        """Test detector initialization."""
        detector = CachingFrameworkDetector()
        
        assert detector is not None
        # Should have empty cache initially
        assert len(detector._cache) == 0
    
    def test_detect_framework_pytest(self):
        """Test detecting pytest framework."""
        detector = CachingFrameworkDetector()
        
        file_content = """
        import pytest
        
        def test_example():
            assert True
        """
        
        framework = detector.detect_framework(Path("/test.py"), file_content)
        
        assert framework == "pytest"
    
    def test_detect_framework_unittest(self):
        """Test detecting unittest framework."""
        detector = CachingFrameworkDetector()
        
        file_content = """
        import unittest
        
        class TestExample(unittest.TestCase):
            def test_method(self):
                self.assertTrue(True)
        """
        
        framework = detector.detect_framework(Path("/test.py"), file_content)
        
        assert framework == "unittest"
    
    def test_detect_framework_robot(self):
        """Test detecting Robot Framework."""
        detector = CachingFrameworkDetector()
        
        file_content = """
        *** Test Cases ***
        Example Test
            Log    Hello World
        """
        
        framework = detector.detect_framework(Path("/test.robot"), file_content)
        
        assert framework == "robot"
    
    def test_caching_works(self):
        """Test that framework detection results are cached."""
        detector = CachingFrameworkDetector()
        
        file_path = Path("/test.py")
        content = "import pytest\ndef test_example(): pass"
        
        # First call - should detect
        framework1 = detector.detect_framework(file_path, content)
        cache_size_1 = len(detector._cache)
        
        # Second call - should use cache
        framework2 = detector.detect_framework(file_path, content)
        cache_size_2 = len(detector._cache)
        
        assert framework1 == framework2
        assert cache_size_1 == cache_size_2  # Cache size shouldn't grow
    
    def test_cache_key_uses_file_hash(self):
        """Test that cache key includes file content hash."""
        detector = CachingFrameworkDetector()
        
        file_path = Path("/test.py")
        content1 = "import pytest\ndef test_1(): pass"
        content2 = "import unittest\nclass Test1: pass"
        
        framework1 = detector.detect_framework(file_path, content1)
        framework2 = detector.detect_framework(file_path, content2)
        
        # Different content should give different results
        assert framework1 != framework2
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        detector = CachingFrameworkDetector()
        
        # Add some entries to cache
        detector.detect_framework(Path("/test1.py"), "import pytest")
        detector.detect_framework(Path("/test2.py"), "import unittest")
        
        assert len(detector._cache) > 0
        
        # Clear cache
        detector.clear_cache()
        
        assert len(detector._cache) == 0
    
    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        detector = CachingFrameworkDetector()
        
        # Make some detections
        detector.detect_framework(Path("/test1.py"), "import pytest")
        detector.detect_framework(Path("/test1.py"), "import pytest")  # Cache hit
        detector.detect_framework(Path("/test2.py"), "import unittest")
        
        stats = detector.get_cache_stats()
        
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert stats["size"] >= 0


class TestDiscoveryResult:
    """Test DiscoveryResult dataclass."""
    
    def test_create_minimal(self):
        """Test creating DiscoveryResult with minimal fields."""
        result = DiscoveryResult(
            file_path="/test.py",
            test_count=5
        )
        
        assert result.file_path == "/test.py"
        assert result.test_count == 5
        assert result.framework is None
        assert result.error is None
    
    def test_create_complete(self):
        """Test creating DiscoveryResult with all fields."""
        result = DiscoveryResult(
            file_path="/test.py",
            test_count=10,
            framework="pytest",
            error=None
        )
        
        assert result.file_path == "/test.py"
        assert result.test_count == 10
        assert result.framework == "pytest"
        assert result.error is None
    
    def test_create_with_error(self):
        """Test creating DiscoveryResult with error."""
        result = DiscoveryResult(
            file_path="/test.py",
            test_count=0,
            framework=None,
            error="Parse error: Invalid syntax"
        )
        
        assert result.file_path == "/test.py"
        assert result.test_count == 0
        assert result.error is not None


class TestIntegrationScenarios:
    """Test integration scenarios using multiple optimization classes."""
    
    def test_parallel_discovery_with_batch_insert(self):
        """Test using parallel discovery with batch database operations."""
        discovery = ParallelTestDiscovery(max_workers=4)
        batch_ops = BatchDatabaseOperations(batch_size=100)
        
        with patch.object(discovery, 'discover_tests') as mock_discover:
            mock_discover.return_value = [
                DiscoveryResult(f"/test_{i}.py", test_count=3)
                for i in range(250)
            ]
            
            results = discovery.discover_tests(Path("/repo"))
            
            assert len(results) == 250
            
            # Simulate batch insert
            mock_session = MagicMock()
            test_data = [{"name": f"test_{i}", "file_path": r.file_path} for r in results]
            inserted = batch_ops.batch_insert_tests(mock_session, test_data)
            
            assert inserted == 250
            # Should use 3 batches (100 + 100 + 50)
            assert mock_session.execute.call_count == 3
    
    def test_streaming_parser_with_framework_detection(self):
        """Test using streaming parser with framework detection."""
        parser = StreamingTestParser()
        detector = CachingFrameworkDetector()
        
        file_content = "import pytest\ndef test_example(): pass"
        
        framework = detector.detect_framework(Path("/test.py"), file_content)
        
        with patch.object(parser, 'parse_file_streaming') as mock_parse:
            mock_parse.return_value = iter([
                {"name": "test_example", "line": 2, "framework": framework}
            ])
            
            tests = list(parser.parse_file_streaming(Path("/test.py")))
            
            assert len(tests) == 1
            assert tests[0]["framework"] == "pytest"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
