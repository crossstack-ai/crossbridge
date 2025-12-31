"""
Batch Processing Orchestration Demo

Demonstrates all features of the batch orchestration system:
1. Unified batch orchestrator
2. Cross-feature coordination
3. Batch result aggregation
4. Distributed processing
"""

import time
from pathlib import Path
import tempfile

from core.orchestration.batch import (
    BatchOrchestrator,
    FeatureCoordinator,
    BatchResultAggregator,
    DistributedExecutor,
    BatchConfig,
    FeatureType,
    ExecutionMode,
    JobPriority
)
from core.logging import get_logger

# Setup
logger = get_logger("demo")
logger.info("🚀 Starting Batch Orchestration Demo")


def sample_task(task_name: str, duration: float = 0.5):
    """Sample task that simulates work."""
    logger.info(f"Executing task: {task_name}")
    time.sleep(duration)
    return {"task": task_name, "status": "completed", "duration": duration}


def demo_unified_orchestrator():
    """Demo 1: Unified Batch Orchestrator"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 1: Unified Batch Orchestrator")
    logger.info("="*60)
    
    # Create orchestrator with parallel execution
    config = BatchConfig(
        execution_mode=ExecutionMode.PARALLEL,
        max_parallel_tasks=3,
        default_max_retries=2
    )
    
    orchestrator = BatchOrchestrator(config)
    
    # Create a job
    job = orchestrator.create_job(
        name="parallel_processing_job",
        description="Demonstrate parallel task execution",
        priority=JobPriority.HIGH
    )
    
    # Add multiple tasks
    for i in range(6):
        orchestrator.add_task(
            job=job,
            name=f"task_{i+1}",
            feature_type=FeatureType.TEST_EXECUTION,
            callable=sample_task,
            args=(f"task_{i+1}", 0.3)
        )
    
    logger.info(f"\n📊 Created job with {job.total_tasks} tasks")
    
    # Execute the job
    logger.info("\n⚡ Executing in parallel mode (max 3 concurrent tasks)...")
    result = orchestrator.execute_job(job)
    
    logger.success(f"\n✅ Job completed!")
    logger.info(f"  • Success rate: {result.success_rate:.1f}%")
    logger.info(f"  • Duration: {result.duration:.2f}s")
    logger.info(f"  • Completed: {result.completed_tasks}/{result.total_tasks}")
    
    orchestrator.shutdown()


def demo_cross_feature_coordination():
    """Demo 2: Cross-Feature Coordination"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 2: Cross-Feature Coordination")
    logger.info("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create orchestrator and coordinator
        orchestrator = BatchOrchestrator()
        coordinator = FeatureCoordinator(orchestrator)
        
        # Create input files
        test_files = []
        for i in range(3):
            test_file = tmpdir / f"test_{i}.py"
            test_file.write_text(f"# Test file {i}")
            test_files.append(test_file)
        
        logger.info(f"\n📁 Created {len(test_files)} test files")
        
        # Create feature pipeline with dependencies
        features = [
            FeatureType.TEST_EXECUTION,
            FeatureType.COVERAGE_COLLECTION,
            FeatureType.FLAKY_DETECTION,
            FeatureType.RESULT_AGGREGATION
        ]
        
        input_files = {
            FeatureType.TEST_EXECUTION: test_files,
            FeatureType.COVERAGE_COLLECTION: test_files,
            FeatureType.FLAKY_DETECTION: test_files,
            FeatureType.RESULT_AGGREGATION: test_files
        }
        
        logger.info(f"\n🔗 Creating pipeline with {len(features)} features...")
        logger.info("   Features: " + " → ".join(f.value for f in features))
        
        job = coordinator.create_feature_pipeline(
            name="test_analysis_pipeline",
            features=features,
            input_files=input_files,
            output_dir=tmpdir / "output"
        )
        
        logger.info(f"\n📋 Pipeline created with {job.total_tasks} tasks")
        
        # Show dependency graph
        logger.info("\n🌐 Dependency graph:")
        for task in job.tasks:
            deps = [f"depends on {len(task.dependencies)} tasks"] if task.dependencies else ["no dependencies"]
            logger.info(f"  • {task.name}: {deps[0]}")
        
        # Execute pipeline
        logger.info("\n⚡ Executing feature pipeline...")
        result = orchestrator.execute_job(job)
        
        logger.success(f"\n✅ Pipeline completed!")
        logger.info(f"  • Duration: {result.duration:.2f}s")
        logger.info(f"  • Features processed: {len(result.feature_results)}")
        
        for feature_type, results in result.feature_results.items():
            logger.info(f"    - {feature_type.value}: {len(results)} results")


def demo_result_aggregation():
    """Demo 3: Batch Result Aggregation"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 3: Batch Result Aggregation")
    logger.info("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create orchestrator and aggregator
        orchestrator = BatchOrchestrator()
        aggregator = BatchResultAggregator(storage_dir=tmpdir)
        
        # Run multiple jobs
        results = []
        
        for job_num in range(3):
            job = orchestrator.create_job(
                name=f"batch_job_{job_num+1}",
                description=f"Batch job {job_num+1}"
            )
            
            # Add tasks with varying success rates
            for i in range(5):
                # Simulate some failures
                def task_with_failure(name, should_fail=False):
                    if should_fail:
                        raise Exception(f"{name} failed")
                    return {"task": name, "status": "completed"}
                
                should_fail = (i % 3 == 0 and job_num == 1)  # Some tasks fail in job 2
                
                orchestrator.add_task(
                    job=job,
                    name=f"task_{i+1}",
                    feature_type=FeatureType.TEST_EXECUTION,
                    callable=task_with_failure,
                    args=(f"task_{i+1}", should_fail)
                )
            
            result = orchestrator.execute_job(job)
            results.append(result)
            
            logger.info(f"\n  Job {job_num+1}: {result.completed_tasks}/{result.total_tasks} tasks completed")
        
        # Aggregate results
        logger.info("\n📊 Aggregating results from all jobs...")
        aggregated = aggregator.aggregate_results(results)
        
        logger.success(f"\n✅ Aggregation complete!")
        logger.info(f"  • Total jobs: {aggregated['total_jobs']}")
        logger.info(f"  • Total tasks: {aggregated['total_tasks']}")
        logger.info(f"  • Completed: {aggregated['completed_tasks']}")
        logger.info(f"  • Failed: {aggregated['failed_tasks']}")
        logger.info(f"  • Avg success rate: {aggregated['avg_success_rate']:.1f}%")
        logger.info(f"  • Total duration: {aggregated['total_duration']:.2f}s")
        
        # Generate report
        logger.info("\n📄 Generating report...")
        report = aggregator.generate_report(results)
        print("\n" + report)
        
        # Save results
        output_file = aggregator.save_results(results)
        logger.success(f"\n💾 Results saved to: {output_file}")


def demo_distributed_processing():
    """Demo 4: Distributed Processing"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 4: Distributed Processing")
    logger.info("="*60)
    
    # Create config for distributed processing
    config = BatchConfig(
        enable_distributed=True,
        worker_count=4,
        max_parallel_tasks=4
    )
    
    # Create executor
    executor = DistributedExecutor(config)
    executor.start()
    
    logger.info(f"\n🌐 Started distributed executor with {config.worker_count} workers")
    
    # Create orchestrator
    orchestrator = BatchOrchestrator(config)
    
    # Create a compute-intensive job
    job = orchestrator.create_job(
        name="distributed_compute_job",
        description="Heavy computation distributed across workers",
        execution_mode=ExecutionMode.PARALLEL
    )
    
    # Add compute tasks
    for i in range(12):
        orchestrator.add_task(
            job=job,
            name=f"compute_task_{i+1}",
            feature_type=FeatureType.TEST_EXECUTION,
            callable=sample_task,
            args=(f"compute_{i+1}", 0.5)
        )
    
    logger.info(f"\n⚡ Distributing {job.total_tasks} tasks across workers...")
    
    # Execute with distributed processing
    result = executor.execute_distributed(job)
    
    logger.success(f"\n✅ Distributed execution completed!")
    logger.info(f"  • Tasks completed: {result['completed_tasks']}/{job.total_tasks}")
    logger.info(f"  • Success rate: {result['success_rate']:.1f}%")
    logger.info(f"  • Duration: {result['duration']:.2f}s")
    logger.info(f"  • Avg time per task: {result['duration']/job.total_tasks:.2f}s")
    
    # Show worker stats
    worker_stats = executor.get_worker_stats()
    logger.info(f"\n👷 Worker statistics:")
    logger.info(f"  • Total workers: {worker_stats['total_workers']}")
    logger.info(f"  • Active: {worker_stats['active_workers']}")
    logger.info(f"  • Idle: {worker_stats['idle_workers']}")
    
    executor.stop()


