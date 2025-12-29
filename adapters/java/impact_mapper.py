"""
Java Page Object detector and mapper.

Detects Page Object classes and maps them to tests using AST analysis.
"""

from pathlib import Path
from typing import List, Set, Optional
import re

from ..common.impact_models import (
    PageObjectMetadata,
    TestToPageObjectMapping,
    PageObjectImpactMap,
    MappingSource
)


class JavaPageObjectDetector:
    """
    Detects Page Object classes in Java projects.
    
    Uses heuristics:
    - Class name ends with "Page"
    - Extends BasePage or similar
    - Located in "pages" package
    """
    
    def __init__(self, source_root: str = "src/main/java"):
        self.source_root = Path(source_root)
    
    def detect_page_objects(self) -> List[PageObjectMetadata]:
        """
        Scan project for Page Object classes.
        
        Returns:
            List of detected Page Object metadata.
        """
        page_objects = []
        
        if not self.source_root.exists():
            return page_objects
        
        for java_file in self.source_root.rglob("*.java"):
            po_metadata = self._analyze_file(java_file)
            if po_metadata and po_metadata.is_page_object():
                page_objects.append(po_metadata)
        
        return page_objects
    
    def _analyze_file(self, java_file: Path) -> Optional[PageObjectMetadata]:
        """Analyze a Java file for Page Object patterns."""
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
            
            # Extract package
            package_match = re.search(r"package\s+([\w.]+);", content)
            package = package_match.group(1) if package_match else ""
            
            # Extract class name
            class_match = re.search(r"(?:public\s+)?class\s+(\w+)", content)
            if not class_match:
                return None
            
            class_name = class_match.group(1)
            qualified_name = f"{package}.{class_name}" if package else class_name
            
            # Extract base class
            extends_match = re.search(r"class\s+\w+\s+extends\s+(\w+)", content)
            base_class = extends_match.group(1) if extends_match else None
            
            # Extract public methods
            methods = re.findall(r"public\s+\w+\s+(\w+)\s*\(", content)
            
            return PageObjectMetadata(
                class_name=qualified_name,
                file_path=str(java_file),
                package=package,
                base_class=base_class,
                methods=methods,
                language="java"
            )
            
        except Exception:
            return None


