"""
Comprehensive unit tests for batch orchestration system.

Tests all 4 major components:
1. Unified batch orchestrator
2. Cross-feature coordination
3. Batch result aggregation
4. Distributed processing
"""

import pytest
import time
from pathlib import Path
from datetime import datetime
import tempfile

from core.orchestration.batch import (
    BatchOrchestrator,
    FeatureCoordinator,
    BatchResultAggregator,
    DistributedExecutor,
    BatchJob,
    BatchTask,
    BatchResult,
    BatchConfig,
    TaskStatus,
    JobPriority,
    FeatureType,
    ExecutionMode
)


# Top-level function for distributed testing (must be picklable)
def distributed_test_task(name, duration):
    """Picklable task function for distributed execution tests."""
    import time
    time.sleep(duration)
    return {"name": name, "status": "completed"}


# Test fixtures

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def orchestrator():
    """Create a basic orchestrator."""
    config = BatchConfig(
        execution_mode=ExecutionMode.SEQUENTIAL,
        max_parallel_tasks=2
    )
    orch = BatchOrchestrator(config)
    yield orch
    orch.shutdown()


@pytest.fixture
def sample_task_callable():
    """Sample task function."""
    def task_func(name, duration=0.1):
        time.sleep(duration)
        return {"task": name, "status": "completed"}
    return task_func


# Test Models

class TestModels:
    """Test batch processing data models."""
    
    def test_batch_task_creation(self, sample_task_callable):
        """Test creating a batch task."""
        task = BatchTask(
            name="test_task",
            feature_type=FeatureType.TEST_EXECUTION,
            callable=sample_task_callable,
            args=("test",)
        )
        
        assert task.name == "test_task"
        assert task.feature_type == FeatureType.TEST_EXECUTION
        assert task.status == TaskStatus.PENDING
        assert not task.is_complete
        assert task.retry_count == 0
    
    def test_batch_job_creation(self):
        """Test creating a batch job."""
        job = BatchJob(
            name="test_job",
            description="Test job description"
        )
        
        assert job.name == "test_job"
        assert job.total_tasks == 0
        assert job.pending_tasks == 0
        # Empty job is considered complete
        assert job.is_complete
    
    def test_task_dependency(self):
        """Test task dependencies."""
        task1 = BatchTask(name="task1", feature_type=FeatureType.TEST_EXECUTION)
        task2 = BatchTask(name="task2", feature_type=FeatureType.COVERAGE_COLLECTION)
        
        task2.add_dependency(task1.task_id)
        
        assert len(task2.dependencies) == 1
        assert task2.dependencies[0].task_id == task1.task_id
    
    def test_job_statistics(self, sample_task_callable):
        """Test job statistics calculation."""
        job = BatchJob(name="stats_job")
        
        for i in range(5):
            task = BatchTask(
                name=f"task_{i}",
                feature_type=FeatureType.TEST_EXECUTION,
                callable=sample_task_callable
            )
            job.add_task(task)
        
        assert job.total_tasks == 5
        assert job.pending_tasks == 5
        
        # Mark some as completed
        job.tasks[0].status = TaskStatus.COMPLETED
        job.tasks[1].status = TaskStatus.COMPLETED
        job.tasks[2].status = TaskStatus.FAILED
        job._update_statistics()
        
        assert job.completed_tasks == 2
        assert job.failed_tasks == 1
        assert job.pending_tasks == 2
    
    def test_batch_config(self):
        """Test batch configuration."""
        config = BatchConfig(
            execution_mode=ExecutionMode.PARALLEL,
            max_parallel_tasks=8,
            default_max_retries=5,
            continue_on_failure=True
        )
        
        assert config.execution_mode == ExecutionMode.PARALLEL
        assert config.max_parallel_tasks == 8
        assert config.default_max_retries == 5
        assert config.continue_on_failure


# Test Orchestrator

