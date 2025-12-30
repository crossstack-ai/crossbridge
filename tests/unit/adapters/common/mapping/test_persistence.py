"""Test persistence layer for step-to-code mappings."""
import pytest
import json
from pathlib import Path
from adapters.common.mapping.persistence import (
    MappingPersistence,
    save_mapping,
    load_mapping,
    save_registry,
    load_registry,
)
from adapters.common.mapping import (
    StepMapping,
    StepSignal,
    SignalType,
    StepSignalRegistry,
)


class TestMappingPersistence:
    """Test MappingPersistence class."""
    
    def test_save_and_load_mapping(self, tmp_path):
        """Save and load a StepMapping."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        
        mapping = StepMapping(
            step="user logs in",
            page_objects=["LoginPage"],
            methods=["login"],
            code_paths=["pages/login.py::LoginPage.login"],
            signals=[]
        )
        
        # Save
        file_path = persistence.save_mapping(mapping, test_id="test_001", run_id="run_123")
        assert Path(file_path).exists()
        
        # Load
        loaded = persistence.load_mapping(test_id="test_001", run_id="run_123")
        assert loaded is not None
        assert loaded.step == "user logs in"
        assert loaded.page_objects == ["LoginPage"]
        assert loaded.code_paths == ["pages/login.py::LoginPage.login"]
    
    def test_load_nonexistent_mapping_returns_none(self, tmp_path):
        """Loading nonexistent mapping returns None."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        loaded = persistence.load_mapping(test_id="nonexistent", run_id="run_123")
        assert loaded is None
    
    def test_save_mapping_with_metadata(self, tmp_path):
        """Save mapping with additional metadata."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        
        mapping = StepMapping(
            step="user logs in",
            page_objects=[],
            methods=[],
            code_paths=[],
            signals=[]
        )
        
        metadata = {"test_file": "test_login.py", "line": 42}
        file_path = persistence.save_mapping(
            mapping,
            test_id="test_001",
            run_id="run_123",
            metadata=metadata
        )
        
        # Verify metadata saved
        with open(file_path, 'r') as f:
            record = json.load(f)
        assert record["metadata"] == metadata
    
    def test_save_mappings_batch(self, tmp_path):
        """Save multiple mappings in batch."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        
        mappings = [
            StepMapping("step 1", [], [], [], []),
            StepMapping("step 2", [], [], [], []),
            StepMapping("step 3", [], [], [], []),
        ]
        test_ids = ["test_001", "test_002", "test_003"]
        
        paths = persistence.save_mappings_batch(
            mappings,
            test_ids,
            run_id="run_123"
        )
        
        assert len(paths) == 3
        for path in paths:
            assert Path(path).exists()
    
    def test_save_batch_with_mismatched_lengths_raises_error(self, tmp_path):
        """Batch save with mismatched lengths raises ValueError."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        
        mappings = [StepMapping("step 1", [], [], [], [])]
        test_ids = ["test_001", "test_002"]  # Different length
        
        with pytest.raises(ValueError, match="must have same length"):
            persistence.save_mappings_batch(mappings, test_ids, run_id="run_123")
    
    def test_load_mappings_for_run(self, tmp_path):
        """Load all mappings for a test run."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        
        # Save multiple mappings
        for i in range(3):
            mapping = StepMapping(f"step {i}", [], [], [], [])
            persistence.save_mapping(mapping, test_id=f"test_{i:03d}", run_id="run_123")
        
        # Load all
        mappings = persistence.load_mappings_for_run("run_123")
        
        assert len(mappings) == 3
        assert "test_000" in mappings
        assert "test_001" in mappings
        assert "test_002" in mappings
    
    def test_load_mappings_for_nonexistent_run(self, tmp_path):
        """Loading mappings for nonexistent run returns empty dict."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        mappings = persistence.load_mappings_for_run("nonexistent_run")
        assert mappings == {}
    
    def test_find_tests_by_code_path(self, tmp_path):
        """Find tests that use a specific code path (impact analysis)."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        
        # Save mappings with different code paths
        persistence.save_mapping(
            StepMapping("step 1", [], [], ["pages/login.py::LoginPage.login"], []),
            test_id="test_001",
            run_id="run_123"
        )
        persistence.save_mapping(
            StepMapping("step 2", [], [], ["pages/login.py::LoginPage.login"], []),
            test_id="test_002",
            run_id="run_123"
        )
        persistence.save_mapping(
            StepMapping("step 3", [], [], ["pages/dashboard.py::DashboardPage.show"], []),
            test_id="test_003",
            run_id="run_123"
        )
        
        # Find tests using login page
        affected = persistence.find_tests_by_code_path(
            "pages/login.py::LoginPage.login",
            run_id="run_123"
        )
        
        assert len(affected) == 2
        assert "test_001" in affected
        assert "test_002" in affected
        assert "test_003" not in affected
    
    def test_get_coverage_report(self, tmp_path):
        """Generate coverage report for a test run."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        
        # Save mappings with different coverage
        persistence.save_mapping(
            StepMapping("step 1", ["LoginPage"], ["login"], ["pages/login.py::LoginPage.login"], []),
            test_id="test_001",
            run_id="run_123"
        )
        persistence.save_mapping(
            StepMapping("step 2", ["DashboardPage"], ["show"], ["pages/dashboard.py::DashboardPage.show"], []),
            test_id="test_002",
            run_id="run_123"
        )
        persistence.save_mapping(
            StepMapping("step 3", [], [], [], []),  # No mapping
            test_id="test_003",
            run_id="run_123"
        )
        
        report = persistence.get_coverage_report("run_123")
        
        assert report["run_id"] == "run_123"
        assert report["total_tests"] == 3
        assert report["code_paths_covered"] == 2
        assert report["page_objects_used"] == 2
        assert report["methods_used"] == 2
        assert len(report["steps_without_mapping"]) == 1
        assert "step 3" in report["steps_without_mapping"]
        assert report["coverage_percentage"] == pytest.approx(66.666, rel=0.1)
    
    def test_save_and_load_registry(self, tmp_path):
        """Save and load a signal registry."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        
        # Create registry with signals
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.CODE_PATH, value="pages/login.py::LoginPage.login")
        )
        registry.register_signal(
            "user clicks button",
            StepSignal(type=SignalType.METHOD, value="ButtonHelper.click")
        )
        
        # Save
        file_path = persistence.save_registry(registry, registry_id="test_registry")
        assert Path(file_path).exists()
        
        # Load
        loaded_registry = persistence.load_registry(registry_id="test_registry")
        assert loaded_registry is not None
        assert loaded_registry.count() == 2
        
        # Verify signals
        signals = loaded_registry.get_signals_for_step("user logs in")
        assert len(signals) >= 1
        assert any(s.value == "pages/login.py::LoginPage.login" for s in signals)
    
    def test_load_nonexistent_registry_returns_none(self, tmp_path):
        """Loading nonexistent registry returns None."""
        persistence = MappingPersistence(storage_path=str(tmp_path))
        loaded = persistence.load_registry(registry_id="nonexistent")
        assert loaded is None


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_save_and_load_mapping_convenience(self, tmp_path, monkeypatch):
        """Test convenience save/load functions."""
        # Monkey-patch default persistence to use tmp_path
        from adapters.common.mapping import persistence as persistence_module
        persistence_module._default_persistence = MappingPersistence(storage_path=str(tmp_path))
        
        mapping = StepMapping("test step", [], [], [], [])
        
        # Save
        file_path = save_mapping(mapping, test_id="test_001", run_id="run_123")
        assert Path(file_path).exists()
        
        # Load
        loaded = load_mapping(test_id="test_001", run_id="run_123")
        assert loaded is not None
        assert loaded.step == "test step"
    
    def test_save_and_load_registry_convenience(self, tmp_path, monkeypatch):
        """Test convenience save/load registry functions."""
        # Monkey-patch default persistence
        from adapters.common.mapping import persistence as persistence_module
        persistence_module._default_persistence = MappingPersistence(storage_path=str(tmp_path))
        
        registry = StepSignalRegistry()
        registry.register_signal(
            "test pattern",
            StepSignal(type=SignalType.CODE_PATH, value="test.py::Test.method")
        )
        
        # Save
        file_path = save_registry(registry, registry_id="test_reg")
        assert Path(file_path).exists()
        
        # Load
        loaded = load_registry(registry_id="test_reg")
        assert loaded is not None
        assert loaded.count() == 1
