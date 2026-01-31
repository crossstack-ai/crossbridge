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
    """
    Parse a single scenario from Cucumber JSON.
    
    Handles both regular scenarios and scenario outline instances.
    For scenario outlines, extracts example data from the scenario name
    which Cucumber includes in the format "Scenario Name <row_index>".
    """
    scenario_name = element.get("name", "Unnamed Scenario")
    scenario_type = element.get("type", "scenario")
    line = element.get("line", -1)
    
    # Gap 2: Extract scenario outline metadata if present
    outline_example_index: Optional[int] = None
    outline_example_data: Optional[dict] = None
    source_outline_uri: Optional[str] = None
    source_outline_line: Optional[int] = None
    
    # Cucumber appends example index to scenario name for outlines
    # E.g., "Login with credentials <1>" or "Login with credentials"
    if scenario_type == "scenario" and "<" in scenario_name and ">" in scenario_name:
        import re
        match = re.search(r'<(\d+)>$', scenario_name)
        if match:
            outline_example_index = int(match.group(1)) - 1  # Convert to 0-based
            # Remove the index suffix from name
            scenario_name = re.sub(r'\s*<\d+>$', '', scenario_name)
            # Mark as originally from outline
            scenario_type = "scenario_outline"
            source_outline_uri = uri
            source_outline_line = line
            
            # Try to extract example data from step text
            # Cucumber replaces <param> with actual values in step text
            outline_example_data = _extract_example_data_from_steps(element.get("steps", []))
    
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
    
    # Gap 3: Extract metadata from environment (if available)
    metadata = None
    try:
        from .metadata_extractor import extract_metadata, MetadataExtractor
        metadata = extract_metadata()
        
        # Enhance metadata with scenario-specific info
        extractor = MetadataExtractor()
        metadata.grouping = extractor.extract_grouping_from_annotations(all_tags)
    except ImportError:
        pass  # Metadata extraction not available
    
    return ScenarioResult(
        feature=feature_name,
        scenario=scenario_name,
        scenario_type=scenario_type,
        tags=all_tags,
        steps=steps,
        status=scenario_status,
        uri=uri,
        line=line,
        metadata=metadata,
        outline_example_index=outline_example_index,
        outline_example_data=outline_example_data,
        source_outline_uri=source_outline_uri,
        source_outline_line=source_outline_line
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


def _extract_example_data_from_steps(steps: List[Dict[str, Any]]) -> dict:
    """
    Extract example data from scenario outline steps.
    
    When Cucumber expands scenario outlines, it replaces <param> placeholders
    with actual values in step text. This function attempts to extract those
    values by comparing step text patterns.
    
    Returns:
        Dictionary of parameter name -> value from example row
    """
    example_data = {}
    
    # Look for quoted strings that might be example values
    # Common pattern: Given I login with "username" and "password"
    import re
    
    for step_data in steps:
        step_name = step_data.get("name", "")
        
        # Find quoted strings (potential example values)
        quoted_values = re.findall(r'"([^"]+)"', step_name)
        
        # Find numeric values
        numeric_values = re.findall(r'\b(\d+)\b', step_name)
        
        # Store with generic keys (we don't know parameter names without original outline)
        for i, value in enumerate(quoted_values):
            example_data[f"param_{i+1}"] = value
        
        for i, value in enumerate(numeric_values):
            example_data[f"numeric_{i+1}"] = value
    
    return example_data if example_data else None


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
