"""
Custom annotation extraction for Selenium Java tests.

Handles @Screenshot, @Retry, @Flaky, and other custom test annotations.
"""

import re
from typing import List, Dict, Optional, Set
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CustomAnnotation:
    """Represents a custom annotation on a test method or class."""
    name: str
    parameters: Dict[str, any]
    target: str  # 'class' or 'method'
    target_name: str


class JavaCustomAnnotationExtractor:
    """Extract custom annotations from Java test files."""
    
    def __init__(self):
        # Common custom annotation patterns
        self.annotation_patterns = {
            'Screenshot': re.compile(
                r'@Screenshot\s*(?:\(\s*([^)]*)\s*\))?',
                re.MULTILINE
            ),
            'Retry': re.compile(
                r'@Retry\s*(?:\(\s*([^)]*)\s*\))?',
                re.MULTILINE
            ),
            'Flaky': re.compile(
                r'@Flaky\s*(?:\(\s*([^)]*)\s*\))?',
                re.MULTILINE
            ),
            'DataFile': re.compile(
                r'@DataFile\s*\(\s*"([^"]+)"\s*\)',
                re.MULTILINE
            ),
            'Description': re.compile(
                r'@Description\s*\(\s*"([^"]+)"\s*\)',
                re.MULTILINE
            ),
            'Issue': re.compile(
                r'@Issue\s*\(\s*"([^"]+)"\s*\)',
                re.MULTILINE
            ),
            'Story': re.compile(
                r'@Story\s*\(\s*"([^"]+)"\s*\)',
                re.MULTILINE
            ),
            'Feature': re.compile(
                r'@Feature\s*\(\s*"([^"]+)"\s*\)',
                re.MULTILINE
            ),
            'Owner': re.compile(
                r'@Owner\s*\(\s*"([^"]+)"\s*\)',
                re.MULTILINE
            ),
            'Severity': re.compile(
                r'@Severity\s*\(\s*(\w+)\s*\)',
                re.MULTILINE
            ),
        }
        
        # Pattern to extract method/class context
        self.method_pattern = re.compile(
            r'(?:public|private|protected)?\s+(?:static\s+)?(?:void|\w+)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+(?:\s*,\s*\w+)*)?\s*\{',
            re.MULTILINE
        )
        self.class_pattern = re.compile(
            r'(?:public|private|protected)?\s+(?:static\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)',
            re.MULTILINE
        )
    
    def extract_annotations(
        self, 
        java_file: Path
    ) -> List[CustomAnnotation]:
        """
        Extract all custom annotations from a Java file.
        
        Args:
            java_file: Path to Java test file
            
        Returns:
            List of CustomAnnotation objects
        """
        if not java_file.exists():
            return []
        
        content = java_file.read_text(encoding='utf-8')
        annotations = []
        
        # Split content into class and method sections
        class_matches = list(self.class_pattern.finditer(content))
        method_matches = list(self.method_pattern.finditer(content))
        
        for annotation_name, pattern in self.annotation_patterns.items():
            for match in pattern.finditer(content):
                # Determine if annotation is on class or method
                annotation_pos = match.start()
                target_type, target_name = self._find_target(
                    annotation_pos,
                    class_matches,
                    method_matches,
                    content
                )
                
                # Parse annotation parameters
                params = self._parse_annotation_params(
                    match.group(1) if match.lastindex else None,
                    annotation_name
                )
                
                annotations.append(CustomAnnotation(
                    name=annotation_name,
                    parameters=params,
                    target=target_type,
                    target_name=target_name
                ))
        
        return annotations
    
    def _find_target(
        self,
        annotation_pos: int,
        class_matches: List,
        method_matches: List,
        content: str
    ) -> tuple:
        """Find the class or method that an annotation targets."""
        # Find the closest method or class after the annotation
        closest_method = None
        for method_match in method_matches:
            if method_match.start() > annotation_pos:
                closest_method = method_match
                break
        
        closest_class = None
        for class_match in class_matches:
            if class_match.start() > annotation_pos:
                closest_class = class_match
                break
        
        # Determine which is closer
        if closest_method and closest_class:
            if closest_method.start() < closest_class.start():
                return 'method', closest_method.group(1)
            else:
                return 'class', closest_class.group(1)
        elif closest_method:
            return 'method', closest_method.group(1)
        elif closest_class:
            return 'class', closest_class.group(1)
        else:
            return 'unknown', 'unknown'
    
    def _parse_annotation_params(
        self,
        params_str: Optional[str],
        annotation_name: str
    ) -> Dict[str, any]:
        """Parse annotation parameters from string."""
        if not params_str:
            return {}
        
        params = {}
        
        # Handle common parameter formats
        if annotation_name == 'Screenshot':
            # @Screenshot(onFailure=true, format="PNG")
            if 'onFailure' in params_str:
                params['on_failure'] = 'true' in params_str.lower()
            if 'format' in params_str:
                format_match = re.search(r'format\s*=\s*"([^"]+)"', params_str)
                if format_match:
                    params['format'] = format_match.group(1)
        
        elif annotation_name == 'Retry':
            # @Retry(maxAttempts=3, delay=1000)
            max_match = re.search(r'maxAttempts\s*=\s*(\d+)', params_str)
            if max_match:
                params['max_attempts'] = int(max_match.group(1))
            delay_match = re.search(r'delay\s*=\s*(\d+)', params_str)
            if delay_match:
                params['delay'] = int(delay_match.group(1))
        
        elif annotation_name in ('Description', 'DataFile', 'Issue', 'Story', 'Feature', 'Owner'):
            # Simple string value
            params['value'] = params_str.strip('"')
        
        elif annotation_name == 'Severity':
            params['level'] = params_str.strip()
        
        return params
    
    def get_annotations_by_target(
        self,
        annotations: List[CustomAnnotation],
        target_type: str
    ) -> List[CustomAnnotation]:
        """Filter annotations by target type (class or method)."""
        return [a for a in annotations if a.target == target_type]
    
    def has_annotation(
        self,
        annotations: List[CustomAnnotation],
        annotation_name: str
    ) -> bool:
        """Check if a specific annotation is present."""
        return any(a.name == annotation_name for a in annotations)
    
    def get_annotated_methods(
        self,
        java_file: Path,
        annotation_name: str
    ) -> List[str]:
        """
        Get all method names annotated with a specific annotation.
        
        Args:
            java_file: Path to Java file
            annotation_name: Name of annotation to search for
            
        Returns:
            List of method names
        """
        annotations = self.extract_annotations(java_file)
        return [
            a.target_name 
            for a in annotations 
            if a.name == annotation_name and a.target == 'method'
        ]
