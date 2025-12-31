"""
RestAssured + Java project detector.

Detects if a project uses RestAssured with TestNG or JUnit 5 for API testing.
"""

from pathlib import Path
from typing import Optional, Dict
import re
import xml.etree.ElementTree as ET


class RestAssuredDetector:
    """Detects RestAssured + Java projects (TestNG or JUnit 5)."""
    
    @staticmethod
    def detect(project_root: str) -> bool:
        """
        Detect if project uses RestAssured with TestNG or JUnit 5.
        
        Args:
            project_root: Path to project root
            
        Returns:
            True if RestAssured with TestNG or JUnit 5 is detected
        """
        project_path = Path(project_root)
        
        # Check for Maven pom.xml
        pom_file = project_path / "pom.xml"
        if pom_file.exists():
            detection = RestAssuredDetector._check_pom_xml(pom_file)
            if detection['has_restassured'] and (detection['has_testng'] or detection['has_junit5']):
                return True
        
        # Check for Gradle build files
        for gradle_file in ["build.gradle", "build.gradle.kts"]:
            gradle_path = project_path / gradle_file
            if gradle_path.exists():
                detection = RestAssuredDetector._check_gradle(gradle_path)
                if detection['has_restassured'] and (detection['has_testng'] or detection['has_junit5']):
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
    def _check_pom_xml(pom_file: Path) -> Dict[str, bool]:
        """Check if pom.xml contains RestAssured and test framework dependencies."""
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
            has_junit5 = False
            
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
                    
                    # Check for JUnit 5
                    if ('org.junit.jupiter' in group or 'junit-jupiter' in artifact):
                        has_junit5 = True
            
            return {
                'has_restassured': has_restassured,
                'has_testng': has_testng,
                'has_junit5': has_junit5
            }
            
        except Exception:
            return {'has_restassured': False, 'has_testng': False, 'has_junit5': False}
    
    @staticmethod
    def _check_gradle(gradle_file: Path) -> Dict[str, bool]:
        """Check if Gradle build file contains RestAssured and test frameworks."""
        try:
            content = gradle_file.read_text(encoding='utf-8', errors='ignore')
            
            has_restassured = bool(
                re.search(r'io\.rest-assured|rest-assured', content, re.IGNORECASE)
            )
            has_testng = bool(
                re.search(r'org\.testng|testng', content, re.IGNORECASE)
            )
            has_junit5 = bool(
                re.search(r'org\.junit\.jupiter|junit-jupiter', content, re.IGNORECASE)
            )
            
            return {
                'has_restassured': has_restassured,
                'has_testng': has_testng,
                'has_junit5': has_junit5
            }
            
        except Exception:
            return {'has_restassured': False, 'has_testng': False, 'has_junit5': False}
    
    @staticmethod
    def _check_source_files(src_dir: Path) -> bool:
        """Check Java source files for RestAssured and test framework usage."""
        try:
            # Find Java files with both RestAssured and test framework imports
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
                    
                    # Check for JUnit 5 imports
                    has_junit5 = bool(
                        re.search(r'import\s+org\.junit\.jupiter', content)
                    )
                    
                    if has_restassured and (has_testng or has_junit5):
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
            Dictionary with configuration details including test framework
        """
        project_path = Path(project_root)
        
        info = {
            'detected': False,
            'build_tool': None,
            'test_framework': None,  # 'testng', 'junit5', or 'both'
            'testng_xml': None,
            'src_root': None,
        }
        
        # Detect build tool and frameworks
        has_testng = False
        has_junit5 = False
        
        if (project_path / "pom.xml").exists():
            info['build_tool'] = 'maven'
            detection = RestAssuredDetector._check_pom_xml(project_path / "pom.xml")
            has_testng = detection['has_testng']
            has_junit5 = detection['has_junit5']
        elif (project_path / "build.gradle").exists() or (project_path / "build.gradle.kts").exists():
            info['build_tool'] = 'gradle'
            gradle_file = project_path / ("build.gradle" if (project_path / "build.gradle").exists() else "build.gradle.kts")
            detection = RestAssuredDetector._check_gradle(gradle_file)
            has_testng = detection['has_testng']
            has_junit5 = detection['has_junit5']
        
        # Determine test framework
        if has_testng and has_junit5:
            info['test_framework'] = 'both'
        elif has_testng:
            info['test_framework'] = 'testng'
        elif has_junit5:
            info['test_framework'] = 'junit5'
        
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
