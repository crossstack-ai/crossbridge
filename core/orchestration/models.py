"""
Core data models for migration orchestration.

These models are used by both CLI and future UI layers.
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class MigrationType(str, Enum):
    """Supported migration types."""
    SELENIUM_JAVA_BDD_TO_ROBOT_PLAYWRIGHT = "selenium_java_bdd_to_robot_playwright"
    SELENIUM_JAVA_TO_PLAYWRIGHT = "selenium_java_to_playwright"
    SELENIUM_JAVA_TO_ROBOT = "selenium_java_to_robot"
    PYTEST_TO_ROBOT = "pytest_to_robot"


class AuthType(str, Enum):
    """Repository authentication types."""
    GITHUB_TOKEN = "github_token"
    BITBUCKET_TOKEN = "bitbucket_token"
    BITBUCKET_APP_PASSWORD = "bitbucket_app_password"
    AZURE_PAT = "azure_pat"
    SSH = "ssh"


class AIMode(str, Enum):
    """AI execution modes."""
    PUBLIC_CLOUD = "public_cloud"
    ON_PREM = "on_prem"
    DISABLED = "disabled"


class MigrationMode(str, Enum):
    """Migration execution mode."""
    TEST = "test"  # Allow overwriting branches/PRs from previous runs
    LIVE = "live"  # Always create new branches, no overwriting


class TransformationMode(str, Enum):
    """Test transformation mode."""
    MANUAL = "manual"  # Provide structure only, manual implementation needed
    ENHANCED = "enhanced"  # Automated Gherkin parsing and Robot generation
    HYBRID = "hybrid"  # Automated with manual review checkpoints


class TransformationTier(str, Enum):
    """Transformation depth level for re-transforming existing files."""
    TIER_1 = "tier_1"  # Quick header refresh (update timestamps, metadata)
    TIER_2 = "tier_2"  # Content validation and optimization (parse, validate, fix)
    TIER_3 = "tier_3"  # Deep re-generation (re-parse from source .feature/.java files)


class OperationType(str, Enum):
    """Operation type for the migration."""
    MIGRATION = "migration"  # Move tests to new framework without structural changes
    TRANSFORMATION = "transformation"  # Refactor tests within same ecosystem
    MIGRATION_AND_TRANSFORMATION = "migration_and_transformation"  # Move and modernize together


class MigrationStatus(str, Enum):
    """Migration execution status."""
    NOT_STARTED = "not_started"
    VALIDATING = "validating"
    ANALYZING = "analyzing"
    TRANSFORMING = "transforming"
    GENERATING = "generating"
    COMMITTING = "committing"
    COMPLETED = "completed"
    FAILED = "failed"


class RepositoryAuth(BaseModel):
    """Repository authentication configuration."""
    auth_type: AuthType
    token: Optional[str] = Field(default=None, exclude=True)  # Never log/serialize
    username: Optional[str] = None
    ssh_key_path: Optional[str] = None


class AIConfig(BaseModel):
    """AI service configuration."""
    mode: AIMode
    provider: Optional[str] = None  # AI provider: openai, anthropic, custom
    api_key: Optional[str] = Field(default=None, exclude=True)  # Never log/serialize
    endpoint: Optional[str] = None
    model: str = "gpt-3.5-turbo"  # Most economical and efficient default model
    region: Optional[str] = "US"  # Data residency region


class MigrationRequest(BaseModel):
    """Complete migration request specification.
    
    This model is used by both CLI and UI layers to request migrations.
    """
    # Core migration settings
    migration_type: Optional[MigrationType] = None  # Required only for MIGRATION operations, not for TRANSFORMATION
    repo_url: str
    branch: str = "auto-detect"
    
    # Authentication
    auth: RepositoryAuth
    
    # AI settings
    use_ai: bool = False
    ai_config: Optional[AIConfig] = None
    
    # Framework-specific configuration (from CLI prompts)
    framework_config: Dict[str, str] = Field(default_factory=dict)
    
    # Optional paths (auto-discover if not specified)
    java_source_path: Optional[str] = None
    feature_files_path: Optional[str] = None
    
    # Execution options
    migration_mode: 'MigrationMode' = MigrationMode.TEST
    operation_type: 'OperationType' = OperationType.MIGRATION_AND_TRANSFORMATION
    transformation_mode: 'TransformationMode' = TransformationMode.ENHANCED
    dry_run: bool = False
    create_pr: bool = True
    target_branch: str = Field(default_factory=lambda: f"feature/crossbridge-migration-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    
    # Re-transformation options (for TRANSFORMATION operation_type)
    force_retransform: bool = Field(
        default=False,
        description="Force re-transformation of already-enhanced files (skips duplicate check)"
    )
    transformation_tier: 'TransformationTier' = Field(
        default=TransformationTier.TIER_1,
        description="Transformation depth: TIER_1 (fast headers), TIER_2 (validation), TIER_3 (deep re-gen)"
    )
    
    # Performance tuning
    max_workers: int = Field(
        default=10,
        description="Maximum number of parallel threads for file transformation (1-20)",
        ge=1,
        le=20
    )
    commit_batch_size: int = Field(
        default=10,
        description="Number of files to commit in a single batch (5-20)",
        ge=5,
        le=20
    )
    
    # Metadata
    request_id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    @field_validator('repo_url')
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        """Validate repository URL format."""
        if not any(x in v for x in ['github.com', 'bitbucket.org', 'dev.azure.com', 'gitlab.com']):
            raise ValueError("Unsupported repository platform")
        return v


class MigrationResult(BaseModel):
    """Individual file transformation result."""
    source_file: str
    target_file: str
    status: str  # "success", "failed", "skipped"
    error: Optional[str] = None


class MigrationResponse(BaseModel):
    """Migration execution response.
    
    Contains results and metadata from migration execution.
    """
    request_id: str
    status: MigrationStatus
    
    # Discovery results
    files_discovered: Dict[str, int] = Field(default_factory=dict)  # {"java": 150, "feature": 260}
    
    # Transformation results
    files_transformed: List[MigrationResult] = Field(default_factory=list)
    
    # Branch/PR info
    branch_created: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    
    # Execution metadata
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Errors
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Logs
    log_file: Optional[str] = None
    
    def mark_completed(self):
        """Mark migration as completed and calculate duration."""
        self.completed_at = datetime.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.status = MigrationStatus.COMPLETED
    
    def mark_failed(self, error: str, code: str):
        """Mark migration as failed with error details."""
        self.completed_at = datetime.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.status = MigrationStatus.FAILED
        self.error_message = error
        self.error_code = code
