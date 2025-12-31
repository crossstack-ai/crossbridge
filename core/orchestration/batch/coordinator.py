"""
Cross-feature batch coordinator for managing feature dependencies.

Coordinates execution of multiple features with dependencies, ensuring
proper ordering and data flow between features.
"""

from typing import Dict, List, Optional, Any, Set
from pathlib import Path

from core.logging import get_logger
from core.orchestration.batch.models import (
    BatchJob,
    BatchTask,
    FeatureType,
    TaskStatus,
    JobPriority
)
from core.orchestration.batch.orchestrator import BatchOrchestrator


class FeatureCoordinator:
    """
    Coordinates execution of multiple features with dependencies.
    
    Features:
    - Feature dependency management
    - Data flow between features
    - Automatic task graph construction
    - Cross-feature result passing
    """
    
    # Feature dependencies (features that must run before others)
    FEATURE_DEPENDENCIES = {
        FeatureType.IMPACT_ANALYSIS: {FeatureType.INTENT_EXTRACTION},
        FeatureType.RESULT_AGGREGATION: {
            FeatureType.TEST_EXECUTION,
            FeatureType.COVERAGE_COLLECTION,
            FeatureType.FLAKY_DETECTION
        },
        FeatureType.VALIDATION: {FeatureType.MIGRATION},
    }
    
    def __init__(self, orchestrator: BatchOrchestrator):
        """
        Initialize feature coordinator.
        
        Args:
            orchestrator: Batch orchestrator to use for execution
        """
        self.orchestrator = orchestrator
        self.logger = get_logger("core.orchestration.batch.coordinator")
        
        self.logger.info("FeatureCoordinator initialized")
    
    def create_feature_pipeline(
        self,
        name: str,
        features: List[FeatureType],
        input_files: Dict[FeatureType, List[Path]],
        output_dir: Path,
        feature_configs: Optional[Dict[FeatureType, Dict[str, Any]]] = None,
        **kwargs
    ) -> BatchJob:
        """
        Create a batch job with properly ordered feature tasks.
        
        Args:
            name: Pipeline name
            features: List of features to execute
            input_files: Input files for each feature
            output_dir: Output directory
            feature_configs: Configuration for each feature
            **kwargs: Additional job parameters
            
        Returns:
            Configured BatchJob with dependency graph
        """
        self.logger.info(f"Creating feature pipeline: {name} with {len(features)} features")
        
        job = self.orchestrator.create_job(
            name=name,
            description=f"Feature pipeline: {', '.join(f.value for f in features)}",
            **kwargs
        )
        
        feature_configs = feature_configs or {}
        task_map: Dict[FeatureType, str] = {}  # feature_type -> task_id
        
        # Resolve feature order based on dependencies
        ordered_features = self._resolve_dependencies(features)
        self.logger.debug(f"Resolved feature order: {[f.value for f in ordered_features]}")
        
        # Create tasks for each feature
        for feature in ordered_features:
            task = self._create_feature_task(
                job=job,
                feature_type=feature,
                input_files=input_files.get(feature, []),
                output_dir=output_dir,
                config=feature_configs.get(feature, {})
            )
            
            task_map[feature] = task.task_id
            
            # Add dependencies
            dependencies = self.FEATURE_DEPENDENCIES.get(feature, set())
            for dep_feature in dependencies:
                if dep_feature in task_map:
                    task.add_dependency(task_map[dep_feature])
                    self.logger.debug(f"Added dependency: {feature.value} depends on {dep_feature.value}")
        
        self.logger.success(f"Created pipeline with {len(ordered_features)} features and {job.total_tasks} tasks")
        
        return job
    
    def create_parallel_feature_job(
        self,
        name: str,
        feature_groups: List[List[FeatureType]],
        input_files: Dict[FeatureType, List[Path]],
        output_dir: Path,
        **kwargs
    ) -> BatchJob:
        """
        Create a job with parallel feature groups.
        
        Each group runs in parallel, groups run sequentially.
        
        Args:
            name: Job name
            feature_groups: List of feature groups (each group runs in parallel)
            input_files: Input files for each feature
            output_dir: Output directory
            **kwargs: Additional job parameters
            
        Returns:
            Configured BatchJob
        """
        self.logger.info(f"Creating parallel feature job: {name} with {len(feature_groups)} groups")
        
        job = self.orchestrator.create_job(name=name, **kwargs)
        
        previous_group_tasks: List[str] = []
        
        for group_idx, group in enumerate(feature_groups):
            self.logger.debug(f"Processing group {group_idx + 1}: {[f.value for f in group]}")
            
            current_group_tasks = []
            
            for feature in group:
                task = self._create_feature_task(
                    job=job,
                    feature_type=feature,
                    input_files=input_files.get(feature, []),
                    output_dir=output_dir,
                    config={}
                )
                
                # Depend on all tasks from previous group
                for prev_task_id in previous_group_tasks:
                    task.add_dependency(prev_task_id)
                
                current_group_tasks.append(task.task_id)
            
            previous_group_tasks = current_group_tasks
        
        self.logger.success(f"Created parallel job with {job.total_tasks} tasks")
        
        return job
    
    def _resolve_dependencies(self, features: List[FeatureType]) -> List[FeatureType]:
        """
        Resolve feature execution order based on dependencies.
        
        Uses topological sort to determine order.
        
        Args:
            features: List of features to order
            
        Returns:
            Ordered list of features
        """
        # Build dependency graph
        graph: Dict[FeatureType, Set[FeatureType]] = {f: set() for f in features}
        in_degree: Dict[FeatureType, int] = {f: 0 for f in features}
        
        for feature in features:
            deps = self.FEATURE_DEPENDENCIES.get(feature, set())
            for dep in deps:
                if dep in graph:
                    graph[dep].add(feature)
                    in_degree[feature] += 1
        
        # Topological sort (Kahn's algorithm)
        queue = [f for f in features if in_degree[f] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(result) != len(features):
            self.logger.warning("Dependency cycle detected, using input order")
            return features
        
        return result
    
    def _create_feature_task(
        self,
        job: BatchJob,
        feature_type: FeatureType,
        input_files: List[Path],
        output_dir: Path,
        config: Dict[str, Any]
    ) -> BatchTask:
        """Create a task for a specific feature."""
        # Feature-specific task creation
        callable_func = self._get_feature_callable(feature_type)
        
        task = self.orchestrator.add_task(
            job=job,
            name=f"{feature_type.value}_task",
            feature_type=feature_type,
            callable=callable_func,
            args=(input_files, output_dir),
            kwargs=config,
            input_files=input_files,
            output_dir=output_dir
        )
        
        return task
    
    def _get_feature_callable(self, feature_type: FeatureType):
        """Get the callable function for a feature type."""
        # Map feature types to their execution functions
        # These would be imported from their respective modules
        
        feature_callables = {
            FeatureType.FLAKY_DETECTION: self._execute_flaky_detection,
            FeatureType.COVERAGE_COLLECTION: self._execute_coverage_collection,
            FeatureType.INTENT_EXTRACTION: self._execute_intent_extraction,
            FeatureType.IMPACT_ANALYSIS: self._execute_impact_analysis,
            FeatureType.TEST_EXECUTION: self._execute_test_execution,
            FeatureType.RESULT_AGGREGATION: self._execute_result_aggregation,
            FeatureType.MIGRATION: self._execute_migration,
            FeatureType.VALIDATION: self._execute_validation,
        }
        
        return feature_callables.get(feature_type, self._execute_generic)
    
    # Feature execution stubs (these would call actual implementations)
    
    def _execute_flaky_detection(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Execute flaky test detection."""
        self.logger.info(f"Executing flaky detection on {len(input_files)} files")
        # TODO: Call actual flaky detection implementation
        return {"feature": "flaky_detection", "files_processed": len(input_files)}
    
    def _execute_coverage_collection(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Execute coverage collection."""
        self.logger.info(f"Executing coverage collection on {len(input_files)} files")
        # TODO: Call actual coverage collection implementation
        return {"feature": "coverage_collection", "files_processed": len(input_files)}
    
    def _execute_intent_extraction(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Execute intent extraction."""
        self.logger.info(f"Executing intent extraction on {len(input_files)} files")
        # TODO: Call actual intent extraction implementation
        return {"feature": "intent_extraction", "files_processed": len(input_files)}
    
    def _execute_impact_analysis(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Execute impact analysis."""
        self.logger.info(f"Executing impact analysis on {len(input_files)} files")
        # TODO: Call actual impact analysis implementation
        return {"feature": "impact_analysis", "files_processed": len(input_files)}
    
    def _execute_test_execution(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Execute test execution."""
        self.logger.info(f"Executing tests on {len(input_files)} files")
        # TODO: Call actual test execution implementation
        return {"feature": "test_execution", "tests_run": len(input_files)}
    
    def _execute_result_aggregation(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Execute result aggregation."""
        self.logger.info(f"Aggregating results from {len(input_files)} files")
        # TODO: Call actual result aggregation implementation
        return {"feature": "result_aggregation", "files_aggregated": len(input_files)}
    
    def _execute_migration(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Execute migration."""
        self.logger.info(f"Migrating {len(input_files)} files")
        # TODO: Call actual migration implementation
        return {"feature": "migration", "files_migrated": len(input_files)}
    
    def _execute_validation(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Execute validation."""
        self.logger.info(f"Validating {len(input_files)} files")
        # TODO: Call actual validation implementation
        return {"feature": "validation", "files_validated": len(input_files)}
    
    def _execute_generic(self, input_files: List[Path], output_dir: Path, **kwargs):
        """Generic feature execution."""
        self.logger.info(f"Executing generic feature on {len(input_files)} files")
        return {"feature": "generic", "files_processed": len(input_files)}
