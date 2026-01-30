"""
Cucumber JSON Report Parser

Parses Cucumber JSON reports and feature files to extract:
- Features
- Scenarios
- Steps
- Execution results
- Tags
- Timings

Supports:
- cucumber.json (standard Cucumber JSON format)
- *.feature files (Gherkin syntax)
"""

import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from core.logging import get_logger
from core.execution.intelligence.models import (
    CucumberScenario,
    CucumberStep,
    ExecutionSignal,
    EntityType,
)

logger = get_logger(__name__)


class CucumberJSONParser:
    """
    Parses Cucumber JSON reports.
    
    Standard format from: cucumber-jvm, cucumber-js, cucumber-ruby
    """
    
    def parse_file(self, json_path: str) -> List[CucumberScenario]:
        """
        Parse Cucumber JSON report file.
        
        Args:
            json_path: Path to cucumber.json file
            
        Returns:
            List of CucumberScenario objects
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return self.parse_json(data)
        except Exception as e:
            logger.error(f"Failed to parse Cucumber JSON: {e}")
            return []
    
    def parse_json(self, data: List[Dict[str, Any]]) -> List[CucumberScenario]:
        """
        Parse Cucumber JSON data structure.
        
        Args:
            data: Parsed JSON data (list of features)
            
        Returns:
            List of CucumberScenario objects
        """
        scenarios = []
        
        for feature in data:
            feature_name = feature.get('name', 'Unknown Feature')
            feature_tags = self._extract_tags(feature.get('tags', []))
            
            # Parse scenarios and scenario outlines
            for element in feature.get('elements', []):
                element_type = element.get('type', '')
                
                if element_type in ['scenario', 'scenario_outline']:
                    scenario = self._parse_scenario(element, feature_name, feature_tags)
                    if scenario:
                        scenarios.append(scenario)
        
        return scenarios
    
    def _parse_scenario(
        self, 
        element: Dict[str, Any], 
        feature_name: str,
        feature_tags: List[str]
    ) -> Optional[CucumberScenario]:
        """Parse a single scenario or scenario outline"""
        try:
            scenario_name = element.get('name', 'Unknown Scenario')
            scenario_tags = feature_tags + self._extract_tags(element.get('tags', []))
            
            # Parse steps
            steps = []
            total_duration_ns = 0
            scenario_status = "passed"
            
            for step_data in element.get('steps', []):
                step = self._parse_step(step_data)
                if step:
                    steps.append(step)
                    total_duration_ns += step_data.get('result', {}).get('duration', 0)
                    
                    # Determine scenario status
                    if step.status == "failed":
                        scenario_status = "failed"
                    elif step.status == "skipped" and scenario_status == "passed":
                        scenario_status = "skipped"
            
            # Convert nanoseconds to milliseconds
            duration_ms = total_duration_ns // 1_000_000
            
            return CucumberScenario(
                name=scenario_name,
                feature_name=feature_name,
                tags=scenario_tags,
                steps=steps,
                status=scenario_status,
                duration_ms=duration_ms,
                line_number=element.get('line'),
                description=element.get('description', '').strip()
            )
        
        except Exception as e:
            logger.error(f"Failed to parse scenario: {e}")
            return None
    
    def _parse_step(self, step_data: Dict[str, Any]) -> Optional[CucumberStep]:
        """Parse a single step"""
        try:
            keyword = step_data.get('keyword', '').strip()
            text = step_data.get('name', '')
            
            result = step_data.get('result', {})
            status = result.get('status', 'skipped')
            duration_ns = result.get('duration', 0)
            duration_ms = duration_ns // 1_000_000
            
            error_message = result.get('error_message')
            
            # Extract stacktrace if available
            stacktrace = None
            if error_message and '\n' in error_message:
                # Full stacktrace in error_message
                stacktrace = error_message
                # Keep first line as error message
                error_message = error_message.split('\n')[0]
            
            return CucumberStep(
                keyword=keyword,
                text=text,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
                stacktrace=stacktrace,
            )
        
        except Exception as e:
            logger.error(f"Failed to parse step: {e}")
            return None
    
    def _extract_tags(self, tags: List[Dict[str, Any]]) -> List[str]:
        """Extract tag names from tag objects"""
        return [tag.get('name', '').lstrip('@') for tag in tags if tag.get('name')]


class FeatureFileParser:
    """
    Parses Gherkin feature files.
    
    Extracts structure without execution results.
    Useful for:
    - Impact analysis
    - Coverage mapping
    - Test inventory
    """
    
    def parse_file(self, feature_path: str) -> Dict[str, Any]:
        """
        Parse a .feature file.
        
        Args:
            feature_path: Path to .feature file
            
        Returns:
            Dictionary with feature structure
        """
        try:
            with open(feature_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.parse_content(content, feature_path)
        except Exception as e:
            logger.error(f"Failed to parse feature file: {e}")
            return {}
    
    def parse_content(self, content: str, file_path: str = "") -> Dict[str, Any]:
        """
        Parse Gherkin content.
        
        Args:
            content: Feature file content
            file_path: Optional file path for metadata
            
        Returns:
            Dictionary with feature structure
        """
        lines = content.split('\n')
        
        feature = {
            'file_path': file_path,
            'name': '',
            'description': [],
            'tags': [],
            'scenarios': [],
            'background': None,
        }
        
        current_section = None
        current_scenario = None
        current_step_list = None
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
            
            # Tags
            if stripped.startswith('@'):
                tags = re.findall(r'@(\w+)', stripped)
                if current_scenario:
                    current_scenario['tags'].extend(tags)
                else:
                    feature['tags'].extend(tags)
                continue
            
            # Feature
            if stripped.startswith('Feature:'):
                feature['name'] = stripped[8:].strip()
                current_section = 'feature_description'
                continue
            
            # Background
            if stripped.startswith('Background:'):
                feature['background'] = {
                    'name': stripped[11:].strip(),
                    'steps': [],
                    'line': line_num,
                }
                current_step_list = feature['background']['steps']
                current_section = 'background'
                continue
            
            # Scenario
            if stripped.startswith('Scenario:') or stripped.startswith('Scenario Outline:'):
                if stripped.startswith('Scenario Outline:'):
                    scenario_name = stripped[17:].strip()
                    scenario_type = 'scenario_outline'
                else:
                    scenario_name = stripped[9:].strip()
                    scenario_type = 'scenario'
                
                current_scenario = {
                    'name': scenario_name,
                    'type': scenario_type,
                    'tags': [],
                    'steps': [],
                    'examples': [],
                    'line': line_num,
                }
                feature['scenarios'].append(current_scenario)
                current_step_list = current_scenario['steps']
                current_section = 'scenario'
                continue
            
            # Examples (for Scenario Outline)
            if stripped.startswith('Examples:'):
                current_section = 'examples'
                continue
            
            # Steps
            step_match = re.match(r'^(Given|When|Then|And|But)\s+(.+)$', stripped)
            if step_match and current_step_list is not None:
                keyword, text = step_match.groups()
                current_step_list.append({
                    'keyword': keyword,
                    'text': text,
                    'line': line_num,
                })
                continue
            
            # Feature description
            if current_section == 'feature_description':
                feature['description'].append(stripped)
        
        return feature


def resolve_step_binding(
    step_text: str,
    step_bindings: List['StepBinding']
) -> Optional['StepBinding']:
    """
    Resolve step text to step definition binding.
    
    Args:
        step_text: Natural language step text
        step_bindings: List of StepBinding objects
        
    Returns:
        Matching StepBinding or None
    """
    for binding in step_bindings:
        if binding.matches(step_text):
            return binding
    
    return None


def cucumber_to_signals(
    scenarios: List[CucumberScenario],
    run_id: Optional[str] = None,
    include_steps: bool = True
) -> List[ExecutionSignal]:
    """
    Convert Cucumber scenarios to canonical ExecutionSignal format.
    
    Args:
        scenarios: List of CucumberScenario objects
        run_id: Optional run identifier
        include_steps: Whether to include step-level signals
        
    Returns:
        List of ExecutionSignal objects
    """
    signals = []
    
    for scenario in scenarios:
        # Add scenario-level signal
        signals.append(scenario.to_signal(run_id))
        
        # Add step-level signals
        if include_steps:
            for step in scenario.steps:
                signals.append(step.to_signal(scenario.name, run_id))
    
    return signals


# Example usage
if __name__ == "__main__":
    # Parse Cucumber JSON
    parser = CucumberJSONParser()
    scenarios = parser.parse_file("cucumber.json")
    
    print(f"Parsed {len(scenarios)} scenarios")
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario.name}")
        print(f"  Feature: {scenario.feature_name}")
        print(f"  Status: {scenario.status}")
        print(f"  Duration: {scenario.duration_ms}ms")
        print(f"  Steps: {len(scenario.steps)}")
        
        for step in scenario.steps:
            status_icon = "✓" if step.status == "passed" else "✗"
            print(f"    {status_icon} {step.keyword} {step.text} ({step.duration_ms}ms)")
    
    # Convert to canonical signals
    signals = cucumber_to_signals(scenarios)
    print(f"\nGenerated {len(signals)} execution signals")
