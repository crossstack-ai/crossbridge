"""
RestAssured + TestNG project detector.

Detects if a project uses RestAssured with TestNG for API testing.
"""

from pathlib import Path
from typing import Optional
import re
import xml.etree.ElementTree as ET


class RestAssuredDetector:
    """Detects RestAssured + TestNG projects."""
    
    @staticmethod
    def detect(project_root: str) -> bool:
        """
        Detect if project uses RestAssured + TestNG.
        
        Args:
            project_root: Path to project root
            
        Returns:
            True if RestAssured + TestNG is detected
        """
        project_path = Path(project_root)
        
        # Check for Maven pom.xml
        pom_file = project_path / "pom.xml"
        if pom_file.exists():
            if RestAssuredDetector._check_pom_xml(pom_file):
                return True
        
        # Check for Gradle build files
        for gradle_file in ["build.gradle", "build.gradle.kts"]:
            gradle_path = project_path / gradle_file
            if gradle_path.exists():
                if RestAssuredDetector._check_gradle(gradle_path):
                    return True
        
        # Check Java source files for RestAssured imports
        src_dirs = [
            project_path / "src" / "test" / "java",
            project_path / "src" / "main" / "java",
            project_path / "test",
        ]
        
        for src_dir in src_dirs:
            if src_dir.exists():
                if RestAssuredDetector._check_source_files(src_dir):
                    return True
        
        return False
    
    @staticmethod
    def _check_pom_xml(pom_file: Path) -> bool:
        """Check if pom.xml contains RestAssured and TestNG dependencies."""
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()
            
            # Handle namespace
            ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            
            # Try without namespace first
            dependencies = root.findall('.//dependency')
            if not dependencies:
                # Try with namespace
                dependencies = root.findall('.//maven:dependency', ns)
            
            has_restassured = False
            has_testng = False
            
            for dep in dependencies:
                group_id = dep.find('groupId')
                if group_id is None:
                    group_id = dep.find('maven:groupId', ns)
                
                artifact_id = dep.find('artifactId')
                if artifact_id is None:
                    artifact_id = dep.find('maven:artifactId', ns)
                
                if group_id is not None and artifact_id is not None:
                    group = group_id.text or ""
                    artifact = artifact_id.text or ""
                    
                    # Check for RestAssured
                    if 'io.rest-assured' in group or 'rest-assured' in artifact:
                        has_restassured = True
                    
                    # Check for TestNG
                    if 'org.testng' in group or 'testng' in artifact:
                        has_testng = True
            
            return has_restassured and has_testng
            
        except Exception:
            return False
    
    @staticmethod
    def _check_gradle(gradle_file: Path) -> bool:
        """Check if Gradle build file contains RestAssured and TestNG."""
        try:
            content = gradle_file.read_text(encoding='utf-8', errors='ignore')
            
            has_restassured = bool(
                re.search(r'io\.rest-assured|rest-assured', content, re.IGNORECASE)
            )
            has_testng = bool(
                re.search(r'org\.testng|testng', content, re.IGNORECASE)
            )
            
            return has_restassured and has_testng
            
        except Exception:
            return False
    
    @staticmethod
    def _check_source_files(src_dir: Path) -> bool:
        """Check Java source files for RestAssured and TestNG usage."""
        try:
            # Find Java files with both RestAssured and TestNG imports
            for java_file in src_dir.rglob("*.java"):
                try:
                    content = java_file.read_text(encoding='utf-8', errors='ignore')
                    
                    # Check for RestAssured imports
                    has_restassured = bool(
                        re.search(r'import\s+(?:static\s+)?io\.restassured', content)
                    )
                    
                    # Check for TestNG imports
                    has_testng = bool(
                        re.search(r'import\s+org\.testng', content)
                    )
                    
                    if has_restassured and has_testng:
                        return True
                        
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False
    
    @staticmethod
    def get_config_info(project_root: str) -> dict:
        """
        Get configuration information about the project.
        
        Args:
            project_root: Path to project root
            
        Returns:
            Dictionary with configuration details
        """
        project_path = Path(project_root)
        
        info = {
            'detected': False,
            'build_tool': None,
            'testng_xml': None,
            'src_root': None,
        }
        
        # Detect build tool
        if (project_path / "pom.xml").exists():
            info['build_tool'] = 'maven'
        elif (project_path / "build.gradle").exists() or (project_path / "build.gradle.kts").exists():
            info['build_tool'] = 'gradle'
        
        # Check for TestNG XML
        for testng_file in ["testng.xml", "src/test/resources/testng.xml"]:
            if (project_path / testng_file).exists():
                info['testng_xml'] = testng_file
                break
        
        # Find source root
        for src_candidate in ["src/test/java", "src/main/java", "test"]:
            if (project_path / src_candidate).exists():
                info['src_root'] = src_candidate
                break
        
        info['detected'] = RestAssuredDetector.detect(project_root)
        
        return info
