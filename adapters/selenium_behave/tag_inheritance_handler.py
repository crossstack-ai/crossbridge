"""
Tag inheritance handler for Behave.

Handles tag inheritance from Feature to Scenario and complex tag combinations.
"""

from typing import List, Dict, Optional, Set
from pathlib import Path
import re


class TagInheritanceHandler:
    """Handle Behave tag inheritance and combinations."""
    
    def __init__(self):
        """Initialize the tag inheritance handler."""
        self.tag_pattern = re.compile(r'@(\w+(?:\.\w+)*)')
        
    def extract_feature_tags(self, feature_file: Path) -> List[str]:
        """
        Extract tags from feature file.
        
        Args:
            feature_file: Path to feature file
            
        Returns:
            List of tags
        """
        if not feature_file.exists():
            return []
        
        try:
            feature_content = feature_file.read_text(encoding='utf-8')
        except Exception:
            return []
        
        lines = feature_content.split('\n')
        feature_tags = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('Feature:'):
                # Look backwards for tags
                j = i - 1
                while j >= 0 and (lines[j].strip().startswith('@') or lines[j].strip() == ''):
                    if lines[j].strip().startswith('@'):
                        tags = self.tag_pattern.findall(lines[j])
                        feature_tags.extend(tags)
                    j -= 1
                break
        
        return feature_tags
    
    def extract_scenario_tags(self, feature_content: str) -> Dict[str, List[str]]:
        """
        Extract tags for each scenario.
        
        Args:
            feature_content: Feature file content
            
        Returns:
            Dictionary mapping scenario names to their tags
        """
        lines = feature_content.split('\n')
        scenarios = {}
        
        for i, line in enumerate(lines):
            if line.strip().startswith('Scenario:') or line.strip().startswith('Scenario Outline:'):
                scenario_name = line.strip().split(':', 1)[1].strip()
                scenario_tags = []
                
                # Look backwards for tags
                j = i - 1
                while j >= 0 and (lines[j].strip().startswith('@') or lines[j].strip() == ''):
                    if lines[j].strip().startswith('@'):
                        tags = self.tag_pattern.findall(lines[j])
                        scenario_tags.extend(tags)
                    j -= 1
                
                scenarios[scenario_name] = scenario_tags
        
        return scenarios
    
    def compute_inherited_tags(self, feature_content: str) -> Dict[str, Set[str]]:
        """
        Compute all tags for each scenario (including inherited).
        
        Args:
            feature_content: Feature file content
            
        Returns:
            Dictionary mapping scenario names to all their tags (inherited + direct)
        """
        feature_tags = set(self.extract_feature_tags(feature_content))
        scenario_tags = self.extract_scenario_tags(feature_content)
        
        inherited = {}
        for scenario, tags in scenario_tags.items():
            # Combine feature tags and scenario tags
            all_tags = feature_tags.union(set(tags))
            inherited[scenario] = all_tags
        
        return inherited
    
    def analyze_tag_usage(self, project_path: Path) -> Dict:
        """
        Analyze tag usage across all feature files.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        feature_files = list(project_path.rglob("*.feature"))
        
        all_tags = set()
        tag_counts = {}
        feature_level_tags = set()
        scenario_level_tags = set()
        
        for feature_file in feature_files:
            try:
                content = feature_file.read_text(encoding='utf-8')
            except Exception:
                continue
            
            # Feature tags
            f_tags = self.extract_feature_tags(content)
            feature_level_tags.update(f_tags)
            
            # Scenario tags
            s_tags = self.extract_scenario_tags(content)
            for tags in s_tags.values():
                scenario_level_tags.update(tags)
            
            # All tags
            all_tags.update(f_tags)
            for tags in s_tags.values():
                all_tags.update(tags)
            
            # Count occurrences
            for tag in f_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            for tags in s_tags.values():
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            'total_tags': len(all_tags),
            'feature_level_tags': sorted(feature_level_tags),
            'scenario_level_tags': sorted(scenario_level_tags),
            'tag_counts': tag_counts,
            'most_common_tags': sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        }
    
    def generate_pytest_markers(self, tags: Set[str]) -> str:
        """
        Generate pytest markers from Behave tags.
        
        Args:
            tags: Set of tags
            
        Returns:
            Python code with pytest markers
        """
        lines = []
        lines.append("import pytest")
        lines.append("")
        
        for tag in sorted(tags):
            # Convert behave tag to pytest marker
            marker_name = tag.replace('.', '_').replace('-', '_')
            lines.append(f"# Behave tag: @{tag}")
            lines.append(f"@pytest.mark.{marker_name}")
        
        return '\n'.join(lines)
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze tag usage across project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        feature_files = list(project_path.rglob("*.feature"))
        
        total_scenarios = 0
        all_tags = set()
        
        for feature_file in feature_files:
            try:
                content = feature_file.read_text(encoding='utf-8')
                # Count scenarios
                total_scenarios += content.count('Scenario:')
                # Extract tags
                tags = self.tag_pattern.findall(content)
                all_tags.update(tags)
            except Exception as e:
                # Skip files that can't be read (permissions, encoding issues)
                continue
        
        return {
            'total_scenarios': total_scenarios,
            'unique_tags': len(all_tags),
            'tags': sorted(all_tags),
        }
    
    def generate_tag_report(self, analysis: Dict) -> str:
        """
        Generate tag usage report.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown report
        """
        lines = []
        lines.append("# Behave Tag Usage Report\n")
        
        lines.append(f"## Summary\n")
        lines.append(f"- Total unique tags: {analysis['total_tags']}")
        lines.append(f"- Feature-level tags: {len(analysis['feature_level_tags'])}")
        lines.append(f"- Scenario-level tags: {len(analysis['scenario_level_tags'])}\n")
        
        lines.append("## Most Common Tags\n")
        for tag, count in analysis['most_common_tags']:
            lines.append(f"- @{tag}: {count} occurrences")
        
        return '\n'.join(lines)
