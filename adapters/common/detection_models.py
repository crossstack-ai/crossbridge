"""
Detection result models for framework detection.
"""

from dataclasses import dataclass
from typing import List, Set
from enum import Enum


class DetectionSource(Enum):
    """Source/method used for framework detection."""
    POM_XML = "pom.xml"
    BUILD_GRADLE = "build.gradle"
    BUILD_GRADLE_KTS = "build.gradle.kts"
    TESTNG_XML = "testng.xml"
    SOURCE_IMPORTS = "source_imports"
    CONFTEST_PY = "conftest.py"
    PYTEST_INI = "pytest.ini"
    ROBOT_FILES = "robot_files"
    UNKNOWN = "unknown"


class DetectionConfidence(Enum):
    """Confidence level of framework detection."""
    HIGH = "high"        # Build files, config files
    MEDIUM = "medium"    # Source code imports
    LOW = "low"          # File extensions only


@dataclass
class FrameworkDetectionResult:
    """
    Result of framework detection with metadata.
    
    Attributes:
        framework: The detected framework name (e.g., "junit", "testng", "pytest")
        detection_source: How the framework was detected
        confidence: Confidence level of the detection
        file_path: Optional path to the file that triggered detection
    """
    framework: str
    detection_source: DetectionSource
    confidence: DetectionConfidence
    file_path: str = None
    
    def to_dict(self):
        """Convert to dictionary for persistence."""
        return {
            "framework": self.framework,
            "detection_source": self.detection_source.value,
            "confidence": self.confidence.value,
            "file_path": self.file_path
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        return cls(
            framework=data["framework"],
            detection_source=DetectionSource(data["detection_source"]),
            confidence=DetectionConfidence(data["confidence"]),
            file_path=data.get("file_path")
        )


@dataclass
class ProjectDetectionResult:
    """
    Complete detection result for a project.
    
    Attributes:
        project_root: Root directory of the project
        detections: List of framework detection results
    """
    project_root: str
    detections: List[FrameworkDetectionResult]
    
    def get_frameworks(self) -> Set[str]:
        """Get unique set of detected framework names."""
        return {d.framework for d in self.detections}
    
    def get_primary_detections(self) -> List[FrameworkDetectionResult]:
        """Get high-confidence detections (build files, config files)."""
        return [d for d in self.detections if d.confidence == DetectionConfidence.HIGH]
    
    def to_dict(self):
        """Convert to dictionary for persistence."""
        return {
            "project_root": self.project_root,
            "detections": [d.to_dict() for d in self.detections]
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        return cls(
            project_root=data["project_root"],
            detections=[FrameworkDetectionResult.from_dict(d) for d in data["detections"]]
        )