class TestOrchestrator:
    """Test unified batch orchestrator."""
    
    def test_create_job(self, orchestrator):
        """Test job creation."""
        job = orchestrator.create_job(
            name="test_job",
            description="Test description",
            priority=JobPriority.HIGH
        )
        
        assert job.name == "test_job"
        assert job.priority == JobPriority.HIGH
        assert job.job_id in orchestrator.active_jobs
    
    def test_add_task(self, orchestrator, sample_task_callable):
        """Test adding tasks to a job."""
        job = orchestrator.create_job(name="task_job")
        
        task = orchestrator.add_task(
            job=job,
            name="test_task",
            feature_type=FeatureType.TEST_EXECUTION,
            callable=sample_task_callable,
            args=("test", 0.01)
        )
        
        assert task.name == "test_task"
        assert len(job.tasks) == 1
        assert job.total_tasks == 1
    
    def test_sequential_execution(self, orchestrator, sample_task_callable):
        """Test sequential task execution."""
        job = orchestrator.create_job(name="seq_job")
        
        for i in range(3):
            orchestrator.add_task(
                job=job,
                name=f"task_{i}",
                feature_type=FeatureType.TEST_EXECUTION,
                callable=sample_task_callable,
                args=(f"task_{i}", 0.05)
            )
        
        result = orchestrator.execute_job(job)
        
        assert result.total_tasks == 3
        assert result.completed_tasks == 3
        assert result.failed_tasks == 0
        assert result.success_rate == 100.0
    
    def test_parallel_execution(self, sample_task_callable):
        """Test parallel task execution."""
        config = BatchConfig(
            execution_mode=ExecutionMode.PARALLEL,
            max_parallel_tasks=3
        )
        orch = BatchOrchestrator(config)
        
        job = orch.create_job(name="parallel_job")
        
        for i in range(6):
            orch.add_task(
                job=job,
                name=f"task_{i}",
                feature_type=FeatureType.TEST_EXECUTION,
                callable=sample_task_callable,
                args=(f"task_{i}", 0.05)
            )
        
        result = orch.execute_job(job)
        
        assert result.completed_tasks == 6
        assert result.success_rate == 100.0
        
        orch.shutdown()
    
    def test_task_failure_handling(self, orchestrator):
        """Test handling of task failures."""
        job = orchestrator.create_job(name="fail_job")
        
        def failing_task():
            raise Exception("Task failed")
        
        orchestrator.add_task(
            job=job,
            name="failing_task",
            feature_type=FeatureType.TEST_EXECUTION,
            callable=failing_task
        )
        
        result = orchestrator.execute_job(job)
        
        assert result.failed_tasks == 1
        assert result.completed_tasks == 0
        assert len(result.errors) > 0
    
    def test_task_retry(self):
        """Test task retry logic."""
        config = BatchConfig(default_max_retries=2)
        orch = BatchOrchestrator(config)
        
        job = orch.create_job(name="retry_job")
        
        call_count = {"count": 0}
        
        def flaky_task():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise Exception("Temporary failure")
            return "success"
        
        orch.add_task(
            job=job,
            name="flaky_task",
            feature_type=FeatureType.TEST_EXECUTION,
            callable=flaky_task
        )
        
        result = orch.execute_job(job)
        
        # Task may be called multiple times due to retry logic
        assert call_count["count"] >= 2
        assert result.completed_tasks == 1
        
        orch.shutdown()
    
    def test_task_dependencies(self, orchestrator, sample_task_callable):
        """Test task dependency execution."""
        job = orchestrator.create_job(name="dep_job")
        
        task1 = orchestrator.add_task(
            job=job,
            name="task1",
            feature_type=FeatureType.TEST_EXECUTION,
            callable=sample_task_callable,
            args=("task1", 0.01)
        )
        
        task2 = orchestrator.add_task(
            job=job,
            name="task2",
            feature_type=FeatureType.COVERAGE_COLLECTION,
            callable=sample_task_callable,
            args=("task2", 0.01),
            dependencies=[task1.task_id]
        )
        
        result = orchestrator.execute_job(job)
        
        # Task2 should run after task1
        assert result.completed_tasks == 2
        assert task1.end_time < task2.start_time


# Test Coordinator

