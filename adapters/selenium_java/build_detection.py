"""
Build tool detection utilities for Java projects.

Detects test frameworks by parsing Maven (pom.xml) and Gradle build files.
"""

from pathlib import Path
from typing import Set, List

from ..common.detection_models import (
    FrameworkDetectionResult, 
    DetectionSource, 
    DetectionConfidence,
    ProjectDetectionResult
)


def detect_from_build_files(project_root: str = ".") -> Set[str]:
    """
    Detect Java test frameworks from build files.
    
    Scans Maven (pom.xml) and Gradle (build.gradle, build.gradle.kts) files
    to determine which test framework is being used.
    
    Args:
        project_root: Root directory of the project.
        
    Returns:
        Set of detected frameworks: "junit", "testng", or both.
        
    Example:
        >>> frameworks = detect_from_build_files(".")
        >>> if "testng" in frameworks:
        ...     print("Using TestNG")
    """
    frameworks = set()
    root = Path(project_root)

    for build_file in ["pom.xml", "build.gradle", "build.gradle.kts"]:
        path = root / build_file
        if not path.exists():
            continue

        try:
            content = path.read_text(encoding="utf-8")

            # TestNG detection
            if "org.testng" in content:
                frameworks.add("testng")

            # JUnit detection (both Jupiter/5 and 4)
            if "org.junit.jupiter" in content or "<groupId>junit</groupId>" in content:
                frameworks.add("junit")
                
        except Exception as e:
            print(f"Warning: Error reading {build_file}: {e}")

    return frameworks


def detect_from_java_sources(source_root: str = "src/test/java") -> Set[str]:
    """
    Detect Java test frameworks from source code imports (SECONDARY method).
    
    Scans Java test files for import statements to determine the framework.
    This is a fallback when build files are not available.
    
    Args:
        source_root: Root directory of test sources.
        
    Returns:
        Set of detected frameworks: "junit", "testng", or both.
        
    Example:
        >>> frameworks = detect_from_java_sources("src/test/java")
        >>> print(frameworks)
    """
    frameworks = set()
    source_path = Path(source_root)
    
    if not source_path.exists():
        return frameworks

    for java_file in source_path.rglob("*.java"):
        try:
            text = java_file.read_text(encoding="utf-8", errors="ignore")

            # TestNG detection (import or annotation)
            if "org.testng.annotations" in text or "org.testng" in text:
                frameworks.add("testng")

            # JUnit detection (both 4 and 5) - check for imports or full class names
            if ("org.junit.Test" in text or 
                "org.junit.jupiter" in text or 
                "org.junit" in text):
                frameworks.add("junit")
                
        except Exception:
            continue  # Skip files that can't be read

    return frameworks


def detect_from_config_files(project_root: str = ".") -> Set[str]:
    """
    Detect Java test frameworks from config files (SUPPORTING SIGNAL).
    
    Checks for framework-specific configuration files.
    TestNG uses testng.xml, JUnit typically doesn't require config files.
    
    Args:
        project_root: Root directory of the project.
        
    Returns:
        Set of detected frameworks.
        
    Example:
        >>> frameworks = detect_from_config_files(".")
        >>> if "testng" in frameworks:
        ...     print("Found testng.xml")
    """
    frameworks = set()
    root = Path(project_root)

    # TestNG config file (very strong signal)
    if (root / "testng.xml").exists():
        frameworks.add("testng")

    # JUnit typically does not require config files → absence is normal

    return frameworks


def detect_java_test_frameworks(project_root: str = ".", source_root: str = "src/test/java") -> Set[str]:
    """
    Detect all Java test frameworks using combined signals (IMPORTANT).
    
    Merges results from all detection methods to provide a comprehensive view:
    - Build files (PRIMARY)
    - Source code imports (SECONDARY)
    - Config files (SUPPORTING)
    
    Args:
        project_root: Root directory of the project.
        source_root: Root directory of test sources.
        
    Returns:
        Set of all detected frameworks: can include both "junit" and "testng".
        
    Example:
        >>> frameworks = detect_java_test_frameworks(".")
        >>> if "junit" in frameworks and "testng" in frameworks:
        ...     print("Mixed framework project detected")
    """
    detected = set()

    detected |= detect_from_build_files(project_root)
    detected |= detect_from_java_sources(source_root)
    detected |= detect_from_config_files(project_root)

    return detected


def get_primary_framework(project_root: str = ".", source_root: str = "src/test/java") -> str:
    """
    Get the primary test framework for a Java project.
    
    Uses multi-tier detection strategy:
    1. PRIMARY: Build files (pom.xml, build.gradle)
    2. SECONDARY: Source code imports
    3. SUPPORTING: Config files (testng.xml)
    
    Args:
        project_root: Root directory of the project.
        source_root: Root directory of test sources.
        
    Returns:
        "junit", "testng", or "junit" (default if none found).
    """
    # PRIMARY: Try build files first
    frameworks = detect_from_build_files(project_root)
    
    # SECONDARY: Fallback to source code if build files don't reveal anything
    if not frameworks:
        frameworks = detect_from_java_sources(source_root)
    
    # SUPPORTING: Config files (additional signal)
    if not frameworks:
        frameworks = detect_from_config_files(project_root)
    
    # If both are detected, prefer TestNG (less common, more intentional)
    if "testng" in frameworks:
        return "testng"
    
    # Default to junit
    return "junit"


