"""
Background step extraction for Behave feature files.

Handles feature-level Background sections that run before each scenario.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class BehaveBackgroundExtractor:
    """Extract Background steps from Behave feature files."""
    
    def __init__(self):
        self.background_pattern = re.compile(
            r'^\s*Background:\s*$',
            re.MULTILINE | re.IGNORECASE
        )
        self.step_pattern = re.compile(
            r'^\s*(Given|When|Then|And|But)\s+(.+)$',
            re.MULTILINE | re.IGNORECASE
        )
    
    def extract_background(self, feature_file: Path) -> Optional[Dict[str, any]]:
        """
        Extract background steps from a feature file.
        
        Args:
            feature_file: Path to .feature file
            
        Returns:
            Dictionary with background steps or None if no background
        """
        if not feature_file.exists():
            return None
        
        content = feature_file.read_text(encoding='utf-8')
        
        # Find Background section
        background_match = self.background_pattern.search(content)
        if not background_match:
            return None
        
        # Extract steps until next section (Scenario, Rule, etc.)
        start_pos = background_match.end()
        section_end = re.search(
            r'^\s*(Scenario|Scenario Outline|Rule|Feature):\s*',
            content[start_pos:],
            re.MULTILINE | re.IGNORECASE
        )
        
        if section_end:
            background_content = content[start_pos:start_pos + section_end.start()]
        else:
            background_content = content[start_pos:]
        
        # Extract individual steps
        steps = []
        for match in self.step_pattern.finditer(background_content):
            keyword = match.group(1)
            text = match.group(2).strip()
            
            steps.append({
                'keyword': keyword,
                'text': text,
                'line': content[:match.start()].count('\n') + 1
            })
        
        if not steps:
            return None
        
        return {
            'steps': steps,
            'line_start': content[:background_match.start()].count('\n') + 1,
            'line_end': content[:start_pos + len(background_content)].count('\n') + 1
        }
    
    def extract_from_multiple_features(
        self, 
        features_dir: Path
    ) -> Dict[str, Optional[Dict]]:
        """
        Extract backgrounds from all feature files in a directory.
        
        Args:
            features_dir: Directory containing .feature files
            
        Returns:
            Dictionary mapping feature file paths to background data
        """
        backgrounds = {}
        
        if not features_dir.exists():
            return backgrounds
        
        for feature_file in features_dir.rglob("*.feature"):
            background = self.extract_background(feature_file)
            if background:
                backgrounds[str(feature_file)] = background
        
        return backgrounds
    
    def has_background(self, feature_file: Path) -> bool:
        """
        Check if a feature file has a Background section.
        
        Args:
            feature_file: Path to .feature file
            
        Returns:
            True if background exists, False otherwise
        """
        if not feature_file.exists():
            return False
        
        content = feature_file.read_text(encoding='utf-8')
        return bool(self.background_pattern.search(content))
