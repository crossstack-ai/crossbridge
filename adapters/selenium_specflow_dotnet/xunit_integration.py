"""
xUnit test framework integration for .NET SpecFlow projects.

Handles xUnit-specific features, assertions, and execution.
"""

import re
import subprocess
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class XUnitTestInfo:
    """Information about an xUnit test."""
    test_name: str
    class_name: str
    namespace: str
    is_async: bool
    traits: Dict[str, List[str]]
    file_path: Path


class SpecFlowXUnitIntegration:
    """Handle xUnit integration with SpecFlow."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.xunit_patterns = {
            'fact': re.compile(r'\[Fact\]', re.IGNORECASE),
            'theory': re.compile(r'\[Theory\]', re.IGNORECASE),
            'inline_data': re.compile(r'\[InlineData\(([^]]+)\)\]', re.IGNORECASE),
            'member_data': re.compile(r'\[MemberData\("([^"]+)"\)\]', re.IGNORECASE),
            'trait': re.compile(r'\[Trait\("([^"]+)",\s*"([^"]+)"\)\]', re.IGNORECASE),
        }
    
    def detect_xunit(self) -> bool:
        """
        Detect if project uses xUnit.
        
        Returns:
            True if xUnit is detected
        """
        # Check .csproj files for xUnit packages
        for csproj in self.project_root.rglob("*.csproj"):
            content = csproj.read_text(encoding='utf-8')
            if any(pkg in content for pkg in [
                'xunit',
                'xUnit',
                'xunit.runner',
                'xunit.assert'
            ]):
                return True
        
        # Check test files for xUnit attributes
        for cs_file in self.project_root.rglob("*.cs"):
            if self._is_test_file(cs_file):
                content = cs_file.read_text(encoding='utf-8')
                if '[Fact]' in content or '[Theory]' in content:
                    return True
        
        return False
    
    def _is_test_file(self, cs_file: Path) -> bool:
        """Check if a C# file is a test file."""
        test_indicators = ['Test', 'Tests', 'Spec', 'Specs']
        return any(indicator in cs_file.stem for indicator in test_indicators)
    
    def extract_xunit_tests(self, cs_file: Path) -> List[XUnitTestInfo]:
        """
        Extract xUnit tests from a C# file.
        
        Args:
            cs_file: Path to C# test file
            
        Returns:
            List of XUnitTestInfo objects
        """
        if not cs_file.exists():
            return []
        
        content = cs_file.read_text(encoding='utf-8')
        tests = []
        
        # Extract namespace
        namespace_match = re.search(r'namespace\s+([\w.]+)', content)
        namespace = namespace_match.group(1) if namespace_match else 'unknown'
        
        # Extract class name
        class_match = re.search(r'(?:public\s+)?class\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else 'unknown'
        
        # Find all test methods
        method_pattern = re.compile(
            r'\[(?:Fact|Theory)\]\s*'
            r'(?:\[.*?\]\s*)*'  # Additional attributes
            r'(?:public\s+)?(?:async\s+)?(?:Task|void)\s+'
            r'(\w+)\s*\([^)]*\)',
            re.MULTILINE | re.DOTALL
        )
        
        for match in method_pattern.finditer(content):
            test_name = match.group(1)
            is_async = 'async' in content[match.start():match.end()]
            
            # Extract traits for this test
            traits = self._extract_traits(content, match.start())
            
            tests.append(XUnitTestInfo(
                test_name=test_name,
                class_name=class_name,
                namespace=namespace,
                is_async=is_async,
                traits=traits,
                file_path=cs_file
            ))
        
        return tests
    
    def _extract_traits(
        self,
        content: str,
        test_start: int
    ) -> Dict[str, List[str]]:
        """Extract traits from test method attributes."""
        traits = {}
        
        # Look backwards for [Trait] attributes
        before_test = content[max(0, test_start - 500):test_start]
        
        for match in self.xunit_patterns['trait'].finditer(before_test):
            trait_name = match.group(1)
            trait_value = match.group(2)
            
            if trait_name not in traits:
                traits[trait_name] = []
            traits[trait_name].append(trait_value)
        
        return traits
    
    def run_xunit_tests(
        self,
        test_filter: Optional[str] = None,
        traits: Optional[Dict[str, str]] = None
    ) -> subprocess.CompletedProcess:
        """
        Run xUnit tests using dotnet test.
        
        Args:
            test_filter: Filter expression for tests
            traits: Dictionary of trait filters
            
        Returns:
            CompletedProcess with test results
        """
        cmd = ['dotnet', 'test', str(self.project_root)]
        
        if test_filter:
            cmd.extend(['--filter', test_filter])
        
        if traits:
            # xUnit trait filtering: --filter "Category=Unit"
            trait_filters = [
                f"{key}={value}"
                for key, value in traits.items()
            ]
            if trait_filters:
                combined_filter = ' & '.join(trait_filters)
                cmd.extend(['--filter', combined_filter])
        
        # Add xUnit-specific options
        cmd.extend([
            '--logger', 'trx',
            '--results-directory', './TestResults'
        ])
        
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
    
    def convert_to_specflow_scenario(
        self,
        test_info: XUnitTestInfo
    ) -> Dict[str, any]:
        """
        Convert xUnit test to SpecFlow scenario format.
        
        Args:
            test_info: XUnitTestInfo object
            
        Returns:
            Dictionary with scenario information
        """
        scenario_name = test_info.test_name.replace('_', ' ').title()
        
        tags = []
        if 'Category' in test_info.traits:
            tags.extend(f"@{cat}" for cat in test_info.traits['Category'])
        if 'Priority' in test_info.traits:
            tags.extend(f"@P{pri}" for pri in test_info.traits['Priority'])
        
        return {
            'name': scenario_name,
            'tags': tags,
            'is_async': test_info.is_async,
            'class': test_info.class_name,
            'namespace': test_info.namespace,
            'original_test': test_info.test_name
        }
    
    def get_xunit_version(self) -> Optional[str]:
        """
        Get xUnit version from project file.
        
        Returns:
            Version string or None
        """
        for csproj in self.project_root.rglob("*.csproj"):
            content = csproj.read_text(encoding='utf-8')
            
            # Look for PackageReference with xUnit
            version_match = re.search(
                r'<PackageReference\s+Include="xunit[^"]*"\s+Version="([^"]+)"',
                content,
                re.IGNORECASE
            )
            
            if version_match:
                return version_match.group(1)
        
        return None
    
    def supports_parallel_execution(self) -> bool:
        """Check if xUnit parallel execution is configured."""
        # Check for xunit.runner.json or assembly attributes
        config_file = self.project_root / 'xunit.runner.json'
        if config_file.exists():
            import json
            try:
                config = json.loads(config_file.read_text())
                return config.get('parallelizeTestCollections', False)
            except (IOError, json.JSONDecodeError) as e:
                logger.debug(f"Failed to parse xunit config: {e}")
        
        return False
