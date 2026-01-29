"""
Playwright multi-language enhancement.

Enhances cross-language support for Java and .NET Playwright bindings.
"""

from typing import List, Dict, Optional
from pathlib import Path
import re


class PlaywrightMultiLanguageEnhancer:
    """Enhance Playwright multi-language support."""
    
    def __init__(self):
        """Initialize the enhancer."""
        pass
    
    def detect_java_playwright(self, project_path: Path) -> Dict:
        """
        Detect Java Playwright usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Detection dictionary
        """
        pom_files = list(project_path.rglob("pom.xml"))
        build_gradle_files = list(project_path.rglob("build.gradle"))
        
        has_playwright = False
        version = None
        test_framework = None
        
        # Check Maven
        for pom in pom_files:
            try:
                content = pom.read_text(encoding='utf-8')
                if 'com.microsoft.playwright' in content:
                    has_playwright = True
                    
                    # Extract version
                    version_match = re.search(r'<version>([^<]+)</version>', content)
                    if version_match:
                        version = version_match.group(1)
                    
                    # Detect test framework
                    if 'junit' in content.lower():
                        test_framework = 'JUnit'
                    elif 'testng' in content.lower():
                        test_framework = 'TestNG'
            except (IOError, UnicodeDecodeError, ET.ParseError) as e:
                logger.debug(f"Failed to parse pom.xml: {e}")
        
        # Check Gradle
        for gradle in build_gradle_files:
            try:
                content = gradle.read_text(encoding='utf-8')
                if 'com.microsoft.playwright' in content:
                    has_playwright = True
                    
                    # Extract version
                    version_match = re.search(r'com\.microsoft\.playwright:playwright:([^\'"]+)', content)
                    if version_match:
                        version = version_match.group(1)
                    
                    # Detect test framework
                    if 'junit' in content.lower():
                        test_framework = 'JUnit'
                    elif 'testng' in content.lower():
                        test_framework = 'TestNG'
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to read build.gradle: {e}")
        
        return {
            'has_playwright': has_playwright,
            'version': version,
            'test_framework': test_framework,
            'language': 'java',
        }
    
    def detect_dotnet_playwright(self, project_path: Path) -> Dict:
        """
        Detect .NET Playwright usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Detection dictionary
        """
        csproj_files = list(project_path.rglob("*.csproj"))
        
        has_playwright = False
        version = None
        test_framework = None
        
        for csproj in csproj_files:
            try:
                content = csproj.read_text(encoding='utf-8')
                if 'Microsoft.Playwright' in content:
                    has_playwright = True
                    
                    # Extract version
                    version_match = re.search(r'Microsoft\.Playwright[^>]*Version="([^"]+)"', content)
                    if version_match:
                        version = version_match.group(1)
                    
                    # Detect test framework
                    if 'Microsoft.Playwright.NUnit' in content:
                        test_framework = 'NUnit'
                    elif 'Microsoft.Playwright.MSTest' in content:
                        test_framework = 'MSTest'
                    elif 'xunit' in content.lower():
                        test_framework = 'xUnit'
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to read .csproj file: {e}")
        
        return {
            'has_playwright': has_playwright,
            'version': version,
            'test_framework': test_framework,
            'language': 'dotnet',
        }
    
    def extract_java_page_objects(self, project_path: Path) -> List[Dict]:
        """
        Extract Java Playwright Page Objects.
        
        Args:
            project_path: Project root path
            
        Returns:
            List of page object dictionaries
        """
        java_files = list(project_path.rglob("*Page.java"))
        
        page_objects = []
        
        for java_file in java_files:
            try:
                content = java_file.read_text(encoding='utf-8', errors='ignore')
                
                if 'Page page' in content or 'import com.microsoft.playwright.Page' in content:
                    # Extract class name
                    class_match = re.search(r'public\s+class\s+(\w+)', content)
                    if class_match:
                        class_name = class_match.group(1)
                        
                        # Count locators
                        locator_count = content.count('.locator(')
                        
                        # Count methods
                        method_count = len(re.findall(r'public\s+\w+\s+\w+\s*\(', content))
                        
                        page_objects.append({
                            'class_name': class_name,
                            'file': str(java_file),
                            'locator_count': locator_count,
                            'method_count': method_count,
                        })
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to analyze Java file: {e}")
        
        return page_objects
    
    def analyze_project(self, project_path: Path) -> Dict:
        """
        Analyze Playwright multi-language usage.
        
        Args:
            project_path: Project root path
            
        Returns:
            Analysis dictionary
        """
        java_detection = self.detect_java_playwright(project_path)
        dotnet_detection = self.detect_dotnet_playwright(project_path)
        
        java_page_objects = []
        if java_detection['has_playwright']:
            java_page_objects = self.extract_java_page_objects(project_path)
        
        return {
            'java': java_detection,
            'dotnet': dotnet_detection,
            'java_page_objects': java_page_objects,
        }
    
    def generate_cross_language_guide(self, analysis: Dict) -> str:
        """
        Generate cross-language migration guide.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown guide
        """
        lines = []
        lines.append("# Playwright Multi-Language Migration Guide\n")
        
        if analysis['java']['has_playwright']:
            lines.append("## Java Playwright\n")
            lines.append(f"- Version: {analysis['java']['version']}")
            lines.append(f"- Test Framework: {analysis['java']['test_framework']}")
            lines.append(f"- Page Objects: {len(analysis['java_page_objects'])}\n")
        
        if analysis['dotnet']['has_playwright']:
            lines.append("## .NET Playwright\n")
            lines.append(f"- Version: {analysis['dotnet']['version']}")
            lines.append(f"- Test Framework: {analysis['dotnet']['test_framework']}\n")
        
        lines.append("## Migration Patterns\n")
        lines.append("### JavaScript/TypeScript to Java\n")
        lines.append("```javascript")
        lines.append("// TypeScript")
        lines.append("await page.goto('https://example.com');")
        lines.append("await page.locator('#button').click();")
        lines.append("```\n")
        
        lines.append("```java")
        lines.append("// Java")
        lines.append("page.navigate(\"https://example.com\");")
        lines.append("page.locator(\"#button\").click();")
        lines.append("```\n")
        
        return '\n'.join(lines)
    
    def generate_documentation(self, analysis: Dict) -> str:
        """
        Generate documentation for multi-language support.
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            Markdown documentation
        """
        lines = []
        lines.append("# Playwright Multi-Language Support\n")
        
        lines.append("## Language Detection\n")
        lines.append(f"- Java: {'✅ Detected' if analysis['java']['has_playwright'] else '❌ Not found'}")
        lines.append(f"- .NET: {'✅ Detected' if analysis['dotnet']['has_playwright'] else '❌ Not found'}\n")
        
        if analysis['java']['has_playwright']:
            lines.append("## Java Details\n")
            lines.append(f"- Playwright Version: {analysis['java']['version']}")
            lines.append(f"- Test Framework: {analysis['java']['test_framework']}")
            lines.append(f"- Page Objects Found: {len(analysis['java_page_objects'])}")
        
        return '\n'.join(lines)