class TestCoordinator:
    """Test cross-feature coordination."""
    
    def test_feature_dependency_resolution(self, orchestrator):
        """Test feature dependency resolution."""
        coordinator = FeatureCoordinator(orchestrator)
        
        features = [
            FeatureType.RESULT_AGGREGATION,  # Has dependencies
            FeatureType.TEST_EXECUTION,       # No dependencies
            FeatureType.COVERAGE_COLLECTION   # No dependencies
        ]
        
        ordered = coordinator._resolve_dependencies(features)
        
        # RESULT_AGGREGATION should come after TEST_EXECUTION and COVERAGE_COLLECTION
        result_idx = ordered.index(FeatureType.RESULT_AGGREGATION)
        test_idx = ordered.index(FeatureType.TEST_EXECUTION)
        coverage_idx = ordered.index(FeatureType.COVERAGE_COLLECTION)
        
        assert result_idx > test_idx
        assert result_idx > coverage_idx
    
    def test_create_feature_pipeline(self, orchestrator, temp_dir):
        """Test creating a feature pipeline."""
        coordinator = FeatureCoordinator(orchestrator)
        
        test_files = []
        for i in range(3):
            f = temp_dir / f"test_{i}.py"
            f.write_text(f"# Test {i}")
            test_files.append(f)
        
        features = [
            FeatureType.TEST_EXECUTION,
            FeatureType.COVERAGE_COLLECTION
        ]
        
        input_files = {
            FeatureType.TEST_EXECUTION: test_files,
            FeatureType.COVERAGE_COLLECTION: test_files
        }
        
        job = coordinator.create_feature_pipeline(
            name="test_pipeline",
            features=features,
            input_files=input_files,
            output_dir=temp_dir / "output"
        )
        
        assert job.total_tasks == len(features)
        assert all(isinstance(t, BatchTask) for t in job.tasks)
    
    def test_parallel_feature_groups(self, orchestrator, temp_dir):
        """Test parallel feature group execution."""
        coordinator = FeatureCoordinator(orchestrator)
        
        test_files = [temp_dir / "test.py"]
        test_files[0].write_text("# Test")
        
        feature_groups = [
            [FeatureType.TEST_EXECUTION, FeatureType.COVERAGE_COLLECTION],
            [FeatureType.FLAKY_DETECTION]
        ]
        
        input_files = {f: test_files for group in feature_groups for f in group}
        
        job = coordinator.create_parallel_feature_job(
            name="parallel_groups",
            feature_groups=feature_groups,
            input_files=input_files,
            output_dir=temp_dir
        )
        
        # Should have 3 tasks total
        assert job.total_tasks == 3


# Test Aggregator

class TestAggregator:
    """Test batch result aggregation."""
    
    def test_aggregate_results(self, temp_dir):
        """Test aggregating multiple batch results."""
        aggregator = BatchResultAggregator(storage_dir=temp_dir)
        
        results = [
            BatchResult(
                job_id="job1",
                job_name="Job 1",
                total_tasks=10,
                completed_tasks=9,
                failed_tasks=1,
                duration=5.0
            ),
            BatchResult(
                job_id="job2",
                job_name="Job 2",
                total_tasks=15,
                completed_tasks=15,
                failed_tasks=0,
                duration=7.0
            )
        ]
        
        aggregated = aggregator.aggregate_results(results)
        
        assert aggregated['total_jobs'] == 2
        assert aggregated['total_tasks'] == 25
        assert aggregated['completed_tasks'] == 24
        assert aggregated['failed_tasks'] == 1
        assert aggregated['total_duration'] == 12.0
    
    def test_aggregate_by_feature(self, temp_dir):
        """Test feature-specific aggregation."""
        aggregator = BatchResultAggregator(storage_dir=temp_dir)
        
        result = BatchResult(
            job_id="job1",
            job_name="Test Job",
            total_tasks=2,
            completed_tasks=2,
            feature_results={
                FeatureType.TEST_EXECUTION: [
                    {"tests_run": 10},
                    {"tests_run": 15}
                ]
            }
        )
        
        feature_agg = aggregator.aggregate_by_feature(
            [result],
            FeatureType.TEST_EXECUTION
        )
        
        assert feature_agg['feature_type'] == 'test_execution'
        assert feature_agg['total_results'] == 2
    
    def test_generate_report(self, temp_dir):
        """Test report generation."""
        aggregator = BatchResultAggregator(storage_dir=temp_dir)
        
        results = [
            BatchResult(
                job_id="job1",
                job_name="Test Job",
                total_tasks=5,
                completed_tasks=5,
                failed_tasks=0,
                duration=2.5
            )
        ]
        
        report = aggregator.generate_report(results, report_format="text")
        
        assert "BATCH EXECUTION REPORT" in report
        assert "Test Job" in report
        assert "5" in report  # task count
    
    def test_save_results(self, temp_dir):
        """Test saving results to file."""
        aggregator = BatchResultAggregator(storage_dir=temp_dir)
        
        results = [
            BatchResult(
                job_id="job1",
                job_name="Test Job",
                total_tasks=3,
                completed_tasks=3
            )
        ]
        
        output_path = aggregator.save_results(results, "test_results.json")
        
        assert output_path.exists()
        assert output_path.suffix == ".json"
    
    def test_compare_results(self, temp_dir):
        """Test result comparison."""
        aggregator = BatchResultAggregator(storage_dir=temp_dir)
        
        baseline = BatchResult(
            job_id="baseline",
            job_name="Baseline",
            total_tasks=10,
            completed_tasks=8,
            failed_tasks=2,
            duration=10.0
        )
        
        current = BatchResult(
            job_id="current",
            job_name="Current",
            total_tasks=10,
            completed_tasks=9,
            failed_tasks=1,
            duration=9.0
        )
        
        comparison = aggregator.compare_results(baseline, current)
        
        assert comparison['changes']['success_rate_delta'] > 0  # Improved
        assert comparison['changes']['duration_delta'] < 0  # Faster
        assert comparison['assessment'] == 'improvement'


