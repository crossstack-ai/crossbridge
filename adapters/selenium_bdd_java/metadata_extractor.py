"""
Test Metadata System for Selenium Java BDD

Captures environment, browser, and test execution metadata:
- Browser capabilities (name, version, OS)
- Environment context (CI, local, docker)
- Test grouping (TestNG groups, JUnit categories)
- Execution context (parallel workers, session IDs)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
import os
import re


class ExecutionEnvironment(Enum):
    """Type of execution environment."""
    LOCAL = "local"
    CI = "ci"
    DOCKER = "docker"
    CLOUD = "cloud"  # BrowserStack, LambdaTest, etc.
    UNKNOWN = "unknown"


@dataclass
class BrowserMetadata:
    """Browser capabilities and configuration."""
    
    name: str = ""  # chrome, firefox, edge, safari
    version: str = ""
    platform: str = ""  # Windows, Linux, macOS
    platform_version: str = ""
    
    # WebDriver info
    driver_version: str = ""
    is_headless: bool = False
    
    # Resolution
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
    
    # Additional capabilities
    capabilities: Dict[str, str] = field(default_factory=dict)
    
    def __str__(self) -> str:
        parts = [self.name, self.version, self.platform]
        return " ".join(filter(None, parts))


@dataclass
class ExecutionContext:
    """Execution context for parallel/distributed test runs."""
    
    # Unique identifiers
    session_id: str = ""  # Unique per test run
    execution_id: str = ""  # Unique per scenario execution
    
    # Parallel execution
    worker_id: Optional[str] = None  # Thread/worker identifier
    parallel_index: Optional[int] = None  # Index in parallel batch
    total_workers: Optional[int] = None
    
    # Retry tracking
    retry_count: int = 0
    is_retry: bool = False
    original_execution_id: Optional[str] = None  # Links to first attempt
    
    # Timing
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None


@dataclass
class CIMetadata:
    """CI/CD system metadata."""
    
    ci_system: str = ""  # jenkins, github_actions, gitlab_ci, etc.
    build_id: str = ""
    build_url: str = ""
    job_name: str = ""
    branch: str = ""
    commit_sha: str = ""
    commit_message: str = ""
    pull_request: Optional[str] = None
    
    # Environment variables captured
    env_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class TestGrouping:
    """Test grouping and categorization metadata."""
    
    # TestNG/JUnit grouping
    groups: List[str] = field(default_factory=list)  # TestNG @Test(groups)
    categories: List[str] = field(default_factory=list)  # JUnit @Category
    
    # Cucumber tags
    cucumber_tags: List[str] = field(default_factory=list)
    
    # Custom attributes
    priority: Optional[str] = None  # high, medium, low
    severity: Optional[str] = None  # critical, major, minor
    test_type: Optional[str] = None  # smoke, regression, integration
    
    # Owner/Team
    owner: Optional[str] = None
    team: Optional[str] = None


@dataclass
class TestMetadata:
    """Complete metadata for a test execution."""
    
    # Browser information
    browser: Optional[BrowserMetadata] = None
    
    # Environment
    environment: ExecutionEnvironment = ExecutionEnvironment.UNKNOWN
    environment_name: Optional[str] = None  # dev, staging, prod
    
    # Execution context
    execution_context: Optional[ExecutionContext] = None
    
    # CI/CD
    ci: Optional[CIMetadata] = None
    
    # Grouping
    grouping: Optional[TestGrouping] = None
    
    # Custom metadata
    custom: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "browser": str(self.browser) if self.browser else None,
            "environment": self.environment.value,
            "environment_name": self.environment_name,
            "session_id": self.execution_context.session_id if self.execution_context else None,
            "retry_count": self.execution_context.retry_count if self.execution_context else 0,
            "ci_system": self.ci.ci_system if self.ci else None,
            "build_id": self.ci.build_id if self.ci else None,
            "groups": self.grouping.groups if self.grouping else [],
            "tags": self.grouping.cucumber_tags if self.grouping else [],
            "custom": self.custom
        }


class MetadataExtractor:
    """
    Extracts test metadata from various sources:
    - Environment variables
    - Browser capabilities
    - CI system variables
    - Test annotations
    """
    
    # CI system detection patterns
    CI_PATTERNS = {
        "jenkins": ["JENKINS_URL", "JENKINS_HOME"],
        "github_actions": ["GITHUB_ACTIONS", "GITHUB_WORKFLOW"],
        "gitlab_ci": ["GITLAB_CI", "CI_SERVER_NAME"],
        "circleci": ["CIRCLECI", "CIRCLE_BUILD_NUM"],
        "travis": ["TRAVIS", "TRAVIS_BUILD_ID"],
        "azure_devops": ["TF_BUILD", "AZURE_PIPELINES"],
    }
    
    def extract_from_environment(self) -> TestMetadata:
        """Extract metadata from environment variables."""
        metadata = TestMetadata()
        
        # Detect execution environment
        metadata.environment = self._detect_environment()
        
        # Extract CI metadata if in CI
        if metadata.environment == ExecutionEnvironment.CI:
            metadata.ci = self._extract_ci_metadata()
        
        # Extract browser info from env vars (common patterns)
        metadata.browser = self._extract_browser_from_env()
        
        # Extract execution context
        metadata.execution_context = self._extract_execution_context()
        
        return metadata
    
    def extract_from_capabilities(self, capabilities: Dict) -> BrowserMetadata:
        """
        Extract browser metadata from WebDriver capabilities.
        
        Args:
            capabilities: Selenium WebDriver capabilities dict
        """
        browser = BrowserMetadata()
        
        browser.name = capabilities.get("browserName", "")
        browser.version = capabilities.get("browserVersion", capabilities.get("version", ""))
        browser.platform = capabilities.get("platformName", capabilities.get("platform", ""))
        
        # Chrome-specific
        if "chrome" in browser.name.lower():
            chrome_options = capabilities.get("goog:chromeOptions", {})
            browser.is_headless = "--headless" in chrome_options.get("args", [])
        
        # Firefox-specific
        elif "firefox" in browser.name.lower():
            moz_options = capabilities.get("moz:firefoxOptions", {})
            browser.is_headless = moz_options.get("args", []).count("--headless") > 0
        
        # Store all capabilities
        browser.capabilities = {k: str(v) for k, v in capabilities.items()}
        
        return browser
    
    def extract_grouping_from_annotations(
        self,
        tags: List[str],
        test_class: Optional[str] = None
    ) -> TestGrouping:
        """Extract test grouping from Cucumber tags and Java annotations."""
        grouping = TestGrouping()
        
        grouping.cucumber_tags = tags
        
        # Parse special tags
        for tag in tags:
            tag_lower = tag.lower()
            
            # Priority tags
            if any(p in tag_lower for p in ["@critical", "@high", "@p0"]):
                grouping.priority = "high"
            elif any(p in tag_lower for p in ["@medium", "@p1"]):
                grouping.priority = "medium"
            elif any(p in tag_lower for p in ["@low", "@p2"]):
                grouping.priority = "low"
            
            # Test type tags
            if "@smoke" in tag_lower:
                grouping.test_type = "smoke"
            elif "@regression" in tag_lower:
                grouping.test_type = "regression"
            elif "@integration" in tag_lower:
                grouping.test_type = "integration"
            
            # Team/Owner tags
            if tag.startswith("@team-"):
                grouping.team = tag[6:]  # Remove @team- prefix
            elif tag.startswith("@owner-"):
                grouping.owner = tag[7:]  # Remove @owner- prefix
        
        return grouping
    
    def _detect_environment(self) -> ExecutionEnvironment:
        """Detect execution environment from env vars."""
        env = os.environ
        
        # Check for CI indicators
        if any(key in env for patterns in self.CI_PATTERNS.values() for key in patterns):
            return ExecutionEnvironment.CI
        
        # Check for Docker
        if os.path.exists("/.dockerenv") or env.get("DOCKER_CONTAINER"):
            return ExecutionEnvironment.DOCKER
        
        # Check for cloud providers
        if any(key in env for key in ["BROWSERSTACK_USERNAME", "LT_USERNAME", "SAUCE_USERNAME"]):
            return ExecutionEnvironment.CLOUD
        
        return ExecutionEnvironment.LOCAL
    
    def _extract_ci_metadata(self) -> CIMetadata:
        """Extract CI system metadata."""
        ci = CIMetadata()
        env = os.environ
        
        # Detect CI system
        for system, patterns in self.CI_PATTERNS.items():
            if any(key in env for key in patterns):
                ci.ci_system = system
                break
        
        # Extract common CI variables
        if ci.ci_system == "jenkins":
            ci.build_id = env.get("BUILD_NUMBER", "")
            ci.build_url = env.get("BUILD_URL", "")
            ci.job_name = env.get("JOB_NAME", "")
            ci.branch = env.get("GIT_BRANCH", "")
            ci.commit_sha = env.get("GIT_COMMIT", "")
        
        elif ci.ci_system == "github_actions":
            ci.build_id = env.get("GITHUB_RUN_ID", "")
            ci.build_url = f"{env.get('GITHUB_SERVER_URL', '')}/{env.get('GITHUB_REPOSITORY', '')}/actions/runs/{env.get('GITHUB_RUN_ID', '')}"
            ci.job_name = env.get("GITHUB_WORKFLOW", "")
            ci.branch = env.get("GITHUB_REF_NAME", "")
            ci.commit_sha = env.get("GITHUB_SHA", "")
            ci.pull_request = env.get("GITHUB_PR_NUMBER")
        
        elif ci.ci_system == "gitlab_ci":
            ci.build_id = env.get("CI_PIPELINE_ID", "")
            ci.build_url = env.get("CI_PIPELINE_URL", "")
            ci.job_name = env.get("CI_JOB_NAME", "")
            ci.branch = env.get("CI_COMMIT_REF_NAME", "")
            ci.commit_sha = env.get("CI_COMMIT_SHA", "")
            ci.commit_message = env.get("CI_COMMIT_MESSAGE", "")
        
        return ci
    
    def _extract_browser_from_env(self) -> Optional[BrowserMetadata]:
        """Extract browser info from environment variables."""
        env = os.environ
        
        browser = BrowserMetadata()
        
        # Common env var patterns
        browser.name = env.get("BROWSER", env.get("SELENIUM_BROWSER", "")).lower()
        browser.version = env.get("BROWSER_VERSION", "")
        browser.platform = env.get("PLATFORM", env.get("OS", ""))
        
        # Headless mode
        browser.is_headless = env.get("HEADLESS", "").lower() in ["true", "1", "yes"]
        
        # Only return if we got something
        if browser.name:
            return browser
        return None
    
    def _extract_execution_context(self) -> ExecutionContext:
        """Extract execution context."""
        env = os.environ
        context = ExecutionContext()
        
        # Generate session ID if not provided
        import uuid
        context.session_id = env.get("TEST_SESSION_ID", str(uuid.uuid4()))
        
        # Parallel execution indicators
        context.worker_id = env.get("WORKER_ID", env.get("NODE_INDEX"))
        
        # Parse parallel index
        if env.get("PARALLEL_INDEX"):
            context.parallel_index = int(env.get("PARALLEL_INDEX"))
        
        if env.get("TOTAL_WORKERS"):
            context.total_workers = int(env.get("TOTAL_WORKERS"))
        
        return context


# Convenience function
def extract_metadata() -> TestMetadata:
    """Extract test metadata from current environment."""
    extractor = MetadataExtractor()
    return extractor.extract_from_environment()
