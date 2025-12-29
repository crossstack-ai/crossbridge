"""
Robot Framework Page Object detector and mapper.

Detects Page Object resources and maps them to test cases.
"""

from pathlib import Path
from typing import List, Set, Optional
import re

from ..common.impact_models import (
    PageObjectMetadata,
    TestToPageObjectMapping,
    PageObjectImpactMap,
    MappingSource,
    PageObjectReference
)


class RobotPageObjectDetector:
    """
    Detects Page Object resources in Robot Framework projects.
    
    Uses heuristics:
    - Resource files with "Page" in name
    - Keywords following Page Object pattern
    - Located in "resources" or "pages" directory
    """
    
    def __init__(self, source_root: str = "resources"):
        self.source_root = Path(source_root)
    
    def detect_page_objects(self) -> List[PageObjectMetadata]:
        """
        Scan project for Page Object resources.
        
        Returns:
            List of detected Page Object metadata.
        """
        page_objects = []
        
        if not self.source_root.exists():
            # Try alternative locations
            for alt_path in ["pages", "keywords", "robot/resources"]:
                if Path(alt_path).exists():
                    self.source_root = Path(alt_path)
                    break
        
        if not self.source_root.exists():
            return page_objects
        
        for robot_file in self.source_root.rglob("*.robot"):
            po_metadata = self._analyze_resource_file(robot_file)
            if po_metadata:
                page_objects.append(po_metadata)
        
        # Also check .resource files
        for resource_file in self.source_root.rglob("*.resource"):
            po_metadata = self._analyze_resource_file(resource_file)
            if po_metadata:
                page_objects.append(po_metadata)
        
        return page_objects
    
    def _analyze_resource_file(self, file_path: Path) -> Optional[PageObjectMetadata]:
        """
        Analyze a Robot resource file for Page Object patterns.
        
        Args:
            file_path: Path to the resource file.
            
        Returns:
            PageObjectMetadata if file is a Page Object, None otherwise.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            
            # Check if file name contains "Page"
            if not ("Page" in file_path.stem or "page" in file_path.stem):
                return None
            
            # Extract keywords
            keywords = self._extract_keywords(content)
            
            if not keywords:
                return None
            
            # Get relative module path
            module_path = str(file_path).replace("\\", "/")
            
            return PageObjectMetadata(
                class_name=file_path.stem,
                file_path=str(file_path),
                package="",
                base_class=None,
                methods=keywords,
                language="robot"
            )
        
        except Exception:
            return None
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keyword names from Robot Framework file."""
        keywords = []
        
        # Pattern to match keyword definitions
        keyword_pattern = r"^\s*([A-Z][A-Za-z0-9\s]+)\s*$"
        
        in_keywords_section = False
        
        for line in content.split("\n"):
            # Check for Keywords section
            if re.match(r"^\*+\s*Keywords\s*\*+", line, re.IGNORECASE):
                in_keywords_section = True
                continue
            
            # Check for other sections
            if re.match(r"^\*+\s*\w+\s*\*+", line):
                in_keywords_section = False
                continue
            
            # Extract keyword if in Keywords section
            if in_keywords_section:
                match = re.match(keyword_pattern, line)
                if match:
                    keyword = match.group(1).strip()
                    if keyword and not keyword.startswith("#"):
                        keywords.append(keyword)
        
        return keywords


