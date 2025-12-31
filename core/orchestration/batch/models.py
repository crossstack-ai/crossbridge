"""
Data models for batch processing orchestration.

Provides unified data structures for managing batch jobs, tasks, and results
across all CrossBridge features.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable
from uuid import uuid4


class TaskStatus(Enum):
    """Status of a batch task."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class JobPriority(Enum):
    """Priority level for batch jobs."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class FeatureType(Enum):
    """Types of features that can be orchestrated."""
    FLAKY_DETECTION = "flaky_detection"
    COVERAGE_COLLECTION = "coverage_collection"
    INTENT_EXTRACTION = "intent_extraction"
    IMPACT_ANALYSIS = "impact_analysis"
    TEST_EXECUTION = "test_execution"
    RESULT_AGGREGATION = "result_aggregation"
    MIGRATION = "migration"
    VALIDATION = "validation"


class ExecutionMode(Enum):
    """Execution modes for batch processing."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DISTRIBUTED = "distributed"
    ADAPTIVE = "adaptive"


@dataclass
class TaskDependency:
    """Dependency between tasks."""
    task_id: str
    required_status: TaskStatus = TaskStatus.COMPLETED
    optional: bool = False  # If True, task can proceed even if dependency fails


@dataclass
class BatchTask:
    """
    Individual task within a batch job.
    
    Represents a single unit of work to be executed.
    """
    task_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    feature_type: FeatureType = FeatureType.TEST_EXECUTION
    
    # Task configuration
    callable: Optional[Callable] = None  # Function to execute
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    
    # Input/Output
    input_files: List[Path] = field(default_factory=list)
    output_dir: Optional[Path] = None
    
    # Execution
    status: TaskStatus = TaskStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None  # Timeout in seconds
    
    # Dependencies
    dependencies: List[TaskDependency] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    
    # Timing
    queued_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    
    # Results
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    stacktrace: Optional[str] = None
    
    # Metadata
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default name if not provided."""
        if not self.name:
            self.name = f"{self.feature_type.value}_{self.task_id[:8]}"
    
    @property
    def is_complete(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.SKIPPED
        }
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (
            self.status == TaskStatus.FAILED and
            self.retry_count < self.max_retries
        )
    
    def add_dependency(self, task_id: str, required_status: TaskStatus = TaskStatus.COMPLETED, optional: bool = False):
        """Add a dependency to this task."""
        self.dependencies.append(TaskDependency(task_id, required_status, optional))


@dataclass
class BatchJob:
    """
    Collection of related tasks to be executed as a batch.
    
    Manages task lifecycle, dependencies, and execution coordination.
    """
    job_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    
    # Tasks
    tasks: List[BatchTask] = field(default_factory=list)
    
    # Configuration
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    priority: JobPriority = JobPriority.NORMAL
    max_parallel_tasks: int = 4
    continue_on_failure: bool = False
    
    # Scheduling
    scheduled_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    
    # Progress
    total_tasks: int = 0
    pending_tasks: int = 0
    queued_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    skipped_tasks: int = 0
    
    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    # Metadata
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize job statistics."""
        if not self.name:
            self.name = f"batch_job_{self.job_id[:8]}"
        self._update_statistics()
    
    def _update_statistics(self):
        """Update task statistics."""
        self.total_tasks = len(self.tasks)
        self.pending_tasks = sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)
        self.queued_tasks = sum(1 for t in self.tasks if t.status == TaskStatus.QUEUED)
        self.running_tasks = sum(1 for t in self.tasks if t.status == TaskStatus.RUNNING)
        self.completed_tasks = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        self.failed_tasks = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
        self.cancelled_tasks = sum(1 for t in self.tasks if t.status == TaskStatus.CANCELLED)
        self.skipped_tasks = sum(1 for t in self.tasks if t.status == TaskStatus.SKIPPED)
    
    def add_task(self, task: BatchTask):
        """Add a task to the job."""
        self.tasks.append(task)
        self._update_statistics()
    
    def get_task(self, task_id: str) -> Optional[BatchTask]:
        """Get a task by ID."""
        return next((t for t in self.tasks if t.task_id == task_id), None)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[BatchTask]:
        """Get all tasks with a specific status."""
        return [t for t in self.tasks if t.status == status]
    
    def get_runnable_tasks(self) -> List[BatchTask]:
        """Get tasks that are ready to run (dependencies satisfied)."""
        runnable = []
        for task in self.get_tasks_by_status(TaskStatus.PENDING):
            if self._are_dependencies_satisfied(task):
                runnable.append(task)
        return runnable
    
    def _are_dependencies_satisfied(self, task: BatchTask) -> bool:
        """Check if all task dependencies are satisfied."""
        for dep in task.dependencies:
            dep_task = self.get_task(dep.task_id)
            if not dep_task:
                if not dep.optional:
                    return False
                continue
            
            if dep_task.status != dep.required_status:
                if not dep.optional:
                    return False
        
        return True
    
    @property
    def is_complete(self) -> bool:
        """Check if job is complete."""
        return all(t.is_complete for t in self.tasks)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_tasks == 0:
            return 0.0
        completed = self.completed_tasks + self.failed_tasks + self.cancelled_tasks + self.skipped_tasks
        return (completed / self.total_tasks) * 100


