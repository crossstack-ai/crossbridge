# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Behave Results Parser for CrossBridge Intelligence.

Parse Behave (Python BDD) test results for execution analysis:
- JSON formatter output
- JUnit XML output
- Scenario and step-level details
- Tags and fixtures
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BehaveStep:
    """Represents a Behave step."""
    keyword: str  # Given, When, Then, And, But
    name: str
    step_type: str  # 'given', 'when', 'then'
    status: str  # 'passed', 'failed', 'skipped', 'undefined'
    duration_ms: float = 0.0
    error: Optional[str] = None
    error_message: Optional[str] = None
    table: Optional[List[Dict]] = None
    text: Optional[str] = None  # Multi-line text
    line: int = 0


@dataclass
class BehaveScenario:
    """Represents a Behave scenario."""
    name: str
    feature_name: str
    status: str  # 'passed', 'failed', 'skipped'
    duration_ms: float = 0.0
    tags: List[str] = field(default_factory=list)
    steps: List[BehaveStep] = field(default_factory=list)
    line: int = 0
    description: str = ''
    
    def get_failed_steps(self) -> List[BehaveStep]:
        """Get all failed steps."""
        return [s for s in self.steps if s.status == 'failed']


@dataclass
class BehaveFeature:
    """Represents a Behave feature."""
    name: str
    description: str = ''
    tags: List[str] = field(default_factory=list)
    scenarios: List[BehaveScenario] = field(default_factory=list)
    line: int = 0
    file_path: str = ''


@dataclass
class BehaveRunResult:
    """Complete Behave test run result."""
    features: List[BehaveFeature] = field(default_factory=list)
    duration_ms: float = 0.0
    
    def get_all_scenarios(self) -> List[BehaveScenario]:
        """Get all scenarios from all features."""
        scenarios = []
        for feature in self.features:
            scenarios.extend(feature.scenarios)
        return scenarios
    
    def get_failed_scenarios(self) -> List[BehaveScenario]:
        """Get all failed scenarios."""
        return [s for s in self.get_all_scenarios() if s.status == 'failed']
    
    def get_statistics(self) -> Dict[str, int]:
        """Get execution statistics."""
        all_scenarios = self.get_all_scenarios()
        all_steps = []
        for scenario in all_scenarios:
            all_steps.extend(scenario.steps)
        
        return {
            'features': len(self.features),
            'scenarios': len(all_scenarios),
            'scenarios_passed': len([s for s in all_scenarios if s.status == 'passed']),
            'scenarios_failed': len([s for s in all_scenarios if s.status == 'failed']),
            'scenarios_skipped': len([s for s in all_scenarios if s.status == 'skipped']),
            'steps': len(all_steps),
            'steps_passed': len([s for s in all_steps if s.status == 'passed']),
            'steps_failed': len([s for s in all_steps if s.status == 'failed']),
            'steps_skipped': len([s for s in all_steps if s.status == 'skipped']),
            'steps_undefined': len([s for s in all_steps if s.status == 'undefined']),
        }