class RobotTestToPageObjectMapper:
    """
    Maps Robot Framework tests to Page Objects they use.
    
    Detects:
    - Resource imports
    - Keyword usage from Page Object resources
    """
    
    def __init__(self, test_root: str = "tests", 
                 known_page_objects: Optional[Set[str]] = None):
        self.test_root = Path(test_root)
        self.known_page_objects = known_page_objects or set()
    
    def map_tests_to_page_objects(self) -> PageObjectImpactMap:
        """
        Scan all tests and create impact map.
        
        Returns:
            Complete impact map.
        """
        impact_map = PageObjectImpactMap(project_root=str(self.test_root.parent))
        
        if not self.test_root.exists():
            return impact_map
        
        for robot_file in self.test_root.rglob("*.robot"):
            mappings = self._analyze_test_file(robot_file)
            for mapping in mappings:
                impact_map.add_mapping(mapping)
        
        return impact_map
    
    def _analyze_test_file(self, test_file: Path) -> List[TestToPageObjectMapping]:
        """
        Analyze a test file for Page Object usage.
        
        Args:
            test_file: Path to the test file.
            
        Returns:
            List of test-to-PO mappings.
        """
        try:
            content = test_file.read_text(encoding="utf-8", errors="ignore")
            
            # Extract imported resources
            imported_pos = self._extract_resource_imports(content)
            
            # Extract test cases
            test_cases = self._extract_test_cases(content, test_file)
            
            mappings = []
            
            for test_name, test_content, line_num in test_cases:
                mapping = TestToPageObjectMapping(
                    test_id=f"{test_file.stem}.{test_name}",
                    test_file=str(test_file),
                    mapping_source=MappingSource.STATIC_AST
                )
                
                # Add imported Page Objects
                for po_name in imported_pos:
                    if self._is_page_object(po_name):
                        mapping.add_page_object(
                            po_name,
                            usage_type="resource_import",
                            line_number=line_num
                        )
                
                # Add Page Objects used in test
                for po_name in self._find_used_page_objects(test_content):
                    if po_name not in mapping.page_objects:
                        mapping.add_page_object(
                            po_name,
                            usage_type="keyword_usage",
                            line_number=line_num
                        )
                
                if mapping.page_objects:
                    mappings.append(mapping)
            
            return mappings
        
        except Exception:
            return []
    
    def _extract_resource_imports(self, content: str) -> Set[str]:
        """Extract resource file imports."""
        resources = set()
        
        # Pattern: Resource    path/to/PageName.robot
        resource_pattern = r"^Resource\s+.*?([A-Z]\w*Page)\.(?:robot|resource)"
        
        for line in content.split("\n"):
            match = re.search(resource_pattern, line, re.IGNORECASE)
            if match:
                resources.add(match.group(1))
        
        return resources
    
    def _extract_test_cases(self, content: str, file_path: Path) -> List[tuple]:
        """Extract test case names and content."""
        test_cases = []
        
        in_test_section = False
        current_test = None
        current_content = []
        current_line = 0
        
        for line_num, line in enumerate(content.split("\n"), 1):
            # Check for Test Cases section
            if re.match(r"^\*+\s*Test\s+Cases\s*\*+", line, re.IGNORECASE):
                in_test_section = True
                continue
            
            # Check for other sections
            if re.match(r"^\*+\s*\w+\s*\*+", line):
                if current_test:
                    test_cases.append((current_test, "\n".join(current_content), current_line))
                in_test_section = False
                current_test = None
                current_content = []
                continue
            
            # Extract test case
            if in_test_section:
                # Test case starts at column 0 (no leading whitespace)
                if line and not line[0].isspace() and not line.startswith("#"):
                    if current_test:
                        test_cases.append((current_test, "\n".join(current_content), current_line))
                    current_test = line.strip()
                    current_content = []
                    current_line = line_num
                elif current_test and line.strip():
                    current_content.append(line)
        
        # Add last test
        if current_test:
            test_cases.append((current_test, "\n".join(current_content), current_line))
        
        return test_cases
    
    def _find_used_page_objects(self, test_content: str) -> Set[str]:
        """Find Page Object names used in test content."""
        used_pos = set()
        
        for po_name in self.known_page_objects:
            # Check if Page Object name appears in test
            if po_name in test_content:
                used_pos.add(po_name)
        
        return used_pos
    
    def _is_page_object(self, name: str) -> bool:
        """Check if a name is likely a Page Object."""
        if self.known_page_objects:
            return name in self.known_page_objects
        
        return name.endswith("Page")


def create_robot_impact_map(project_root: str,
                            source_root: str = "resources",
                            test_root: str = "tests") -> PageObjectImpactMap:
    """
    Create complete Page Object → Test impact map for a Robot Framework project.
    
    Args:
        project_root: Root directory of the project.
        source_root: Resource directory (for Page Objects).
        test_root: Test code directory.
        
    Returns:
        Complete impact map.
    """
    # Step 1: Detect Page Objects
    detector = RobotPageObjectDetector(f"{project_root}/{source_root}")
    page_objects = detector.detect_page_objects()
    
    # Extract Page Object names
    po_names = {po.class_name for po in page_objects}
    
    # Step 2: Map tests to Page Objects
    mapper = RobotTestToPageObjectMapper(
        f"{project_root}/{test_root}",
        known_page_objects=po_names
    )
    
    return mapper.map_tests_to_page_objects()