@dataclass
class BatchResult:
    """
    Aggregated results from a batch job execution.
    """
    job_id: str
    job_name: str
    execution_time: datetime = field(default_factory=datetime.now)
    
    # Execution summary
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    duration: float = 0.0
    
    # Task results
    task_results: Dict[str, Any] = field(default_factory=dict)
    
    # Feature-specific results
    feature_results: Dict[FeatureType, Any] = field(default_factory=dict)
    
    # Errors
    errors: List[Dict[str, str]] = field(default_factory=list)
    
    # Performance metrics
    avg_task_duration: float = 0.0
    max_task_duration: float = 0.0
    min_task_duration: float = 0.0
    
    # Resource usage
    peak_parallel_tasks: int = 0
    total_retries: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_tasks > 0:
            if self.task_results:
                durations = [r.get('duration', 0) for r in self.task_results.values() if isinstance(r, dict)]
                if durations:
                    self.avg_task_duration = sum(durations) / len(durations)
                    self.max_task_duration = max(durations)
                    self.min_task_duration = min(durations)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    @property
    def is_successful(self) -> bool:
        """Check if batch was successful."""
        return self.failed_tasks == 0 and self.completed_tasks == self.total_tasks


@dataclass
class BatchConfig:
    """
    Configuration for batch processing orchestration.
    """
    # Execution
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL
    max_parallel_tasks: int = 4
    max_parallel_jobs: int = 2
    
    # Retry policy
    default_max_retries: int = 3
    retry_delay: float = 1.0  # Seconds between retries
    exponential_backoff: bool = True
    
    # Timeouts
    default_task_timeout: Optional[float] = 300.0  # 5 minutes
    job_timeout: Optional[float] = 3600.0  # 1 hour
    
    # Error handling
    continue_on_failure: bool = False
    fail_fast: bool = False
    collect_partial_results: bool = True
    
    # Distributed processing
    enable_distributed: bool = False
    worker_count: int = 4
    worker_timeout: float = 30.0
    heartbeat_interval: float = 5.0
    
    # Resource limits
    max_memory_per_task: Optional[int] = None  # MB
    max_cpu_per_task: Optional[int] = None  # CPU cores
    
    # Storage
    storage_dir: Optional[Path] = None
    save_intermediate_results: bool = True
    compress_results: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_task_progress: bool = True
    log_to_file: bool = True
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerInfo:
    """Information about a distributed worker."""
    worker_id: str = field(default_factory=lambda: str(uuid4()))
    hostname: str = ""
    pid: int = 0
    
    # Status
    status: str = "idle"  # idle, busy, disconnected
    current_task: Optional[str] = None
    
    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    
    # Statistics
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_duration: float = 0.0
    
    # Metadata
    capabilities: Set[FeatureType] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_alive(self) -> bool:
        """Check if worker is alive based on heartbeat."""
        return (datetime.now() - self.last_heartbeat).total_seconds() < 30.0
    
    @property
    def avg_task_duration(self) -> float:
        """Calculate average task duration."""
        if self.tasks_completed == 0:
            return 0.0
        return self.total_duration / self.tasks_completed
