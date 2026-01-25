"""
SpecFlow+ ecosystem handler.

Handles SpecFlow+ Runner, LivingDoc, and Excel integration.
"""

from typing import List, Dict, Optional
from pathlib import Path
import json
import xml.etree.ElementTree as ET


class SpecFlowPlusHandler:
    """Handle SpecFlow+ ecosystem features."""
    
    def __init__(self):
        """Initialize the handler."""
        pass
    
    def detect_specflow_plus(self, project_path: Path) -> Dict:
        """
        Detect SpecFlow+ usage in project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Detection dictionary
        """
        detection = {
            'has_specflow_plus': False,
            'has_specflow_plus_runner': False,
            'has_living_doc': False,
            'has_excel_integration': False,
            'runner_config': None,
            'living_doc_config': None,
        }
        
        # Check for SpecFlow+ Runner
        runner_config = project_path / "specflow.json"
        if runner_config.exists():
            try:
                config = json.loads(runner_config.read_text())
                if 'specFlowPlus' in config or 'runner' in config:
                    detection['has_specflow_plus'] = True
                    detection['has_specflow_plus_runner'] = True
                    detection['runner_config'] = config
            except:
                pass
        
        # Check for LivingDoc
        csproj_files = list(project_path.rglob("*.csproj"))
        for csproj in csproj_files:
            try:
                tree = ET.parse(csproj)
                root = tree.getroot()
                for package_ref in root.findall(".//PackageReference"):
                    include = package_ref.get('Include', '')
                    if 'SpecFlow.Plus.LivingDoc' in include:
                        detection['has_living_doc'] = True
                    if 'SpecFlow.Plus.Excel' in include:
                        detection['has_excel_integration'] = True
            except:
                pass
        
        return detection
    
    def extract_runner_configuration(self, config_file: Path) -> Dict:
        """
        Extract SpecFlow+ Runner configuration.
        
        Args:
            config_file: Path to specflow.json or app.config
            
        Returns:
            Configuration dictionary
        """
        if not config_file.exists():
            return {}
        
        try:
            if config_file.suffix == '.json':
                config = json.loads(config_file.read_text())
                
                # Check both 'runner' and 'specFlowPlus' sections
                runner_section = config.get('runner', config.get('specFlowPlus', {}))
                
                return {
                    'file': str(config_file),
                    'parallel_execution': runner_section.get('parallelExecution', False),
                    'max_threads': runner_section.get('maxThreads'),
                    'execution_timeout': runner_section.get('executionTimeout'),
                    'retry_count': runner_section.get('retryCount', 0),
                    'filter_tags': runner_section.get('filter', {}).get('tags', []),
                }
        except:
            pass
        
        return {}
    
    def extract_living_doc_metadata(self, project_path: Path) -> Dict:
        """
        Extract LivingDoc metadata from feature files.
        
        Args:
            project_path: Project root path
            
        Returns:
            Metadata dictionary
        """
        feature_files = list(project_path.rglob("*.feature"))
        
        metadata = {
            'total_features': len(feature_files),
            'features_with_description': 0,
            'total_scenarios': 0,
            'tags_used': set(),
        }
        
        for feature_file in feature_files:
            try:
                content = feature_file.read_text(encoding='utf-8')
                
                # Check for feature description
                if 'Feature:' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith('Feature:'):
                            # Check if next lines have description
                            if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('@'):
                                metadata['features_with_description'] += 1
                            break
                
                # Count scenarios
                metadata['total_scenarios'] += content.count('Scenario:')
                metadata['total_scenarios'] += content.count('Scenario Outline:')
                
                # Extract tags
                import re
                tags = re.findall(r'@(\w+)', content)
                metadata['tags_used'].update(tags)
                
            except:
                pass
        
        metadata['tags_used'] = sorted(metadata['tags_used'])
        
        return metadata
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze SpecFlow+ usage in project.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        detection = self.detect_specflow_plus(project_path)
        
        runner_config = {}
        if detection['has_specflow_plus_runner']:
            config_file = project_path / "specflow.json"
            if config_file.exists():
                runner_config = self.extract_runner_configuration(config_file)
        
        living_doc_metadata = {}
        if detection['has_living_doc']:
            living_doc_metadata = self.extract_living_doc_metadata(project_path)
        
        return {
            **detection,
            'runner_configuration': runner_config,
            'living_doc_metadata': living_doc_metadata,
        }
    
    def generate_pytest_equivalent_config(self, runner_config: Dict) -> str:
        """
        Generate pytest configuration equivalent to SpecFlow+ Runner.
        
        Args:
            runner_config: Runner configuration dictionary
            
        Returns:
            pytest.ini content
        """
        lines = []
        lines.append("[pytest]")
        lines.append("testpaths = tests")
        lines.append("python_files = test_*.py")
        lines.append("python_classes = Test*")
        lines.append("python_functions = test_*")
        lines.append("")
        
        # Parallel execution
        if runner_config.get('parallel_execution'):
            lines.append("# Parallel execution (use pytest-xdist)")
            lines.append("addopts = -n auto")
            lines.append("")
        
        # Timeout
        if runner_config.get('execution_timeout'):
            lines.append("# Execution timeout (use pytest-timeout)")
            timeout = runner_config['execution_timeout']
            lines.append(f"timeout = {timeout}")
            lines.append("")
        
        # Retry
        if runner_config.get('retry_count'):
            lines.append("# Retry on failure (use pytest-rerunfailures)")
            retry = runner_config['retry_count']
            lines.append(f"addopts = --reruns {retry}")
            lines.append("")
        
        # Tag filtering
        if runner_config.get('filter_tags'):
            lines.append("# Tag filtering")
            tags = runner_config['filter_tags']
            lines.append(f"markers =")
            for tag in tags:
                lines.append(f"    {tag}: {tag} tests")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for SpecFlow+ usage.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# SpecFlow+ Ecosystem Usage\n")
        
        lines.append("## Detection\n")
        lines.append(f"- SpecFlow+ Runner: {'✅ Yes' if analysis['has_specflow_plus_runner'] else '❌ No'}")
        lines.append(f"- LivingDoc: {'✅ Yes' if analysis['has_living_doc'] else '❌ No'}")
        lines.append(f"- Excel Integration: {'✅ Yes' if analysis['has_excel_integration'] else '❌ No'}\n")
        
        if analysis['runner_configuration']:
            lines.append("## Runner Configuration\n")
            config = analysis['runner_configuration']
            if config.get('parallel_execution'):
                lines.append("- Parallel execution: ✅ Enabled")
            if config.get('execution_timeout'):
                lines.append(f"- Execution timeout: {config['execution_timeout']}")
            if config.get('retry_count'):
                lines.append(f"- Retry count: {config['retry_count']}")
            lines.append("")
        
        if analysis['living_doc_metadata']:
            lines.append("## LivingDoc Metadata\n")
            meta = analysis['living_doc_metadata']
            lines.append(f"- Total features: {meta['total_features']}")
            lines.append(f"- Features with descriptions: {meta['features_with_description']}")
            lines.append(f"- Total scenarios: {meta['total_scenarios']}")
            lines.append(f"- Tags used: {len(meta['tags_used'])}")
        
        return '\n'.join(lines)
