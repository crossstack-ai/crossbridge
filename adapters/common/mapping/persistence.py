"""
Persistence layer for step-to-code-path mappings.

Provides save/load functionality for StepMapping objects to enable:
- Impact analysis across test runs
- Coverage tracking and reporting  
- Historical mapping data for trends
- Offline analysis and debugging
"""
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime, timezone
from adapters.common.mapping.models import StepMapping, StepSignal, SignalType
from adapters.common.mapping.registry import StepSignalRegistry


class MappingPersistence:
    """
    Persist and load step mappings to/from storage.
    
    Supports JSON file storage with optional database backend.
    """
    
    def __init__(self, storage_path: str = ".crossbridge/mappings"):
        """
        Initialize persistence layer.
        
        Args:
            storage_path: Directory path for storing mapping files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_mapping(
        self,
        mapping: StepMapping,
        test_id: str,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a StepMapping to storage.
        
        Args:
            mapping: StepMapping to save
            test_id: Unique identifier for the test
            run_id: Optional test run identifier
            metadata: Optional additional metadata
            
        Returns:
            Path to saved file
            
        Example:
            >>> persistence = MappingPersistence()
            >>> mapping = StepMapping(
            ...     step="user logs in",
            ...     page_objects=["LoginPage"],
            ...     methods=["login"],
            ...     code_paths=["pages/login.py::LoginPage.login"]
            ... )
            >>> file_path = persistence.save_mapping(
            ...     mapping,
            ...     test_id="test_login_001",
            ...     run_id="run_20250101_123456"
            ... )
        """
        # Create run directory if run_id provided
        if run_id:
            save_dir = self.storage_path / run_id
        else:
            save_dir = self.storage_path / "default"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Create storage record
        record = {
            "test_id": test_id,
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mapping": mapping.to_dict(),
            "metadata": metadata or {}
        }
        
        # Save to file
        file_path = save_dir / f"{test_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2)
        
        return str(file_path)
    
    def load_mapping(
        self,
        test_id: str,
        run_id: Optional[str] = None
    ) -> Optional[StepMapping]:
        """
        Load a StepMapping from storage.
        
        Args:
            test_id: Unique identifier for the test
            run_id: Optional test run identifier
            
        Returns:
            StepMapping if found, None otherwise
            
        Example:
            >>> persistence = MappingPersistence()
            >>> mapping = persistence.load_mapping(
            ...     test_id="test_login_001",
            ...     run_id="run_20250101_123456"
            ... )
            >>> mapping.code_paths
            ['pages/login.py::LoginPage.login']
        """
        # Determine file path
        if run_id:
            file_path = self.storage_path / run_id / f"{test_id}.json"
        else:
            file_path = self.storage_path / "default" / f"{test_id}.json"
        
        if not file_path.exists():
            return None
        
        # Load from file
        with open(file_path, 'r', encoding='utf-8') as f:
            record = json.load(f)
        
        # Restore StepMapping
        return StepMapping.from_dict(record["mapping"])
    
    def save_mappings_batch(
        self,
        mappings: List[StepMapping],
        test_ids: List[str],
        run_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Save multiple StepMappings in batch.
        
        Args:
            mappings: List of StepMapping objects
            test_ids: List of test identifiers (same length as mappings)
            run_id: Test run identifier
            metadata: Optional metadata for all mappings
            
        Returns:
            List of file paths where mappings were saved
            
        Example:
            >>> paths = persistence.save_mappings_batch(
            ...     mappings=[mapping1, mapping2, mapping3],
            ...     test_ids=["test_001", "test_002", "test_003"],
            ...     run_id="run_20250101_123456"
            ... )
        """
        if len(mappings) != len(test_ids):
            raise ValueError("mappings and test_ids must have same length")
        
        paths = []
        for mapping, test_id in zip(mappings, test_ids):
            path = self.save_mapping(mapping, test_id, run_id, metadata)
            paths.append(path)
        
        return paths
    
    def load_mappings_for_run(self, run_id: str) -> Dict[str, StepMapping]:
        """
        Load all mappings for a specific test run.
        
        Args:
            run_id: Test run identifier
            
        Returns:
            Dictionary mapping test_id to StepMapping
            
        Example:
            >>> mappings = persistence.load_mappings_for_run("run_20250101_123456")
            >>> for test_id, mapping in mappings.items():
            ...     print(f"{test_id}: {len(mapping.code_paths)} code paths")
        """
        run_dir = self.storage_path / run_id
        if not run_dir.exists():
            return {}
        
        mappings = {}
        for file_path in run_dir.glob("*.json"):
            test_id = file_path.stem
            mapping = self.load_mapping(test_id, run_id)
            if mapping:
                mappings[test_id] = mapping
        
        return mappings
    
    def find_tests_by_code_path(
        self,
        code_path: str,
        run_id: Optional[str] = None
    ) -> List[str]:
        """
        Find all test IDs that use a specific code path (impact analysis).
        
        Args:
            code_path: Code path to search for
            run_id: Optional test run to search in
            
        Returns:
            List of test IDs that use this code path
            
        Example:
            >>> affected = persistence.find_tests_by_code_path(
            ...     "pages/login.py::LoginPage.login",
            ...     run_id="run_20250101_123456"
            ... )
            >>> print(f"Tests affected by change: {affected}")
        """
        affected_tests = []
        
        if run_id:
            search_dir = self.storage_path / run_id
            if not search_dir.exists():
                return []
            search_dirs = [search_dir]
        else:
            # Search all runs
            search_dirs = [d for d in self.storage_path.iterdir() if d.is_dir()]
        
        for search_dir in search_dirs:
            for file_path in search_dir.glob("*.json"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    record = json.load(f)
                
                mapping_dict = record["mapping"]
                if code_path in mapping_dict.get("code_paths", []):
                    affected_tests.append(record["test_id"])
        
        return affected_tests
    
    def get_coverage_report(self, run_id: str) -> Dict[str, Any]:
        """
        Generate coverage report for a test run.
        
        Args:
            run_id: Test run identifier
            
        Returns:
            Dictionary with coverage statistics
            
        Example:
            >>> report = persistence.get_coverage_report("run_20250101_123456")
            >>> print(f"Total tests: {report['total_tests']}")
            >>> print(f"Code paths covered: {report['code_paths_covered']}")
        """
        mappings = self.load_mappings_for_run(run_id)
        
        all_code_paths = set()
        all_page_objects = set()
        all_methods = set()
        steps_without_mapping = []
        
        for test_id, mapping in mappings.items():
            all_code_paths.update(mapping.code_paths)
            all_page_objects.update(mapping.page_objects)
            all_methods.update(mapping.methods)
            
            if not mapping.code_paths:
                steps_without_mapping.append(mapping.step)
        
        return {
            "run_id": run_id,
            "total_tests": len(mappings),
            "code_paths_covered": len(all_code_paths),
            "page_objects_used": len(all_page_objects),
            "methods_used": len(all_methods),
            "steps_without_mapping": steps_without_mapping,
            "coverage_percentage": (len([m for m in mappings.values() if m.code_paths]) / len(mappings) * 100) if mappings else 0
        }
    
    def save_registry(
        self,
        registry: StepSignalRegistry,
        registry_id: str = "default"
    ) -> str:
        """
        Save signal registry to storage.
        
        Args:
            registry: StepSignalRegistry to save
            registry_id: Identifier for the registry
            
        Returns:
            Path to saved file
            
        Example:
            >>> persistence = MappingPersistence()
            >>> registry = StepSignalRegistry()
            >>> # ... register signals ...
            >>> file_path = persistence.save_registry(registry, "selenium_adapter")
        """
        # Get all registered patterns and signals
        patterns = registry.get_all_patterns()
        
        registry_data = {
            "registry_id": registry_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_signals": registry.count(),
            "patterns": {}
        }
        
        # Export signals for each pattern
        for pattern in patterns:
            signals = registry.get_signals_for_step(pattern)
            registry_data["patterns"][pattern] = [
                {
                    "type": signal.type.value,
                    "value": signal.value,
                    "metadata": signal.metadata
                }
                for signal in signals
            ]
        
        # Save to file
        file_path = self.storage_path / f"registry_{registry_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(registry_data, f, indent=2)
        
        return str(file_path)
    
    def load_registry(
        self,
        registry_id: str = "default"
    ) -> Optional[StepSignalRegistry]:
        """
        Load signal registry from storage.
        
        Args:
            registry_id: Identifier for the registry
            
        Returns:
            StepSignalRegistry if found, None otherwise
            
        Example:
            >>> persistence = MappingPersistence()
            >>> registry = persistence.load_registry("selenium_adapter")
            >>> print(f"Loaded {registry.count()} signals")
        """
        file_path = self.storage_path / f"registry_{registry_id}.json"
        
        if not file_path.exists():
            return None
        
        # Load from file
        with open(file_path, 'r', encoding='utf-8') as f:
            registry_data = json.load(f)
        
        # Restore registry
        registry = StepSignalRegistry()
        for pattern, signals_data in registry_data["patterns"].items():
            for signal_data in signals_data:
                signal = StepSignal(
                    type=SignalType(signal_data["type"]),
                    value=signal_data["value"],
                    metadata=signal_data["metadata"]
                )
                registry.register_signal(pattern, signal)
        
        return registry


# Convenience functions for simple usage

_default_persistence = None

def get_default_persistence() -> MappingPersistence:
    """Get or create default persistence instance."""
    global _default_persistence
    if _default_persistence is None:
        _default_persistence = MappingPersistence()
    return _default_persistence


def save_mapping(
    mapping: StepMapping,
    test_id: str,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function to save a StepMapping.
    
    Example:
        >>> from adapters.common.mapping.persistence import save_mapping
        >>> save_mapping(mapping, test_id="test_001", run_id="run_123")
    """
    return get_default_persistence().save_mapping(mapping, test_id, run_id, metadata)


def load_mapping(
    test_id: str,
    run_id: Optional[str] = None
) -> Optional[StepMapping]:
    """
    Convenience function to load a StepMapping.
    
    Example:
        >>> from adapters.common.mapping.persistence import load_mapping
        >>> mapping = load_mapping(test_id="test_001", run_id="run_123")
    """
    return get_default_persistence().load_mapping(test_id, run_id)


def save_registry(
    registry: StepSignalRegistry,
    registry_id: str = "default"
) -> str:
    """
    Convenience function to save a StepSignalRegistry.
    
    Example:
        >>> from adapters.common.mapping.persistence import save_registry
        >>> save_registry(registry, "selenium_adapter")
    """
    return get_default_persistence().save_registry(registry, registry_id)


def load_registry(
    registry_id: str = "default"
) -> Optional[StepSignalRegistry]:
    """
    Convenience function to load a StepSignalRegistry.
    
    Example:
        >>> from adapters.common.mapping.persistence import load_registry
        >>> registry = load_registry("selenium_adapter")
    """
    return get_default_persistence().load_registry(registry_id)
