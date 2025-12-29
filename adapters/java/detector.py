"""
Framework detection for Java test projects.

Determines whether a project uses JUnit 4, JUnit 5, TestNG, or a mix.
"""

from pathlib import Path
from typing import Set
from .model import JavaTestFramework


def detect_frameworks_from_imports(java_file: Path) -> Set[JavaTestFramework]:
    """
    Detect test frameworks from import statements in a Java file.
    
    Args:
        java_file: Path to Java source file.
        
    Returns:
        Set of detected frameworks.
    """
    frameworks = set()
    
    try:
        content = java_file.read_text(encoding="utf-8", errors="ignore")
        
        # Check for JUnit 5 (Jupiter)
        if "org.junit.jupiter" in content:
            frameworks.add(JavaTestFramework.JUNIT5)
        
        # Check for JUnit 4 (but not if JUnit 5 already detected)
        elif "org.junit.Test" in content or "org.junit.Before" in content:
            frameworks.add(JavaTestFramework.JUNIT4)
        
        # Check for TestNG
        if "org.testng" in content:
            frameworks.add(JavaTestFramework.TESTNG)
            
    except Exception:
        pass
    
    return frameworks


def detect_project_frameworks(project_root: str, source_root: str = "src/test/java") -> Set[str]:
    """
    Detect all test frameworks used in a project.
    
    Args:
        project_root: Root directory of the project.
        source_root: Root directory of test sources.
        
    Returns:
        Set of framework names as strings: "junit4", "junit5", "testng"
    """
    source_path = Path(project_root) / source_root
    
    if not source_path.exists():
        return set()
    
    frameworks = set()
    
    for java_file in source_path.rglob("*.java"):
        detected = detect_frameworks_from_imports(java_file)
        frameworks.update(detected)
        
        # Early exit if we've found all possible frameworks
        if len(frameworks) >= 3:
            break
    
    # Convert enums to strings
    return {fw.value for fw in frameworks}


def get_primary_framework_from_detection(frameworks: Set[str]) -> str:
    """
    Get primary framework when multiple are detected.
    
    Priority: TestNG > JUnit 5 > JUnit 4 > default to junit
    
    Args:
        frameworks: Set of detected framework names.
        
    Returns:
        Primary framework name.
    """
    if "testng" in frameworks:
        return "testng"
    elif "junit5" in frameworks:
        return "junit5"
    elif "junit4" in frameworks:
        return "junit4"
    
    return "junit"
