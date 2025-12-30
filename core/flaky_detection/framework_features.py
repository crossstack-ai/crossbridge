"""
Framework-Specific Feature Extractors for Flaky Detection.

Each framework has unique failure patterns. This module extracts specialized
features that capture framework-specific flakiness indicators.

Supports:
- Selenium Java: UI timing, element staleness, wait failures
- Cucumber/BDD: Step instability, scenario outline variance
- Pytest: Fixture failures, order dependency, xfail flips
- Robot Framework: Keyword retries, environment sensitivity
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import Counter
import re

from .models import TestExecutionRecord, TestFramework


# ============================================================================
# Framework-Specific Feature Models
# ============================================================================

@dataclass
class SeleniumFeatures:
    """Selenium/WebDriver-specific flakiness features."""
    
    timeout_failure_rate: float           # TimeoutException frequency
    stale_element_rate: float             # StaleElementReferenceException frequency
    wait_related_failures: float          # Explicit/implicit wait issues
    browser_restart_sensitivity: float    # Failures after browser restart
    element_not_found_rate: float         # NoSuchElementException frequency
    javascript_error_rate: float          # JS execution failures
    
    def to_array(self) -> List[float]:
        """Convert to numpy-compatible array."""
        return [
            self.timeout_failure_rate,
            self.stale_element_rate,
            self.wait_related_failures,
            self.browser_restart_sensitivity,
            self.element_not_found_rate,
            self.javascript_error_rate,
        ]


@dataclass
class CucumberFeatures:
    """Cucumber/BDD-specific flakiness features."""
    
    unstable_step_ratio: float            # Ratio of unstable steps in scenario
    scenario_outline_variance: float      # Variance across example rows
    step_duration_variance: float         # Step execution time variance
    hook_failure_rate: float              # Before/After hook failures
    background_step_failures: float       # Background step instability
    data_table_sensitivity: float         # Failures with data tables
    
    def to_array(self) -> List[float]:
        """Convert to numpy-compatible array."""
        return [
            self.unstable_step_ratio,
            self.scenario_outline_variance,
            self.step_duration_variance,
            self.hook_failure_rate,
            self.background_step_failures,
            self.data_table_sensitivity,
        ]


@dataclass
class PytestFeatures:
    """Pytest-specific flakiness features."""
    
    fixture_failure_rate: float           # Setup/teardown failures
    order_dependency_score: float         # Sensitivity to test execution order
    xfail_flip_rate: float                # xfail unexpectedly passing
    parametrize_variance: float           # Variance across parameters
    conftest_sensitivity: float           # Configuration-dependent failures
    marker_based_variance: float          # Variance by test markers
    
    def to_array(self) -> List[float]:
        """Convert to numpy-compatible array."""
        return [
            self.fixture_failure_rate,
            self.order_dependency_score,
            self.xfail_flip_rate,
            self.parametrize_variance,
            self.conftest_sensitivity,
            self.marker_based_variance,
        ]


@dataclass
class RobotFeatures:
    """Robot Framework-specific flakiness features."""
    
    keyword_retry_rate: float             # Keyword-level retry frequency
    environment_variable_sensitivity: float  # Env var dependency
    library_import_failures: float        # Import/initialization issues
    variable_resolution_failures: float   # ${variable} resolution issues
    suite_setup_teardown_rate: float      # Suite-level hook failures
    resource_import_sensitivity: float    # Resource file dependency
    
    def to_array(self) -> List[float]:
        """Convert to numpy-compatible array."""
        return [
            self.keyword_retry_rate,
            self.environment_variable_sensitivity,
            self.library_import_failures,
            self.variable_resolution_failures,
            self.suite_setup_teardown_rate,
            self.resource_import_sensitivity,
        ]


# ============================================================================
# Error Classifiers
# ============================================================================

class SeleniumErrorClassifier:
    """Classify Selenium/WebDriver errors."""
    
    TIMEOUT_PATTERNS = [
        r"TimeoutException",
        r"timeout",
        r"timed out",
        r"wait.*failed",
    ]
    
    STALE_ELEMENT_PATTERNS = [
        r"StaleElementReferenceException",
        r"stale element",
        r"element.*no longer attached",
    ]
    
    ELEMENT_NOT_FOUND_PATTERNS = [
        r"NoSuchElementException",
        r"element.*not found",
        r"Unable to locate element",
    ]
    
    JAVASCRIPT_ERROR_PATTERNS = [
        r"JavascriptException",
        r"javascript error",
        r"script timeout",
    ]
    
    @classmethod
    def classify(cls, error_signature: str) -> Dict[str, bool]:
        """Classify error into Selenium-specific categories."""
        if not error_signature:
            return {
                "timeout": False,
                "stale_element": False,
                "element_not_found": False,
                "javascript": False,
            }
        
        error_lower = error_signature.lower()
        
        return {
            "timeout": any(re.search(p, error_lower, re.IGNORECASE) 
                          for p in cls.TIMEOUT_PATTERNS),
            "stale_element": any(re.search(p, error_lower, re.IGNORECASE) 
                                for p in cls.STALE_ELEMENT_PATTERNS),
            "element_not_found": any(re.search(p, error_lower, re.IGNORECASE) 
                                    for p in cls.ELEMENT_NOT_FOUND_PATTERNS),
            "javascript": any(re.search(p, error_lower, re.IGNORECASE) 
                             for p in cls.JAVASCRIPT_ERROR_PATTERNS),
        }


class PytestErrorClassifier:
    """Classify Pytest errors."""
    
    FIXTURE_PATTERNS = [
        r"fixture.*error",
        r"setup.*failed",
        r"teardown.*failed",
        r"fixture.*not found",
    ]
    
    XFAIL_PATTERNS = [
        r"xfail",
        r"xpass",
        r"expected.*fail",
    ]
    
    @classmethod
    def classify(cls, error_signature: str) -> Dict[str, bool]:
        """Classify error into Pytest-specific categories."""
        if not error_signature:
            return {
                "fixture": False,
                "xfail": False,
            }
        
        error_lower = error_signature.lower()
        
        return {
            "fixture": any(re.search(p, error_lower, re.IGNORECASE) 
                          for p in cls.FIXTURE_PATTERNS),
            "xfail": any(re.search(p, error_lower, re.IGNORECASE) 
                        for p in cls.XFAIL_PATTERNS),
        }


class RobotErrorClassifier:
    """Classify Robot Framework errors."""
    
    KEYWORD_PATTERNS = [
        r"keyword.*failed",
        r"keyword.*not found",
    ]
    
    VARIABLE_PATTERNS = [
        r"variable.*not found",
        r"variable.*undefined",
        r"\$\{.*\}.*not.*defined",
    ]
    
    IMPORT_PATTERNS = [
        r"import.*failed",
        r"library.*not found",
        r"resource.*not found",
    ]
    
    @classmethod
    def classify(cls, error_signature: str) -> Dict[str, bool]:
        """Classify error into Robot-specific categories."""
        if not error_signature:
            return {
                "keyword": False,
                "variable": False,
                "import": False,
            }
        
        error_lower = error_signature.lower()
        
        return {
            "keyword": any(re.search(p, error_lower, re.IGNORECASE) 
                          for p in cls.KEYWORD_PATTERNS),
            "variable": any(re.search(p, error_lower, re.IGNORECASE) 
                           for p in cls.VARIABLE_PATTERNS),
            "import": any(re.search(p, error_lower, re.IGNORECASE) 
                         for p in cls.IMPORT_PATTERNS),
        }


# ============================================================================
# Framework Feature Extractors
# ============================================================================

class SeleniumFeatureExtractor:
    """Extract Selenium-specific features from execution history."""
    
    def extract(self, executions: List[TestExecutionRecord]) -> SeleniumFeatures:
        """Extract Selenium features."""
        if not executions:
            return SeleniumFeatures(0, 0, 0, 0, 0, 0)
        
        total = len(executions)
        failures = [e for e in executions if e.status == "failed"]
        
        if not failures:
            return SeleniumFeatures(0, 0, 0, 0, 0, 0)
        
        # Classify errors
        timeout_count = 0
        stale_element_count = 0
        element_not_found_count = 0
        javascript_count = 0
        wait_related_count = 0
        
        for failure in failures:
            classification = SeleniumErrorClassifier.classify(
                failure.error_signature or ""
            )
            
            if classification["timeout"]:
                timeout_count += 1
                wait_related_count += 1
            if classification["stale_element"]:
                stale_element_count += 1
            if classification["element_not_found"]:
                element_not_found_count += 1
            if classification["javascript"]:
                javascript_count += 1
        
        # Calculate browser restart sensitivity
        # (failures immediately after first execution in a session)
        browser_restart_failures = sum(
            1 for i, e in enumerate(executions)
            if i > 0 and e.status == "failed" and 
            executions[i-1].status == "passed"
        )
        
        return SeleniumFeatures(
            timeout_failure_rate=timeout_count / total,
            stale_element_rate=stale_element_count / total,
            wait_related_failures=wait_related_count / total,
            browser_restart_sensitivity=browser_restart_failures / max(1, total - 1),
            element_not_found_rate=element_not_found_count / total,
            javascript_error_rate=javascript_count / total,
        )


class CucumberFeatureExtractor:
    """Extract Cucumber/BDD-specific features from execution history."""
    
    def extract(self, executions: List[TestExecutionRecord]) -> CucumberFeatures:
        """Extract Cucumber features."""
        if not executions:
            return CucumberFeatures(0, 0, 0, 0, 0, 0)
        
        total = len(executions)
        failures = [e for e in executions if e.status == "failed"]
        
        if not failures:
            return CucumberFeatures(0, 0, 0, 0, 0, 0)
        
        # Extract step information from metadata
        step_failures = []
        hook_failures = 0
        background_failures = 0
        data_table_failures = 0
        
        for failure in failures:
            error = failure.error_signature or ""
            
            # Check for hook failures
            if "before" in error.lower() or "after" in error.lower():
                hook_failures += 1
            
            # Check for background failures
            if "background" in error.lower():
                background_failures += 1
            
            # Check for data table issues
            if "data table" in error.lower() or "table" in error.lower():
                data_table_failures += 1
        
        # Calculate step duration variance
        durations = [e.duration_ms for e in executions if e.duration_ms > 0]
        duration_variance = 0.0
        if len(durations) > 1:
            mean_duration = sum(durations) / len(durations)
            variance = sum((d - mean_duration) ** 2 for d in durations) / len(durations)
            duration_variance = variance / (mean_duration ** 2) if mean_duration > 0 else 0
        
        # Scenario outline variance (check metadata for outline indicators)
        outline_failures = sum(
            1 for f in failures 
            if f.test_name and ("outline" in f.test_name.lower() or 
                               "example" in f.test_name.lower())
        )
        
        return CucumberFeatures(
            unstable_step_ratio=len(step_failures) / max(1, total),
            scenario_outline_variance=outline_failures / max(1, len(failures)),
            step_duration_variance=duration_variance,
            hook_failure_rate=hook_failures / total,
            background_step_failures=background_failures / total,
            data_table_sensitivity=data_table_failures / total,
        )


class PytestFeatureExtractor:
    """Extract Pytest-specific features from execution history."""
    
    def extract(self, executions: List[TestExecutionRecord]) -> PytestFeatures:
        """Extract Pytest features."""
        if not executions:
            return PytestFeatures(0, 0, 0, 0, 0, 0)
        
        total = len(executions)
        failures = [e for e in executions if e.status == "failed"]
        
        if not failures:
            return PytestFeatures(0, 0, 0, 0, 0, 0)
        
        # Classify errors
        fixture_count = 0
        xfail_count = 0
        
        for failure in failures:
            classification = PytestErrorClassifier.classify(
                failure.error_signature or ""
            )
            
            if classification["fixture"]:
                fixture_count += 1
            if classification["xfail"]:
                xfail_count += 1
        
        # Order dependency: check if pass/fail depends on position
        order_changes = 0
        for i in range(1, len(executions)):
            if executions[i].status != executions[i-1].status:
                order_changes += 1
        order_dependency = order_changes / max(1, total - 1)
        
        # Parametrize variance: check metadata for parametrize
        parametrize_failures = sum(
            1 for f in failures 
            if f.test_name and "[" in f.test_name  # Pytest parametrize marker
        )
        parametrize_variance = parametrize_failures / max(1, len(failures))
        
        # Conftest sensitivity (check environment metadata)
        env_variance = len(set(e.environment for e in executions if e.environment))
        conftest_sensitivity = env_variance / max(1, total)
        
        return PytestFeatures(
            fixture_failure_rate=fixture_count / total,
            order_dependency_score=order_dependency,
            xfail_flip_rate=xfail_count / total,
            parametrize_variance=parametrize_variance,
            conftest_sensitivity=conftest_sensitivity,
            marker_based_variance=0.0,  # Would need metadata
        )


class RobotFeatureExtractor:
    """Extract Robot Framework-specific features from execution history."""
    
    def extract(self, executions: List[TestExecutionRecord]) -> RobotFeatures:
        """Extract Robot features."""
        if not executions:
            return RobotFeatures(0, 0, 0, 0, 0, 0)
        
        total = len(executions)
        failures = [e for e in executions if e.status == "failed"]
        
        if not failures:
            return RobotFeatures(0, 0, 0, 0, 0, 0)
        
        # Classify errors
        keyword_count = 0
        variable_count = 0
        import_count = 0
        
        for failure in failures:
            classification = RobotErrorClassifier.classify(
                failure.error_signature or ""
            )
            
            if classification["keyword"]:
                keyword_count += 1
            if classification["variable"]:
                variable_count += 1
            if classification["import"]:
                import_count += 1
        
        # Keyword retry detection (from retry_count)
        retry_count = sum(e.retry_count for e in executions)
        keyword_retry_rate = retry_count / max(1, total)
        
        # Environment variable sensitivity
        env_variance = len(set(e.environment for e in executions if e.environment))
        env_sensitivity = env_variance / max(1, total)
        
        # Suite setup/teardown (check metadata)
        suite_failures = sum(
            1 for f in failures
            if f.error_signature and ("suite setup" in f.error_signature.lower() or
                                      "suite teardown" in f.error_signature.lower())
        )
        
        return RobotFeatures(
            keyword_retry_rate=keyword_retry_rate,
            environment_variable_sensitivity=env_sensitivity,
            library_import_failures=import_count / total,
            variable_resolution_failures=variable_count / total,
            suite_setup_teardown_rate=suite_failures / total,
            resource_import_sensitivity=import_count / max(1, len(failures)),
        )


# ============================================================================
# Unified Framework Feature Extractor
# ============================================================================

class FrameworkFeatureExtractor:
    """Unified extractor that delegates to framework-specific extractors."""
    
    def __init__(self):
        self.selenium_extractor = SeleniumFeatureExtractor()
        self.cucumber_extractor = CucumberFeatureExtractor()
        self.pytest_extractor = PytestFeatureExtractor()
        self.robot_extractor = RobotFeatureExtractor()
    
    def extract(
        self,
        executions: List[TestExecutionRecord],
        framework: TestFramework
    ) -> List[float]:
        """
        Extract framework-specific features.
        
        Returns:
            List of feature values to append to base features
        """
        if framework == TestFramework.SELENIUM_JAVA:
            features = self.selenium_extractor.extract(executions)
            return features.to_array()
        
        elif framework == TestFramework.CUCUMBER:
            features = self.cucumber_extractor.extract(executions)
            return features.to_array()
        
        elif framework == TestFramework.PYTEST:
            features = self.pytest_extractor.extract(executions)
            return features.to_array()
        
        elif framework == TestFramework.ROBOT:
            features = self.robot_extractor.extract(executions)
            return features.to_array()
        
        elif framework == TestFramework.JUNIT:
            # JUnit uses Selenium features (often Selenium-based)
            features = self.selenium_extractor.extract(executions)
            return features.to_array()
        
        elif framework == TestFramework.TESTNG:
            # TestNG uses Selenium features (often Selenium-based)
            features = self.selenium_extractor.extract(executions)
            return features.to_array()
        
        else:
            # Unknown framework: return zeros
            return [0.0] * 6
    
    def get_feature_names(self, framework: TestFramework) -> List[str]:
        """Get feature names for a framework."""
        if framework in (TestFramework.SELENIUM_JAVA, TestFramework.JUNIT, TestFramework.TESTNG):
            return [
                "timeout_failure_rate",
                "stale_element_rate",
                "wait_related_failures",
                "browser_restart_sensitivity",
                "element_not_found_rate",
                "javascript_error_rate",
            ]
        
        elif framework == TestFramework.CUCUMBER:
            return [
                "unstable_step_ratio",
                "scenario_outline_variance",
                "step_duration_variance",
                "hook_failure_rate",
                "background_step_failures",
                "data_table_sensitivity",
            ]
        
        elif framework == TestFramework.PYTEST:
            return [
                "fixture_failure_rate",
                "order_dependency_score",
                "xfail_flip_rate",
                "parametrize_variance",
                "conftest_sensitivity",
                "marker_based_variance",
            ]
        
        elif framework == TestFramework.ROBOT:
            return [
                "keyword_retry_rate",
                "environment_variable_sensitivity",
                "library_import_failures",
                "variable_resolution_failures",
                "suite_setup_teardown_rate",
                "resource_import_sensitivity",
            ]
        
        else:
            return ["framework_feature_" + str(i) for i in range(6)]
