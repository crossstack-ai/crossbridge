"""
Unified batch orchestrator for managing batch job execution.

Coordinates task execution, dependency resolution, and lifecycle management
across all CrossBridge features.
"""

import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Callable, Any
from queue import PriorityQueue

from core.logging import get_logger
from core.orchestration.batch.models import (
    BatchJob,
    BatchTask,
    BatchResult,
    BatchConfig,
    TaskStatus,
    JobPriority,
    ExecutionMode,
    FeatureType
)


class BatchOrchestrator:
    """
    Unified batch orchestrator for managing batch jobs.
    
    Features:
    - Task lifecycle management
    - Dependency resolution
    - Parallel/sequential execution
    - Retry logic with exponential backoff
    - Progress tracking
    - Resource management
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """
        Initialize batch orchestrator.
        
        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig()
        self.logger = get_logger("core.orchestration.batch")
        
        # Job management
        self.active_jobs: Dict[str, BatchJob] = {}
        self.completed_jobs: Dict[str, BatchResult] = {}
        
        # Task queue
        self.task_queue: PriorityQueue = PriorityQueue()
        
        # Thread pool for parallel execution
        self.executor: Optional[ThreadPoolExecutor] = None
        if self.config.execution_mode in {ExecutionMode.PARALLEL, ExecutionMode.ADAPTIVE}:
            self.executor = ThreadPoolExecutor(
                max_workers=self.config.max_parallel_tasks
            )
        
        self.logger.info(
            f"BatchOrchestrator initialized with mode={self.config.execution_mode.value}, "
            f"max_parallel={self.config.max_parallel_tasks}"
        )
    
    def create_job(
        self,
        name: str,
        description: str = "",
        execution_mode: Optional[ExecutionMode] = None,
        priority: JobPriority = JobPriority.NORMAL,
        **kwargs
    ) -> BatchJob:
        """
        Create a new batch job.
        
        Args:
            name: Job name
            description: Job description
            execution_mode: Execution mode (overrides config)
            priority: Job priority
            **kwargs: Additional job parameters
            
        Returns:
            Created BatchJob
        """
        job = BatchJob(
            name=name,
            description=description,
            execution_mode=execution_mode or self.config.execution_mode,
            priority=priority,
            max_parallel_tasks=self.config.max_parallel_tasks,
            continue_on_failure=self.config.continue_on_failure,
            **kwargs
        )
        
        self.active_jobs[job.job_id] = job
        self.logger.info(f"Created batch job: {name} (ID: {job.job_id[:8]})")
        
        return job
    
    def add_task(
        self,
        job: BatchJob,
        name: str,
        feature_type: FeatureType,
        callable: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        **task_kwargs
    ) -> BatchTask:
        """
        Add a task to a batch job.
        
        Args:
            job: Target batch job
            name: Task name
            feature_type: Type of feature to execute
            callable: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            dependencies: List of task IDs this task depends on
            **task_kwargs: Additional task parameters
            
        Returns:
            Created BatchTask
        """
        task = BatchTask(
            name=name,
            feature_type=feature_type,
            callable=callable,
            args=args,
            kwargs=kwargs or {},
            max_retries=self.config.default_max_retries,
            timeout=self.config.default_task_timeout,
            **task_kwargs
        )
        
        # Add dependencies
        if dependencies:
            for dep_id in dependencies:
                task.add_dependency(dep_id)
        
        job.add_task(task)
        self.logger.debug(f"Added task '{name}' to job '{job.name}'")
        
        return task
    
    def execute_job(self, job: BatchJob) -> BatchResult:
        """
        Execute a batch job.
        
        Args:
            job: Job to execute
            
        Returns:
            BatchResult with execution summary
        """
        self.logger.info(f"Starting execution of job: {job.name}")
        job.start_time = datetime.now()
        
        try:
            if job.execution_mode == ExecutionMode.SEQUENTIAL:
                self._execute_sequential(job)
            elif job.execution_mode == ExecutionMode.PARALLEL:
                self._execute_parallel(job)
            elif job.execution_mode == ExecutionMode.ADAPTIVE:
                self._execute_adaptive(job)
            else:
                raise ValueError(f"Unsupported execution mode: {job.execution_mode}")
            
            job.end_time = datetime.now()
            job.duration = (job.end_time - job.start_time).total_seconds()
            
            result = self._create_result(job)
            self.completed_jobs[job.job_id] = result
            
            self.logger.success(
                f"Job '{job.name}' completed: {result.completed_tasks}/{result.total_tasks} "
                f"tasks successful in {result.duration:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Job '{job.name}' failed: {e}", exc_info=True)
            job.end_time = datetime.now()
            job.duration = (job.end_time - job.start_time).total_seconds()
            job.errors.append(str(e))
            
            result = self._create_result(job)
            self.completed_jobs[job.job_id] = result
            
            return result
        
        finally:
            # Cleanup
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
    
    def _execute_sequential(self, job: BatchJob):
        """Execute tasks sequentially."""
        self.logger.info(f"Executing {job.total_tasks} tasks sequentially")
        
        while not job.is_complete:
            runnable_tasks = job.get_runnable_tasks()
            
            if not runnable_tasks:
                # Check if we're stuck (no runnable tasks but job not complete)
                if not job.is_complete:
                    pending = job.get_tasks_by_status(TaskStatus.PENDING)
                    if pending:
                        self.logger.warning(
                            f"Deadlock detected: {len(pending)} pending tasks with unsatisfied dependencies"
                        )
                        for task in pending:
                            task.status = TaskStatus.SKIPPED
                            task.error = "Dependency deadlock"
                            job._update_statistics()
                break
            
            # Execute one task at a time
            task = runnable_tasks[0]
            self._execute_task(job, task)
    
    def _execute_parallel(self, job: BatchJob):
        """Execute tasks in parallel."""
        self.logger.info(f"Executing {job.total_tasks} tasks in parallel (max={job.max_parallel_tasks})")
        
        futures = {}
        
        while not job.is_complete or futures:
            # Get runnable tasks
            runnable_tasks = job.get_runnable_tasks()
            
            # Submit new tasks up to the parallel limit
            while runnable_tasks and len(futures) < job.max_parallel_tasks:
                task = runnable_tasks.pop(0)
                task.status = TaskStatus.QUEUED
                task.queued_time = datetime.now()
                job._update_statistics()
                
                future = self.executor.submit(self._execute_task_wrapper, job, task)
                futures[future] = task
                
                self.logger.debug(f"Submitted task '{task.name}' for execution")
            
            # Wait for any task to complete
            if futures:
                done, _ = as_completed(futures.keys()), None
                for future in list(futures.keys()):
                    if future.done():
                        task = futures.pop(future)
                        try:
                            future.result()
                        except Exception as e:
                            self.logger.error(f"Task '{task.name}' failed: {e}")
            
            # Break if no progress can be made
            if not runnable_tasks and not futures:
                break
    
    def _execute_adaptive(self, job: BatchJob):
        """Execute with adaptive parallelism based on task characteristics."""
        # Start with parallel execution
        self.logger.info("Executing with adaptive parallelism")
        
        # For now, use parallel execution
        # TODO: Implement adaptive logic based on task duration, resource usage, etc.
        self._execute_parallel(job)
    
    def _execute_task(self, job: BatchJob, task: BatchTask) -> bool:
        """
        Execute a single task.
        
        Args:
            job: Parent job
            task: Task to execute
            
        Returns:
            True if successful, False otherwise
        """
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        job._update_statistics()
        
        self.logger.info(f"Executing task: {task.name} ({task.feature_type.value})")
        
        try:
            # Execute the task
            if task.callable:
                result = task.callable(*task.args, **task.kwargs)
                task.result = result
            
            task.status = TaskStatus.COMPLETED
            task.end_time = datetime.now()
            task.duration = (task.end_time - task.start_time).total_seconds()
            job._update_statistics()
            
            self.logger.success(f"Task '{task.name}' completed in {task.duration:.2f}s")
            
            return True
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.error_type = type(e).__name__
            task.stacktrace = traceback.format_exc()
            task.end_time = datetime.now()
            task.duration = (task.end_time - task.start_time).total_seconds()
            job._update_statistics()
            
            self.logger.error(f"Task '{task.name}' failed: {e}")
            
            # Retry logic
            if task.can_retry:
                self.logger.warning(f"Retrying task '{task.name}' ({task.retry_count + 1}/{task.max_retries})")
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                job._update_statistics()
                
                # Exponential backoff
                if self.config.exponential_backoff:
                    delay = self.config.retry_delay * (2 ** task.retry_count)
                    import time
                    time.sleep(min(delay, 60))  # Max 60 seconds
                
                return self._execute_task(job, task)
            
            job.errors.append(f"Task '{task.name}': {str(e)}")
            
            # Check if we should continue
            if not job.continue_on_failure and self.config.fail_fast:
                raise
            
            return False
    
    def _execute_task_wrapper(self, job: BatchJob, task: BatchTask):
        """Wrapper for thread pool execution."""
        return self._execute_task(job, task)
    
    def _create_result(self, job: BatchJob) -> BatchResult:
        """Create a BatchResult from a completed job."""
        # Collect task results
        task_results = {}
        for task in job.tasks:
            task_results[task.task_id] = {
                'name': task.name,
                'status': task.status.value,
                'duration': task.duration,
                'result': task.result,
                'error': task.error
            }
        
        # Group results by feature type
        feature_results = {}
        for task in job.tasks:
            if task.status == TaskStatus.COMPLETED and task.result:
                if task.feature_type not in feature_results:
                    feature_results[task.feature_type] = []
                feature_results[task.feature_type].append(task.result)
        
        result = BatchResult(
            job_id=job.job_id,
            job_name=job.name,
            total_tasks=job.total_tasks,
            completed_tasks=job.completed_tasks,
            failed_tasks=job.failed_tasks,
            skipped_tasks=job.skipped_tasks,
            duration=job.duration,
            task_results=task_results,
            feature_results=feature_results,
            errors=[{'task': e} for e in job.errors]
        )
        
        return result
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a job."""
        job = self.active_jobs.get(job_id) or self.completed_jobs.get(job_id)
        if not job:
            return None
        
        if isinstance(job, BatchJob):
            return {
                'job_id': job.job_id,
                'name': job.name,
                'status': 'running',
                'progress': job.progress_percentage,
                'total_tasks': job.total_tasks,
                'completed_tasks': job.completed_tasks,
                'failed_tasks': job.failed_tasks,
                'running_tasks': job.running_tasks
            }
        else:  # BatchResult
            return {
                'job_id': job.job_id,
                'name': job.job_name,
                'status': 'completed',
                'success_rate': job.success_rate,
                'total_tasks': job.total_tasks,
                'completed_tasks': job.completed_tasks,
                'failed_tasks': job.failed_tasks,
                'duration': job.duration
            }
    
    def cancel_job(self, job_id: str):
        """Cancel a running job."""
        job = self.active_jobs.get(job_id)
        if not job:
            self.logger.warning(f"Job {job_id} not found or already completed")
            return
        
        self.logger.warning(f"Cancelling job: {job.name}")
        
        for task in job.tasks:
            if task.status in {TaskStatus.PENDING, TaskStatus.QUEUED}:
                task.status = TaskStatus.CANCELLED
        
        job._update_statistics()
    
    def shutdown(self):
        """Shutdown the orchestrator and cleanup resources."""
        self.logger.info("Shutting down BatchOrchestrator")
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        self.active_jobs.clear()