class BehaveResultsParser:
    """
    Parse Behave test results.
    
    Supports:
    - JSON formatter output (--format json)
    - JUnit XML output (basic parsing)
    """
    
    def __init__(self):
        self._last_result = None  # Cache last parsed result
    
    def parse(self, data: List[Dict]) -> Dict[str, Any]:
        """
        Parse Behave results from JSON list (for sidecar API).
        
        Args:
            data: Behave results as list of feature dicts
            
        Returns:
            Dict with parsed results in API format
        """
        result = BehaveRunResult()
        
        # Behave JSON is a list of features
        if isinstance(data, list):
            for feature_data in data:
                feature = self._parse_feature(feature_data)
                result.features.append(feature)
        
        # Calculate total duration
        for feature in result.features:
            for scenario in feature.scenarios:
                result.duration_ms += scenario.duration_ms
        
        self._last_result = result
        
        # Convert to API dict format
        all_scenarios = result.get_all_scenarios()
        failed_scenarios = result.get_failed_scenarios()
        stats = result.get_statistics()
        
        return {
            "framework": "behave",
            "total_features": len(result.features),
            "total_scenarios": len(all_scenarios),
            "passed_scenarios": stats['scenarios_passed'],
            "failed_scenarios": stats['scenarios_failed'],
            "skipped_scenarios": stats['scenarios_skipped'],
            "pass_rate": (stats['scenarios_passed'] / len(all_scenarios) * 100) if all_scenarios else 0,
            "duration_ms": result.duration_ms,
            "failed_scenarios_list": [
                {
                    "test_name": f"{s.feature_name}: {s.name}",
                    "scenario_name": s.name,
                    "feature_name": s.feature_name,
                    "status": s.status,
                    "error_message": " | ".join([step.error_message for step in s.get_failed_steps() if step.error_message]),
                    "failed_steps": len(s.get_failed_steps()),
                    "duration_ms": s.duration_ms,
                    "tags": s.tags,
                }
                for s in failed_scenarios
            ],
            "all_scenarios": [
                {
                    "test_name": f"{s.feature_name}: {s.name}",
                    "scenario_name": s.name,
                    "feature_name": s.feature_name,
                    "status": s.status,
                    "error_message": " | ".join([step.error_message for step in s.get_failed_steps() if step.error_message]) if s.status == 'failed' else "",
                    "duration_ms": s.duration_ms,
                    "tags": s.tags,
                }
                for s in all_scenarios
            ],
            "statistics": stats,
        }
    
    def parse_json(self, json_path: Path) -> Optional[BehaveRunResult]:
        """
        Parse Behave JSON results.
        
        Args:
            json_path: Path to JSON output file
            
        Returns:
            BehaveRunResult or None
        """
        try:
            if not json_path.exists():
                logger.error(f"Results file not found: {json_path}")
                return None
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            result = BehaveRunResult()
            
            # Behave JSON is a list of features
            if isinstance(data, list):
                for feature_data in data:
                    feature = self._parse_feature(feature_data)
                    result.features.append(feature)
            else:
                logger.warning("Unexpected Behave JSON format")
                return None
            
            # Calculate total duration
            for feature in result.features:
                for scenario in feature.scenarios:
                    result.duration_ms += scenario.duration_ms
            
            logger.info(f"Parsed Behave results: {len(result.features)} features, "
                       f"{len(result.get_all_scenarios())} scenarios")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in results file: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse Behave results {json_path}: {e}")
            return None
    
    def _parse_feature(self, feature_data: Dict) -> BehaveFeature:
        """Parse a single feature."""
        feature = BehaveFeature(
            name=feature_data.get('name', 'Unknown Feature'),
            description=feature_data.get('description', ''),
            tags=[tag.get('name', '').lstrip('@') for tag in feature_data.get('tags', [])],
            line=feature_data.get('line', 0),
            file_path=feature_data.get('location', '')
        )
        
        # Parse scenarios
        elements = feature_data.get('elements', [])
        for element_data in elements:
            # Elements can be scenarios, scenario outlines, or backgrounds
            element_type = element_data.get('type', 'scenario')
            
            if element_type in ['scenario', 'scenario_outline']:
                scenario = self._parse_scenario(element_data, feature.name)
                feature.scenarios.append(scenario)
        
        return feature
    
    def _parse_scenario(self, scenario_data: Dict, feature_name: str) -> BehaveScenario:
        """Parse a single scenario."""
        scenario = BehaveScenario(
            name=scenario_data.get('name', 'Unknown Scenario'),
            feature_name=feature_name,
            status=scenario_data.get('status', 'unknown'),
            tags=[tag.get('name', '').lstrip('@') for tag in scenario_data.get('tags', [])],
            line=scenario_data.get('line', 0),
            description=scenario_data.get('description', '')
        )
        
        # Parse steps
        steps = scenario_data.get('steps', [])
        for step_data in steps:
            step = self._parse_step(step_data)
            scenario.steps.append(step)
            scenario.duration_ms += step.duration_ms
        
        # Determine overall status from steps
        if not scenario.status or scenario.status == 'unknown':
            if any(s.status == 'failed' for s in scenario.steps):
                scenario.status = 'failed'
            elif any(s.status == 'skipped' for s in scenario.steps):
                scenario.status = 'skipped'
            elif all(s.status == 'passed' for s in scenario.steps):
                scenario.status = 'passed'
        
        return scenario
    
    def _parse_step(self, step_data: Dict) -> BehaveStep:
        """Parse a single step."""
        result = step_data.get('result', {})
        
        step = BehaveStep(
            keyword=step_data.get('keyword', '').strip(),
            name=step_data.get('name', ''),
            step_type=step_data.get('step_type', step_data.get('keyword', '').lower().strip()),
            status=result.get('status', 'unknown'),
            duration_ms=result.get('duration', 0) * 1000,  # Behave reports in seconds
            line=step_data.get('line', 0)
        )
        
        # Parse error if step failed
        if step.status == 'failed':
            step.error = result.get('error_message', '')
            if 'error_message' in result:
                # Extract just the error message without full traceback
                error_lines = result['error_message'].split('\n')
                step.error_message = error_lines[0] if error_lines else ''
        
        # Parse table (data tables)
        if 'table' in step_data:
            table_data = step_data['table']
            step.table = []
            if 'rows' in table_data:
                headers = [h.get('name', '') for h in table_data.get('headings', [])]
                for row in table_data['rows']:
                    cells = [c.get('value', '') for c in row.get('cells', [])]
                    if len(headers) == len(cells):
                        step.table.append(dict(zip(headers, cells)))
        
        # Parse multi-line text
        if 'text' in step_data:
            step.text = step_data['text']
        
        return step
    
    def get_test_summary(self, result: BehaveRunResult) -> Dict[str, Any]:
        """Get human-readable test summary."""
        stats = result.get_statistics()
        
        pass_rate = 0
        if stats['scenarios'] > 0:
            pass_rate = (stats['scenarios_passed'] / stats['scenarios']) * 100
        
        return {
            'features': stats['features'],
            'scenarios': stats['scenarios'],
            'passed': stats['scenarios_passed'],
            'failed': stats['scenarios_failed'],
            'skipped': stats['scenarios_skipped'],
            'total_steps': stats['steps'],
            'duration_ms': result.duration_ms,
            'pass_rate': pass_rate,
        }