def has_maven(project_root: str = ".") -> bool:
    """Check if project uses Maven."""
    return (Path(project_root) / "pom.xml").exists()


def has_gradle(project_root: str = ".") -> bool:
    """Check if project uses Gradle."""
    root = Path(project_root)
    return (root / "build.gradle").exists() or (root / "build.gradle.kts").exists()


def get_build_tool(project_root: str = ".") -> str:
    """
    Detect the build tool being used.
    
    Args:
        project_root: Root directory of the project.
        
    Returns:
        "maven", "gradle", or "unknown".
    """
    if has_maven(project_root):
        return "maven"
    elif has_gradle(project_root):
        return "gradle"
    return "unknown"


def detect_with_metadata(project_root: str = ".", source_root: str = "src/test/java") -> ProjectDetectionResult:
    """
    Detect Java test frameworks with full metadata about detection sources.
    
    Returns detailed information about how each framework was detected,
    including confidence levels and source files.
    
    Args:
        project_root: Root directory of the project.
        source_root: Root directory of test sources.
        
    Returns:
        ProjectDetectionResult with detailed detection metadata.
        
    Example:
        >>> result = detect_with_metadata(".")
        >>> for detection in result.detections:
        ...     print(f"{detection.framework} detected from {detection.detection_source.value}")
    """
    detections = []
    root = Path(project_root)
    
    # Check pom.xml (Maven)
    pom_xml = root / "pom.xml"
    if pom_xml.exists():
        try:
            content = pom_xml.read_text(encoding="utf-8", errors="ignore")
            if "junit" in content.lower() or "junit.jupiter" in content:
                detections.append(FrameworkDetectionResult(
                    framework="junit",
                    detection_source=DetectionSource.POM_XML,
                    confidence=DetectionConfidence.HIGH,
                    file_path=str(pom_xml)
                ))
            if "testng" in content.lower():
                detections.append(FrameworkDetectionResult(
                    framework="testng",
                    detection_source=DetectionSource.POM_XML,
                    confidence=DetectionConfidence.HIGH,
                    file_path=str(pom_xml)
                ))
        except Exception:
            pass
    
    # Check build.gradle (Gradle)
    build_gradle = root / "build.gradle"
    if build_gradle.exists():
        try:
            content = build_gradle.read_text(encoding="utf-8", errors="ignore")
            if "junit" in content.lower():
                detections.append(FrameworkDetectionResult(
                    framework="junit",
                    detection_source=DetectionSource.BUILD_GRADLE,
                    confidence=DetectionConfidence.HIGH,
                    file_path=str(build_gradle)
                ))
            if "testng" in content.lower():
                detections.append(FrameworkDetectionResult(
                    framework="testng",
                    detection_source=DetectionSource.BUILD_GRADLE,
                    confidence=DetectionConfidence.HIGH,
                    file_path=str(build_gradle)
                ))
        except Exception:
            pass
    
    # Check build.gradle.kts (Kotlin Gradle)
    build_gradle_kts = root / "build.gradle.kts"
    if build_gradle_kts.exists():
        try:
            content = build_gradle_kts.read_text(encoding="utf-8", errors="ignore")
            if "junit" in content.lower():
                detections.append(FrameworkDetectionResult(
                    framework="junit",
                    detection_source=DetectionSource.BUILD_GRADLE_KTS,
                    confidence=DetectionConfidence.HIGH,
                    file_path=str(build_gradle_kts)
                ))
            if "testng" in content.lower():
                detections.append(FrameworkDetectionResult(
                    framework="testng",
                    detection_source=DetectionSource.BUILD_GRADLE_KTS,
                    confidence=DetectionConfidence.HIGH,
                    file_path=str(build_gradle_kts)
                ))
        except Exception:
            pass
    
    # Check testng.xml (TestNG config)
    testng_xml = root / "testng.xml"
    if testng_xml.exists():
        detections.append(FrameworkDetectionResult(
            framework="testng",
            detection_source=DetectionSource.TESTNG_XML,
            confidence=DetectionConfidence.HIGH,
            file_path=str(testng_xml)
        ))
    
    # If no high-confidence detections, try source code (SECONDARY)
    if not detections:
        source_path = Path(source_root)
        if source_path.exists():
            junit_found = False
            testng_found = False
            
            for java_file in source_path.rglob("*.java"):
                try:
                    text = java_file.read_text(encoding="utf-8", errors="ignore")
                    
                    if not junit_found and ("org.junit" in text):
                        detections.append(FrameworkDetectionResult(
                            framework="junit",
                            detection_source=DetectionSource.SOURCE_IMPORTS,
                            confidence=DetectionConfidence.MEDIUM,
                            file_path=str(java_file)
                        ))
                        junit_found = True
                    
                    if not testng_found and ("org.testng" in text):
                        detections.append(FrameworkDetectionResult(
                            framework="testng",
                            detection_source=DetectionSource.SOURCE_IMPORTS,
                            confidence=DetectionConfidence.MEDIUM,
                            file_path=str(java_file)
                        ))
                        testng_found = True
                    
                    # Stop once we've found both
                    if junit_found and testng_found:
                        break
                        
                except Exception:
                    continue
    
    return ProjectDetectionResult(
        project_root=project_root,
        detections=detections
    )

    if has_maven(project_root):
        return "maven"
    elif has_gradle(project_root):
        return "gradle"
    else:
        return "unknown"
