"""
.NET Core/5/6+ version handler for SpecFlow.

Handles modern .NET version detection and compatibility.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re
import xml.etree.ElementTree as ET


class DotNetVersionHandler:
    """Handle .NET version detection and compatibility."""
    
    SUPPORTED_VERSIONS = [
        'netcoreapp3.1',
        'net5.0',
        'net6.0',
        'net7.0',
        'net8.0',
    ]
    
    def __init__(self):
        """Initialize the version handler."""
        self.detected_versions = set()
        
    def parse_csproj(self, file_path: Path) -> Dict:
        """
        Parse .csproj file to extract .NET version and packages.
        
        Args:
            file_path: Path to .csproj file
            
        Returns:
            Project information dictionary
        """
        if not file_path.exists():
            return {}
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError:
            return {}
        
        info = {
            'target_framework': None,
            'specflow_version': None,
            'packages': [],
            'file': str(file_path),
        }
        
        # Find TargetFramework
        for prop_group in root.findall('.//PropertyGroup'):
            tf = prop_group.find('TargetFramework')
            if tf is not None and tf.text:
                info['target_framework'] = tf.text
                self.detected_versions.add(tf.text)
        
        # Find PackageReference elements
        for pkg_ref in root.findall('.//PackageReference'):
            pkg_name = pkg_ref.get('Include')
            pkg_version = pkg_ref.get('Version')
            
            if pkg_name:
                info['packages'].append({
                    'name': pkg_name,
                    'version': pkg_version,
                })
                
                # Detect SpecFlow version
                if 'SpecFlow' in pkg_name:
                    info['specflow_version'] = pkg_version
        
        return info
    
    def is_modern_dotnet(self, target_framework: str) -> bool:
        """
        Check if target framework is modern .NET (Core/5+).
        
        Args:
            target_framework: Target framework string
            
        Returns:
            True if modern .NET
        """
        if not target_framework:
            return False
        
        return any(
            target_framework.startswith(version)
            for version in ['netcoreapp', 'net5', 'net6', 'net7', 'net8']
        )
    
    def parse_global_json(self, file_path: Path) -> Dict:
        """
        Parse global.json for SDK version.
        
        Args:
            file_path: Path to global.json
            
        Returns:
            SDK information dictionary
        """
        if not file_path.exists():
            return {}
        
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                'sdk_version': data.get('sdk', {}).get('version'),
                'file': str(file_path),
            }
        except (json.JSONDecodeError, OSError):
            return {}
    
    def detect_runtime_config(self, file_path: Path) -> Dict:
        """
        Parse runtimeconfig.json for runtime information.
        
        Args:
            file_path: Path to runtimeconfig.json
            
        Returns:
            Runtime configuration dictionary
        """
        if not file_path.exists():
            return {}
        
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            runtime_options = data.get('runtimeOptions', {})
            framework = runtime_options.get('framework', {})
            
            return {
                'framework_name': framework.get('name'),
                'framework_version': framework.get('version'),
                'file': str(file_path),
            }
        except (json.JSONDecodeError, OSError):
            return {}
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze entire project for .NET version information.
        
        Args:
            project_path: Root path of project
            
        Returns:
            Complete version analysis dictionary
        """
        result = {
            'projects': [],
            'global_config': {},
            'runtime_configs': [],
            'target_frameworks': set(),
            'is_modern_dotnet': False,
        }
        
        # Find all .csproj files
        csproj_files = list(project_path.rglob("*.csproj"))
        for csproj in csproj_files:
            proj_info = self.parse_csproj(csproj)
            if proj_info:
                result['projects'].append(proj_info)
                if proj_info['target_framework']:
                    result['target_frameworks'].add(proj_info['target_framework'])
        
        # Check for global.json
        global_json = project_path / "global.json"
        if global_json.exists():
            result['global_config'] = self.parse_global_json(global_json)
        
        # Check for runtimeconfig.json files
        runtime_configs = list(project_path.rglob("*.runtimeconfig.json"))
        for rc in runtime_configs:
            rc_info = self.detect_runtime_config(rc)
            if rc_info:
                result['runtime_configs'].append(rc_info)
        
        # Determine if using modern .NET
        result['target_frameworks'] = list(result['target_frameworks'])
        result['is_modern_dotnet'] = any(
            self.is_modern_dotnet(tf) for tf in result['target_frameworks']
        )
        
        return result
    
    def generate_compatibility_report(self, analysis: Dict) -> str:
        """
        Generate compatibility report.
        
        Args:
            analysis: Version analysis dictionary
            
        Returns:
            Markdown report string
        """
        lines = []
        lines.append("# .NET Version Compatibility Report\n")
        
        # Target frameworks
        lines.append("## Target Frameworks\n")
        for tf in analysis['target_frameworks']:
            is_modern = "✅ Modern" if self.is_modern_dotnet(tf) else "⚠️ Legacy"
            lines.append(f"- {tf} {is_modern}")
        lines.append("")
        
        # Projects
        lines.append("## Projects\n")
        for proj in analysis['projects']:
            lines.append(f"### {Path(proj['file']).name}")
            lines.append(f"- Target Framework: {proj['target_framework']}")
            if proj['specflow_version']:
                lines.append(f"- SpecFlow Version: {proj['specflow_version']}")
            lines.append("")
        
        # Global SDK
        if analysis['global_config']:
            lines.append("## Global SDK Configuration\n")
            sdk_version = analysis['global_config'].get('sdk_version')
            if sdk_version:
                lines.append(f"- SDK Version: {sdk_version}")
            lines.append("")
        
        # Recommendations
        lines.append("## Recommendations\n")
        if not analysis['is_modern_dotnet']:
            lines.append("⚠️ **Action Required**: Project uses legacy .NET Framework.")
            lines.append("- Consider migrating to .NET 6 or later")
            lines.append("- .NET 6 is LTS (Long Term Support)")
        else:
            lines.append("✅ Project uses modern .NET Core/5+")
        lines.append("")
        
        return '\n'.join(lines)
    
    def suggest_migration_steps(self, analysis: Dict) -> List[str]:
        """
        Suggest migration steps for legacy projects.
        
        Args:
            analysis: Version analysis dictionary
            
        Returns:
            List of migration step strings
        """
        if analysis['is_modern_dotnet']:
            return ["✅ Already using modern .NET"]
        
        steps = []
        steps.append("1. Update .csproj TargetFramework to net6.0 or net8.0")
        steps.append("2. Update SpecFlow packages to latest versions")
        steps.append("3. Replace app.config with appsettings.json")
        steps.append("4. Update test runner (xUnit/NUnit/MSTest)")
        steps.append("5. Test all scenarios after migration")
        steps.append("6. Update CI/CD pipelines to use .NET SDK")
        
        return steps
    
    def check_specflow_compatibility(self, specflow_version: str, target_framework: str) -> Dict:
        """
        Check SpecFlow version compatibility with .NET version.
        
        Args:
            specflow_version: SpecFlow version string
            target_framework: .NET target framework
            
        Returns:
            Compatibility information dictionary
        """
        result = {
            'compatible': True,
            'warnings': [],
            'recommendations': [],
        }
        
        # SpecFlow 3.x requires .NET Core 3.1+
        if specflow_version and specflow_version.startswith('3.'):
            if target_framework and not self.is_modern_dotnet(target_framework):
                result['compatible'] = False
                result['warnings'].append(
                    f"SpecFlow {specflow_version} requires .NET Core 3.1+ but found {target_framework}"
                )
        
        # Recommend latest versions
        if self.is_modern_dotnet(target_framework):
            if not specflow_version or int(specflow_version.split('.')[0]) < 3:
                result['recommendations'].append(
                    "Consider upgrading to SpecFlow 3.x for better .NET Core/5+ support"
                )
        
        return result
    
    def generate_dotnet_config(self, target_framework: str = 'net6.0') -> str:
        """
        Generate .NET configuration for SpecFlow project.
        
        Args:
            target_framework: Target .NET framework
            
        Returns:
            XML configuration string
        """
        config = f"""<?xml version="1.0" encoding="utf-8"?>
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>{target_framework}</TargetFramework>
    <IsPackable>false</IsPackable>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="SpecFlow.Plus.LivingDocPlugin" Version="3.9.57" />
    <PackageReference Include="SpecFlow.xUnit" Version="3.9.74" />
    <PackageReference Include="xunit" Version="2.6.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.4" />
    <PackageReference Include="FluentAssertions" Version="6.12.0" />
  </ItemGroup>

  <ItemGroup>
    <Folder Include="Features\\" />
    <Folder Include="StepDefinitions\\" />
  </ItemGroup>
</Project>
"""
        return config
