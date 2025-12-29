"""
Selenium-Java adapter orchestration layer.

High-level adapter that:
1. Detects build tool (Maven/Gradle)
2. Detects test framework (JUnit/TestNG)
3. Delegates execution to appropriate runner
4. Normalizes results

This is the main entry point for running Selenium-Java tests.
"""

from pathlib import Path
from typing import Optional
from .models import (
    TestExecutionRequest,
    TestExecutionResult,
    BuildToolConfig,
    TestFrameworkConfig
)
from .maven_runner import MavenRunner
from .gradle_runner import GradleRunner
from ...selenium_java.config import SeleniumJavaConfig


class SeleniumJavaAdapter:
    """
    Framework-agnostic Selenium-Java test adapter.
    
    Responsibilities:
    - Detect build tool and test framework
    - Build execution request
    - Delegate to appropriate runner
    - Return normalized results
    
    Does NOT reimplement test execution logic - delegates to native runners.
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.build_config = self.detect_build_tool()
        self.framework_config = self.detect_test_framework()
    
    def detect_build_tool(self) -> BuildToolConfig:
        """
        Detect Maven or Gradle.
        
        Returns:
            BuildToolConfig with tool type and paths
            
        Raises:
            RuntimeError if no supported build tool found
        """
        if (self.project_root / "pom.xml").exists():
            return BuildToolConfig(
                tool="maven",
                test_output_dir="target/surefire-reports",
                test_source_dir="src/test/java"
            )
        
        if (self.project_root / "build.gradle").exists() or \
           (self.project_root / "build.gradle.kts").exists():
            return BuildToolConfig(
                tool="gradle",
                test_output_dir="build/test-results/test",
                test_source_dir="src/test/java"
            )
        
        raise RuntimeError(
            f"No supported build tool found in {self.project_root}. "
            "Expected pom.xml (Maven) or build.gradle (Gradle)."
        )
    
    def detect_test_framework(self) -> TestFrameworkConfig:
        """
        Detect JUnit 4, JUnit 5, or TestNG.
        
        Uses existing SeleniumJavaConfig from detection module.
        
        Returns:
            TestFrameworkConfig with framework details
        """
        detected_frameworks = SeleniumJavaConfig.detect_all_frameworks(
            project_root=str(self.project_root),
            source_root=str(self.project_root / "src" / "test" / "java")
        )
        
        if not detected_frameworks:
            # Default to JUnit 5 if nothing detected
            return TestFrameworkConfig(
                framework="junit5",
                supports_tags=True,
                supports_groups=False,
                supports_categories=False
            )
        
        # Get first framework (convert set to list)
        primary = list(detected_frameworks)[0] if detected_frameworks else "junit5"
        
        if "junit5" in primary.lower() or "jupiter" in primary.lower():
            return TestFrameworkConfig(
                framework="junit5",
                supports_tags=True,
                supports_groups=False,
                supports_categories=False
            )
        elif "junit" in primary.lower():
            return TestFrameworkConfig(
                framework="junit4",
                supports_tags=False,
                supports_groups=False,
                supports_categories=True
            )
        elif "testng" in primary.lower():
            return TestFrameworkConfig(
                framework="testng",
                supports_tags=False,
                supports_groups=True,
                supports_categories=False
            )
        
        # Default
        return TestFrameworkConfig(
            framework="junit5",
            supports_tags=True
        )
    
    def run_tests(
        self,
        tests: Optional[list] = None,
        test_methods: Optional[list] = None,
        tags: Optional[list] = None,
        groups: Optional[list] = None,
        categories: Optional[list] = None,
        parallel: bool = False,
        thread_count: Optional[int] = None,
        properties: Optional[dict] = None
    ) -> TestExecutionResult:
        """
        Run Selenium-Java tests with selective execution.
        
        Args:
            tests: Fully qualified test class names (e.g., com.example.LoginTest)
            test_methods: Specific methods (e.g., LoginTest#testValidLogin)
            tags: JUnit 5 tags to include
            groups: TestNG groups to include
            categories: JUnit 4 categories to include
            parallel: Enable parallel execution
            thread_count: Number of parallel threads
            properties: Additional system properties
            
        Returns:
            TestExecutionResult with status, exit code, and reports
            
        Raises:
            RuntimeError if build tool not available
        """
        # Validate selective execution options against framework
        self._validate_request(tags, groups, categories)
        
        # Build execution request
        request = TestExecutionRequest(
            working_dir=str(self.project_root),
            tests=tests,
            test_methods=test_methods,
            tags=tags,
            groups=groups,
            categories=categories,
            parallel=parallel,
            thread_count=thread_count,
            properties=properties
        )
        
        # Delegate to appropriate runner
        if self.build_config.tool == "maven":
            runner = MavenRunner(str(self.project_root))
            if not runner.verify_maven_available():
                return TestExecutionResult(
                    status="error",
                    exit_code=1,
                    error_message="Maven not found. Please install Maven or use Maven wrapper (mvnw)."
                )
            return runner.run_tests(request)
        
        elif self.build_config.tool == "gradle":
            runner = GradleRunner(str(self.project_root))
            if not runner.verify_gradle_available():
                return TestExecutionResult(
                    status="error",
                    exit_code=1,
                    error_message="Gradle not found. Please install Gradle or use Gradle wrapper (gradlew)."
                )
            return runner.run_tests(request)
        
        else:
            return TestExecutionResult(
                status="error",
                exit_code=1,
                error_message=f"Unsupported build tool: {self.build_config.tool}"
            )
    
    def _validate_request(
        self,
        tags: Optional[list],
        groups: Optional[list],
        categories: Optional[list]
    ):
        """
        Validate that requested selective execution features are supported.
        
        Raises:
            ValueError if unsupported features requested
        """
        if tags and not self.framework_config.supports_tags:
            raise ValueError(
                f"Tags are not supported by {self.framework_config.framework}. "
                "Use groups (TestNG) or categories (JUnit 4) instead."
            )
        
        if groups and not self.framework_config.supports_groups:
            raise ValueError(
                f"Groups are not supported by {self.framework_config.framework}. "
                "TestNG only."
            )
        
        if categories and not self.framework_config.supports_categories:
            raise ValueError(
                f"Categories are not supported by {self.framework_config.framework}. "
                "JUnit 4 only."
            )
    
    def get_info(self) -> dict:
        """
        Get adapter configuration information.
        
        Returns:
            Dictionary with build tool, framework, and capabilities
        """
        return {
            "build_tool": self.build_config.tool,
            "test_framework": self.framework_config.framework,
            "test_output_dir": self.build_config.test_output_dir,
            "test_source_dir": self.build_config.test_source_dir,
            "selective_execution": self.framework_config.get_selective_execution_support()
        }


def run_selenium_java_tests(
    project_root: str,
    tests: Optional[list] = None,
    test_methods: Optional[list] = None,
    tags: Optional[list] = None,
    groups: Optional[list] = None,
    categories: Optional[list] = None,
    parallel: bool = False,
    thread_count: Optional[int] = None,
    properties: Optional[dict] = None
) -> TestExecutionResult:
    """
    Convenience function to run Selenium-Java tests.
    
    Creates adapter instance and delegates execution.
    
    Args:
        project_root: Path to Java project root
        tests: Test classes to run
        test_methods: Specific test methods
        tags: JUnit 5 tags
        groups: TestNG groups
        categories: JUnit 4 categories
        parallel: Enable parallel execution
        thread_count: Number of threads
        properties: Additional properties
        
    Returns:
        TestExecutionResult
    """
    adapter = SeleniumJavaAdapter(project_root)
    return adapter.run_tests(
        tests=tests,
        test_methods=test_methods,
        tags=tags,
        groups=groups,
        categories=categories,
        parallel=parallel,
        thread_count=thread_count,
        properties=properties
    )
