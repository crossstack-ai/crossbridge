"""
Robot Framework Metadata Extraction Module.

Extracts comprehensive test execution metadata for Robot Framework tests
including CI system information, environment details, browser metadata,
and execution context.

This module addresses Gap 6.2 in the Framework Gap Analysis:
- CI system detection (Jenkins, GitHub Actions, GitLab CI, etc.)
- Environment tracking (dev, staging, prod)
- Browser metadata (when using SeleniumLibrary)
- Execution context (parallel workers, retries, tags)

Usage:
    from adapters.robot.metadata_extractor import extract_robot_metadata
    
    metadata = extract_robot_metadata(
        output_xml_path="output.xml",
        project_root="/path/to/project"
    )
    
    print(f"CI System: {metadata.ci_system}")
    print(f"Browser: {metadata.browser_name}")
    print(f"Environment: {metadata.environment}")
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path
from xml.etree import ElementTree as ET


class ExecutionEnvironment(Enum):
    """Test execution environment."""
    LOCAL = "local"
    CI = "ci"
    DOCKER = "docker"
    CLOUD = "cloud"
    UNKNOWN = "unknown"


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
    pipeline_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ci_system": self.ci_system,
            "build_id": self.build_id,
            "build_url": self.build_url,
            "job_name": self.job_name,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "commit_message": self.commit_message,
            "pull_request": self.pull_request,
            "build_number": self.build_number,
            "pipeline_id": self.pipeline_id,
        }


@dataclass
class BrowserMetadata:
    """Browser metadata from SeleniumLibrary."""
    browser_name: Optional[str] = None      # chrome, firefox, safari, edge
    browser_version: Optional[str] = None
    platform: Optional[str] = None          # windows, linux, mac
    headless: bool = False
    remote: bool = False
    remote_url: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "browser_name": self.browser_name,
            "browser_version": self.browser_version,
            "platform": self.platform,
            "headless": self.headless,
            "remote": self.remote,
            "remote_url": self.remote_url,
            "capabilities": self.capabilities,
        }


@dataclass
class ExecutionContext:
    """Test execution context."""
    parallel: bool = False
    worker_count: Optional[int] = None
    worker_id: Optional[str] = None
    retry_count: int = 0
    max_retries: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    included_tags: List[str] = field(default_factory=list)
    excluded_tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "parallel": self.parallel,
            "worker_count": self.worker_count,
            "worker_id": self.worker_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "tags": self.tags,
            "included_tags": self.included_tags,
            "excluded_tags": self.excluded_tags,
        }


@dataclass
class RobotMetadata:
    """Complete Robot Framework test metadata."""
    # CI Information
    ci_metadata: Optional[CIMetadata] = None
    environment: ExecutionEnvironment = ExecutionEnvironment.UNKNOWN
    
    # Browser Information (from SeleniumLibrary)
    browser_metadata: Optional[BrowserMetadata] = None
    
    # Execution Context
    execution_context: ExecutionContext = field(default_factory=ExecutionContext)
    
    # Robot Framework specific
    robot_version: Optional[str] = None
    python_version: Optional[str] = None
    libraries: List[str] = field(default_factory=list)
    
    # Project Information
    project_root: Optional[str] = None
    test_suite_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "ci_metadata": self.ci_metadata.to_dict() if self.ci_metadata else None,
            "environment": self.environment.value,
            "browser_metadata": self.browser_metadata.to_dict() if self.browser_metadata else None,
            "execution_context": self.execution_context.to_dict(),
            "robot_version": self.robot_version,
            "python_version": self.python_version,
            "libraries": self.libraries,
            "project_root": self.project_root,
            "test_suite_path": self.test_suite_path,
        }


# CI System detection patterns
CI_PATTERNS = {
    "jenkins": [
        "JENKINS_HOME", "JENKINS_URL", "BUILD_NUMBER", "JOB_NAME"
    ],
    "github_actions": [
        "GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_WORKFLOW"
    ],
    "gitlab_ci": [
        "GITLAB_CI", "CI_JOB_ID", "CI_PIPELINE_ID"
    ],
    "circleci": [
        "CIRCLECI", "CIRCLE_BUILD_NUM", "CIRCLE_JOB"
    ],
    "travis": [
        "TRAVIS", "TRAVIS_BUILD_ID", "TRAVIS_JOB_ID"
    ],
    "azure_pipelines": [
        "TF_BUILD", "BUILD_BUILDID", "SYSTEM_TEAMPROJECT"
    ],
    "bamboo": [
        "bamboo_buildNumber", "bamboo_buildKey"
    ],
    "teamcity": [
        "TEAMCITY_VERSION", "BUILD_NUMBER"
    ],
}


def extract_robot_metadata(
    output_xml_path: Optional[str] = None,
    project_root: Optional[str] = None,
    extra_args: Optional[List[str]] = None
) -> RobotMetadata:
    """
    Extract comprehensive metadata from Robot Framework test execution.
    
    Args:
        output_xml_path: Path to Robot's output.xml file (optional)
        project_root: Project root directory
        extra_args: Additional command-line arguments passed to robot
        
    Returns:
        RobotMetadata with all extracted information
    """
    metadata = RobotMetadata()
    
    # Detect CI system
    ci_info = _detect_ci_system()
    if ci_info:
        metadata.ci_metadata = ci_info
        metadata.environment = ExecutionEnvironment.CI
    else:
        metadata.environment = _detect_environment()
    
    # Parse output.xml if provided
    if output_xml_path and Path(output_xml_path).exists():
        _parse_output_xml(output_xml_path, metadata)
    
    # Extract execution context from args
    if extra_args:
        _parse_execution_args(extra_args, metadata.execution_context)
    
    # Set project root
    metadata.project_root = project_root
    
    return metadata


def _detect_ci_system() -> Optional[CIMetadata]:
    """Detect which CI system is running the tests."""
    env = os.environ
    
    # Check each CI system
    for ci_system, patterns in CI_PATTERNS.items():
        if any(pattern in env for pattern in patterns):
            return _extract_ci_metadata(ci_system, env)
    
    # Generic CI detection
    if env.get("CI") == "true":
        return CIMetadata(ci_system="generic_ci", build_id=env.get("BUILD_ID"))
    
    return None


def _extract_ci_metadata(ci_system: str, env: Dict[str, str]) -> CIMetadata:
    """Extract CI-specific metadata."""
    
    if ci_system == "jenkins":
        return CIMetadata(
            ci_system="jenkins",
            build_id=env.get("BUILD_ID"),
            build_url=env.get("BUILD_URL"),
            job_name=env.get("JOB_NAME"),
            build_number=int(env["BUILD_NUMBER"]) if env.get("BUILD_NUMBER") else None,
            branch=env.get("GIT_BRANCH", env.get("BRANCH_NAME")),
            commit_sha=env.get("GIT_COMMIT"),
        )
    
    elif ci_system == "github_actions":
        return CIMetadata(
            ci_system="github_actions",
            build_id=env.get("GITHUB_RUN_ID"),
            build_url=f"{env.get('GITHUB_SERVER_URL')}/{env.get('GITHUB_REPOSITORY')}/actions/runs/{env.get('GITHUB_RUN_ID')}",
            job_name=env.get("GITHUB_WORKFLOW"),
            branch=env.get("GITHUB_REF_NAME"),
            commit_sha=env.get("GITHUB_SHA"),
            pull_request=env.get("GITHUB_HEAD_REF") if env.get("GITHUB_EVENT_NAME") == "pull_request" else None,
        )
    
    elif ci_system == "gitlab_ci":
        return CIMetadata(
            ci_system="gitlab_ci",
            build_id=env.get("CI_JOB_ID"),
            build_url=env.get("CI_JOB_URL"),
            job_name=env.get("CI_JOB_NAME"),
            pipeline_id=env.get("CI_PIPELINE_ID"),
            branch=env.get("CI_COMMIT_REF_NAME"),
            commit_sha=env.get("CI_COMMIT_SHA"),
            commit_message=env.get("CI_COMMIT_MESSAGE"),
            pull_request=env.get("CI_MERGE_REQUEST_IID"),
        )
    
    elif ci_system == "circleci":
        return CIMetadata(
            ci_system="circleci",
            build_id=env.get("CIRCLE_BUILD_NUM"),
            build_url=env.get("CIRCLE_BUILD_URL"),
            job_name=env.get("CIRCLE_JOB"),
            branch=env.get("CIRCLE_BRANCH"),
            commit_sha=env.get("CIRCLE_SHA1"),
            pull_request=env.get("CIRCLE_PULL_REQUEST"),
        )
    
    elif ci_system == "travis":
        return CIMetadata(
            ci_system="travis",
            build_id=env.get("TRAVIS_BUILD_ID"),
            build_url=env.get("TRAVIS_BUILD_WEB_URL"),
            job_name=env.get("TRAVIS_JOB_NAME"),
            build_number=int(env["TRAVIS_BUILD_NUMBER"]) if env.get("TRAVIS_BUILD_NUMBER") else None,
            branch=env.get("TRAVIS_BRANCH"),
            commit_sha=env.get("TRAVIS_COMMIT"),
            commit_message=env.get("TRAVIS_COMMIT_MESSAGE"),
            pull_request=env.get("TRAVIS_PULL_REQUEST") if env.get("TRAVIS_PULL_REQUEST") != "false" else None,
        )
    
    elif ci_system == "azure_pipelines":
        return CIMetadata(
            ci_system="azure_pipelines",
            build_id=env.get("BUILD_BUILDID"),
            build_url=f"{env.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')}{env.get('SYSTEM_TEAMPROJECT')}/_build/results?buildId={env.get('BUILD_BUILDID')}",
            job_name=env.get("SYSTEM_DEFINITIONNAME"),
            build_number=int(env["BUILD_BUILDNUMBER"]) if env.get("BUILD_BUILDNUMBER") else None,
            branch=env.get("BUILD_SOURCEBRANCHNAME"),
            commit_sha=env.get("BUILD_SOURCEVERSION"),
        )
    
    elif ci_system == "bamboo":
        return CIMetadata(
            ci_system="bamboo",
            build_id=env.get("bamboo_buildKey"),
            build_url=env.get("bamboo_buildResultsUrl"),
            job_name=env.get("bamboo_planName"),
            build_number=int(env["bamboo_buildNumber"]) if env.get("bamboo_buildNumber") else None,
            branch=env.get("bamboo_planRepository_branch"),
            commit_sha=env.get("bamboo_planRepository_revision"),
        )
    
    elif ci_system == "teamcity":
        return CIMetadata(
            ci_system="teamcity",
            build_id=env.get("BUILD_NUMBER"),
            job_name=env.get("TEAMCITY_BUILDCONF_NAME"),
            branch=env.get("BUILD_VCS_BRANCH"),
        )
    
    return CIMetadata(ci_system=ci_system)


def _detect_environment() -> ExecutionEnvironment:
    """Detect execution environment when not in CI."""
    env = os.environ
    
    # Check for Docker
    if os.path.exists("/.dockerenv") or env.get("DOCKER_CONTAINER"):
        return ExecutionEnvironment.DOCKER
    
    # Check for cloud environments
    if any(key in env for key in ["AWS_EXECUTION_ENV", "LAMBDA_TASK_ROOT"]):
        return ExecutionEnvironment.CLOUD
    if env.get("GOOGLE_CLOUD_PROJECT"):
        return ExecutionEnvironment.CLOUD
    if env.get("AZURE_FUNCTIONS_ENVIRONMENT"):
        return ExecutionEnvironment.CLOUD
    
    # Default to local
    return ExecutionEnvironment.LOCAL


def _parse_output_xml(output_xml_path: str, metadata: RobotMetadata) -> None:
    """Parse Robot Framework output.xml for metadata."""
    try:
        tree = ET.parse(output_xml_path)
        root = tree.getroot()
        
        # Extract robot version
        metadata.robot_version = root.get("generator", "").replace("Robot ", "")
        
        # Extract libraries
        for suite in root.iter("suite"):
            for kw in suite.iter("kw"):
                library = kw.get("library")
                if library and library not in metadata.libraries:
                    metadata.libraries.append(library)
        
        # Extract browser metadata from SeleniumLibrary keywords
        browser_meta = _extract_browser_metadata_from_xml(root)
        if browser_meta:
            metadata.browser_metadata = browser_meta
        
        # Extract test suite path
        for suite in root.iter("suite"):
            source = suite.get("source")
            if source:
                metadata.test_suite_path = source
                break
        
        # Extract tags from statistics
        tags = []
        for stat in root.iter("stat"):
            tag_name = stat.text
            if tag_name and tag_name not in tags:
                tags.append(tag_name)
        metadata.execution_context.tags = tags
        
    except Exception as e:
        # Silently handle parsing errors
        pass


def _extract_browser_metadata_from_xml(root: ET.Element) -> Optional[BrowserMetadata]:
    """Extract browser metadata from SeleniumLibrary keywords in output.xml."""
    browser_meta = BrowserMetadata()
    found_browser = False
    
    # Look for "Open Browser" keyword calls
    for kw in root.iter("kw"):
        if kw.get("name") in ["Open Browser", "Create Webdriver"]:
            found_browser = True
            
            # Extract browser name from arguments
            for arg in kw.iter("arg"):
                arg_text = arg.text or ""
                arg_lower = arg_text.lower()
                
                if any(browser in arg_lower for browser in ["chrome", "firefox", "safari", "edge", "ie"]):
                    for browser_name in ["chrome", "firefox", "safari", "edge"]:
                        if browser_name in arg_lower:
                            browser_meta.browser_name = browser_name
                            break
                
                if "headless" in arg_lower:
                    browser_meta.headless = True
                
                if "remote_url" in arg_lower or "http://" in arg_text or "https://" in arg_text:
                    browser_meta.remote = True
                    # Extract URL
                    url_match = re.search(r'https?://[^\s]+', arg_text)
                    if url_match:
                        browser_meta.remote_url = url_match.group(0)
    
    # Check environment variables for browser info
    if not browser_meta.browser_name:
        browser_env = os.environ.get("BROWSER", "").lower()
        if browser_env in ["chrome", "firefox", "safari", "edge"]:
            browser_meta.browser_name = browser_env
            found_browser = True
    
    # Detect platform
    import platform
    browser_meta.platform = platform.system().lower()
    
    return browser_meta if found_browser else None


def _parse_execution_args(args: List[str], context: ExecutionContext) -> None:
    """Parse Robot Framework command-line arguments for execution context."""
    i = 0
    while i < len(args):
        arg = args[i]
        
        # Tag filtering
        if arg in ["--include", "-i"]:
            if i + 1 < len(args):
                context.included_tags.append(args[i + 1])
                i += 1
        elif arg in ["--exclude", "-e"]:
            if i + 1 < len(args):
                context.excluded_tags.append(args[i + 1])
                i += 1
        
        # Parallel execution (pabot)
        elif arg == "--processes":
            if i + 1 < len(args):
                try:
                    context.worker_count = int(args[i + 1])
                    context.parallel = True
                except ValueError:
                    pass
                i += 1
        
        # Retry
        elif arg in ["--rerunfailed", "--retry"]:
            context.retry_count += 1
            if i + 1 < len(args):
                i += 1
        
        i += 1
    
    # Check for pabot environment variable
    if os.environ.get("PABOT_POOL_ID"):
        context.parallel = True
        context.worker_id = os.environ.get("PABOT_POOL_ID")


def enrich_test_result_with_metadata(
    test_result: Dict[str, Any],
    metadata: RobotMetadata
) -> Dict[str, Any]:
    """
    Enrich a test result dictionary with metadata.
    
    Args:
        test_result: Test result dictionary
        metadata: Extracted metadata
        
    Returns:
        Enriched test result dictionary
    """
    test_result["metadata"] = metadata.to_dict()
    
    # Add top-level convenience fields
    if metadata.ci_metadata:
        test_result["ci_system"] = metadata.ci_metadata.ci_system
        test_result["build_id"] = metadata.ci_metadata.build_id
        test_result["branch"] = metadata.ci_metadata.branch
    
    if metadata.browser_metadata:
        test_result["browser"] = metadata.browser_metadata.browser_name
        test_result["browser_version"] = metadata.browser_metadata.browser_version
        test_result["headless"] = metadata.browser_metadata.headless
    
    test_result["environment"] = metadata.environment.value
    test_result["parallel"] = metadata.execution_context.parallel
    
    return test_result