class JavaTestToPageObjectMapper:
    """
    Maps Java tests to Page Objects they use.
    
    Detects:
    - Imports of Page Object classes
    - Instantiations (new LoginPage())
    - Field declarations
    - Method calls on Page Objects
    """
    
    def __init__(self, test_root: str = "src/test/java", 
                 known_page_objects: Optional[Set[str]] = None):
        self.test_root = Path(test_root)
        self.known_page_objects = known_page_objects or set()
    
    def map_tests_to_page_objects(self) -> PageObjectImpactMap:
        """
        Scan all tests and create impact map.
        
        Returns:
            Complete Page Object impact map.
        """
        impact_map = PageObjectImpactMap(project_root=str(self.test_root.parent.parent))
        
        if not self.test_root.exists():
            return impact_map
        
        for java_file in self.test_root.rglob("*.java"):
            mappings = self._analyze_test_file(java_file)
            for mapping in mappings:
                impact_map.add_mapping(mapping)
        
        return impact_map
    
    def _analyze_test_file(self, test_file: Path) -> List[TestToPageObjectMapping]:
        """Analyze a test file for Page Object usage."""
        try:
            content = test_file.read_text(encoding="utf-8", errors="ignore")
            
            # Extract package and class
            package_match = re.search(r"package\s+([\w.]+);", content)
            package = package_match.group(1) if package_match else ""
            
            class_match = re.search(r"(?:public\s+)?class\s+(\w+)", content)
            if not class_match:
                return []
            
            class_name = class_match.group(1)
            qualified_class = f"{package}.{class_name}" if package else class_name
            
            # Find test methods
            test_methods = self._find_test_methods(content)
            
            mappings = []
            for method_name, line_num in test_methods:
                test_id = f"{qualified_class}.{method_name}"
                mapping = TestToPageObjectMapping(
                    test_id=test_id,
                    test_file=str(test_file),
                    mapping_source=MappingSource.STATIC_AST
                )
                
                # Detect Page Object usage
                self._detect_imports(content, mapping)
                self._detect_instantiations(content, mapping)
                self._detect_fields(content, mapping)
                
                if mapping.page_objects:  # Only add if POs were found
                    mappings.append(mapping)
            
            return mappings
            
        except Exception:
            return []
    
    def _find_test_methods(self, content: str) -> List[tuple]:
        """Find test methods with line numbers."""
        test_methods = []
        
        # Find @Test annotations
        for match in re.finditer(r"@Test[\s\S]*?(?:public\s+)?void\s+(\w+)\s*\(", content):
            method_name = match.group(1)
            # Approximate line number
            line_num = content[:match.start()].count('\n') + 1
            test_methods.append((method_name, line_num))
        
        return test_methods
    
    def _detect_imports(self, content: str, mapping: TestToPageObjectMapping):
        """Detect imported Page Object classes."""
        import_pattern = r"import\s+([\w.]+);"
        
        for match in re.finditer(import_pattern, content):
            import_stmt = match.group(1)
            class_name = import_stmt.split(".")[-1]
            
            # Check if it's a Page Object
            if self._is_page_object_class(class_name, import_stmt):
                mapping.add_page_object(
                    import_stmt,
                    usage_type="import",
                    line_number=content[:match.start()].count('\n') + 1
                )
    
    def _detect_instantiations(self, content: str, mapping: TestToPageObjectMapping):
        """Detect Page Object instantiations."""
        instantiation_pattern = r"new\s+(\w+)\s*\("
        
        for match in re.finditer(instantiation_pattern, content):
            class_name = match.group(1)
            
            if self._is_page_object_class(class_name):
                mapping.add_page_object(
                    class_name,
                    usage_type="instantiation",
                    line_number=content[:match.start()].count('\n') + 1
                )
    
    def _detect_fields(self, content: str, mapping: TestToPageObjectMapping):
        """Detect Page Object field declarations."""
        field_pattern = r"(?:private|protected|public)\s+(\w+)\s+(\w+)\s*;"
        
        for match in re.finditer(field_pattern, content):
            class_name = match.group(1)
            
            if self._is_page_object_class(class_name):
                mapping.add_page_object(
                    class_name,
                    usage_type="field",
                    line_number=content[:match.start()].count('\n') + 1
                )
    
    def _is_page_object_class(self, class_name: str, qualified_name: str = "") -> bool:
        """Check if a class is likely a Page Object."""
        # Check against known Page Objects
        if self.known_page_objects:
            if class_name in self.known_page_objects or qualified_name in self.known_page_objects:
                return True
        
        # Heuristic: ends with "Page"
        return class_name.endswith("Page")


def create_impact_map(project_root: str, 
                     source_root: str = "src/main/java",
                     test_root: str = "src/test/java") -> PageObjectImpactMap:
    """
    Create complete Page Object → Test impact map for a Java project.
    
    Args:
        project_root: Root directory of the project.
        source_root: Source code directory (for Page Objects).
        test_root: Test code directory.
        
    Returns:
        Complete impact map.
        
    Example:
        >>> impact_map = create_impact_map(".")
        >>> impacted_tests = impact_map.get_impacted_tests("LoginPage")
        >>> print(f"Tests impacted: {impacted_tests}")
    """
    # Step 1: Detect Page Objects
    detector = JavaPageObjectDetector(f"{project_root}/{source_root}")
    page_objects = detector.detect_page_objects()
    
    # Extract Page Object class names
    po_classes = {po.class_name for po in page_objects}
    po_simple_names = {po.get_simple_name() for po in page_objects}
    all_po_names = po_classes | po_simple_names
    
    # Step 2: Map tests to Page Objects
    mapper = JavaTestToPageObjectMapper(
        f"{project_root}/{test_root}",
        known_page_objects=all_po_names
    )
    
    return mapper.map_tests_to_page_objects()
