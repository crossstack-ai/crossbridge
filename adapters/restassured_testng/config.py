"""
Configuration for RestAssured + TestNG adapter.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class RestAssuredConfig:
    """Configuration for RestAssured + TestNG tests."""
    
    # Project structure
    project_root: str = "."
    src_root: str = "src/test/java"
    
    # Maven/Gradle
    maven_command: str = "mvn"
    gradle_command: str = "gradle"
    
    # Test execution
    testng_xml: Optional[str] = "testng.xml"  # TestNG suite XML
    parallel_threads: int = 1
    groups: List[str] = field(default_factory=list)  # TestNG groups to run
    
    # Reporting
    surefire_reports: str = "target/surefire-reports"
    testng_output: str = "test-output"
    
    # Build tool detection
    build_tool: Optional[str] = None  # "maven" or "gradle", auto-detect if None
    
    def __post_init__(self):
        """Auto-detect build tool if not specified."""
        if self.build_tool is None:
            from pathlib import Path
            
            project_path = Path(self.project_root)
            
            if (project_path / "pom.xml").exists():
                self.build_tool = "maven"
            elif (project_path / "build.gradle").exists() or (project_path / "build.gradle.kts").exists():
                self.build_tool = "gradle"
            else:
                self.build_tool = "maven"  # Default to Maven
