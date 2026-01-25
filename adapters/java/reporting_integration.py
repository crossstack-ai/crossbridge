"""
Allure and ExtentReports integration extractor for Java tests.

Handles test reporting frameworks commonly used with TestNG and JUnit.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class ReportingIntegrationExtractor:
    """Extract reporting integration patterns from Java test code."""
    
    def __init__(self):
        """Initialize the reporting extractor."""
        self.allure_patterns = {
            'test_annotation': re.compile(r'@Test.*?@(?:Description|Epic|Feature|Story|Severity)\("([^"]+)"\)', re.DOTALL),
            'step': re.compile(r'@Step\("([^"]+)"\)'),
            'attachment': re.compile(r'Allure\.addAttachment\("([^"]+)",\s*([^)]+)\)'),
            'link': re.compile(r'@Link\(name\s*=\s*"([^"]+)",\s*url\s*=\s*"([^"]+)"\)'),
            'issue': re.compile(r'@Issue\("([^"]+)"\)'),
            'tms_link': re.compile(r'@TmsLink\("([^"]+)"\)'),
        }
        
        self.extent_patterns = {
            'test_annotation': re.compile(r'@Test.*?extent\.createTest\("([^"]+)"', re.DOTALL),
            'log': re.compile(r'test\.log\(Status\.(\w+),\s*"([^"]+)"\)'),
            'screenshot': re.compile(r'test\.addScreenCaptureFromPath\("([^"]+)"\)'),
            'category': re.compile(r'test\.assignCategory\("([^"]+)"\)'),
            'author': re.compile(r'test\.assignAuthor\("([^"]+)"\)'),
        }
    
    def detect_reporting_framework(self, file_path: Path) -> Optional[str]:
        """
        Detect which reporting framework is being used.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            'allure', 'extent', or None
        """
        if not file_path.exists():
            return None
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        has_allure = any([
            'io.qameta.allure' in content,
            '@Step' in content,
            'Allure.addAttachment' in content,
            '@Epic' in content,
            '@Feature' in content,
        ])
        
        has_extent = any([
            'com.aventstack.extentreports' in content,
            'ExtentReports' in content,
            'ExtentTest' in content,
            'extent.createTest' in content,
        ])
        
        if has_allure:
            return 'allure'
        elif has_extent:
            return 'extent'
        return None
    
    def extract_allure_annotations(self, file_path: Path) -> List[Dict]:
        """
        Extract Allure annotations and metadata.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of Allure annotation dictionaries
        """
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        annotations = []
        
        # Extract @Description, @Epic, @Feature, @Story
        annotation_types = ['Description', 'Epic', 'Feature', 'Story', 'Severity']
        for ann_type in annotation_types:
            pattern = re.compile(rf'@{ann_type}\("([^"]+)"\)')
            for match in pattern.finditer(content):
                annotations.append({
                    'type': ann_type,
                    'value': match.group(1),
                    'line': content[:match.start()].count('\n') + 1,
                })
        
        # Extract @Step methods
        step_pattern = re.compile(r'@Step\("([^"]+)"\)\s+(?:public|private)?\s*\w+\s+(\w+)\(')
        for match in step_pattern.finditer(content):
            annotations.append({
                'type': 'Step',
                'description': match.group(1),
                'method': match.group(2),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        # Extract @Link annotations
        for match in self.allure_patterns['link'].finditer(content):
            annotations.append({
                'type': 'Link',
                'name': match.group(1),
                'url': match.group(2),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        # Extract @Issue and @TmsLink
        for match in self.allure_patterns['issue'].finditer(content):
            annotations.append({
                'type': 'Issue',
                'value': match.group(1),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        for match in self.allure_patterns['tms_link'].finditer(content):
            annotations.append({
                'type': 'TmsLink',
                'value': match.group(1),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        return annotations
    
    def extract_allure_attachments(self, file_path: Path) -> List[Dict]:
        """
        Extract Allure attachment calls.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            List of attachment dictionaries
        """
        if not file_path.exists():
            return []
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        attachments = []
        
        for match in self.allure_patterns['attachment'].finditer(content):
            attachments.append({
                'name': match.group(1),
                'content': match.group(2),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        return attachments
    
    def extract_extent_reports(self, file_path: Path) -> Dict:
        """
        Extract ExtentReports configuration and usage.
        
        Args:
            file_path: Path to Java file
            
        Returns:
            ExtentReports information dictionary
        """
        if not file_path.exists():
            return {}
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        result = {
            'tests': [],
            'logs': [],
            'screenshots': [],
            'categories': [],
            'authors': [],
        }
        
        # Extract test creation
        test_pattern = re.compile(r'extent\.createTest\("([^"]+)"(?:,\s*"([^"]+)")?\)')
        for match in test_pattern.finditer(content):
            result['tests'].append({
                'name': match.group(1),
                'description': match.group(2) if match.group(2) else None,
                'line': content[:match.start()].count('\n') + 1,
            })
        
        # Extract log statements
        for match in self.extent_patterns['log'].finditer(content):
            result['logs'].append({
                'status': match.group(1),
                'message': match.group(2),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        # Extract screenshots
        for match in self.extent_patterns['screenshot'].finditer(content):
            result['screenshots'].append({
                'path': match.group(1),
                'line': content[:match.start()].count('\n') + 1,
            })
        
        # Extract categories
        for match in self.extent_patterns['category'].finditer(content):
            result['categories'].append(match.group(1))
        
        # Extract authors
        for match in self.extent_patterns['author'].finditer(content):
            result['authors'].append(match.group(1))
        
        return result
    
    def extract_all_reporting(self, project_path: Path) -> Dict:
        """
        Extract all reporting information from a project.
        
        Args:
            project_path: Root path of Java project
            
        Returns:
            Dictionary with all reporting information
        """
        java_files = list(project_path.rglob("*.java"))
        
        result = {
            'allure': {
                'annotations': [],
                'attachments': [],
                'files': [],
            },
            'extent': {
                'reports': [],
                'files': [],
            },
            'files_analyzed': len(java_files),
        }
        
        for java_file in java_files:
            framework = self.detect_reporting_framework(java_file)
            
            if framework == 'allure':
                annotations = self.extract_allure_annotations(java_file)
                attachments = self.extract_allure_attachments(java_file)
                
                if annotations or attachments:
                    result['allure']['annotations'].extend(annotations)
                    result['allure']['attachments'].extend(attachments)
                    result['allure']['files'].append(str(java_file))
            
            elif framework == 'extent':
                report_info = self.extract_extent_reports(java_file)
                
                if report_info.get('tests'):
                    result['extent']['reports'].append({
                        'file': str(java_file),
                        'info': report_info,
                    })
                    result['extent']['files'].append(str(java_file))
        
        return result
    
    def convert_to_pytest_reporting(self, reporting_info: Dict) -> str:
        """
        Convert Java reporting to pytest-allure format.
        
        Args:
            reporting_info: Reporting information dictionary
            
        Returns:
            Python pytest code with allure decorators
        """
        code_lines = []
        code_lines.append("import allure")
        code_lines.append("import pytest\n")
        
        # Convert Allure annotations to pytest decorators
        for annotation in reporting_info.get('allure', {}).get('annotations', []):
            ann_type = annotation['type']
            value = annotation['value']
            
            if ann_type == 'Epic':
                code_lines.append(f'@allure.epic("{value}")')
            elif ann_type == 'Feature':
                code_lines.append(f'@allure.feature("{value}")')
            elif ann_type == 'Story':
                code_lines.append(f'@allure.story("{value}")')
            elif ann_type == 'Severity':
                code_lines.append(f'@allure.severity(allure.severity_level.{value})')
            elif ann_type == 'Step':
                code_lines.append(f'@allure.step("{annotation["description"]}")')
                code_lines.append(f'def {annotation.get("method", "step_method")}():')
                code_lines.append('    pass\n')
        
        return '\n'.join(code_lines)
    
    def generate_allure_config(self, reporting_info: Dict) -> str:
        """
        Generate allure configuration YAML.
        
        Args:
            reporting_info: Reporting information dictionary
            
        Returns:
            YAML configuration string
        """
        config = []
        config.append("# Allure configuration")
        config.append("allure:")
        config.append("  results_directory: allure-results")
        config.append("  report_directory: allure-report")
        
        # Extract unique categories
        categories = set()
        for report in reporting_info.get('extent', {}).get('reports', []):
            categories.update(report.get('info', {}).get('categories', []))
        
        if categories:
            config.append("  categories:")
            for category in sorted(categories):
                config.append(f"    - {category}")
        
        return '\n'.join(config)
    
    def get_reporting_statistics(self, reporting_info: Dict) -> Dict:
        """
        Get statistics about reporting usage.
        
        Args:
            reporting_info: Reporting information dictionary
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'allure': {
                'total_annotations': len(reporting_info.get('allure', {}).get('annotations', [])),
                'total_attachments': len(reporting_info.get('allure', {}).get('attachments', [])),
                'files_with_allure': len(reporting_info.get('allure', {}).get('files', [])),
            },
            'extent': {
                'total_reports': len(reporting_info.get('extent', {}).get('reports', [])),
                'files_with_extent': len(reporting_info.get('extent', {}).get('files', [])),
            },
            'total_files_analyzed': reporting_info.get('files_analyzed', 0),
        }
        
        # Count annotation types
        annotation_counts = {}
        for annotation in reporting_info.get('allure', {}).get('annotations', []):
            ann_type = annotation['type']
            annotation_counts[ann_type] = annotation_counts.get(ann_type, 0) + 1
        
        stats['allure']['annotation_breakdown'] = annotation_counts
        
        return stats
