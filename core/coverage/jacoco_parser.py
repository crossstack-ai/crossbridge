"""
JaCoCo XML Coverage Parser.

Parses JaCoCo XML reports to extract code coverage data.
JaCoCo is the standard coverage tool for Java/Selenium projects.

XML Structure (simplified):
<report>
  <package name="com/example">
    <class name="com/example/LoginService">
      <method name="login" desc="(Ljava/lang/String;)V">
        <counter type="INSTRUCTION" covered="45" missed="2"/>
        <counter type="LINE" covered="12" missed="1"/>
        <counter type="BRANCH" covered="4" missed="0"/>
      </method>
    </class>
  </package>
</report>
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import defaultdict

from core.coverage.models import (
    CoveredCodeUnit,
    TestCoverageMapping,
    CoverageType,
    CoverageSource,
    ExecutionMode,
    CoverageConfidenceCalculator
)


class JaCoCoXMLParser:
    """
    Parse JaCoCo XML coverage reports.
    
    Extracts:
    - Covered classes
    - Covered methods
    - Coverage metrics (instruction, line, branch)
    """
    
    def __init__(self):
        self.confidence_calculator = CoverageConfidenceCalculator()
    
    def parse(
        self,
        xml_path: Path,
        test_id: Optional[str] = None,
        test_name: Optional[str] = None,
        execution_mode: ExecutionMode = ExecutionMode.ISOLATED
    ) -> TestCoverageMapping:
        """
        Parse JaCoCo XML report.
        
        Args:
            xml_path: Path to jacoco.xml
            test_id: Test identifier (if known)
            test_name: Human-readable test name
            execution_mode: How coverage was collected
            
        Returns:
            TestCoverageMapping with covered classes/methods
        """
        if not xml_path.exists():
            raise FileNotFoundError(f"JaCoCo XML not found: {xml_path}")
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Extract coverage data
        covered_units = []
        covered_classes = set()
        covered_methods = set()
        has_source_paths = False
        
        for package in root.findall("package"):
            package_name = package.attrib.get("name", "").replace("/", ".")
            
            for cls in package.findall("class"):
                class_name = cls.attrib.get("name", "").replace("/", ".")
                source_file = cls.attrib.get("sourcefilename")
                
                if source_file:
                    has_source_paths = True
                
                # Check if class has any coverage
                class_has_coverage = False
                
                for method in cls.findall("method"):
                    method_name = method.attrib.get("name", "")
                    method_desc = method.attrib.get("desc", "")
                    
                    # Parse counters
                    counters = self._parse_counters(method)
                    
                    # Check if method is covered
                    if counters.get("instruction_covered", 0) > 0:
                        class_has_coverage = True
                        
                        # Create covered code unit
                        unit = CoveredCodeUnit(
                            class_name=class_name,
                            method_name=method_name,
                            file_path=source_file,
                            instruction_coverage=self._calculate_coverage(
                                counters.get("instruction_covered", 0),
                                counters.get("instruction_total", 0)
                            ),
                            line_coverage=self._calculate_coverage(
                                counters.get("line_covered", 0),
                                counters.get("line_total", 0)
                            ),
                            branch_coverage=self._calculate_coverage(
                                counters.get("branch_covered", 0),
                                counters.get("branch_total", 0)
                            ),
                            covered_branches=counters.get("branch_covered", 0),
                            total_branches=counters.get("branch_total", 0)
                        )
                        
                        covered_units.append(unit)
                        covered_methods.add(f"{class_name}.{method_name}")
                
                if class_has_coverage:
                    covered_classes.add(class_name)
        
        # Calculate confidence
        confidence = self.confidence_calculator.calculate(
            execution_mode=execution_mode,
            has_source_paths=has_source_paths
        )
        
        # Create mapping
        return TestCoverageMapping(
            test_id=test_id or "unknown",
            test_name=test_name,
            test_framework="junit",  # Assume JUnit for JaCoCo
            covered_classes=covered_classes,
            covered_methods=covered_methods,
            covered_code_units=covered_units,
            coverage_type=CoverageType.INSTRUCTION,
            coverage_source=CoverageSource.JACOCO,
            execution_mode=execution_mode,
            confidence=confidence
        )
    
    def parse_batch(
        self,
        xml_path: Path,
        test_ids: List[str],
        execution_mode: ExecutionMode = ExecutionMode.SMALL_BATCH
    ) -> Dict[str, TestCoverageMapping]:
        """
        Parse coverage for a batch of tests.
        
        When multiple tests run together, coverage is shared.
        We create mappings for each test with reduced confidence.
        
        Args:
            xml_path: Path to jacoco.xml
            test_ids: List of tests that ran
            execution_mode: Batch execution mode
            
        Returns:
            Map of test_id -> TestCoverageMapping
        """
        # Parse the XML once
        base_mapping = self.parse(
            xml_path=xml_path,
            test_id="batch",
            execution_mode=execution_mode
        )
        
        # Calculate batch confidence
        batch_confidence = self.confidence_calculator.calculate(
            execution_mode=execution_mode,
            batch_size=len(test_ids)
        )
        
        # Create mapping for each test (with lower confidence)
        mappings = {}
        
        for test_id in test_ids:
            mappings[test_id] = TestCoverageMapping(
                test_id=test_id,
                test_framework="junit",
                covered_classes=base_mapping.covered_classes.copy(),
                covered_methods=base_mapping.covered_methods.copy(),
                covered_code_units=base_mapping.covered_code_units.copy(),
                coverage_type=CoverageType.INSTRUCTION,
                coverage_source=CoverageSource.JACOCO,
                execution_mode=execution_mode,
                confidence=batch_confidence
            )
        
        return mappings
    
    def _parse_counters(self, method_element: ET.Element) -> Dict[str, int]:
        """
        Parse JaCoCo counter elements.
        
        Returns dict with:
        - instruction_covered, instruction_total
        - line_covered, line_total
        - branch_covered, branch_total
        """
        counters = {}
        
        for counter in method_element.findall("counter"):
            counter_type = counter.attrib.get("type", "").lower()
            covered = int(counter.attrib.get("covered", 0))
            missed = int(counter.attrib.get("missed", 0))
            total = covered + missed
            
            if counter_type == "instruction":
                counters["instruction_covered"] = covered
                counters["instruction_missed"] = missed
                counters["instruction_total"] = total
            elif counter_type == "line":
                counters["line_covered"] = covered
                counters["line_missed"] = missed
                counters["line_total"] = total
            elif counter_type == "branch":
                counters["branch_covered"] = covered
                counters["branch_missed"] = missed
                counters["branch_total"] = total
        
        return counters
    
    def _calculate_coverage(self, covered: int, total: int) -> float:
        """Calculate coverage percentage."""
        if total == 0:
            return 0.0
        return covered / total
    
    def extract_covered_classes_only(self, xml_path: Path) -> Set[str]:
        """
        Quick extraction of covered classes only (no detailed parsing).
        
        Useful for fast impact queries.
        """
        if not xml_path.exists():
            return set()
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        covered_classes = set()
        
        for package in root.findall("package"):
            for cls in package.findall("class"):
                class_name = cls.attrib.get("name", "").replace("/", ".")
                
                # Check if class has any covered methods
                has_coverage = any(
                    int(counter.attrib.get("covered", 0)) > 0
                    for method in cls.findall("method")
                    for counter in method.findall("counter")
                )
                
                if has_coverage:
                    covered_classes.add(class_name)
        
        return covered_classes
    
    def extract_covered_methods_only(self, xml_path: Path) -> Set[str]:
        """
        Quick extraction of covered methods only.
        
        Returns set of "ClassName.methodName" strings.
        """
        if not xml_path.exists():
            return set()
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        covered_methods = set()
        
        for package in root.findall("package"):
            for cls in package.findall("class"):
                class_name = cls.attrib.get("name", "").replace("/", ".")
                
                for method in cls.findall("method"):
                    method_name = method.attrib.get("name", "")
                    
                    # Check if method is covered
                    covered = any(
                        int(counter.attrib.get("covered", 0)) > 0
                        for counter in method.findall("counter")
                    )
                    
                    if covered:
                        covered_methods.add(f"{class_name}.{method_name}")
        
        return covered_methods


class JaCoCoReportLocator:
    """
    Locate JaCoCo XML reports in a project.
    
    Common locations:
    - target/site/jacoco/jacoco.xml (Maven)
    - build/reports/jacoco/test/jacocoTestReport.xml (Gradle)
    """
    
    COMMON_PATHS = [
        "target/site/jacoco/jacoco.xml",
        "build/reports/jacoco/test/jacocoTestReport.xml",
        "build/jacoco/jacoco.xml",
    ]
    
    @classmethod
    def locate(cls, project_root: Path) -> Optional[Path]:
        """
        Locate JaCoCo XML report in project.
        
        Args:
            project_root: Project root directory
            
        Returns:
            Path to jacoco.xml if found, None otherwise
        """
        for path_str in cls.COMMON_PATHS:
            candidate = project_root / path_str
            if candidate.exists():
                return candidate
        
        return None
    
    @classmethod
    def find_report(cls, project_root: Path) -> Optional[Path]:
        """Alias for locate() for backward compatibility."""
        return cls.locate(project_root)
    
    @classmethod
    def get_common_locations(cls, project_root: Path) -> List[Path]:
        """Get list of common JaCoCo report locations."""
        return [project_root / path_str for path_str in cls.COMMON_PATHS]
    
    @classmethod
    def locate_all(cls, project_root: Path) -> List[Path]:
        """
        Locate all JaCoCo XML reports (for multi-module projects).
        
        Returns:
            List of paths to jacoco.xml files
        """
        reports = []
        
        # Search for jacoco.xml files
        for xml_file in project_root.rglob("jacoco.xml"):
            if xml_file.exists():
                reports.append(xml_file)
        
        return reports