def demo_complete_workflow():
    """Demo 5: Complete End-to-End Workflow"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 5: Complete End-to-End Workflow")
    logger.info("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Step 1: Setup
        logger.info("\n📝 Step 1: Setting up batch orchestration...")
        
        config = BatchConfig(
            execution_mode=ExecutionMode.PARALLEL,
            max_parallel_tasks=3,
            continue_on_failure=True
        )
        
        orchestrator = BatchOrchestrator(config)
        coordinator = FeatureCoordinator(orchestrator)
        aggregator = BatchResultAggregator(storage_dir=tmpdir)
        
        # Step 2: Create test files
        logger.info("\n📁 Step 2: Creating test files...")
        test_files = []
        for i in range(5):
            test_file = tmpdir / f"test_{i}.py"
            test_file.write_text(f"def test_{i}(): assert True")
            test_files.append(test_file)
        
        logger.success(f"Created {len(test_files)} test files")
        
        # Step 3: Create feature pipeline
        logger.info("\n🔗 Step 3: Creating multi-feature pipeline...")
        
        features = [
            FeatureType.TEST_EXECUTION,
            FeatureType.COVERAGE_COLLECTION,
            FeatureType.FLAKY_DETECTION,
            FeatureType.RESULT_AGGREGATION
        ]
        
        job = coordinator.create_feature_pipeline(
            name="complete_test_workflow",
            features=features,
            input_files={f: test_files for f in features},
            output_dir=tmpdir / "results"
        )
        
        logger.success(f"Created pipeline with {job.total_tasks} tasks")
        
        # Step 4: Execute
        logger.info("\n⚡ Step 4: Executing pipeline...")
        result = orchestrator.execute_job(job)
        
        # Step 5: Aggregate and report
        logger.info("\n📊 Step 5: Aggregating results...")
        report = aggregator.generate_report([result])
        
        logger.success("\n✅ Complete workflow finished!")
        logger.info(f"  • Total features: {len(features)}")
        logger.info(f"  • Tasks executed: {result.total_tasks}")
        logger.info(f"  • Success rate: {result.success_rate:.1f}%")
        logger.info(f"  • Total duration: {result.duration:.2f}s")
        
        print("\n" + "="*60)
        print("FINAL REPORT")
        print("="*60)
        print(report)


def main():
    """Run all demos"""
    try:
        demo_unified_orchestrator()
        demo_cross_feature_coordination()
        demo_result_aggregation()
        demo_distributed_processing()
        demo_complete_workflow()
        
        logger.info("\n" + "="*60)
        logger.success("🎉 All demos completed successfully!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
