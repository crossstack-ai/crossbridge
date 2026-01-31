"""
RestAssured Metadata Extraction.

Extracts comprehensive test execution metadata for RestAssured API tests
including CI system information, environment details, and execution context.

Gap 1.2 Implementation - RestAssured Metadata Enrichment
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import os
import uuid
from datetime import datetime


class ExecutionEnvironment(Enum):
    """Test execution environment."""
    LOCAL = "local"
    CI = "ci"
    DOCKER = "docker"
    CLOUD = "cloud"
    UNKNOWN = "unknown"


@dataclass
class APIMetadata:
    """API-specific metadata."""
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    auth_type: Optional[str] = None  # basic, bearer, oauth, api_key
    content_type: Optional[str] = None
    request_logging: bool = False
    response_logging: bool = False


@dataclass
class CIMetadata:
    """CI system metadata."""
    ci_system: str  # jenkins, github_actions, gitlab_ci, etc.
    build_id: Optional[str] = None
    build_url: Optional[str] = None
    job_name: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    pull_request: Optional[str] = None
    build_number: Optional[int] = None


@dataclass
class ExecutionContext:
    """Execution context metadata."""
    session_id: str
    worker_id: Optional[str] = None
    parallel_index: Optional[int] = None
    retry_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class TestGrouping:
    """Test grouping and categorization."""
    groups: List[str] = field(default_factory=list)  # TestNG groups
    categories: List[str] = field(default_factory=list)  # JUnit categories
    tags: List[str] = field(default_factory=list)  # Custom tags
    priority: Optional[str] = None  # high, medium, low
    test_type: Optional[str] = None  # smoke, regression, sanity
    team: Optional[str] = None
    owner: Optional[str] = None


@dataclass
class RestAssuredTestMetadata:
    """
    Complete metadata for RestAssured test execution.
    
    Includes API-specific metadata, CI information, execution context,
    and test grouping.
    """
    api: Optional[APIMetadata] = None
    environment: ExecutionEnvironment = ExecutionEnvironment.UNKNOWN
    ci: Optional[CIMetadata] = None
    execution_context: Optional[ExecutionContext] = None
    grouping: Optional[TestGrouping] = None
    
    # Java-specific
    java_version: Optional[str] = None
    maven_version: Optional[str] = None
    gradle_version: Optional[str] = None
    restassured_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "api_base_url": self.api.base_url if self.api else None,
            "api_version": self.api.api_version if self.api else None,
            "auth_type": self.api.auth_type if self.api else None,
            "environment": self.environment.value,
            "ci_system": self.ci.ci_system if self.ci else None,
            "build_id": self.ci.build_id if self.ci else None,
            "branch": self.ci.branch if self.ci else None,
            "session_id": self.execution_context.session_id if self.execution_context else None,
            "retry_count": self.execution_context.retry_count if self.execution_context else 0,
            "priority": self.grouping.priority if self.grouping else None,
            "test_type": self.grouping.test_type if self.grouping else None,
            "java_version": self.java_version,
            "restassured_version": self.restassured_version
        }


class RestAssuredMetadataExtractor:
    """Extract metadata for RestAssured test executions."""
    
    def extract_from_environment(self) -> RestAssuredTestMetadata:
        """
        Extract metadata from environment variables and system properties.
        
        Returns:
            Complete RestAssured test metadata
        """
        return RestAssuredTestMetadata(
            api=self._extract_api_metadata(),
            environment=self._detect_environment(),
            ci=self._extract_ci_metadata(),
            execution_context=self._extract_execution_context(),
            java_version=self._extract_java_version(),
            maven_version=self._extract_maven_version(),
            restassured_version=self._extract_restassured_version()
        )
    
    def extract_grouping_from_annotations(
        self,
        groups: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> TestGrouping:
        """
        Extract test grouping from TestNG groups or custom tags.
        
        Args:
            groups: TestNG groups
            tags: Custom tags
            
        Returns:
            TestGrouping with extracted metadata
        """
        grouping = TestGrouping(
            groups=groups or [],
            tags=tags or []
        )
        
        # Parse priority from groups/tags
        all_markers = (groups or []) + (tags or [])
        for marker in all_markers:
            marker_lower = marker.lower()
            
            # Priority detection
            if marker_lower in ['critical', 'high', 'p0']:
                grouping.priority = 'high'
            elif marker_lower in ['medium', 'p1']:
                grouping.priority = 'medium'
            elif marker_lower in ['low', 'p2', 'p3']:
                grouping.priority = 'low'
            
            # Test type detection
            if marker_lower in ['smoke', 'sanity']:
                grouping.test_type = 'smoke'
            elif marker_lower == 'regression':
                grouping.test_type = 'regression'
            elif marker_lower == 'integration':
                grouping.test_type = 'integration'
            
            # Team extraction (format: team-<name>)
            if marker_lower.startswith('team-'):
                grouping.team = marker[5:]
            
            # Owner extraction (format: owner-<name>)
            if marker_lower.startswith('owner-'):
                grouping.owner = marker[6:]
        
        return grouping
    
    def _extract_api_metadata(self) -> APIMetadata:
        """Extract API configuration from environment."""
        return APIMetadata(
            base_url=os.environ.get('API_BASE_URL') or os.environ.get('BASE_URL'),
            api_version=os.environ.get('API_VERSION'),
            auth_type=self._detect_auth_type(),
            content_type=os.environ.get('CONTENT_TYPE', 'application/json'),
            request_logging=os.environ.get('REQUEST_LOGGING', '').lower() == 'true',
            response_logging=os.environ.get('RESPONSE_LOGGING', '').lower() == 'true'
        )
    
    def _detect_auth_type(self) -> Optional[str]:
        """Detect authentication type from environment."""
        if os.environ.get('API_KEY'):
            return 'api_key'
        elif os.environ.get('BEARER_TOKEN') or os.environ.get('JWT_TOKEN'):
            return 'bearer'
        elif os.environ.get('OAUTH_TOKEN'):
            return 'oauth'
        elif os.environ.get('BASIC_AUTH_USER'):
            return 'basic'
        return None
    
    def _detect_environment(self) -> ExecutionEnvironment:
        """Detect execution environment."""
        # Check for CI environment
        ci_indicators = [
            'CI', 'CONTINUOUS_INTEGRATION',
            'JENKINS_URL', 'GITHUB_ACTIONS', 'GITLAB_CI',
            'CIRCLECI', 'TRAVIS', 'AZURE_PIPELINES'
        ]
        
        if any(os.environ.get(var) for var in ci_indicators):
            return ExecutionEnvironment.CI
        
        # Check for Docker
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
            return ExecutionEnvironment.DOCKER
        
        # Check for cloud platforms
        cloud_indicators = ['AWS_EXECUTION_ENV', 'AZURE_FUNCTIONS', 'GOOGLE_CLOUD_PROJECT']
        if any(os.environ.get(var) for var in cloud_indicators):
            return ExecutionEnvironment.CLOUD
        
        return ExecutionEnvironment.LOCAL
    
    def _extract_ci_metadata(self) -> Optional[CIMetadata]:
        """Extract CI system metadata."""
        # Jenkins
        if os.environ.get('JENKINS_URL'):
            return CIMetadata(
                ci_system='jenkins',
                build_id=os.environ.get('BUILD_ID'),
                build_url=os.environ.get('BUILD_URL'),
                job_name=os.environ.get('JOB_NAME'),
                branch=os.environ.get('GIT_BRANCH') or os.environ.get('BRANCH_NAME'),
                commit_sha=os.environ.get('GIT_COMMIT'),
                build_number=self._parse_int(os.environ.get('BUILD_NUMBER'))
            )
        
        # GitHub Actions
        if os.environ.get('GITHUB_ACTIONS'):
            return CIMetadata(
                ci_system='github_actions',
                build_id=os.environ.get('GITHUB_RUN_ID'),
                build_url=f"https://github.com/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}",
                job_name=os.environ.get('GITHUB_WORKFLOW'),
                branch=os.environ.get('GITHUB_REF_NAME'),
                commit_sha=os.environ.get('GITHUB_SHA'),
                pull_request=os.environ.get('GITHUB_HEAD_REF')
            )
        
        # GitLab CI
        if os.environ.get('GITLAB_CI'):
            return CIMetadata(
                ci_system='gitlab_ci',
                build_id=os.environ.get('CI_JOB_ID'),
                build_url=os.environ.get('CI_JOB_URL'),
                job_name=os.environ.get('CI_JOB_NAME'),
                branch=os.environ.get('CI_COMMIT_REF_NAME'),
                commit_sha=os.environ.get('CI_COMMIT_SHA'),
                commit_message=os.environ.get('CI_COMMIT_MESSAGE')
            )
        
        # CircleCI
        if os.environ.get('CIRCLECI'):
            return CIMetadata(
                ci_system='circleci',
                build_id=os.environ.get('CIRCLE_BUILD_NUM'),
                build_url=os.environ.get('CIRCLE_BUILD_URL'),
                job_name=os.environ.get('CIRCLE_JOB'),
                branch=os.environ.get('CIRCLE_BRANCH'),
                commit_sha=os.environ.get('CIRCLE_SHA1'),
                pull_request=os.environ.get('CIRCLE_PULL_REQUEST')
            )
        
        # Travis CI
        if os.environ.get('TRAVIS'):
            return CIMetadata(
                ci_system='travis',
                build_id=os.environ.get('TRAVIS_BUILD_ID'),
                build_url=os.environ.get('TRAVIS_BUILD_WEB_URL'),
                job_name=os.environ.get('TRAVIS_JOB_NAME'),
                branch=os.environ.get('TRAVIS_BRANCH'),
                commit_sha=os.environ.get('TRAVIS_COMMIT'),
                commit_message=os.environ.get('TRAVIS_COMMIT_MESSAGE'),
                pull_request=os.environ.get('TRAVIS_PULL_REQUEST')
            )
        
        # Azure Pipelines
        if os.environ.get('AZURE_PIPELINES') or os.environ.get('TF_BUILD'):
            return CIMetadata(
                ci_system='azure_pipelines',
                build_id=os.environ.get('BUILD_BUILDID'),
                build_url=f"{os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')}{os.environ.get('SYSTEM_TEAMPROJECT')}/_build/results?buildId={os.environ.get('BUILD_BUILDID')}",
                job_name=os.environ.get('BUILD_DEFINITIONNAME'),
                branch=os.environ.get('BUILD_SOURCEBRANCH'),
                commit_sha=os.environ.get('BUILD_SOURCEVERSION')
            )
        
        return None
    
    def _extract_execution_context(self) -> ExecutionContext:
        """Extract execution context."""
        return ExecutionContext(
            session_id=os.environ.get('TEST_SESSION_ID') or str(uuid.uuid4()),
            worker_id=os.environ.get('WORKER_ID') or os.environ.get('NODE_INDEX'),
            parallel_index=self._parse_int(os.environ.get('PARALLEL_INDEX')),
            retry_count=self._parse_int(os.environ.get('RETRY_COUNT'), default=0),
            start_time=datetime.now()
        )
    
    def _extract_java_version(self) -> Optional[str]:
        """Extract Java version."""
        return os.environ.get('JAVA_VERSION') or os.environ.get('JAVA_HOME', '').split('/')[-1]
    
    def _extract_maven_version(self) -> Optional[str]:
        """Extract Maven version."""
        return os.environ.get('MAVEN_VERSION')
    
    def _extract_restassured_version(self) -> Optional[str]:
        """Extract RestAssured version."""
        return os.environ.get('RESTASSURED_VERSION')
    
    @staticmethod
    def _parse_int(value: Optional[str], default: Optional[int] = None) -> Optional[int]:
        """Safely parse integer from string."""
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            return default


# Convenience function for quick extraction
def extract_restassured_metadata() -> RestAssuredTestMetadata:
    """
    Extract RestAssured test metadata from environment.
    
    Returns:
        Complete RestAssured test metadata
    """
    extractor = RestAssuredMetadataExtractor()
    return extractor.extract_from_environment()
