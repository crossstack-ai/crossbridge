"""
Cucumber JSON Report Parser.

Parses Cucumber JSON reports (from Cucumber JVM, Cucumber JS, etc.) into
framework-neutral domain models for CrossBridge platform.

The parser is:
- Framework-neutral: Works with any Cucumber implementation
- Deterministic: Same input produces same output
- Independent: Does not require test execution
- DB-ready: Produces clean domain objects for persistence
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from .models import FeatureResult, ScenarioResult, StepResult


class CucumberJsonParseError(Exception):
    """Raised when Cucumber JSON parsing fails."""
    pass


def parse_cucumber_json(report_path: str | Path) -> List[FeatureResult]:
    """
    Parse a Cucumber JSON report file into framework-neutral domain models.
    
    Args:
        report_path: Path to the cucumber-report.json file
        
    Returns:
        List of FeatureResult objects containing parsed test data
        
    Raises:
        FileNotFoundError: If report file doesn't exist
        CucumberJsonParseError: If JSON is invalid or malformed
        
    Example:
        >>> features = parse_cucumber_json("target/cucumber-report.json")
        >>> for feature in features:
        ...     print(f"{feature.name}: {feature.overall_status}")
    """
    path = Path(report_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Cucumber report not found: {path}")
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CucumberJsonParseError(f"Invalid JSON in {path}: {e}")
    
    if not isinstance(data, list):
        raise CucumberJsonParseError(
            f"Expected JSON array of features, got {type(data).__name__}"
        )
    
    features: List[FeatureResult] = []
    
    for feature_data in data:
        try:
            feature = _parse_feature(feature_data)
            features.append(feature)
        except Exception as e:
            # Log warning but continue parsing other features
            print(f"Warning: Failed to parse feature {feature_data.get('name', 'unknown')}: {e}")
            continue
    
    return features


def _parse_feature(feature_data: Dict[str, Any]) -> FeatureResult:
    """Parse a single feature from Cucumber JSON."""
    feature_name = feature_data.get("name", "Unnamed Feature")
    uri = feature_data.get("uri", "")
    description = feature_data.get("description", None)
    
    # Parse feature-level tags
    feature_tags = [
        _normalize_tag(tag.get("name", ""))
        for tag in feature_data.get("tags", [])
    ]
    
    scenarios: List[ScenarioResult] = []
    
    for element in feature_data.get("elements", []):
        element_type = element.get("type", "")
        
        # Skip background and other non-scenario elements for now
        # Background steps are typically merged into scenarios by Cucumber
        if element_type not in ("scenario", "scenario_outline"):
            continue
        
        try:
            scenario = _parse_scenario(element, feature_name, uri, feature_tags)
            scenarios.append(scenario)
        except Exception as e:
            print(f"Warning: Failed to parse scenario {element.get('name', 'unknown')}: {e}")
            continue
    
    return FeatureResult(
        name=feature_name,
        uri=uri,
        scenarios=scenarios,
        description=description,
        tags=feature_tags
    )


def _parse_scenario(
    element: Dict[str, Any],
    feature_name: str,
    uri: str,
    feature_tags: List[str]
) -> ScenarioResult:
    """Parse a single scenario from Cucumber JSON."""
    scenario_name = element.get("name", "Unnamed Scenario")
    scenario_type = element.get("type", "scenario")
    line = element.get("line", -1)
    
    # Parse scenario-level tags (combine with feature tags)
    scenario_tags = [
        _normalize_tag(tag.get("name", ""))
        for tag in element.get("tags", [])
    ]
    
    # Combine feature and scenario tags (remove duplicates)
    all_tags = list(set(feature_tags + scenario_tags))
    
    # Parse steps
    steps: List[StepResult] = []
    scenario_status = "passed"  # Default status
    
    for step_data in element.get("steps", []):
        step, step_status = _parse_step(step_data)
        steps.append(step)
        
        # Compute scenario status based on step statuses
        # Priority: failed > skipped > passed
        if step_status == "failed":
            scenario_status = "failed"
        elif step_status in ("skipped", "pending", "undefined") and scenario_status != "failed":
            scenario_status = "skipped"
    
    return ScenarioResult(
        feature=feature_name,
        scenario=scenario_name,
        scenario_type=scenario_type,
        tags=all_tags,
        steps=steps,
        status=scenario_status,
        uri=uri,
        line=line
    )


def _parse_step(step_data: Dict[str, Any]) -> tuple[StepResult, str]:
    """
    Parse a single step from Cucumber JSON.
    
    Returns:
        Tuple of (StepResult, raw_status) where raw_status is the original
        Cucumber status for scenario status computation.
    """
    step_name = step_data.get("name", "")
    keyword = step_data.get("keyword", "")
    
    # Include keyword in step name for better readability
    full_name = f"{keyword.strip()} {step_name}".strip()
    
    result = step_data.get("result", {})
    status = result.get("status", "skipped")
    duration_ns = result.get("duration", 0)
    
    # Extract error message if present
    error_message: Optional[str] = None
    if status == "failed":
        error_message = result.get("error_message")
        
        # Some Cucumber implementations nest error details
        if not error_message and "error" in result:
            error_obj = result["error"]
            if isinstance(error_obj, str):
                error_message = error_obj
            elif isinstance(error_obj, dict):
                error_message = error_obj.get("message", str(error_obj))
    
    # Normalize status for our model
    normalized_status = _normalize_step_status(status)
    
    step_result = StepResult(
        name=full_name,
        status=normalized_status,
        duration_ns=duration_ns,
        error_message=error_message
    )
    
    return step_result, status


def _normalize_step_status(status: str) -> str:
    """
    Normalize Cucumber step status to our standard set.
    
    Cucumber can have: passed, failed, skipped, pending, undefined
    We normalize to: passed, failed, skipped, pending, undefined
    """
    status = status.lower()
    
    # Map various status values to our standard set
    status_map = {
        "passed": "passed",
        "failed": "failed",
        "skipped": "skipped",
        "pending": "pending",
        "undefined": "undefined",
        "ambiguous": "failed",  # Treat ambiguous as failed
    }
    
    return status_map.get(status, "skipped")


def _normalize_tag(tag: str) -> str:
    """Normalize a tag by ensuring it starts with @."""
    tag = tag.strip()
    if not tag.startswith("@"):
        tag = f"@{tag}"
    return tag


def parse_multiple_cucumber_reports(report_paths: List[str | Path]) -> List[FeatureResult]:
    """
    Parse multiple Cucumber JSON reports and combine results.
    
    Useful when test execution is split across multiple runners or modules.
    
    Args:
        report_paths: List of paths to Cucumber JSON report files
        
    Returns:
        Combined list of FeatureResult objects from all reports
        
    Example:
        >>> reports = [
        ...     "module-a/target/cucumber.json",
        ...     "module-b/target/cucumber.json"
        ... ]
        >>> features = parse_multiple_cucumber_reports(reports)
    """
    all_features: List[FeatureResult] = []
    
    for report_path in report_paths:
        try:
            features = parse_cucumber_json(report_path)
            all_features.extend(features)
        except FileNotFoundError:
            print(f"Warning: Report not found: {report_path}")
            continue
        except CucumberJsonParseError as e:
            print(f"Warning: Failed to parse {report_path}: {e}")
            continue
    
    return all_features