# Test Distributed Executor

class TestDistributed:
    """Test distributed processing."""
    
    def test_executor_initialization(self):
        """Test distributed executor initialization."""
        config = BatchConfig(
            enable_distributed=True,
            worker_count=2
        )
        
        executor = DistributedExecutor(config)
        
        assert executor.config.worker_count == 2
        assert not executor.is_running
    
    def test_executor_start_stop(self):
        """Test starting and stopping executor."""
        config = BatchConfig(worker_count=2)
        executor = DistributedExecutor(config)
        
        executor.start()
        assert executor.is_running
        assert executor.worker_pool is not None
        
        executor.stop()
        assert not executor.is_running
    
    def test_distributed_execution(self):
        """Test distributed task execution."""
        config = BatchConfig(
            enable_distributed=True,
            worker_count=2
        )
        executor = DistributedExecutor(config)
        
        job = BatchJob(name="distributed_job")
        
        for i in range(4):
            task = BatchTask(
                name=f"task_{i}",
                feature_type=FeatureType.TEST_EXECUTION,
                callable=distributed_test_task,  # Use top-level function
                args=(f"task_{i}", 0.05)
            )
            job.add_task(task)
        
        result = executor.execute_distributed(job)
        
        assert result['completed_tasks'] == 4
        assert result['success_rate'] == 100.0
        
        executor.stop()


# Integration Tests

class TestIntegration:
    """Test end-to-end workflows."""
    
    def test_complete_pipeline(self, temp_dir):
        """Test complete batch processing pipeline."""
        # Setup
        config = BatchConfig(
            execution_mode=ExecutionMode.PARALLEL,
            max_parallel_tasks=2
        )
        orchestrator = BatchOrchestrator(config)
        coordinator = FeatureCoordinator(orchestrator)
        aggregator = BatchResultAggregator(storage_dir=temp_dir)
        
        # Create test files
        test_files = []
        for i in range(3):
            f = temp_dir / f"test_{i}.py"
            f.write_text(f"def test_{i}(): pass")
            test_files.append(f)
        
        # Create pipeline
        features = [
            FeatureType.TEST_EXECUTION,
            FeatureType.COVERAGE_COLLECTION
        ]
        
        job = coordinator.create_feature_pipeline(
            name="integration_pipeline",
            features=features,
            input_files={f: test_files for f in features},
            output_dir=temp_dir / "output"
        )
        
        # Execute
        result = orchestrator.execute_job(job)
        
        # Verify
        assert result.completed_tasks == len(features)
        assert result.success_rate == 100.0
        
        # Aggregate
        aggregated = aggregator.aggregate_results([result])
        
        assert aggregated['total_jobs'] == 1
        assert aggregated['completed_tasks'] == len(features)
        
        # Generate report
        report = aggregator.generate_report([result])
        assert "BATCH EXECUTION REPORT" in report
        
        orchestrator.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
