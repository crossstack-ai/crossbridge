"""
Distributed processing support for batch orchestration.

Enables distributed execution of batch jobs across multiple workers
for improved performance and scalability.
"""

import socket
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime
from multiprocessing import Manager, Queue
from pathlib import Path
from queue import Empty
from typing import Dict, List, Optional, Callable, Any

from core.logging import get_logger
from core.orchestration.batch.models import (
    BatchJob,
    BatchTask,
    BatchConfig,
    TaskStatus,
    WorkerInfo,
    FeatureType
)


class DistributedExecutor:
    """
    Distributed executor for parallel batch processing.
    
    Features:
    - Multi-process execution
    - Worker pool management
    - Task distribution
    - Load balancing
    - Fault tolerance
    - Progress monitoring
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """
        Initialize distributed executor.
        
        Args:
            config: Batch configuration
        """
        self.config = config or BatchConfig(enable_distributed=True)
        self.logger = get_logger("core.orchestration.batch.distributed")
        
        # Worker management
        self.workers: Dict[str, WorkerInfo] = {}
        self.worker_pool: Optional[ProcessPoolExecutor] = None
        
        # Task queue for distribution
        self.manager = Manager()
        self.task_queue: Queue = self.manager.Queue()
        self.result_queue: Queue = self.manager.Queue()
        
        # Monitoring
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        self.logger.info(
            f"DistributedExecutor initialized with {self.config.worker_count} workers"
        )
    
    def start(self):
        """Start the distributed executor."""
        if self.is_running:
            self.logger.warning("Executor already running")
            return
        
        self.logger.info("Starting distributed executor")
        
        # Create worker pool
        self.worker_pool = ProcessPoolExecutor(
            max_workers=self.config.worker_count
        )
        
        # Start monitoring thread
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_workers, daemon=True)
        self.monitor_thread.start()
        
        self.logger.success(f"Started {self.config.worker_count} workers")
    
    def stop(self):
        """Stop the distributed executor."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping distributed executor")
        
        self.is_running = False
        
        if self.worker_pool:
            self.worker_pool.shutdown(wait=True)
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.success("Distributed executor stopped")
    
    def execute_distributed(self, job: BatchJob) -> Dict[str, Any]:
        """
        Execute a batch job in distributed mode.
        
        Args:
            job: Job to execute
            
        Returns:
            Execution results
        """
        if not self.is_running:
            self.start()
        
        self.logger.info(f"Executing job '{job.name}' in distributed mode with {job.total_tasks} tasks")
        
        job.start_time = datetime.now()
        
        # Submit all tasks to queue
        for task in job.tasks:
            if task.status == TaskStatus.PENDING:
                self.task_queue.put((job.job_id, task.task_id, task.callable, task.args, task.kwargs))
                task.status = TaskStatus.QUEUED
        
        job._update_statistics()
        
        # Process tasks with worker pool
        futures = []
        completed_tasks = 0
        
        while completed_tasks < job.total_tasks:
            # Submit work to workers
            try:
                job_id, task_id, callable_fn, args, kwargs = self.task_queue.get(timeout=1.0)
                
                future = self.worker_pool.submit(
                    self._execute_task_worker,
                    job_id,
                    task_id,
                    callable_fn,
                    args,
                    kwargs
                )
                futures.append((future, task_id))
                
            except Empty:
                pass
            
            # Collect completed tasks
            for future, task_id in list(futures):
                if future.done():
                    futures.remove((future, task_id))
                    
                    try:
                        success, result, error = future.result()
                        
                        task = job.get_task(task_id)
                        if task:
                            if success:
                                task.status = TaskStatus.COMPLETED
                                task.result = result
                            else:
                                task.status = TaskStatus.FAILED
                                task.error = error
                            
                            completed_tasks += 1
                            job._update_statistics()
                            
                            self.logger.debug(
                                f"Task {task.name} completed: {task.status.value}"
                            )
                    
                    except Exception as e:
                        self.logger.error(f"Error processing task result: {e}")
                        completed_tasks += 1
            
            # Check if we need to wait for more results
            if not futures and self.task_queue.empty():
                break
        
        job.end_time = datetime.now()
        job.duration = (job.end_time - job.start_time).total_seconds()
        
        results = {
            'job_id': job.job_id,
            'completed_tasks': job.completed_tasks,
            'failed_tasks': job.failed_tasks,
            'duration': job.duration,
            'success_rate': job.success_rate
        }
        
        self.logger.success(
            f"Distributed execution completed: {job.completed_tasks}/{job.total_tasks} "
            f"tasks in {job.duration:.2f}s"
        )
        
        return results
    
    def execute_parallel_jobs(self, jobs: List[BatchJob]) -> List[Dict[str, Any]]:
        """
        Execute multiple jobs in parallel.
        
        Args:
            jobs: List of jobs to execute
            
        Returns:
            List of execution results
        """
        if not self.is_running:
            self.start()
        
        self.logger.info(f"Executing {len(jobs)} jobs in parallel")
        
        with ThreadPoolExecutor(max_workers=self.config.max_parallel_jobs) as executor:
            futures = {executor.submit(self.execute_distributed, job): job for job in jobs}
            
            results = []
            for future in as_completed(futures):
                job = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Job '{job.name}' failed: {e}")
                    results.append({'job_id': job.job_id, 'error': str(e)})
        
        return results
    
    @staticmethod
    def _execute_task_worker(
        job_id: str,
        task_id: str,
        callable_fn: Callable,
        args: tuple,
        kwargs: dict
    ) -> tuple:
        """
        Worker function to execute a task.
        
        Returns:
            (success, result, error)
        """
        try:
            result = callable_fn(*args, **kwargs)
            return (True, result, None)
        except Exception as e:
            return (False, None, str(e))
    
    def _monitor_workers(self):
        """Monitor worker health and performance."""
        while self.is_running:
            try:
                # Update worker heartbeats
                for worker_id, worker in list(self.workers.items()):
                    if not worker.is_alive:
                        self.logger.warning(f"Worker {worker_id[:8]} appears to be dead")
                        # Could implement worker restart logic here
                
                time.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error in worker monitor: {e}")
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics about workers."""
        return {
            'total_workers': len(self.workers),
            'active_workers': sum(1 for w in self.workers.values() if w.status == "busy"),
            'idle_workers': sum(1 for w in self.workers.values() if w.status == "idle"),
            'disconnected_workers': sum(1 for w in self.workers.values() if not w.is_alive),
            'workers': [
                {
                    'worker_id': w.worker_id[:8],
                    'status': w.status,
                    'tasks_completed': w.tasks_completed,
                    'tasks_failed': w.tasks_failed,
                    'avg_duration': w.avg_task_duration
                }
                for w in self.workers.values()
            ]
        }


class LoadBalancer:
    """
    Load balancer for distributing tasks across workers.
    
    Implements various load balancing strategies.
    """
    
    def __init__(self, strategy: str = "round_robin"):
        """
        Initialize load balancer.
        
        Args:
            strategy: Load balancing strategy (round_robin, least_loaded, capability_based)
        """
        self.strategy = strategy
        self.logger = get_logger("core.orchestration.batch.loadbalancer")
        self.current_worker_index = 0
    
    def assign_task(
        self,
        task: BatchTask,
        workers: List[WorkerInfo]
    ) -> Optional[WorkerInfo]:
        """
        Assign a task to a worker.
        
        Args:
            task: Task to assign
            workers: Available workers
            
        Returns:
            Selected worker or None if no workers available
        """
        available_workers = [w for w in workers if w.status == "idle"]
        
        if not available_workers:
            return None
        
        if self.strategy == "round_robin":
            return self._round_robin(available_workers)
        elif self.strategy == "least_loaded":
            return self._least_loaded(available_workers)
        elif self.strategy == "capability_based":
            return self._capability_based(task, available_workers)
        else:
            return available_workers[0]
    
    def _round_robin(self, workers: List[WorkerInfo]) -> WorkerInfo:
        """Round-robin selection."""
        worker = workers[self.current_worker_index % len(workers)]
        self.current_worker_index += 1
        return worker
    
    def _least_loaded(self, workers: List[WorkerInfo]) -> WorkerInfo:
        """Select worker with least tasks completed (fastest)."""
        return min(workers, key=lambda w: w.tasks_completed)
    
    def _capability_based(
        self,
        task: BatchTask,
        workers: List[WorkerInfo]
    ) -> WorkerInfo:
        """Select worker based on capabilities."""
        # Filter workers that can handle this task type
        capable_workers = [
            w for w in workers
            if task.feature_type in w.capabilities or not w.capabilities
        ]
        
        if not capable_workers:
            return workers[0]
        
        # Select least loaded among capable workers
        return self._least_loaded(capable_workers)


class WorkerPool:
    """
    Pool of workers for distributed execution.
    """
    
    def __init__(self, worker_count: int = 4):
        """
        Initialize worker pool.
        
        Args:
            worker_count: Number of workers to create
        """
        self.worker_count = worker_count
        self.logger = get_logger("core.orchestration.batch.workerpool")
        self.workers: List[WorkerInfo] = []
        
        self._initialize_workers()
    
    def _initialize_workers(self):
        """Initialize worker pool."""
        hostname = socket.gethostname()
        
        for i in range(self.worker_count):
            worker = WorkerInfo(
                hostname=hostname,
                pid=0,  # Will be set when worker starts
                status="idle"
            )
            self.workers.append(worker)
            
        self.logger.info(f"Initialized pool with {self.worker_count} workers")
    
    def get_available_worker(self) -> Optional[WorkerInfo]:
        """Get an available worker."""
        for worker in self.workers:
            if worker.status == "idle" and worker.is_alive:
                return worker
        return None
    
    def shutdown(self):
        """Shutdown all workers."""
        self.logger.info("Shutting down worker pool")
        self.workers.clear()