# ============================================================================
# Selenium WebDriver Log Parser
# ============================================================================

@dataclass
class SeleniumLogEntry:
    """Represents a Selenium WebDriver log entry."""
    timestamp: str
    level: str  # 'INFO', 'WARNING', 'ERROR', 'DEBUG'
    source: str  # 'browser', 'driver', 'network', etc.
    message: str


@dataclass
class SeleniumLogResult:
    """Parsed Selenium logs."""
    entries: List[SeleniumLogEntry] = field(default_factory=list)
    
    def get_errors(self) -> List[SeleniumLogEntry]:
        """Get error-level entries."""
        return [e for e in self.entries if e.level in ['ERROR', 'SEVERE']]
    
    def get_warnings(self) -> List[SeleniumLogEntry]:
        """Get warning-level entries."""
        return [e for e in self.entries if e.level == 'WARNING']
    
    def get_network_errors(self) -> List[SeleniumLogEntry]:
        """Get network-related errors."""
        return [e for e in self.entries 
                if e.level in ['ERROR', 'SEVERE'] and 'network' in e.source.lower()]


class SeleniumLogParser:
    """
    Parse Selenium WebDriver logs.
    
    Supports:
    - Browser console logs
    - Driver logs
    - Network logs
    """
    
    def parse_json_logs(self, log_path: Path) -> Optional[SeleniumLogResult]:
        """
        Parse Selenium logs in JSON format.
        
        Args:
            log_path: Path to log file (JSON array format)
            
        Returns:
            SeleniumLogResult or None
        """
        try:
            if not log_path.exists():
                logger.error(f"Log file not found: {log_path}")
                return None
            
            with open(log_path, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            result = SeleniumLogResult()
            
            if isinstance(logs, list):
                for log_entry in logs:
                    entry = SeleniumLogEntry(
                        timestamp=log_entry.get('timestamp', ''),
                        level=log_entry.get('level', 'INFO'),
                        source=log_entry.get('source', 'browser'),
                        message=log_entry.get('message', '')
                    )
                    result.entries.append(entry)
            
            logger.info(f"Parsed {len(result.entries)} Selenium log entries")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse Selenium logs {log_path}: {e}")
            return None


# ============================================================================
# Convenience Functions
# ============================================================================

def parse_behave_results(json_path: Path) -> Optional[BehaveRunResult]:
    """
    Convenience function to parse Behave results.
    
    Args:
        json_path: Path to Behave JSON output
        
    Returns:
        BehaveRunResult or None
    """
    parser = BehaveResultsParser()
    return parser.parse_json(json_path)


def parse_selenium_logs(log_path: Path) -> Optional[SeleniumLogResult]:
    """
    Convenience function to parse Selenium logs.
    
    Args:
        log_path: Path to Selenium log file
        
    Returns:
        SeleniumLogResult or None
    """
    parser = SeleniumLogParser()
    return parser.parse_json_logs(log_path)


def analyze_behave_failures(json_path: Path) -> Dict[str, Any]:
    """
    Analyze Behave failures for common patterns.
    
    Args:
        json_path: Path to Behave JSON output
        
    Returns:
        Dict with failure analysis
    """
    result = parse_behave_results(json_path)
    if not result:
        return {}
    
    failed_scenarios = result.get_failed_scenarios()
    
    # Group failures by step type
    failed_steps_by_type = {'given': 0, 'when': 0, 'then': 0}
    error_messages = {}
    
    for scenario in failed_scenarios:
        for step in scenario.get_failed_steps():
            step_type = step.step_type.lower()
            if step_type in failed_steps_by_type:
                failed_steps_by_type[step_type] += 1
            
            if step.error_message:
                error_messages[step.error_message] = error_messages.get(step.error_message, 0) + 1
    
    # Find most common error
    most_common_error = max(error_messages.items(), key=lambda x: x[1]) if error_messages else (None, 0)
    
    return {
        'total_failures': len(failed_scenarios),
        'failed_given_steps': failed_steps_by_type['given'],
        'failed_when_steps': failed_steps_by_type['when'],
        'failed_then_steps': failed_steps_by_type['then'],
        'most_common_error': most_common_error[0],
        'most_common_error_count': most_common_error[1],
        'unique_errors': len(error_messages),
    }
